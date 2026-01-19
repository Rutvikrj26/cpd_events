"""
Stripe integration service for billing.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class StripeService:
    """
    Service for Stripe API interactions.

    Handles:
    - Customer management
    - Subscription lifecycle
    - Checkout sessions
    - Billing portal
    - Webhooks
    """

    def __init__(self):
        self._stripe = None

    @property
    def stripe(self):
        """Lazy load Stripe SDK."""
        if self._stripe is None:
            try:
                import stripe

                stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
                self._stripe = stripe
            except ImportError:
                logger.warning("Stripe SDK not installed")
                return None
        return self._stripe

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return bool(getattr(settings, 'STRIPE_SECRET_KEY', None))

    def _with_retry(self, func, *args, **kwargs):
        """Retry Stripe API calls for transient errors."""
        import time

        max_attempts = 3
        delay = 1
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not self.stripe or not hasattr(self.stripe, 'error'):
                    raise
                transient_errors = (
                    self.stripe.error.APIConnectionError,
                    self.stripe.error.RateLimitError,
                )
                if not isinstance(e, transient_errors) or attempt == max_attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 2

    def get_price_id(self, plan: str, billing_interval: str = 'month') -> str | None:
        """
        Get Stripe price ID for a plan.

        Now reads from database instead of environment variables.

        Args:
            plan: The plan name (e.g., 'organizer', 'lms', 'organization')
            billing_interval: 'month' or 'year' (default: 'month')

        Returns:
            Stripe price ID or None
        """
        if not self.is_configured:
            return None

        try:
            from .models import StripeProduct

            # Find product for this plan
            product = StripeProduct.objects.filter(plan=plan, is_active=True).first()
            if not product:
                logger.warning(f"No StripeProduct found for plan '{plan}'")
                return None

            # Find price for billing interval
            interval = billing_interval or 'month'
            if interval not in ('month', 'year'):
                logger.warning(f"Invalid billing interval '{interval}' for plan '{plan}'")
                return None
            price = product.prices.filter(billing_interval=interval, is_active=True).first()

            if not price:
                logger.warning(f"No active price found for plan '{plan}' with interval '{interval}'")
                return None

            return price.stripe_price_id

        except Exception as e:
            logger.error(f"Error getting price ID from database: {e}")
            return None

    def get_trial_days(self, plan: str) -> int:
        """
        Get trial period days for a plan.

        Reads from database (StripeProduct.trial_period_days).
        Returns 0 if product not found or configured.
        """
        try:
            from .models import StripeProduct

            product = StripeProduct.objects.filter(plan=plan, is_active=True).first()
            if product:
                return product.get_trial_days()

        except Exception as e:
            logger.error(f"Error getting trial days from database: {e}")

        # Default to 0 (no trial) if not explicitly configured in DB
        return 0

    def sync_trial_period_days(self, plan: str, trial_days: int, previous_trial_days: int | None = None) -> dict[str, int]:
        """
        Extend trial periods for existing trialing subscriptions on a plan.

        Only extends trials when trial_days increases. Does not shorten trials.
        """
        if previous_trial_days is not None and trial_days <= previous_trial_days:
            return {'updated': 0, 'skipped': 0}

        if trial_days <= 0:
            return {'updated': 0, 'skipped': 0}

        updated = 0
        skipped = 0
        now = timezone.now()

        try:
            from organizations.models import OrganizationSubscription

            from .models import Subscription

            subscriptions = list(
                Subscription.objects.filter(
                    plan=plan,
                    status=Subscription.Status.TRIALING,
                    trial_ends_at__isnull=False,
                )
            )

            if plan == OrganizationSubscription.Plan.ORGANIZATION:
                org_subscriptions = list(
                    OrganizationSubscription.objects.filter(
                        plan=plan,
                        status=OrganizationSubscription.Status.TRIALING,
                        trial_ends_at__isnull=False,
                    )
                )
            else:
                org_subscriptions = []
        except Exception as exc:
            logger.error(f"Failed to load subscriptions for trial sync: {exc}")
            return {'updated': 0, 'skipped': 0}

        for sub in subscriptions:
            new_trial_end = None
            if sub.current_period_start:
                new_trial_end = sub.current_period_start + timedelta(days=trial_days)

            if not new_trial_end or new_trial_end <= now:
                skipped += 1
                continue

            if sub.trial_ends_at and new_trial_end <= sub.trial_ends_at:
                skipped += 1
                continue

            if self.is_configured and sub.stripe_subscription_id:
                try:
                    self.stripe.Subscription.modify(
                        sub.stripe_subscription_id,
                        trial_end=int(new_trial_end.timestamp()),
                    )
                except Exception as exc:
                    logger.error(f"Failed to update Stripe trial for {sub.stripe_subscription_id}: {exc}")
                    skipped += 1
                    continue

            sub.trial_ends_at = new_trial_end
            sub.save(update_fields=['trial_ends_at', 'updated_at'])
            updated += 1

        for sub in org_subscriptions:
            new_trial_end = None
            if sub.current_period_start:
                new_trial_end = sub.current_period_start + timedelta(days=trial_days)

            if not new_trial_end or new_trial_end <= now:
                skipped += 1
                continue

            if sub.trial_ends_at and new_trial_end <= sub.trial_ends_at:
                skipped += 1
                continue

            if self.is_configured and sub.stripe_subscription_id:
                try:
                    self.stripe.Subscription.modify(
                        sub.stripe_subscription_id,
                        trial_end=int(new_trial_end.timestamp()),
                    )
                except Exception as exc:
                    logger.error(f"Failed to update Stripe trial for org {sub.stripe_subscription_id}: {exc}")
                    skipped += 1
                    continue

            sub.trial_ends_at = new_trial_end
            sub.save(update_fields=['trial_ends_at', 'updated_at'])
            updated += 1

        return {'updated': updated, 'skipped': skipped}

    def _apply_plan_to_user(self, user, plan: str) -> None:
        """Apply account_type changes based on subscription plan."""
        if plan in ['organizer', 'organization']:
            user.upgrade_to_organizer()
        elif plan == 'lms':
            user.upgrade_to_course_manager()
        elif plan == 'attendee':
            user.downgrade_to_attendee()

    # =========================================================================
    # Customer Management
    # =========================================================================

    def create_customer(self, user) -> str | None:
        """
        Create or retrieve Stripe customer for user.

        Returns:
            Stripe customer ID
        """
        if not self.is_configured:
            logger.warning("Stripe not configured, skipping customer creation")
            return None

        # Check if user already has a customer ID
        subscription = getattr(user, 'subscription', None)
        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        try:
            customer = self._with_retry(
                self.stripe.Customer.create,
                email=user.email,
                name=user.full_name or user.email,
                metadata={
                    'user_uuid': str(user.uuid),
                },
            )

            # Store customer ID
            if subscription:
                subscription.stripe_customer_id = customer.id
                subscription.save(update_fields=['stripe_customer_id', 'updated_at'])

            return customer.id

        except Exception as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return None

    def update_customer(self, customer_id: str, **kwargs) -> bool:
        """Update Stripe customer."""
        if not self.is_configured:
            return False

        try:
            self.stripe.Customer.modify(customer_id, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to update Stripe customer: {e}")
            return False

    def get_invoice(self, invoice_id: str):
        """Retrieve a Stripe invoice."""
        if not self.is_configured:
            return None
        try:
            return self._with_retry(self.stripe.Invoice.retrieve, invoice_id)
        except Exception as e:
            logger.warning(f"Failed to retrieve invoice {invoice_id}: {e}")
            return None

    def list_payment_intents(self, created_gte: datetime | None = None, limit: int = 200) -> dict[str, Any]:
        """List recent payment intents for reconciliation."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            params: dict[str, Any] = {'limit': 100}
            if created_gte:
                params['created'] = {'gte': int(created_gte.timestamp())}

            intents = []
            response = self._with_retry(self.stripe.PaymentIntent.list, **params)
            for intent in response.auto_paging_iter():
                intents.append(intent)
                if len(intents) >= limit:
                    break

            return {'success': True, 'payment_intents': intents}
        except Exception as e:
            logger.error(f"Failed to list payment intents: {e}")
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Subscription Management
    # =========================================================================

    def create_subscription(
        self,
        user,
        plan: str,
        payment_method_id: str | None = None,
        billing_interval: str = 'month',
    ) -> dict[str, Any]:
        """
        Create a subscription for a user.

        Returns:
            Dict with subscription details or error
        """
        from django.db import transaction

        from billing.models import Subscription

        if not self.is_configured:
            # Create local subscription without Stripe
            with transaction.atomic():
                subscription = Subscription.create_for_user(user, plan)
                # Upgrade user account_type in same transaction
                self._apply_plan_to_user(user, plan)
            return {'success': True, 'subscription': subscription}

        # Check for existing active subscription (uniqueness enforcement)
        existing = getattr(user, 'subscription', None)
        if existing and existing.stripe_subscription_id and existing.status in ['active', 'trialing']:
            return {'success': False, 'error': 'User already has an active subscription. Use update to change plans.'}

        billing_interval = billing_interval or 'month'
        price_id = self.get_price_id(plan, billing_interval=billing_interval)
        if not price_id:
            return {'success': False, 'error': f'No price configured for plan: {plan}'}

        try:
            # Ensure customer exists
            customer_id = self.create_customer(user)
            if not customer_id:
                return {'success': False, 'error': 'Failed to create customer'}

            trial_days = self.get_trial_days(plan)
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'expand': ['latest_invoice.payment_intent'],
                'automatic_tax': {'enabled': True},
                'metadata': {
                    'user_uuid': str(user.uuid),
                    'plan': plan,
                    'billing_interval': billing_interval,
                },
            }

            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id
            if trial_days > 0:
                subscription_params['trial_period_days'] = trial_days

            stripe_subscription = self._with_retry(self.stripe.Subscription.create, **subscription_params)

            # Atomically update local subscription
            with transaction.atomic():
                subscription, _ = Subscription.objects.select_for_update().get_or_create(user=user)
                subscription.stripe_subscription_id = stripe_subscription.id
                subscription.stripe_customer_id = customer_id
                subscription.plan = plan
                subscription.status = stripe_subscription.status
                subscription.billing_interval = billing_interval
                subscription.pending_plan = None
                subscription.pending_billing_interval = None
                subscription.pending_change_at = None
                subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start, tz=UTC)
                subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end, tz=UTC)
                subscription.trial_ends_at = (
                    datetime.fromtimestamp(stripe_subscription.trial_end, tz=UTC)
                    if getattr(stripe_subscription, 'trial_end', None)
                    else None
                )
                subscription.save()

                # Upgrade user account_type in same transaction
                self._apply_plan_to_user(user, plan)

            return {
                'success': True,
                'subscription': subscription,
                'client_secret': getattr(stripe_subscription.latest_invoice.payment_intent, 'client_secret', None),
            }

        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return {'success': False, 'error': str(e)}

    def cancel_subscription(self, subscription, immediate: bool = False, reason: str = '') -> bool:
        """Cancel a subscription atomically."""
        from django.db import transaction

        if not self.is_configured or not subscription.stripe_subscription_id:
            with transaction.atomic():
                subscription.cancel(reason=reason, immediate=immediate)
                # Downgrade user if immediate cancellation
                if immediate:
                    subscription.user.downgrade_to_attendee()
            return True

        try:
            if immediate:
                self.stripe.Subscription.delete(subscription.stripe_subscription_id)
            else:
                self.stripe.Subscription.modify(
                    subscription.stripe_subscription_id, cancel_at_period_end=True, metadata={'cancellation_reason': reason}
                )

            with transaction.atomic():
                subscription.cancel(reason=reason, immediate=immediate)
                # Downgrade user if immediate cancellation
                if immediate:
                    subscription.user.downgrade_to_attendee()
            return True

        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False

    def reactivate_subscription(self, subscription) -> bool:
        """Reactivate a canceled subscription atomically."""
        from django.db import transaction

        if not self.is_configured or not subscription.stripe_subscription_id:
            with transaction.atomic():
                subscription.reactivate()
            return True

        try:
            self.stripe.Subscription.modify(subscription.stripe_subscription_id, cancel_at_period_end=False)
            with transaction.atomic():
                subscription.reactivate()
            return True
        except Exception as e:
            logger.error(f"Failed to reactivate subscription: {e}")
            return False

    def update_subscription(
        self,
        subscription,
        new_plan: str,
        immediate: bool = True,
        billing_interval: str = 'month',
    ) -> dict[str, Any]:
        """
        Update an existing subscription to a new plan atomically.

        Args:
            subscription: Current subscription object
            new_plan: New plan tier to switch to
            immediate: If True, change immediately with proration.
                      If False, schedule change for end of period.

        Returns:
            Dict with success status and updated subscription or error
        """
        from django.db import transaction

        from billing.models import Subscription

        # Handle local-only mode (no Stripe configured)
        if not self.is_configured:
            with transaction.atomic():
                subscription.plan = new_plan
                subscription.billing_interval = billing_interval
                subscription.pending_plan = None
                subscription.pending_billing_interval = None
                subscription.pending_change_at = None
                subscription.save(
                    update_fields=[
                        'plan',
                        'billing_interval',
                        'pending_plan',
                        'pending_billing_interval',
                        'pending_change_at',
                        'updated_at',
                    ]
                )
                # Update user account_type in same transaction
                self._apply_plan_to_user(subscription.user, new_plan)
            return {'success': True, 'subscription': subscription}

        # Validate plan exists
        if new_plan not in [choice[0] for choice in Subscription.Plan.choices]:
            return {'success': False, 'error': f'Invalid plan: {new_plan}'}

        # Get price ID for new plan
        billing_interval = billing_interval or 'month'
        price_id = self.get_price_id(new_plan, billing_interval=billing_interval)
        if not price_id:
            return {'success': False, 'error': f'No price configured for plan: {new_plan}'}

        # Check if subscription has Stripe ID
        if not subscription.stripe_subscription_id:
            return {'success': False, 'error': 'No Stripe subscription found. Please create a subscription first.'}

        try:
            # Retrieve current Stripe subscription
            stripe_sub = self.stripe.Subscription.retrieve(subscription.stripe_subscription_id)

            if not stripe_sub or not stripe_sub.get('items'):
                return {'success': False, 'error': 'Stripe subscription not found or has no items'}

            # Get the subscription item ID (first item)
            item_id = stripe_sub['items']['data'][0].id

            if immediate:
                # Immediate upgrade/downgrade with proration
                updated_stripe_sub = self.stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    items=[
                        {
                            'id': item_id,
                            'price': price_id,
                        }
                    ],
                    proration_behavior='always_invoice',
                    billing_cycle_anchor='unchanged',
                )

                # Atomically update local database
                with transaction.atomic():
                    subscription.plan = new_plan
                    subscription.status = updated_stripe_sub.get('status', subscription.status)
                    subscription.billing_interval = billing_interval
                    subscription.pending_plan = None
                    subscription.pending_billing_interval = None
                    subscription.pending_change_at = None
                    subscription.save(
                        update_fields=[
                            'plan',
                            'status',
                            'billing_interval',
                            'pending_plan',
                            'pending_billing_interval',
                            'pending_change_at',
                            'updated_at',
                        ]
                    )
                    # Update user account_type in same transaction
                    self._apply_plan_to_user(subscription.user, new_plan)
            else:
                # Schedule change for end of period
                current_item = stripe_sub['items']['data'][0]
                current_price = current_item.price if hasattr(current_item, 'price') else current_item.get('price')
                current_price_id = getattr(current_price, 'id', None) or current_price.get('id')
                current_quantity = getattr(current_item, 'quantity', None) or current_item.get('quantity') or 1
                current_period_end = getattr(stripe_sub, 'current_period_end', None)
                if current_period_end is None and hasattr(stripe_sub, 'get'):
                    current_period_end = stripe_sub.get('current_period_end')

                if not current_price_id or not current_period_end:
                    return {'success': False, 'error': 'Stripe subscription missing price or period end'}

                schedule_id = getattr(stripe_sub, 'schedule', None)
                if schedule_id is None and hasattr(stripe_sub, 'get'):
                    schedule_id = stripe_sub.get('schedule')
                if schedule_id:
                    schedule = self.stripe.SubscriptionSchedule.retrieve(schedule_id)
                else:
                    schedule = self.stripe.SubscriptionSchedule.create(from_subscription=subscription.stripe_subscription_id)

                self.stripe.SubscriptionSchedule.modify(
                    schedule.id,
                    phases=[
                        {
                            'items': [{'price': current_price_id, 'quantity': current_quantity}],
                            'end_date': current_period_end,
                        },
                        {
                            'items': [{'price': price_id, 'quantity': current_quantity}],
                        },
                    ],
                    end_behavior='release',
                )

                with transaction.atomic():
                    subscription.pending_plan = new_plan
                    subscription.pending_billing_interval = billing_interval
                    subscription.pending_change_at = datetime.fromtimestamp(current_period_end, tz=UTC)
                    subscription.save(
                        update_fields=[
                            'pending_plan',
                            'pending_billing_interval',
                            'pending_change_at',
                            'updated_at',
                        ]
                    )

            logger.info(f"Successfully updated subscription {subscription.id} to plan {new_plan}")
            return {'success': True, 'subscription': subscription}

        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            return {'success': False, 'error': str(e)}

    def update_subscription_trial(self, subscription_id: str, trial_end: datetime) -> dict[str, Any]:
        """
        Update subscription trial end date in Stripe.

        Args:
            subscription_id: Stripe subscription ID
            trial_end: New trial end date (datetime)

        Returns:
            Dict with success status or error
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            # Unix timestamp
            trial_end_ts = int(trial_end.timestamp())

            # Ensure future date
            if trial_end_ts <= int(timezone.now().timestamp()):
                # Stripe requires trial_end to be in the future (or 'now' to end it?)
                # Actually to end a trial immediately, you usually set trial_end='now'
                # But here we assume admin wants to set a specific date.
                pass

            self.stripe.Subscription.modify(
                subscription_id,
                trial_end=trial_end_ts,
                proration_behavior='none', # Changing trial shouldn't trigger proration normally but safe to specify
            )

            logger.info(f"Updated Stripe trial end for {subscription_id} to {trial_end}")
            return {'success': True}

        except Exception as e:
            logger.error(f"Failed to update Stripe trial: {e}")
            return {'success': False, 'error': str(e)}

    def update_subscription_quantity(self, subscription_id: str, quantity: int) -> dict[str, Any]:
        """
        Update the quantity (number of seats) of a Stripe subscription.

        Args:
            subscription_id: Stripe subscription ID
            quantity: New total quantity

        Returns:
            Dict with success status or error
        """
        if not self.is_configured:
            # If not configured, we assume success for local dev (caller handles local DB)
            return {'success': True}

        try:
            # Retrieve subscription to get item ID
            stripe_sub = self.stripe.Subscription.retrieve(subscription_id)
            if not stripe_sub or not stripe_sub.get('items'):
                return {'success': False, 'error': 'Stripe subscription not found or has no items'}

            item_id = stripe_sub['items']['data'][0].id

            # Update quantity
            # usage_type='licensed' means we set exact quantity
            # If it were metered, we'd use Usage Records, but here we are scaling seats.
            self.stripe.SubscriptionItem.modify(
                item_id,
                quantity=quantity,
                proration_behavior='always_invoice',  # Charge immediately for adds, credit for removes
            )

            return {'success': True}

        except Exception as e:
            logger.error(f"Failed to update subscription quantity: {e}")
            return {'success': False, 'error': str(e)}

    def sync_subscription(self, user) -> dict[str, Any]:
        """
        Sync local subscription with Stripe atomically.
        Useful when webhooks are not available (e.g. local dev).
        """
        from django.db import transaction

        from billing.models import StripeProduct, Subscription

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        subscription = getattr(user, 'subscription', None)
        if not subscription:
            # Create a blank one to populate
            subscription = Subscription.objects.create(user=user)

        try:
            # 1. Try to find subscription by ID if we have it
            stripe_sub = None
            if subscription.stripe_subscription_id:
                try:
                    stripe_sub = self.stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                except Exception:
                    stripe_sub = None

            # 2. If not found, try to find by customer ID
            if not stripe_sub and subscription.stripe_customer_id:
                subs = self.stripe.Subscription.list(customer=subscription.stripe_customer_id, status='all', limit=1)
                if subs and subs.data:
                    stripe_sub = subs.data[0]

            # 3. If still not found, try to find customer by email and then subscription
            if not stripe_sub:
                customers = self.stripe.Customer.list(email=user.email, limit=1)
                if customers and customers.data:
                    customer = customers.data[0]
                    subscription.stripe_customer_id = customer.id
                    subscription.save(update_fields=['stripe_customer_id'])

                    subs = self.stripe.Subscription.list(customer=customer.id, status='all', limit=1)
                    if subs and subs.data:
                        stripe_sub = subs.data[0]

            if not stripe_sub:
                return {'success': False, 'error': 'No subscription found in Stripe'}

            # Atomically update local database
            with transaction.atomic():
                # Refresh subscription with lock
                subscription = Subscription.objects.select_for_update().get(pk=subscription.pk)

                subscription.stripe_subscription_id = stripe_sub.id
                subscription.status = stripe_sub.status
                subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start, tz=UTC)
                subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end, tz=UTC)
                subscription.trial_ends_at = (
                    datetime.fromtimestamp(stripe_sub.trial_end, tz=UTC) if stripe_sub.trial_end else None
                )
                subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
                subscription.canceled_at = (
                    datetime.fromtimestamp(stripe_sub.canceled_at, tz=UTC) if stripe_sub.canceled_at else None
                )

                # Determine plan from price
                if stripe_sub.get('items') and stripe_sub['items'].data:
                    try:
                        item = stripe_sub['items'].data[0]
                        product_id = item.price.product
                        local_product = StripeProduct.objects.filter(stripe_product_id=product_id).first()
                        if local_product:
                            subscription.plan = local_product.plan
                        if item.price and item.price.recurring:
                            subscription.billing_interval = item.price.recurring.interval
                    except Exception as e:
                        logger.warning(f"Could not map Stripe product to local plan: {e}")

                subscription.pending_plan = None
                subscription.pending_billing_interval = None
                subscription.pending_change_at = None
                subscription.save()

                # Upgrade/downgrade account_type in same transaction
                self._apply_plan_to_user(user, subscription.plan)
                logger.info(f"Updated user {user.email} account_type based on plan {subscription.plan}")

            return {'success': True, 'subscription': subscription}

        except Exception as e:
            logger.error(f"Failed to sync subscription: {e}")
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Checkout & Portal
    # =========================================================================

    def create_checkout_session(
        self,
        user,
        plan: str,
        success_url: str,
        cancel_url: str,
        organization_uuid: str | None = None,
        billing_interval: str = 'month',
    ) -> dict[str, Any]:
        """
        Create Stripe Checkout Session.

        Includes session_id in success_url for synchronous confirmation.
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        # Check for existing active subscription (uniqueness enforcement)
        existing = getattr(user, 'subscription', None)
        if existing and existing.stripe_subscription_id and existing.status in ['active', 'trialing']:
            # Verify with Stripe that subscription is truly active
            try:
                stripe_sub = self.stripe.Subscription.retrieve(existing.stripe_subscription_id)
                if stripe_sub.status in ['active', 'trialing']:
                    return {
                        'success': False,
                        'error': 'You already have an active subscription. Use the billing portal to upgrade.',
                    }
            except Exception:
                pass  # Subscription doesn't exist in Stripe, continue with checkout

        billing_interval = billing_interval or 'month'
        price_id = self.get_price_id(plan, billing_interval=billing_interval)
        if not price_id:
            return {'success': False, 'error': f'No price configured for plan: {plan}'}

        # Get trial days from database (per-plan configuration)
        trial_days = self.get_trial_days(plan)

        # Check if user is currently in a trial (local) and adjust Stripe trial to match remaining time
        # This prevents "double trial" (e.g. 30 days local + 30 days Stripe)
        existing_sub = getattr(user, 'subscription', None)
        if existing_sub and existing_sub.is_trialing and existing_sub.trial_ends_at:
            from django.utils import timezone

            remaining = (existing_sub.trial_ends_at - timezone.now()).days
            # Only override if remaining time is LESS than the plan's default trial
            # (e.g. if they have 5 days left, give them 5 days on Stripe. If they have -5, give 0).
            if remaining < trial_days:
                trial_days = max(0, remaining)

        try:
            customer_id = self.create_customer(user)

            metadata = {
                'user_uuid': str(user.uuid),
                'plan': plan,
                'billing_interval': billing_interval,
            }
            if organization_uuid:
                metadata['organization_uuid'] = organization_uuid

            # Add session_id placeholder to success_url for sync confirmation
            # Stripe replaces {CHECKOUT_SESSION_ID} with actual session ID
            success_url_with_session = success_url
            if '{CHECKOUT_SESSION_ID}' not in success_url:
                separator = '&' if '?' in success_url else '?'
                success_url_with_session = f"{success_url}{separator}session_id={{CHECKOUT_SESSION_ID}}"

            session = self.stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url=success_url_with_session,
                cancel_url=cancel_url,
                automatic_tax={'enabled': True},
                customer_update={'address': 'auto'},
                subscription_data={
                    'trial_period_days': trial_days,
                    'metadata': metadata,
                },
                metadata=metadata,
            )

            return {'success': True, 'session_id': session.id, 'url': session.url}

        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return {'success': False, 'error': str(e)}

    def create_one_time_checkout_session(
        self,
        user,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, Any] = None,
        client_reference_id: str = None,
    ) -> dict[str, Any]:
        """
        Create Stripe Checkout Session for one-time payment (e.g. Course).
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            customer_id = self.create_customer(user)

            # Prepare success URL with session_id
            success_url_with_session = success_url
            if '{CHECKOUT_SESSION_ID}' not in success_url:
                separator = '&' if '?' in success_url else '?'
                success_url_with_session = f"{success_url}{separator}session_id={{CHECKOUT_SESSION_ID}}"

            session_params = {
                'customer': customer_id,
                'payment_method_types': ['card'],
                'line_items': [{'price': price_id, 'quantity': 1}],
                'mode': 'payment',
                'success_url': success_url_with_session,
                'cancel_url': cancel_url,
                'automatic_tax': {'enabled': True},
                'customer_update': {'address': 'auto'},
                'metadata': metadata or {},
            }

            if client_reference_id:
                session_params['client_reference_id'] = client_reference_id

            session = self.stripe.checkout.Session.create(**session_params)

            return {'success': True, 'session_id': session.id, 'url': session.url}

        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return {'success': False, 'error': str(e)}

    def retrieve_checkout_session(self, session_id: str) -> dict[str, Any]:
        """
        Retrieve a checkout session from Stripe.
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            session = self._with_retry(self.stripe.checkout.Session.retrieve, session_id)
            return {'success': True, 'session': session}
        except Exception as e:
            logger.error(f"Failed to retrieve checkout session {session_id}: {e}")
            return {'success': False, 'error': str(e)}

    def confirm_checkout_session(self, user, session_id: str, max_retries: int = 3) -> dict[str, Any]:
        """
        Atomically confirm checkout session and sync subscription.

        Called by frontend after returning from Stripe Checkout.
        This is the PRIMARY path for subscription creation (webhooks are fallback).

        Args:
            user: The user who completed checkout
            session_id: Stripe Checkout Session ID (cs_xxx)
            max_retries: Number of retries for transient failures

        Returns:
            dict with success status and subscription or error
        """
        import time

        from django.db import transaction

        from billing.models import StripeProduct, Subscription

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        for attempt in range(max_retries):
            try:
                # 1. Retrieve checkout session from Stripe
                session = self.stripe.checkout.Session.retrieve(
                    session_id, expand=['subscription', 'subscription.latest_invoice']
                )

                # 2. Verify session belongs to this user (via customer or metadata)
                existing_sub = getattr(user, 'subscription', None)
                expected_customer = existing_sub.stripe_customer_id if existing_sub else None

                # Check by customer ID or metadata
                session_belongs_to_user = (expected_customer and session.customer == expected_customer) or session.metadata.get(
                    'user_uuid'
                ) == str(user.uuid)

                if not session_belongs_to_user:
                    return {'success': False, 'error': 'Checkout session does not belong to this user'}

                # 3. Get subscription from session
                stripe_sub = session.subscription
                if not stripe_sub:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)  # Wait for subscription to be created
                        continue
                    return {'success': False, 'error': 'No subscription found in checkout session'}

                # If stripe_sub is a string (ID), retrieve full object
                if isinstance(stripe_sub, str):
                    stripe_sub = self.stripe.Subscription.retrieve(stripe_sub)

                # 4. Idempotency Check & Duplicate Handling
                # Check if subscription is already updated (e.g. by webhook) to avoid locking
                try:
                    existing_sub = Subscription.objects.get(user=user)
                    if (
                        existing_sub.stripe_subscription_id == stripe_sub.id
                        and existing_sub.status == stripe_sub.status
                    ):
                        logger.info(f"Checkout session {session_id}: Subscription already up to date, skipping DB write")

                        # Ensure payment methods are synced (outside transaction)
                        sync_result = self.sync_payment_methods(user, customer_id=session.customer)

                        return {'success': True, 'subscription': existing_sub}
                except Subscription.DoesNotExist:
                    pass

                # If user already has a different subscription, cancel the new one
                with transaction.atomic():
                    subscription, created = Subscription.objects.select_for_update().get_or_create(user=user)

                    if subscription.stripe_subscription_id and subscription.stripe_subscription_id != stripe_sub.id:
                        # User has two subscriptions - this shouldn't happen
                        # Check if existing one is still valid
                        try:
                            existing_stripe_sub = self.stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                            if existing_stripe_sub.status in ['active', 'trialing']:
                                # Cancel the new one to maintain consistency
                                logger.warning(
                                    f"User {user.email} already has subscription {subscription.stripe_subscription_id}, canceling new one {stripe_sub.id}"
                                )
                                self.stripe.Subscription.cancel(stripe_sub.id)
                                return {'success': False, 'error': 'User already has an active subscription'}
                        except Exception:
                            pass  # Existing subscription doesn't exist, continue with new one

                    # 5. Update subscription fields
                    subscription.stripe_subscription_id = stripe_sub.id
                    subscription.stripe_customer_id = session.customer
                    subscription.status = stripe_sub.status
                    subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start, tz=UTC)
                    subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end, tz=UTC)

                    # Handle trial
                    if stripe_sub.trial_end:
                        subscription.trial_ends_at = datetime.fromtimestamp(stripe_sub.trial_end, tz=UTC)

                    # Determine plan from metadata or price
                    plan = session.metadata.get('plan')
                    billing_interval = session.metadata.get('billing_interval')
                    if not plan:
                        # Try to determine from subscription items
                        if stripe_sub.get('items') and stripe_sub['items'].data:
                            try:
                                item = stripe_sub['items'].data[0]
                                product_id = item.price.product
                                local_product = StripeProduct.objects.filter(stripe_product_id=product_id).first()
                                if local_product:
                                    plan = local_product.plan
                                if not billing_interval and item.price and item.price.recurring:
                                    billing_interval = item.price.recurring.interval
                            except Exception:
                                pass
                    plan = plan or 'organizer'  # Default to organizer if unknown
                    billing_interval = billing_interval or 'month'

                    subscription.plan = plan
                    subscription.billing_interval = billing_interval
                    subscription.pending_plan = None
                    subscription.pending_billing_interval = None
                    subscription.pending_change_at = None
                    subscription.save()

                    # 6. Upgrade user account_type in same transaction
                    self._apply_plan_to_user(user, plan)
                    logger.info(f"User {user.email} account_type updated via checkout confirmation")

                sync_result = self.sync_payment_methods(user, customer_id=session.customer)
                if not sync_result.get('success'):
                    logger.warning(f"Payment method sync failed for session {session_id}: {sync_result.get('error')}")

                logger.info(f"Checkout session {session_id} confirmed for user {user.email}")
                return {'success': True, 'subscription': subscription}

            except Exception as e:
                error_str = str(e).lower()
                if ('unique constraint' in error_str or 'database is locked' in error_str) and attempt < max_retries - 1:
                    time.sleep(1)  # Increased backoff
                    continue
                logger.error(f"Failed to confirm checkout session {session_id}: {e}")
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Max retries exceeded'}

    def confirm_organization_checkout_session(self, organization, session_id: str, max_retries: int = 3) -> dict[str, Any]:
        """
        Atomically confirm checkout session and sync Organization Subscription.
        """
        import time
        from datetime import datetime

        from django.db import transaction

        from organizations.models import OrganizationSubscription

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        for attempt in range(max_retries):
            try:
                # 1. Retrieve
                session = self.stripe.checkout.Session.retrieve(session_id, expand=['subscription'])

                # 2. Verify ownership
                if session.metadata.get('organization_uuid') != str(organization.uuid):
                    return {'success': False, 'error': 'Checkout session does not belong to this organization'}

                # 3. Get subscription
                stripe_sub = session.subscription
                if not stripe_sub:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        continue
                    return {'success': False, 'error': 'No subscription found'}

                if isinstance(stripe_sub, str):
                    stripe_sub = self.stripe.Subscription.retrieve(stripe_sub)

                # 4. Update
                with transaction.atomic():
                    subscription, created = OrganizationSubscription.objects.select_for_update().get_or_create(
                        organization=organization
                    )

                # Idempotency check: if already updated, skip
                if (
                    not created
                    and subscription.stripe_subscription_id == stripe_sub.id
                    and subscription.status == stripe_sub.status
                ):
                    return {'success': True, 'subscription': subscription}

                subscription.stripe_subscription_id = stripe_sub.id
                subscription.stripe_customer_id = session.customer
                subscription.status = stripe_sub.status
                subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start, tz=UTC)
                subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end, tz=UTC)

                if stripe_sub.trial_end:
                    subscription.trial_ends_at = datetime.fromtimestamp(stripe_sub.trial_end, tz=UTC)
                else:
                    subscription.trial_ends_at = None

                plan = session.metadata.get('plan')
                product = None
                if not plan and stripe_sub.get('items') and stripe_sub['items'].data:
                    try:
                        item = stripe_sub['items'].data[0]
                        product_id = item.price.product
                        from billing.models import StripeProduct

                        product = StripeProduct.objects.filter(stripe_product_id=product_id).first()
                        if product:
                            plan = product.plan
                    except Exception:
                        pass

                if plan:
                    subscription.plan = plan
                    if not product:
                        try:
                            from billing.models import StripeProduct

                            product = StripeProduct.objects.filter(plan=plan, is_active=True).first()
                        except Exception:
                            product = None
                    if product:
                        if product.included_seats is not None:
                            subscription.included_seats = product.included_seats
                        if product.seat_price_cents is not None:
                            subscription.seat_price_cents = product.seat_price_cents

                subscription.save()

                return {'success': True, 'subscription': subscription}

            except Exception as e:
                # Retry on unique constraint or database lock
                error_str = str(e).lower()
                if ('unique constraint' in error_str or 'database is locked' in error_str) and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                logger.error(f"Failed to confirm org checkout {session_id}: {e}")
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Failed to confirm checkout session after retries'}

    def sync_payment_methods(self, user, customer_id: str | None = None) -> dict[str, Any]:
        """
        Sync Stripe payment methods into local PaymentMethod records.

        Intended to be called after checkout/portal flows; webhooks are fallback.
        """
        from django.db import transaction

        from billing.models import PaymentMethod

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        subscription = getattr(user, 'subscription', None)
        customer_id = customer_id or (subscription.stripe_customer_id if subscription else None)

        if not customer_id:
            try:
                customers = self.stripe.Customer.list(email=user.email, limit=1)
                if customers and customers.data:
                    customer_id = customers.data[0].id
                    if subscription:
                        subscription.stripe_customer_id = customer_id
                        subscription.save(update_fields=['stripe_customer_id'])
            except Exception as e:
                logger.error(f"Failed to lookup Stripe customer for {user.email}: {e}")
                return {'success': False, 'error': 'Failed to lookup Stripe customer'}

        if not customer_id:
            return {'success': False, 'error': 'No Stripe customer found'}

        try:
            customer = self.stripe.Customer.retrieve(customer_id)
            invoice_settings = (
                customer.get('invoice_settings', {})
                if isinstance(customer, dict)
                else getattr(customer, 'invoice_settings', {})
            )
            default_pm_id = (
                invoice_settings.get('default_payment_method')
                if isinstance(invoice_settings, dict)
                else getattr(invoice_settings, 'default_payment_method', None)
            )

            pm_list = self.stripe.PaymentMethod.list(customer=customer_id, type='card')
            pm_data = pm_list.data if hasattr(pm_list, 'data') else pm_list.get('data', [])

            stripe_ids: set[str] = set()
            with transaction.atomic():
                PaymentMethod.objects.filter(user=user).update(is_default=False)

                for pm in pm_data:
                    stripe_ids.add(pm.id)
                    card = pm.card if hasattr(pm, 'card') else pm.get('card', {})
                    card_brand = card.brand if hasattr(card, 'brand') else card.get('brand', '')
                    card_last4 = card.last4 if hasattr(card, 'last4') else card.get('last4', '')
                    card_exp_month = card.exp_month if hasattr(card, 'exp_month') else card.get('exp_month')
                    card_exp_year = card.exp_year if hasattr(card, 'exp_year') else card.get('exp_year')

                    payment_method, _ = PaymentMethod.objects.update_or_create(
                        stripe_payment_method_id=pm.id,
                        defaults={
                            'user': user,
                            'card_brand': card_brand or '',
                            'card_last4': card_last4 or '',
                            'card_exp_month': card_exp_month,
                            'card_exp_year': card_exp_year,
                            'is_default': pm.id == default_pm_id,
                        },
                    )

                    if pm.id == default_pm_id:
                        payment_method.set_as_default()

                if stripe_ids:
                    PaymentMethod.objects.filter(user=user).exclude(stripe_payment_method_id__in=stripe_ids).delete()

            return {'success': True, 'count': len(stripe_ids)}
        except Exception as e:
            logger.error(f"Failed to sync payment methods for {user.email}: {e}")
            return {'success': False, 'error': str(e)}

    def create_portal_session(self, user, return_url: str, customer_id: str | None = None) -> dict[str, Any]:
        """Create Stripe Customer Portal session."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        # If customer_id not provided, get from user
        if not customer_id:
            customer_id = self.create_customer(user)

        if not customer_id:
            return {'success': False, 'error': 'Failed to create billing account'}

        try:
            session = self.stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
            return {'success': True, 'url': session.url}
        except Exception as e:
            logger.error(f"Failed to create portal session: {e}")
            return {'success': False, 'error': str(e)}

    def create_setup_intent(self, user) -> dict[str, Any]:
        """
        Create a SetupIntent for collecting payment method via Stripe Elements.

        Returns:
            Dict with client_secret for frontend Stripe Elements
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        # Get or create Stripe customer
        customer_id = self.create_customer(user)
        if not customer_id:
            return {'success': False, 'error': 'Failed to create billing account'}

        try:
            setup_intent = self.stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=['card'],
                metadata={
                    'user_uuid': str(user.uuid),
                },
            )

            # Get subscription for trial end date
            subscription = getattr(user, 'subscription', None)
            trial_end = None
            if subscription and subscription.trial_ends_at:
                trial_end = subscription.trial_ends_at.isoformat()

            return {
                'success': True,
                'client_secret': setup_intent.client_secret,
                'customer_id': customer_id,
                'trial_ends_at': trial_end,
            }
        except Exception as e:
            logger.error(f"Failed to create setup intent: {e}")
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Payment Methods
    # =========================================================================

    def attach_payment_method(self, user, payment_method_id: str, set_as_default: bool = True) -> dict[str, Any]:
        """Attach a payment method to user."""
        from billing.models import PaymentMethod

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        subscription = getattr(user, 'subscription', None)
        if not subscription or not subscription.stripe_customer_id:
            return {'success': False, 'error': 'No billing account found'}

        try:
            # Attach to customer
            pm = self.stripe.PaymentMethod.attach(payment_method_id, customer=subscription.stripe_customer_id)

            # Set as default if requested
            if set_as_default:
                self.stripe.Customer.modify(
                    subscription.stripe_customer_id, invoice_settings={'default_payment_method': payment_method_id}
                )
        except Exception as e:
            logger.error(f"Failed to attach payment method to Stripe: {e}")
            return {'success': False, 'error': str(e)}

        # Database operations with retry for locking
        import time

        from django.db import OperationalError, transaction

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Store locally
                    payment_method, _ = PaymentMethod.objects.update_or_create(
                        stripe_payment_method_id=payment_method_id,
                        defaults={
                            'user': user,
                            'card_brand': pm.card.brand if pm.card else '',
                            'card_last4': pm.card.last4 if pm.card else '',
                            'card_exp_month': pm.card.exp_month if pm.card else None,
                            'card_exp_year': pm.card.exp_year if pm.card else None,
                            'is_default': set_as_default,
                        },
                    )

                    if set_as_default:
                        payment_method.set_as_default()

                return {'success': True, 'payment_method': payment_method}

            except OperationalError as e:
                # Retry on SQLite database locked error
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                logger.error(f"Database locked in attach_payment_method: {e}")
                return {'success': False, 'error': 'Database busy, please try again'}
            except Exception as e:
                logger.error(f"Failed to attach payment method locally: {e}")
                return {'success': False, 'error': str(e)}

    def detach_payment_method(self, payment_method) -> bool:
        """Detach a payment method."""
        if not self.is_configured:
            payment_method.delete()
            return True

        try:
            self.stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
            payment_method.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to detach payment method: {e}")
            return False


