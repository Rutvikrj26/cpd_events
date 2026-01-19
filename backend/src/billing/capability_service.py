"""
Centralized Capability Service for subscription-based access control.

This service is the SINGLE SOURCE OF TRUTH for:
- What users can do (capabilities based on plan)
- How much they can do (limits and quotas)
- Plan transitions (upgrade/downgrade)
- Access status (trial, grace period, blocked)

Design Principles:
1. DRY: All subscription logic in one place
2. Atomic: Limit checks and increments are transactional
3. Default-deny: Missing subscription = no access; missing limits = unlimited
4. Type-safe: Uses CapabilityResult for all responses

Usage:
    from billing.capability_service import capability_service

    # Check and increment atomically
    result = capability_service.check_and_increment_event(user)
    if not result.allowed:
        raise PermissionDenied(result.error_message)

    # Simple capability check
    if capability_service.can_create_events(user):
        ...
"""

import logging
from typing import TYPE_CHECKING, Optional

from django.db import transaction

from billing.types import AccessStatus, CapabilityResult, ErrorCodes, PlanCapabilities, UsageSummary
from common.messages import CAPABILITY_MESSAGES

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()

logger = logging.getLogger(__name__)


class CapabilityService:
    """
    Centralized service for subscription-based capability checks.

    All subscription access, capability checks, limit enforcement,
    and plan transitions should go through this service.
    """

    # =========================================================================
    # Plan Configuration
    # =========================================================================

    # Plans that allow event creation
    EVENT_CREATION_PLANS = {"organizer", "pro"}

    # Plans that allow course creation
    COURSE_CREATION_PLANS = {"lms", "pro"}

    # Plans that allow certificate issuance
    CERTIFICATE_PLANS = {"organizer", "lms", "pro"}

    # =========================================================================
    # Subscription Access (DRY: replaces 69+ scattered access patterns)
    # =========================================================================

    @staticmethod
    def get_subscription(user) -> Optional["Subscription"]:
        """
        Get user's subscription or None.

        This is the canonical way to access a user's subscription.
        Returns None if user has no subscription (fallback to unlimited).

        IMPORTANT: OneToOneField reverse relations raise DoesNotExist when accessed
        if the related object doesn't exist. We must use try/except, not getattr.
        """
        from billing.models import Subscription

        try:
            return Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return None

    @staticmethod
    def get_or_create_subscription(user) -> "Subscription":
        """
        Get or create subscription for user.

        New subscriptions default to ATTENDEE plan with ACTIVE status.
        """
        from billing.models import Subscription

        subscription, created = Subscription.objects.get_or_create(
            user=user,
            defaults={
                "plan": Subscription.Plan.ATTENDEE,
                "status": Subscription.Status.ACTIVE,
            },
        )
        if created:
            logger.info(f"Created default subscription for user {user.id}")
        return subscription

    @classmethod
    def get_limits(cls, user) -> dict:
        """
        Get effective limits for a user.

        Priority:
        1. StripeProduct limits (database-driven)
        2. PLAN_LIMITS from config (code fallback)

        Returns dict with None values meaning unlimited.
        If no subscription exists, returns strict 0 limits (no access).
        """
        subscription = cls.get_subscription(user)

        if not subscription:
            # No subscription = no access
            return {
                "events_per_month": 0,
                "courses_per_month": 0,
                "certificates_per_month": 0,
                "max_attendees_per_event": 0,
            }

        # subscription.limits already handles StripeProduct -> PLAN_LIMITS fallback
        limits = subscription.limits

        # Ensure all keys exist with None as unlimited fallback
        return {
            "events_per_month": limits.get("events_per_month"),
            "courses_per_month": limits.get("courses_per_month"),
            "certificates_per_month": limits.get("certificates_per_month"),
            "max_attendees_per_event": limits.get("max_attendees_per_event"),
        }

    # =========================================================================
    # Capability Checks (DRY: replaces hardcoded plan checks)
    # =========================================================================

    @classmethod
    def can_create_events(cls, user) -> bool:
        """
        Check if user can create events based on their plan.

        Returns True if:
        - Plan is in EVENT_CREATION_PLANS (organizer, pro)
        - Subscription exists
        """
        subscription = cls.get_subscription(user)

        if not subscription:
            # No subscription = no access
            return False

        return subscription.plan.lower() in cls.EVENT_CREATION_PLANS

    @classmethod
    def can_create_courses(cls, user) -> bool:
        """
        Check if user can create courses based on their plan.

        Returns True if:
        - Plan is in COURSE_CREATION_PLANS (lms, pro)
        - Subscription exists
        """
        subscription = cls.get_subscription(user)

        if not subscription:
            # No subscription = no access
            return False

        return subscription.plan.lower() in cls.COURSE_CREATION_PLANS

    @classmethod
    def can_issue_certificates(cls, user) -> bool:
        """
        Check if user can issue certificates based on their plan.

        Returns True if:
        - Plan is in CERTIFICATE_PLANS (organizer, lms, pro)
        - Subscription exists
        """
        subscription = cls.get_subscription(user)

        if not subscription:
            return False

        return subscription.plan.lower() in cls.CERTIFICATE_PLANS

    @classmethod
    def has_active_subscription(cls, user) -> bool:
        """
        Check if user has an active (non-blocked) subscription.

        Returns True if:
        - Subscription exists AND
        - Subscription is active or trialing
        """
        subscription = cls.get_subscription(user)

        if not subscription:
            return False

        return subscription.is_active

    # =========================================================================
    # Access Status (comprehensive status for frontend)
    # =========================================================================

    @classmethod
    def get_access_status(cls, user) -> AccessStatus:
        """
        Get comprehensive access status for a user.

        Used by frontend to display appropriate UI states.
        """
        subscription = cls.get_subscription(user)

        if not subscription:
            # No subscription = no access
            return AccessStatus(
                is_active=False,
                is_trialing=False,
                is_trial_expired=False,
                is_in_grace_period=False,
                is_access_blocked=True,
                days_until_trial_ends=None,
                plan="none",
                status="none",
                has_payment_method=False,
            )

        has_payment_method = False
        if hasattr(user, "payment_methods"):
            has_payment_method = user.payment_methods.exists()

        return AccessStatus(
            is_active=subscription.is_active,
            is_trialing=subscription.is_trialing,
            is_trial_expired=subscription.is_trial_expired,
            is_in_grace_period=subscription.is_in_grace_period,
            is_access_blocked=subscription.is_access_blocked,
            days_until_trial_ends=subscription.days_until_trial_ends,
            plan=subscription.plan,
            status=subscription.status,
            has_payment_method=has_payment_method,
        )

    @classmethod
    def get_usage_summary(cls, user) -> UsageSummary:
        """Get usage summary for a user's current billing period."""
        subscription = cls.get_subscription(user)
        return UsageSummary.from_subscription(subscription)

    # =========================================================================
    # Limit Enforcement (Atomic check + increment)
    # =========================================================================

    @classmethod
    def check_and_increment_event(cls, user) -> CapabilityResult:
        """
        Atomically check event limit and increment counter.

        This is the ONLY way to create events - ensures:
        1. Access is not blocked (trial expired, etc.)
        2. User has event creation capability
        3. Limit is not exceeded
        4. Counter is incremented atomically

        Returns CapabilityResult with allowed=True if successful.
        """
        from billing.models import Subscription

        subscription = cls.get_subscription(user)

        # No subscription = no access
        if not subscription:
            return CapabilityResult.denied(
                ErrorCodes.NO_SUBSCRIPTION,
                CAPABILITY_MESSAGES["subscription_required"],
            )

        # Check plan capability first
        if subscription.plan.lower() not in cls.EVENT_CREATION_PLANS:
            return CapabilityResult.denied(
                ErrorCodes.PLAN_UPGRADE_REQUIRED,
                CAPABILITY_MESSAGES["event_creation_required"],
            )

        # Use atomic transaction for check + increment
        with transaction.atomic():
            # Lock the subscription row
            sub = Subscription.objects.select_for_update().get(pk=subscription.pk)

            # Check access status
            if sub.is_access_blocked:
                return CapabilityResult.denied(
                    ErrorCodes.ACCESS_BLOCKED,
                    CAPABILITY_MESSAGES["subscription_expired"],
                )

            if sub.is_trial_expired:
                return CapabilityResult.denied(
                    ErrorCodes.TRIAL_EXPIRED,
                    CAPABILITY_MESSAGES["trial_expired"],
                )

            # Check limit (None = unlimited)
            limit = sub.limits.get("events_per_month")
            current_usage = sub.events_created_this_period

            if limit is not None and current_usage >= limit:
                return CapabilityResult.denied(
                    ErrorCodes.EVENT_LIMIT_REACHED,
                    CAPABILITY_MESSAGES["event_limit_reached"].format(limit=limit),
                    limit=limit,
                    current_usage=current_usage,
                )

            # Increment counter
            sub.events_created_this_period += 1
            sub.save(update_fields=["events_created_this_period", "updated_at"])

            return CapabilityResult.success(
                limit=limit,
                current_usage=sub.events_created_this_period,
            )

    @classmethod
    def check_and_increment_course(cls, user) -> CapabilityResult:
        """
        Atomically check course limit and increment counter.

        Same pattern as check_and_increment_event but for courses.
        """
        from billing.models import Subscription

        subscription = cls.get_subscription(user)

        # No subscription = no access
        if not subscription:
            return CapabilityResult.denied(
                ErrorCodes.NO_SUBSCRIPTION,
                CAPABILITY_MESSAGES["subscription_required"],
            )

        # Check plan capability
        if subscription.plan.lower() not in cls.COURSE_CREATION_PLANS:
            return CapabilityResult.denied(
                ErrorCodes.PLAN_UPGRADE_REQUIRED,
                CAPABILITY_MESSAGES["course_creation_required"],
            )

        with transaction.atomic():
            sub = Subscription.objects.select_for_update().get(pk=subscription.pk)

            if sub.is_access_blocked:
                return CapabilityResult.denied(
                    ErrorCodes.ACCESS_BLOCKED,
                    CAPABILITY_MESSAGES["subscription_expired"],
                )

            if sub.is_trial_expired:
                return CapabilityResult.denied(
                    ErrorCodes.TRIAL_EXPIRED,
                    CAPABILITY_MESSAGES["trial_expired"],
                )

            limit = sub.limits.get("courses_per_month")
            current_usage = sub.courses_created_this_period

            if limit is not None and current_usage >= limit:
                return CapabilityResult.denied(
                    ErrorCodes.COURSE_LIMIT_REACHED,
                    CAPABILITY_MESSAGES["course_limit_reached"].format(limit=limit),
                    limit=limit,
                    current_usage=current_usage,
                )

            sub.courses_created_this_period += 1
            sub.save(update_fields=["courses_created_this_period", "updated_at"])

            return CapabilityResult.success(
                limit=limit,
                current_usage=sub.courses_created_this_period,
            )

    @classmethod
    def check_and_increment_certificate(cls, user, count: int = 1) -> CapabilityResult:
        """
        Atomically check certificate limit and increment counter.

        Args:
            user: The user issuing certificates
            count: Number of certificates being issued (for bulk operations)
        """
        from billing.models import Subscription

        subscription = cls.get_subscription(user)

        # No subscription = no access
        if not subscription:
            return CapabilityResult.denied(
                ErrorCodes.NO_SUBSCRIPTION,
                CAPABILITY_MESSAGES["subscription_required"],
            )

        # Check plan capability
        if subscription.plan.lower() not in cls.CERTIFICATE_PLANS:
            return CapabilityResult.denied(
                ErrorCodes.PLAN_UPGRADE_REQUIRED,
                CAPABILITY_MESSAGES["certificate_issuance_required"],
            )

        with transaction.atomic():
            sub = Subscription.objects.select_for_update().get(pk=subscription.pk)

            if sub.is_access_blocked:
                return CapabilityResult.denied(
                    ErrorCodes.ACCESS_BLOCKED,
                    CAPABILITY_MESSAGES["subscription_expired"],
                )

            if sub.is_trial_expired:
                return CapabilityResult.denied(
                    ErrorCodes.TRIAL_EXPIRED,
                    CAPABILITY_MESSAGES["trial_expired"],
                )

            limit = sub.limits.get("certificates_per_month")
            current_usage = sub.certificates_issued_this_period

            if limit is not None and (current_usage + count) > limit:
                return CapabilityResult.denied(
                    ErrorCodes.CERTIFICATE_LIMIT_REACHED,
                    CAPABILITY_MESSAGES["certificate_limit_reached"].format(limit=limit),
                    limit=limit,
                    current_usage=current_usage,
                )

            sub.certificates_issued_this_period += count
            sub.save(update_fields=["certificates_issued_this_period", "updated_at"])

            return CapabilityResult.success(
                limit=limit,
                current_usage=sub.certificates_issued_this_period,
            )

    @classmethod
    def check_attendee_limit(cls, user, event) -> CapabilityResult:
        """
        Check if an event can accept more attendees based on plan limits.

        Checks both:
        1. Event-level max_attendees (set by organizer)
        2. Plan-level max_attendees_per_event (subscription limit)

        Args:
            user: The event owner
            event: The event to check
        """
        # Get plan limit
        limits = cls.get_limits(user)
        plan_limit = limits.get("max_attendees_per_event")

        # Get event-level limit
        event_limit = event.max_attendees

        # Determine effective limit (most restrictive)
        if plan_limit is None and event_limit is None:
            # Both unlimited
            return CapabilityResult.success()

        if plan_limit is None:
            effective_limit = event_limit
        elif event_limit is None:
            effective_limit = plan_limit
        else:
            effective_limit = min(plan_limit, event_limit)

        # Get current registration count
        from registrations.models import Registration

        current_count = Registration.objects.filter(
            event=event,
            status=Registration.Status.CONFIRMED,
            deleted_at__isnull=True,
        ).count()

        if current_count >= effective_limit:
            return CapabilityResult.denied(
                ErrorCodes.ATTENDEE_LIMIT_REACHED,
                CAPABILITY_MESSAGES["attendee_limit_reached"].format(limit=effective_limit),
                limit=effective_limit,
                current_usage=current_count,
            )

        return CapabilityResult.success(
            limit=effective_limit,
            current_usage=current_count,
        )

    # =========================================================================
    # Plan Transitions
    # =========================================================================

    @classmethod
    def downgrade_to_attendee(cls, user, skip_content_check: bool = False) -> CapabilityResult:
        """
        Downgrade user to attendee plan.

        Args:
            user: User to downgrade
            skip_content_check: If True, skip checking for active content
                               (used by automated processes like trial expiration)

        Returns:
            CapabilityResult indicating success or failure
        """
        from billing.models import Subscription

        subscription = cls.get_subscription(user)

        if not subscription:
            # Create attendee subscription
            cls.get_or_create_subscription(user)
            return CapabilityResult.success()

        if subscription.plan.lower() == "attendee":
            return CapabilityResult.denied(
                ErrorCodes.ALREADY_ON_PLAN,
                CAPABILITY_MESSAGES["already_on_plan"].format(plan="Attendee"),
            )

        # Check for active content unless skipped
        if not skip_content_check:
            from events.models import Event
            from learning.models import Course

            has_active_events = Event.objects.filter(
                owner=user,
                status__in=[Event.Status.DRAFT, Event.Status.PUBLISHED, Event.Status.LIVE],
                deleted_at__isnull=True,
            ).exists()

            has_active_courses = Course.objects.filter(
                owner=user,
                status__in=[Course.Status.DRAFT, Course.Status.PUBLISHED],
            ).exists()

            if has_active_events or has_active_courses:
                return CapabilityResult.denied(
                    ErrorCodes.ACTIVE_CONTENT_EXISTS,
                    CAPABILITY_MESSAGES["active_content_exists"],
                )

        # Perform downgrade atomically
        with transaction.atomic():
            sub = Subscription.objects.select_for_update().get(pk=subscription.pk)
            previous_plan = sub.plan
            sub.plan = Subscription.Plan.ATTENDEE
            sub.save(update_fields=["plan", "updated_at"])

            logger.info(f"User {user.id} downgraded from {previous_plan} to attendee")

        return CapabilityResult.success()

    @classmethod
    def upgrade_to_plan(cls, user, plan: str) -> CapabilityResult:
        """
        Upgrade user to a specified plan.

        Note: This only updates the local subscription record.
        For Stripe integration, use billing.services.stripe_service.

        Args:
            user: User to upgrade
            plan: Target plan (organizer, lms, pro)

        Returns:
            CapabilityResult indicating success or failure
        """
        from billing.models import Subscription

        valid_plans = {"organizer", "lms", "pro"}
        plan_lower = plan.lower()

        if plan_lower not in valid_plans:
            return CapabilityResult.denied(
                ErrorCodes.INVALID_PLAN,
                CAPABILITY_MESSAGES["invalid_plan"].format(plan=plan),
            )

        subscription = cls.get_or_create_subscription(user)

        if subscription.plan.lower() == plan_lower:
            return CapabilityResult.denied(
                ErrorCodes.ALREADY_ON_PLAN,
                CAPABILITY_MESSAGES["already_on_plan"].format(plan=plan),
            )

        with transaction.atomic():
            sub = Subscription.objects.select_for_update().get(pk=subscription.pk)
            previous_plan = sub.plan
            sub.plan = plan_lower
            sub.save(update_fields=["plan", "updated_at"])

            logger.info(f"User {user.id} upgraded from {previous_plan} to {plan_lower}")

        return CapabilityResult.success()


# Singleton instance for convenience
capability_service = CapabilityService()
