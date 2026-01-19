import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from billing.capability_service import capability_service
from billing.models import Subscription
from billing.types import ErrorCodes, AccessStatus, CapabilityResult
from events.models import Event

User = get_user_model()


@pytest.mark.django_db
class TestCapabilityService:
    """Tests for the Centralized Capability Service."""

    @pytest.fixture
    def user(self):
        """User fixture without subscription - deletes auto-created subscription."""
        user = User.objects.create_user(email="test@example.com", password="password", first_name="Test", last_name="User")
        # Delete the auto-created subscription from the signal
        Subscription.objects.filter(user=user).delete()
        # Return fresh instance to ensure no cached subscription
        return User.objects.get(pk=user.pk)

    @pytest.fixture
    def organizer_user(self):
        """User fixture with organizer plan subscription."""
        user = User.objects.create_user(email="organizer@example.com", password="password", first_name="Org", last_name="User")
        # Use .filter().update() to bypass model logic and force DB update
        Subscription.objects.filter(user=user).update(plan="organizer", status="active")
        # Return fresh instance to ensure correct subscription is loaded
        return User.objects.get(pk=user.pk)

    @pytest.fixture
    def attendee_user(self):
        """User fixture with attendee plan subscription."""
        user = User.objects.create_user(
            email="attendee@example.com", password="password", first_name="Attendee", last_name="User"
        )
        # Use .filter().update() to bypass model logic and force DB update
        Subscription.objects.filter(user=user).update(plan="attendee", status="active")
        # Return fresh instance to ensure correct subscription is loaded
        return User.objects.get(pk=user.pk)

    # =========================================================================
    # Subscription Access Tests
    # =========================================================================

    def test_get_subscription_exists(self, organizer_user):
        """Should return subscription object if it exists."""
        sub = capability_service.get_subscription(organizer_user)
        assert sub is not None
        assert sub.plan == "organizer"

    def test_get_subscription_none(self, user):
        """Should return None if no subscription exists."""
        # Fixture already deleted the subscription, verify it's gone
        try:
            _ = user.subscription
            assert False, "Expected subscription to not exist"
        except Subscription.DoesNotExist:
            pass  # Expected

        sub = capability_service.get_subscription(user)
        assert sub is None

    def test_get_or_create_subscription(self, user):
        """Should create default attendee subscription if missing."""
        # Verify no subscription exists (fixture already deleted it)
        try:
            _ = user.subscription
            assert False, "Expected subscription to not exist"
        except Subscription.DoesNotExist:
            pass  # Expected

        sub = capability_service.get_or_create_subscription(user)

        assert sub is not None
        assert sub.plan == "attendee"
        assert sub.status == "active"

        # Verify it persists
        user = User.objects.get(pk=user.pk)
        assert user.subscription.pk == sub.pk

    # =========================================================================
    # Limit Tests
    # =========================================================================

    def test_get_limits_no_subscription(self, user):
        """Should return strict 0 limits if no subscription."""
        limits = capability_service.get_limits(user)

        assert limits["events_per_month"] == 0
        assert limits["courses_per_month"] == 0
        assert limits["certificates_per_month"] == 0

    def test_get_limits_with_subscription(self, organizer_user):
        """Should return plan limits."""
        # Organizer plan usually has limits, but fallback to None (unlimited) for now
        # based on code logic if StripeProduct doesn't exist.
        # Let's ensure structure is correct at least.
        limits = capability_service.get_limits(organizer_user)
        assert "events_per_month" in limits
        assert "max_attendees_per_event" in limits

    # =========================================================================
    # Boolean Capability Checks
    # =========================================================================

    def test_can_create_events_no_subscription(self, user):
        """Should return False if no subscription."""
        assert capability_service.can_create_events(user) is False

    def test_can_create_events_attendee(self, attendee_user):
        """Should return False for attendee plan."""
        assert capability_service.can_create_events(attendee_user) is False

    def test_can_create_events_organizer(self, organizer_user):
        """Should return True for organizer plan."""
        assert capability_service.can_create_events(organizer_user) is True

    def test_has_active_subscription_no_sub(self, user):
        """Should return False if no subscription."""
        assert capability_service.has_active_subscription(user) is False

    def test_has_active_subscription_active(self, organizer_user):
        """Should return True if active."""
        assert capability_service.has_active_subscription(organizer_user) is True

    def test_has_active_subscription_canceled(self, organizer_user):
        """Should return False if canceled/expired."""
        sub = organizer_user.subscription
        sub.status = "canceled"
        sub.save()
        assert capability_service.has_active_subscription(organizer_user) is False

    # =========================================================================
    # Atomic Check & Increment Tests
    # =========================================================================

    def test_check_and_increment_event_no_subscription(self, user):
        """Should fail with NO_SUBSCRIPTION error."""
        result = capability_service.check_and_increment_event(user)

        assert result.allowed is False
        assert result.error_code == ErrorCodes.NO_SUBSCRIPTION

    def test_check_and_increment_event_wrong_plan(self, attendee_user):
        """Should fail with PLAN_UPGRADE_REQUIRED."""
        result = capability_service.check_and_increment_event(attendee_user)

        assert result.allowed is False
        assert result.error_code == ErrorCodes.PLAN_UPGRADE_REQUIRED

    def test_check_and_increment_event_success(self, organizer_user):
        """Should succeed and increment counter."""
        initial_count = organizer_user.subscription.events_created_this_period

        result = capability_service.check_and_increment_event(organizer_user)

        assert result.allowed is True

        # Verify increment
        organizer_user.subscription.refresh_from_db()
        assert organizer_user.subscription.events_created_this_period == initial_count + 1

    def test_check_and_increment_limit_reached(self, organizer_user):
        """Should fail if limit reached."""
        # Manually set a limit
        sub = organizer_user.subscription
        sub.limits_override = {"events_per_month": 5}
        sub.events_created_this_period = 5
        sub.save()

        result = capability_service.check_and_increment_event(organizer_user)

        assert result.allowed is False
        assert result.error_code == ErrorCodes.EVENT_LIMIT_REACHED

    # =========================================================================
    # Transition Tests
    # =========================================================================

    def test_downgrade_to_attendee_no_sub(self, user):
        """Should create attendee sub if none exists."""
        result = capability_service.downgrade_to_attendee(user)

        assert result.allowed is True
        user.refresh_from_db()
        assert user.subscription.plan == "attendee"

    def test_downgrade_to_attendee_success(self, organizer_user):
        """Should successfully downgrade."""
        result = capability_service.downgrade_to_attendee(organizer_user)

        assert result.allowed is True
        organizer_user.subscription.refresh_from_db()
        assert organizer_user.subscription.plan == "attendee"

    def test_downgrade_blocked_by_content(self, organizer_user):
        """Should fail if user has active content."""
        # Create an active event
        Event.objects.create(
            owner=organizer_user, title="Active Event", starts_at=timezone.now(), duration_minutes=60, status="published"
        )

        result = capability_service.downgrade_to_attendee(organizer_user)

        assert result.allowed is False
        assert result.error_code == ErrorCodes.ACTIVE_CONTENT_EXISTS
