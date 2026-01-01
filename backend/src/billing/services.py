"""
Stripe integration service for billing.
"""

import logging
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
        Falls back to global setting if not configured.

        Args:
            plan: The plan name

        Returns:
            Number of trial days
        """
        try:
            from .models import StripeProduct

            product = StripeProduct.objects.filter(plan=plan, is_active=True).first()
            if product:
                return product.get_trial_days()

        except Exception as e:
            logger.error(f"Error getting trial days from database: {e}")

        # Fallback to global setting
        return getattr(settings, 'BILLING_TRIAL_DAYS', 14)

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

        if not self.is_configured:
            # Create local subscription without Stripe
            subscription = Subscription.create_for_user(user, plan)
            return {'success': True, 'subscription': subscription}

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
                'metadata': {
                    'user_uuid': str(user.uuid),
                    'plan': plan,
                },
            }

            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id

            stripe_subscription = self.stripe.Subscription.create(**subscription_params)

            # Update local subscription
            subscription, _ = Subscription.objects.get_or_create(user=user)
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.stripe_customer_id = customer_id
            subscription.plan = plan
            subscription.status = stripe_subscription.status
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_start, tz=timezone.utc
            )
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                stripe_subscription.current_period_end, tz=timezone.utc
            )
            subscription.save()

            return {
                'success': True,
                'subscription': subscription,
                'client_secret': getattr(stripe_subscription.latest_invoice.payment_intent, 'client_secret', None),
            }

        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return {'success': False, 'error': str(e)}

    def cancel_subscription(self, subscription, immediate: bool = False, reason: str = '') -> bool:
        """Cancel a subscription."""
        if not self.is_configured or not subscription.stripe_subscription_id:
            subscription.cancel(reason=reason, immediate=immediate)
            return True

        try:
            if immediate:
                self.stripe.Subscription.delete(subscription.stripe_subscription_id)
            else:
                self.stripe.Subscription.modify(
                    subscription.stripe_subscription_id, cancel_at_period_end=True, metadata={'cancellation_reason': reason}
                )

            subscription.cancel(reason=reason, immediate=immediate)
            return True

        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False

    def reactivate_subscription(self, subscription) -> bool:
        """Reactivate a canceled subscription."""
        if not self.is_configured or not subscription.stripe_subscription_id:
            subscription.reactivate()
            return True

        try:
            self.stripe.Subscription.modify(subscription.stripe_subscription_id, cancel_at_period_end=False)
            subscription.reactivate()
            return True
        except Exception as e:
            logger.error(f"Failed to reactivate subscription: {e}")
            return False

    def update_subscription(self, subscription, new_plan: str, immediate: bool = True) -> dict[str, Any]:
        """
        Update an existing subscription to a new plan.

        Args:
            subscription: Current subscription object
            new_plan: New plan tier to switch to
            immediate: If True, change immediately with proration.
                      If False, schedule change for end of period.

        Returns:
            Dict with success status and updated subscription or error
        """
        from billing.models import Subscription

        # Handle local-only mode (no Stripe configured)
        if not self.is_configured:
            subscription.plan = new_plan
            subscription.save(update_fields=['plan', 'updated_at'])
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

            # Update local database model
            subscription.plan = new_plan
            subscription.status = updated_stripe_sub.get('status', subscription.status)
            subscription.save(update_fields=['plan', 'status', 'updated_at'])

            logger.info(f"Successfully updated subscription {subscription.id} to plan {new_plan}")
            return {'success': True, 'subscription': subscription}

        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Checkout & Portal
    # =========================================================================

    def create_checkout_session(self, user, plan: str, success_url: str, cancel_url: str, organization_uuid: str | None = None) -> dict[str, Any]:
        """Create Stripe Checkout Session."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        price_id = self.get_price_id(plan)
        if not price_id:
            return {'success': False, 'error': f'No price configured for plan: {plan}'}

        # Get trial days from database (per-plan configuration)
        trial_days = self.get_trial_days(plan)

        try:
            customer_id = self.create_customer(user)

            metadata = {
                'user_uuid': str(user.uuid),
                'plan': plan,
            }
            if organization_uuid:
                metadata['organization_uuid'] = organization_uuid

            session = self.stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
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

    def create_payment_intent(self, registration, amount_cents: int = None) -> dict[str, Any]:
        """
        Create a PaymentIntent for a registration.

        Uses Destination Charges (on_behalf_of) or Transfer logic.
        Destination Charges: Platform is responsible.
        Direct Charges: Connected account is responsible.

        We will use Destination Charges with `transfer_data`.

        Args:
            registration: The Registration instance
            amount_cents: Optional custom amount (e.g., after discount).
                          If not provided, uses event.price.
        """
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        event = registration.event

        # Determine payee
        payee_account_id = None
        if event.organization and event.organization.stripe_connect_id:
            payee_account_id = event.organization.stripe_connect_id
        elif event.owner.stripe_connect_id:
            payee_account_id = event.owner.stripe_connect_id

        if not payee_account_id:
            return {'success': False, 'error': 'Event organizer is not connected to Stripe'}

        try:
            # Calculate amount in cents (use custom amount if provided, otherwise event price)
            if amount_cents is None:
                amount_cents = int(event.price * 100)

            # Platform fee (application_fee_amount goes to the platform)
            from django.conf import settings as django_settings
            fee_percent = getattr(django_settings, 'PLATFORM_FEE_PERCENT', 2.0)
            application_fee_cents = int(amount_cents * fee_percent / 100)

            intent = self._stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=event.currency,
                payment_method_types=['card'],
                transfer_data={
                    'destination': payee_account_id,
                },
                application_fee_amount=application_fee_cents,
                metadata={
                    'registration_id': str(registration.uuid),
                    'event_id': str(event.uuid),
                    'event_title': event.title,
                }
            )

            return {
                'success': True,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
            }

        except Exception as e:
            logger.error(f"Failed to create payment intent: {e}")
            return {'success': False, 'error': str(e)}

    def retrieve_payment_intent(self, payment_intent_id: str):
        """Retrieve a payment intent."""
        if not self.is_configured:
            return None
        return self._stripe.PaymentIntent.retrieve(payment_intent_id)

# Singleton instances
stripe_connect_service = StripeConnectService()
stripe_payment_service = StripePaymentService()

