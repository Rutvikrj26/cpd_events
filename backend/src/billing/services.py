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

    def get_price_id(self, plan: str) -> str | None:
        """Get Stripe price ID for a plan."""
        price_ids = getattr(settings, 'STRIPE_PRICE_IDS', {})
        return price_ids.get(plan)

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

    # =========================================================================
    # Checkout & Portal
    # =========================================================================

    def create_checkout_session(self, user, plan: str, success_url: str, cancel_url: str) -> dict[str, Any]:
        """Create Stripe Checkout Session."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        price_id = self.get_price_id(plan)
        if not price_id:
            return {'success': False, 'error': f'No price configured for plan: {plan}'}

        try:
            customer_id = self.create_customer(user)

            session = self.stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_uuid': str(user.uuid),
                    'plan': plan,
                },
            )

            return {'success': True, 'session_id': session.id, 'url': session.url}

        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return {'success': False, 'error': str(e)}

    def create_portal_session(self, user, return_url: str) -> dict[str, Any]:
        """Create Stripe Customer Portal session."""
        if not self.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        subscription = getattr(user, 'subscription', None)
        if not subscription or not subscription.stripe_customer_id:
            return {'success': False, 'error': 'No billing account found'}

        try:
            session = self.stripe.billing_portal.Session.create(customer=subscription.stripe_customer_id, return_url=return_url)
            return {'success': True, 'url': session.url}
        except Exception as e:
            logger.error(f"Failed to create portal session: {e}")
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

    def create_payment_intent(self, registration) -> dict[str, Any]:
        """
        Create a PaymentIntent for a registration.

        Uses Destination Charges (on_behalf_of) or Transfer logic.
        Destination Charges: Platform is responsible.
        Direct Charges: Connected account is responsible.

        We will use Destination Charges with `transfer_data`.
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
            # Calculate amount in cents
            amount_cents = int(event.price * 100)
            
            # Application fee (optional, set to 0 for now)
            application_fee_cents = 0 

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