# Singleton instance
stripe_service = StripeService()


class StripeConnectService:
    """
    Service for Stripe Connect integration.

    Handles:
    - Connected Account creation (Express/Standard)
    - Onboarding links
    - Account status checks
    """

    def __init__(self):
        self._stripe = stripe_service.stripe

    @property
    def is_configured(self) -> bool:
        return stripe_service.is_configured

    def create_account(self, email: str, country: str = 'US') -> str | None:
        """
        Create a Stripe Connect account (Express).

        Args:
            email: Account owner email
            country: Two-letter country code

        Returns:
            Account ID
        """
        if not self.is_configured:
            return None

        try:
            account = self._stripe.Account.create(
                type='express',
                country=country,
                email=email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
                settings={
                    'payouts': {'schedule': {'interval': 'manual'}},  # Platform controls payouts? Or let them manage.
                },
            )
            return account.id
        except Exception as e:
            logger.error(f"Failed to create Connect account: {e}")
            return None

    def create_account_link(self, account_id: str, refresh_url: str, return_url: str) -> str | None:
        """
        Generate an account onboarding link.
        """
        if not self.is_configured:
            return None

        try:
            account_link = self._stripe.AccountLink.create(
                account=account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
            return account_link.url
        except Exception as e:
            logger.error(f"Failed to create account link: {e}")
            return None

    def create_login_link(self, account_id: str) -> str | None:
        """Generate a Stripe Express dashboard login link."""
        if not self.is_configured:
            return None

        try:
            login_link = self._stripe.Account.create_login_link(account_id)
            return login_link.url
        except Exception as e:
            logger.error(f"Failed to create login link: {e}")
            return None

    def get_account_status(self, account_id: str) -> dict:
        """
        Check account status.

        Returns:
            Dict with status info
        """
        if not self.is_configured:
            return {'charges_enabled': False, 'details_submitted': False}

        try:
            account = self._stripe.Account.retrieve(account_id)
            return {
                'charges_enabled': account.charges_enabled,
                'details_submitted': account.details_submitted,
                'payouts_enabled': account.payouts_enabled,
                'requirements': account.requirements,
            }
        except Exception as e:
            logger.error(f"Failed to get account status: {e}")
            return {'error': str(e)}

    def create_payout(self, user, amount_cents: int, currency: str = 'usd') -> dict[str, Any]:
        """
        Initiate a manual payout from the connected account to the external bank account.

        Args:
            user: The organizer user
            amount_cents: Amount to pay out
            currency: Currency code

        Returns:
            Dict with success status and payout details
        """
        from billing.models import PayoutRequest

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        subscription = getattr(user, 'subscription', None)
        if not subscription or not subscription.stripe_connect_account_id:
            return {'success': False, 'error': 'User has no connected account'}

        connect_id = subscription.stripe_connect_account_id

        try:
            # Create Payout in Stripe
            # For Express accounts, we make the API call *on behalf of* the connected account
            payout = self._stripe.Payout.create(
                amount=amount_cents,
                currency=currency,
                stripe_account=connect_id,  # Important: perform on connected account
            )

            # Record in DB
            PayoutRequest.objects.create(
                user=user,
                stripe_connect_account_id=connect_id,
                stripe_payout_id=payout.id,
                amount_cents=amount_cents,
                currency=currency,
                status=PayoutRequest.Status.PENDING,  # Will update via webhook
                arrival_date=datetime.fromtimestamp(payout.arrival_date, tz=UTC) if payout.arrival_date else None,
                destination_bank_last4=getattr(payout.destination, 'last4', ''),
            )

            return {'success': True, 'payout_id': payout.id}

        except Exception as e:
            logger.error(f"Failed to create payout for {user.email}: {e}")
            return {'success': False, 'error': str(e)}

    def get_available_balance(self, user) -> int:
        """Get available balance in cents for connected account."""
        if not self.is_configured:
            return 0

        subscription = getattr(user, 'subscription', None)
        if not subscription or not subscription.stripe_connect_account_id:
            return 0

        try:
            balance = self._stripe.Balance.retrieve(stripe_account=subscription.stripe_connect_account_id)
            # Sum up available funds in default currency
            total = 0
            for fund in balance.available:
                total += fund.amount
            return total
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0


class RefundService:
    """
    Service for processing refunds.

    Handles:
    - Stripe refund creation
    - Fee reversals
    - Registration status updates
    - Audit logging
    """

    def __init__(self):
        self._stripe = stripe_service.stripe

    @property
    def is_configured(self) -> bool:
        return stripe_service.is_configured

    def process_refund(
        self, registration, amount_cents: int | None = None, reason: str = 'requested_by_customer', processed_by=None
    ) -> dict[str, Any]:
        """
        Process a refund for a registration.

        If amount_cents is None (full refund request), we retrieve the original Stripe processing fee
        and deduct it from the refund amount so the platform doesn't pay the fee.

        Args:
            registration: Registration object
            amount_cents: Amount to refund (None for "full" refund minus fees)
            reason: Reason code
            processed_by: User who initiated the refund (optional)

        Returns:
            Dict with success status
        """
        from django.db import transaction

        from billing.models import RefundRecord, TransferRecord
        from registrations.models import Registration

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        if not registration.payment_intent_id:
            return {'success': False, 'error': 'Registration has no payment record'}

        # Default to full refund if amount not specified
        is_full_refund_request = amount_cents is None

        try:
            # 1. Retrieve Payment Intent to get Fees
            # We need to expand latest_charge.balance_transaction to get the fee details
            pi = self._stripe.PaymentIntent.retrieve(
                registration.payment_intent_id,
                expand=['latest_charge.balance_transaction'],
            )

            stripe_fee = 0
            if (
                pi.latest_charge
                and getattr(pi.latest_charge, 'balance_transaction', None)
            ):
                # balance_transaction can be an object or ID, but expand ensures object
                bt = pi.latest_charge.balance_transaction
                if hasattr(bt, 'fee'):
                     stripe_fee = bt.fee

            # Calculate Refund Amount
            if is_full_refund_request:
                # Deduct Stripe fee from the total refundable amount
                # pi.amount_received is what the customer paid
                amount_cents = max(0, pi.amount_received - stripe_fee)

            # Check if amount is valid
            if amount_cents <= 0:
                 return {'success': False, 'error': 'Refund amount after fees is zero or negative.'}

            # 2. Create Refund in Stripe
            refund_params = {
                'payment_intent': registration.payment_intent_id,
                'amount': amount_cents,
                'reason': reason if reason in ['duplicate', 'fraudulent', 'requested_by_customer'] else 'requested_by_customer',
                'reverse_transfer': True,
            }

            # If application fee was taken, we might want to refund it too
            # For now, we accept the default behavior (platform keeps fee unless specified)
            # To reverse fee: refund_application_fee=True

            stripe_refund = self._stripe.Refund.create(**refund_params)

            # 3. Record in DB
            with transaction.atomic():
                RefundRecord.objects.create(
                    registration=registration,
                    processed_by=processed_by,
                    stripe_refund_id=stripe_refund.id,
                    stripe_payment_intent_id=registration.payment_intent_id,
                    amount_cents=stripe_refund.amount,
                    currency=stripe_refund.currency,
                    status=(
                        RefundRecord.Status.SUCCEEDED if stripe_refund.status == 'succeeded' else RefundRecord.Status.PENDING
                    ),
                    reason=reason,
                )

                # Update Registration Status if full refund (or close to it)
                total_amount_cents = int((registration.total_amount or registration.amount_paid) * 100)

                # Check if this is effectively a full refund (allowing for fee deduction)
                # If we refunded everything minus the fee, it counts as a "full" cancellation
                is_effectively_full = False
                if is_full_refund_request or amount_cents >= (total_amount_cents - stripe_fee):
                     is_effectively_full = True

                if is_effectively_full:
                    registration.payment_status = Registration.PaymentStatus.REFUNDED
                    registration.status = Registration.Status.CANCELLED
                    registration.save(update_fields=['payment_status', 'status', 'updated_at'])
                    try:
                        from promo_codes.models import PromoCodeUsage

                        PromoCodeUsage.release_for_registration(registration)
                    except Exception as e:
                        logger.warning("Failed to release promo code usage for %s: %s", registration.uuid, e)
                    if registration.stripe_transfer_id:
                        TransferRecord.objects.filter(
                            stripe_transfer_id=registration.stripe_transfer_id,
                            reversed=False,
                        ).update(reversed=True, reversed_at=timezone.now(), updated_at=timezone.now())

                    # Release seat?
                    # Logic for seat release is usually handled by signal or explicit method
                    # But verifying 'CANCELLED' status should trigger it if implemented.

            if registration.user:
                try:
                    from accounts.notifications import create_notification

                    create_notification(
                        user=registration.user,
                        notification_type='refund_processed',
                        title='Refund processed',
                        message=f"Your refund for {registration.event.title} has been processed.",
                        action_url='/my-events',
                        metadata={'registration_uuid': str(registration.uuid)},
                    )
                except Exception as exc:
                    logger.warning("Failed to create refund notification: %s", exc)

            return {'success': True, 'refund_id': stripe_refund.id}

        except Exception as e:
            logger.error(f"Refund failed for registration {registration.uuid}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


class StripePaymentService:
    """
    Service for processing payments via Stripe Connect.
    """

    def __init__(self):
        self._stripe = stripe_service.stripe

    @property
    def is_configured(self) -> bool:
        return stripe_service.is_configured

    def get_payee_account_id(self, event) -> str | None:
        """Resolve the connected account to receive transfers for this event."""
        payee_account_id = None
        if event.organization and event.organization.stripe_connect_id:
            payee_account_id = event.organization.stripe_connect_id
            if not event.organization.stripe_charges_enabled:
                return None
        elif event.owner.stripe_connect_id:
            payee_account_id = event.owner.stripe_connect_id
            if not event.owner.stripe_charges_enabled:
                return None
        return payee_account_id

    def _calculate_service_fee_cents(self, ticket_amount_cents: int, currency: str) -> int:
        """Calculate service fee in cents based on ticket price."""
        from decimal import ROUND_HALF_UP, Decimal

        from common.config.billing import TicketingFees

        if ticket_amount_cents <= 0:
            return 0

        percent = Decimal(str(TicketingFees.get_service_fee_percent(currency)))
        fixed = Decimal(str(TicketingFees.get_service_fee_fixed(currency)))
        ticket_amount = Decimal(ticket_amount_cents) / Decimal('100')
        fee = (ticket_amount * percent / Decimal('100')).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        ) + fixed
        fee_cents = (fee * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return int(fee_cents)

    def _calculate_processing_fee_cents(self, base_total_cents: int, currency: str) -> int:
        """Calculate processing fee in cents based on total order."""
        from decimal import ROUND_HALF_UP, Decimal

        from common.config.billing import TicketingFees

        if base_total_cents <= 0:
            return 0

        percent = Decimal(str(TicketingFees.get_processing_fee_percent(currency)))
        fixed = Decimal(str(TicketingFees.get_processing_fee_fixed(currency)))
        rate = percent / Decimal('100')
        if rate >= 1:
            raise ValueError("Processing fee percent must be less than 100")

        base_total = Decimal(base_total_cents) / Decimal('100')
        fee = (rate * base_total + fixed) / (Decimal('1') - rate)
        fee = fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        fee_cents = (fee * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return int(fee_cents)

    def _get_ticket_tax_code(self, event) -> str:
        """Get Stripe Tax code for the event ticket."""
        from common.config.billing import TicketingTaxCodes

        if event.format == 'online':
            return TicketingTaxCodes.TICKET_ONLINE
        return TicketingTaxCodes.TICKET_IN_PERSON

    def _get_service_fee_tax_code(self, event) -> str:
        """Get Stripe Tax code for the service fee."""
        from common.config.billing import TicketingTaxCodes

        return TicketingTaxCodes.SERVICE_FEE

    def _build_customer_details(self, registration) -> dict[str, Any]:
        """Build customer details for Stripe Tax."""
        if not registration.billing_country or not registration.billing_postal_code:
            raise ValueError("Billing country and postal code are required for tax calculation")

        address = {
            'country': registration.billing_country,
            'postal_code': registration.billing_postal_code,
        }
        if registration.billing_state:
            address['state'] = registration.billing_state
        if registration.billing_city:
            address['city'] = registration.billing_city

        return {
            'address': address,
            'address_source': 'billing',
        }

    def _create_tax_calculation(
        self,
        currency: str,
        customer_details: dict[str, Any],
        line_items: list[dict[str, Any]],
    ):
        """Create Stripe Tax calculation on the platform account."""
        return self._stripe.tax.Calculation.create(
            currency=currency.lower(),
            customer_details=customer_details,
            line_items=line_items,
            expand=['line_items'],
        )

    def create_tax_transaction_from_calculation(self, calculation_id: str, reference: str | None = None) -> dict[str, Any]:
        """Create a Stripe Tax transaction from a calculation."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        if not calculation_id:
            return {'success': False, 'error': 'Missing tax calculation ID'}

        try:
            transaction = self._stripe.tax.Transaction.create_from_calculation(
                calculation=calculation_id,
                reference=reference or calculation_id,
            )
            return {'success': True, 'tax_transaction_id': transaction.id}
        except Exception as e:
            logger.error(f"Failed to create tax transaction from calculation {calculation_id}: {e}")
            return {'success': False, 'error': str(e)}

    def create_tax_transaction_for_registration(self, registration) -> dict[str, Any]:
        """Create a Stripe Tax transaction for a registration if missing."""
        if registration.stripe_tax_transaction_id:
            return {
                'success': True,
                'tax_transaction_id': registration.stripe_tax_transaction_id,
                'existing': True,
            }

        calculation_id = registration.stripe_tax_calculation_id
        if not calculation_id:
            return {'success': False, 'error': 'Registration missing tax calculation ID'}

        reference = f"registration_{registration.uuid}"
        result = self.create_tax_transaction_from_calculation(calculation_id, reference=reference)
        if result.get('success'):
            registration.stripe_tax_transaction_id = result['tax_transaction_id']
            registration.save(update_fields=['stripe_tax_transaction_id', 'updated_at'])
        return result

    def create_tax_transaction_reversal(self, registration, reference: str | None = None) -> dict[str, Any]:
        """Create a Stripe Tax transaction reversal for a registration."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        if not registration.stripe_tax_transaction_id:
            create_result = self.create_tax_transaction_for_registration(registration)
            if not create_result.get('success'):
                return {
                    'success': False,
                    'error': create_result.get('error', 'Tax transaction not available'),
                }

        try:
            reversal = self._stripe.tax.Transaction.create_reversal(
                original_transaction=registration.stripe_tax_transaction_id,
                mode='full',
                reference=reference or f"refund_{registration.uuid}",
            )
            return {'success': True, 'tax_reversal_id': reversal.id}
        except Exception as e:
            logger.error(f"Failed to create tax transaction reversal for registration {registration.uuid}: {e}")
            return {'success': False, 'error': str(e)}

    def create_payment_intent(self, registration, ticket_amount_cents: int | None = None) -> dict[str, Any]:
        """
        Create a PaymentIntent for a registration.

        Uses destination charges on the platform account with
        an application fee for the platform and transfers to the organizer.

        Args:
            registration: The Registration instance
            ticket_amount_cents: Optional custom ticket amount (after discount).
                                 If not provided, uses registration.amount_paid or event.price.
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        event = registration.event

        payee_account_id = self.get_payee_account_id(event)
        if not payee_account_id:
            return {'success': False, 'error': 'Event organizer is not connected to Stripe or charges are disabled'}

        try:
            # Calculate ticket amount (use custom amount if provided, otherwise stored price)
            if ticket_amount_cents is None:
                if registration.amount_paid:
                    ticket_amount_cents = int(registration.amount_paid * 100)
                else:
                    ticket_amount_cents = int(event.price * 100)

            service_fee_cents = self._calculate_service_fee_cents(ticket_amount_cents, event.currency)
            customer_details = self._build_customer_details(registration)

            base_line_items = [
                {
                    'amount': ticket_amount_cents,
                    'tax_code': self._get_ticket_tax_code(event),
                    'reference': 'ticket',
                    'tax_behavior': 'exclusive',
                }
            ]
            if service_fee_cents > 0:
                base_line_items.append(
                    {
                        'amount': service_fee_cents,
                        'tax_code': self._get_service_fee_tax_code(event),
                        'reference': 'service_fee',
                        'tax_behavior': 'exclusive',
                    }
                )

            base_tax_calc = self._create_tax_calculation(
                currency=event.currency,
                customer_details=customer_details,
                line_items=base_line_items,
            )
            base_total_cents = int(base_tax_calc.amount_total)
            processing_fee_cents = self._calculate_processing_fee_cents(base_total_cents, event.currency)

            final_line_items = list(base_line_items)
            if processing_fee_cents > 0:
                from common.config.billing import TicketingTaxCodes

                final_line_items.append(
                    {
                        'amount': processing_fee_cents,
                        'tax_code': TicketingTaxCodes.NON_TAXABLE,
                        'reference': 'processing_fee',
                        'tax_behavior': 'exclusive',
                    }
                )

            final_tax_calc = self._create_tax_calculation(
                currency=event.currency,
                customer_details=customer_details,
                line_items=final_line_items,
            )

            total_amount_cents = int(final_tax_calc.amount_total)
            tax_cents = int(getattr(final_tax_calc, 'tax_amount_exclusive', 0) or 0)

            intent_params = {
                'amount': total_amount_cents,
                'currency': event.currency.lower(),
                'payment_method_types': ['card'],
                'metadata': {
                    'registration_id': str(registration.uuid),
                    'event_id': str(event.uuid),
                    'event_title': event.title,
                    'payee_account_id': payee_account_id,
                    'ticket_amount_cents': str(ticket_amount_cents),
                    'service_fee_cents': str(service_fee_cents),
                    'processing_fee_cents': str(processing_fee_cents),
                    'tax_cents': str(tax_cents),
                    'tax_calculation_id': final_tax_calc.id,
                },
            }
            intent_params['transfer_data'] = {
                'destination': payee_account_id,
                'amount': ticket_amount_cents,
            }

            intent = stripe_service._with_retry(self._stripe.PaymentIntent.create, **intent_params)

            from decimal import Decimal

            registration.platform_fee_amount = Decimal(service_fee_cents) / Decimal('100')
            registration.service_fee_amount = Decimal(service_fee_cents) / Decimal('100')
            registration.processing_fee_amount = Decimal(processing_fee_cents) / Decimal('100')
            registration.tax_amount = Decimal(tax_cents) / Decimal('100')
            registration.total_amount = Decimal(total_amount_cents) / Decimal('100')
            registration.stripe_tax_calculation_id = final_tax_calc.id
            registration.save(
                update_fields=[
                    'platform_fee_amount',
                    'service_fee_amount',
                    'processing_fee_amount',
                    'tax_amount',
                    'total_amount',
                    'stripe_tax_calculation_id',
                    'updated_at',
                ]
            )

            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'ticket_amount_cents': ticket_amount_cents,
                'service_fee_cents': service_fee_cents,
                'processing_fee_cents': processing_fee_cents,
                'tax_cents': tax_cents,
                'total_amount_cents': total_amount_cents,
                'tax_calculation_id': final_tax_calc.id,
            }

        except Exception as e:
            logger.error(f"Failed to create payment intent: {e}")
            return {'success': False, 'error': str(e)}

    def retrieve_payment_intent(self, payment_intent_id: str):
        """Retrieve a payment intent."""
        if not self.is_configured:
            return None
        try:
            return self._stripe.PaymentIntent.retrieve(payment_intent_id)
        except Exception as e:
            logger.warning(f"Failed to retrieve payment intent {payment_intent_id}: {e}")
            return None

    def refund_payment_intent(self, payment_intent_id: str, registration=None) -> dict[str, Any]:
        """Refund a payment intent and reverse the transfer + application fee."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            refund = self._stripe.Refund.create(
                payment_intent=payment_intent_id,
                reverse_transfer=True,
            )
            result: dict[str, Any] = {'success': True, 'refund_id': refund.id}
            if registration is not None:
                reversal_result = self.create_tax_transaction_reversal(
                    registration,
                    reference=f"refund_{payment_intent_id}",
                )
                if reversal_result.get('success'):
                    result['tax_reversal_id'] = reversal_result.get('tax_reversal_id')
                else:
                    result['tax_reversal_error'] = reversal_result.get('error', 'Tax reversal failed')
            return result
        except Exception as e:
            logger.error(f"Failed to refund payment intent {payment_intent_id}: {e}")
            return {'success': False, 'error': str(e)}


# Singleton instances
stripe_connect_service = StripeConnectService()
stripe_payment_service = StripePaymentService()
