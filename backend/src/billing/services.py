"""
Stripe integration service for billing.
"""

import logging
from datetime import datetime, timedelta, timezone as dt_timezone
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

    def get_price_id(self, plan: str, annual: bool = False) -> str | None:
        """
        Get Stripe price ID for a plan.

        Now reads from database instead of environment variables.
        Falls back to settings if database is empty (for backward compatibility).

        Args:
            plan: The plan name (e.g., 'starter', 'professional', 'premium')
            annual: Whether to get annual pricing (default: False for monthly)

        Returns:
            Stripe price ID or None
        """
        if not self.is_configured:
            return None

        try:
            from .models import StripeProduct, StripePrice

            # Find product for this plan
            product = StripeProduct.objects.filter(plan=plan, is_active=True).first()
            if not product:
                # Fallback to environment variables
                logger.warning(f"No StripeProduct found for plan '{plan}', falling back to settings")
                price_ids = getattr(settings, 'STRIPE_PRICE_IDS', {})
                price_key = f"{plan}_annual" if annual else plan
                return price_ids.get(price_key)

            # Find price for billing interval
            interval = 'year' if annual else 'month'
            price = product.prices.filter(billing_interval=interval, is_active=True).first()

            if not price:
                logger.warning(f"No active price found for plan '{plan}' with interval '{interval}'")
                # Fallback to environment variables
                price_ids = getattr(settings, 'STRIPE_PRICE_IDS', {})
                price_key = f"{plan}_annual" if annual else plan
                return price_ids.get(price_key)

            return price.stripe_price_id

        except Exception as e:
            logger.error(f"Error getting price ID from database: {e}")
            # Fallback to environment variables
            price_ids = getattr(settings, 'STRIPE_PRICE_IDS', {})
            price_key = f"{plan}_annual" if annual else plan
            return price_ids.get(price_key)

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
            customer = self.stripe.Customer.create(
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

    # =========================================================================
    # Subscription Management
    # =========================================================================

    def create_subscription(self, user, plan: str, payment_method_id: str | None = None) -> dict[str, Any]:
        """
        Create a subscription for a user.

        Returns:
            Dict with subscription details or error
        """
        from billing.models import Subscription
        from django.db import transaction

        if not self.is_configured:
            # Create local subscription without Stripe
            with transaction.atomic():
                subscription = Subscription.create_for_user(user, plan)
                # Upgrade user account_type in same transaction
                if plan in ['professional', 'organization']:
                    user.upgrade_to_organizer()
            return {'success': True, 'subscription': subscription}

        # Check for existing active subscription (uniqueness enforcement)
        existing = getattr(user, 'subscription', None)
        if existing and existing.stripe_subscription_id and existing.status in ['active', 'trialing']:
            return {
                'success': False,
                'error': 'User already has an active subscription. Use update to change plans.'
            }

        price_id = self.get_price_id(plan)
        if not price_id:
            return {'success': False, 'error': f'No price configured for plan: {plan}'}

        try:
            # Ensure customer exists
            customer_id = self.create_customer(user)
            if not customer_id:
                return {'success': False, 'error': 'Failed to create customer'}

            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'expand': ['latest_invoice.payment_intent'],
                'automatic_tax': {'enabled': True},
                'metadata': {
                    'user_uuid': str(user.uuid),
                    'plan': plan,
                },
            }

            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id

            stripe_subscription = self.stripe.Subscription.create(**subscription_params)

            # Atomically update local subscription
            with transaction.atomic():
                subscription, _ = Subscription.objects.select_for_update().get_or_create(user=user)
                subscription.stripe_subscription_id = stripe_subscription.id
                subscription.stripe_customer_id = customer_id
                subscription.plan = plan
                subscription.status = stripe_subscription.status
                subscription.current_period_start = datetime.fromtimestamp(
                    stripe_subscription.current_period_start, tz=dt_timezone.utc
                )
                subscription.current_period_end = datetime.fromtimestamp(
                    stripe_subscription.current_period_end, tz=dt_timezone.utc
                )
                subscription.save()

                # Upgrade user account_type in same transaction
                if plan in ['professional', 'organization']:
                    user.upgrade_to_organizer()

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

    def update_subscription(self, subscription, new_plan: str, immediate: bool = True) -> dict[str, Any]:
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
        from billing.models import Subscription
        from django.db import transaction

        # Handle local-only mode (no Stripe configured)
        if not self.is_configured:
            with transaction.atomic():
                subscription.plan = new_plan
                subscription.save(update_fields=['plan', 'updated_at'])
                # Update user account_type in same transaction
                if new_plan in ['professional', 'organization']:
                    subscription.user.upgrade_to_organizer()
                elif new_plan == 'attendee':
                    subscription.user.downgrade_to_attendee()
            return {'success': True, 'subscription': subscription}

        # Validate plan exists
        if new_plan not in [choice[0] for choice in Subscription.Plan.choices]:
            return {'success': False, 'error': f'Invalid plan: {new_plan}'}

        # Get price ID for new plan
        price_id = self.get_price_id(new_plan)
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

            # Prepare modification parameters
            modification_params = {
                'items': [{
                    'id': item_id,
                    'price': price_id,
                }],
            }

            if immediate:
                # Immediate upgrade with proration
                modification_params['proration_behavior'] = 'always_invoice'
                modification_params['billing_cycle_anchor'] = 'unchanged'
            else:
                # Schedule change for end of period (downgrade)
                modification_params['proration_behavior'] = 'none'
                modification_params['billing_cycle_anchor'] = 'unchanged'

            # Update subscription in Stripe
            updated_stripe_sub = self.stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                **modification_params
            )

            # Atomically update local database
            with transaction.atomic():
                subscription.plan = new_plan
                subscription.status = updated_stripe_sub.get('status', subscription.status)
                subscription.save(update_fields=['plan', 'status', 'updated_at'])
                # Update user account_type in same transaction
                if new_plan in ['professional', 'organization']:
                    subscription.user.upgrade_to_organizer()
                elif new_plan == 'attendee':
                    subscription.user.downgrade_to_attendee()

            logger.info(f"Successfully updated subscription {subscription.id} to plan {new_plan}")
            return {'success': True, 'subscription': subscription}

        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            return {'success': False, 'error': str(e)}

    def sync_subscription(self, user) -> dict[str, Any]:
        """
        Sync local subscription with Stripe atomically.
        Useful when webhooks are not available (e.g. local dev).
        """
        from billing.models import Subscription, StripeProduct
        from django.db import transaction

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
                subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start, tz=dt_timezone.utc)
                subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end, tz=dt_timezone.utc)
                subscription.trial_ends_at = datetime.fromtimestamp(stripe_sub.trial_end, tz=dt_timezone.utc) if stripe_sub.trial_end else None
                subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
                subscription.canceled_at = datetime.fromtimestamp(stripe_sub.canceled_at, tz=dt_timezone.utc) if stripe_sub.canceled_at else None

                # Determine plan from price
                if stripe_sub.get('items') and stripe_sub['items'].data:
                    try:
                        product_id = stripe_sub['items'].data[0].price.product
                        local_product = StripeProduct.objects.filter(stripe_product_id=product_id).first()
                        if local_product:
                            subscription.plan = local_product.plan
                    except Exception as e:
                        logger.warning(f"Could not map Stripe product to local plan: {e}")

                subscription.save()

                # Upgrade/downgrade account_type in same transaction
                if subscription.plan in ['professional', 'organization']:
                    user.upgrade_to_organizer()
                    logger.info(f"Upgraded user {user.email} to organizer based on plan {subscription.plan}")
                elif subscription.plan == 'attendee':
                    user.downgrade_to_attendee()
                    logger.info(f"Downgraded user {user.email} to attendee")

            return {'success': True, 'subscription': subscription}

        except Exception as e:
            logger.error(f"Failed to sync subscription: {e}")
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Checkout & Portal
    # =========================================================================

    def create_checkout_session(self, user, plan: str, success_url: str, cancel_url: str, organization_uuid: str | None = None) -> dict[str, Any]:
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
                        'error': 'You already have an active subscription. Use the billing portal to upgrade.'
                    }
            except Exception:
                pass  # Subscription doesn't exist in Stripe, continue with checkout

        price_id = self.get_price_id(plan)
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
        from billing.models import Subscription, StripeProduct
        from django.db import transaction

        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        for attempt in range(max_retries):
            try:
                # 1. Retrieve checkout session from Stripe
                session = self.stripe.checkout.Session.retrieve(
                    session_id,
                    expand=['subscription', 'subscription.latest_invoice']
                )

                # 2. Verify session belongs to this user (via customer or metadata)
                existing_sub = getattr(user, 'subscription', None)
                expected_customer = existing_sub.stripe_customer_id if existing_sub else None

                # Check by customer ID or metadata
                session_belongs_to_user = (
                    (expected_customer and session.customer == expected_customer) or
                    session.metadata.get('user_uuid') == str(user.uuid)
                )

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

                # 4. Check for duplicate subscription (uniqueness enforcement)
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
                                logger.warning(f"User {user.email} already has subscription {subscription.stripe_subscription_id}, canceling new one {stripe_sub.id}")
                                self.stripe.Subscription.cancel(stripe_sub.id)
                                return {'success': False, 'error': 'User already has an active subscription'}
                        except Exception:
                            pass  # Existing subscription doesn't exist, continue with new one

                    # 5. Update subscription fields
                    subscription.stripe_subscription_id = stripe_sub.id
                    subscription.stripe_customer_id = session.customer
                    subscription.status = stripe_sub.status
                    subscription.current_period_start = datetime.fromtimestamp(
                        stripe_sub.current_period_start, tz=dt_timezone.utc
                    )
                    subscription.current_period_end = datetime.fromtimestamp(
                        stripe_sub.current_period_end, tz=dt_timezone.utc
                    )

                    # Handle trial
                    if stripe_sub.trial_end:
                        subscription.trial_ends_at = datetime.fromtimestamp(
                            stripe_sub.trial_end, tz=dt_timezone.utc
                        )

                    # Determine plan from metadata or price
                    plan = session.metadata.get('plan')
                    if not plan:
                        # Try to determine from subscription items
                        if stripe_sub.get('items') and stripe_sub['items'].data:
                            try:
                                product_id = stripe_sub['items'].data[0].price.product
                                local_product = StripeProduct.objects.filter(stripe_product_id=product_id).first()
                                if local_product:
                                    plan = local_product.plan
                            except Exception:
                                pass
                    plan = plan or 'professional'  # Default to professional if unknown

                    subscription.plan = plan
                    subscription.save()

                    # 6. Upgrade user account_type in same transaction
                    if plan in ['professional', 'organization']:
                        user.upgrade_to_organizer()
                        logger.info(f"User {user.email} upgraded to organizer via checkout confirmation")

                sync_result = self.sync_payment_methods(user, customer_id=session.customer)
                if not sync_result['success']:
                    logger.warning(
                        f"Checkout session {session_id} confirmed, but payment method sync failed: {sync_result['error']}"
                    )

                logger.info(f"Checkout session {session_id} confirmed for user {user.email}, subscription {stripe_sub.id}")
                return {'success': True, 'subscription': subscription}

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                logger.error(f"Failed to confirm checkout session: {e}")
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Max retries exceeded'}

    def sync_payment_methods(self, user, customer_id: str | None = None) -> dict[str, Any]:
        """
        Sync Stripe payment methods into local PaymentMethod records.

        Intended to be called after checkout/portal flows; webhooks are fallback.
        """
        from billing.models import PaymentMethod
        from django.db import transaction

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
                customer.get('invoice_settings', {}) if isinstance(customer, dict) else getattr(customer, 'invoice_settings', {})
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

    def create_portal_session(self, user, return_url: str) -> dict[str, Any]:
        """Create Stripe Customer Portal session."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        # Get or create Stripe customer for trial users
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

        except Exception as e:
            logger.error(f"Failed to attach payment method: {e}")
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
                    'payouts': {'schedule': {'interval': 'manual'}}, # Platform controls payouts? Or let them manage.
                }
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
        from decimal import Decimal, ROUND_HALF_UP
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
        from decimal import Decimal, ROUND_HALF_UP
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
            logger.error(
                f"Failed to create tax transaction reversal for registration {registration.uuid}: {e}"
            )
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

            intent = self._stripe.PaymentIntent.create(**intent_params)

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
