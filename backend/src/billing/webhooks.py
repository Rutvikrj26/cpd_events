"""
Stripe webhook handlers.
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Handle Stripe webhooks.

    POST /webhooks/stripe/
    """

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if not sig_header:
            logger.warning("Missing Stripe signature header")
            return HttpResponse(status=400)

        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

        if not webhook_secret:
            logger.warning("Stripe webhook secret not configured")
            return HttpResponse(status=500)

        try:
            import stripe

            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return HttpResponse(status=400)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return HttpResponse(status=400)

        # Handle the event
        event_type = event['type']
        event_data = event['data']['object']

        handler = self._get_handler(event_type)
        if handler:
            try:
                handler(event_data)
            except Exception as e:
                logger.error(f"Error handling webhook {event_type}: {e}")
                return HttpResponse(status=500)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

        return HttpResponse(status=200)

    def _get_handler(self, event_type: str):
        """Get handler function for event type."""
        handlers = {
            'customer.subscription.created': self._handle_subscription_created,
            'customer.subscription.updated': self._handle_subscription_updated,
            'customer.subscription.deleted': self._handle_subscription_deleted,
            'invoice.paid': self._handle_invoice_paid,
            'invoice.payment_failed': self._handle_invoice_payment_failed,
            'invoice.finalized': self._handle_invoice_finalized,
            'payment_method.attached': self._handle_payment_method_attached,
            'payment_method.detached': self._handle_payment_method_detached,
        }
        return handlers.get(event_type)

    def _handle_subscription_created(self, data):
        """Handle subscription.created event."""
        from django.contrib.auth import get_user_model

        from billing.models import Subscription

        get_user_model()

        customer_id = data.get('customer')
        if not customer_id:
            return

        # Find user by customer ID
        try:
            subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        except Subscription.DoesNotExist:
            logger.warning(f"No subscription found for customer {customer_id}")
            return

        subscription.stripe_subscription_id = data.get('id')
        subscription.status = data.get('status', 'active')

        if data.get('current_period_start'):
            subscription.current_period_start = timezone.datetime.fromtimestamp(data['current_period_start'], tz=timezone.utc)
        if data.get('current_period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(data['current_period_end'], tz=timezone.utc)

        subscription.save()
        logger.info(f"Subscription created for customer {customer_id}")

    def _handle_subscription_updated(self, data):
        """Handle subscription.updated event."""
        from billing.models import Subscription

        subscription_id = data.get('id')
        if not subscription_id:
            return

        try:
            subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            logger.warning(f"No subscription found for {subscription_id}")
            return

        subscription.status = data.get('status', subscription.status)
        subscription.cancel_at_period_end = data.get('cancel_at_period_end', False)

        if data.get('current_period_start'):
            subscription.current_period_start = timezone.datetime.fromtimestamp(data['current_period_start'], tz=timezone.utc)
        if data.get('current_period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(data['current_period_end'], tz=timezone.utc)
        if data.get('canceled_at'):
            subscription.canceled_at = timezone.datetime.fromtimestamp(data['canceled_at'], tz=timezone.utc)

        subscription.save()
        logger.info(f"Subscription updated: {subscription_id}")

    def _handle_subscription_deleted(self, data):
        """Handle subscription.deleted event."""
        from billing.models import Subscription

        subscription_id = data.get('id')
        if not subscription_id:
            return

        try:
            subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            return

        subscription.status = Subscription.Status.CANCELED
        subscription.canceled_at = timezone.now()
        subscription.save()
        logger.info(f"Subscription deleted: {subscription_id}")

    def _handle_invoice_paid(self, data):
        """Handle invoice.paid event."""
        from billing.models import Invoice, Subscription

        invoice_id = data.get('id')
        customer_id = data.get('customer')

        if not invoice_id or not customer_id:
            return

        try:
            subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        except Subscription.DoesNotExist:
            return

        Invoice.objects.update_or_create(
            stripe_invoice_id=invoice_id,
            defaults={
                'user': subscription.user,
                'subscription': subscription,
                'amount_cents': data.get('amount_paid', 0),
                'currency': data.get('currency', 'usd'),
                'status': Invoice.Status.PAID,
                'invoice_pdf_url': data.get('invoice_pdf', ''),
                'hosted_invoice_url': data.get('hosted_invoice_url', ''),
                'paid_at': timezone.now(),
                'period_start': (
                    timezone.datetime.fromtimestamp(data['period_start'], tz=timezone.utc) if data.get('period_start') else None
                ),
                'period_end': (
                    timezone.datetime.fromtimestamp(data['period_end'], tz=timezone.utc) if data.get('period_end') else None
                ),
            },
        )

        # Reset usage counters on successful payment
        subscription.reset_usage()
        logger.info(f"Invoice paid: {invoice_id}")

    def _handle_invoice_payment_failed(self, data):
        """Handle invoice.payment_failed event."""
        from billing.models import Invoice, Subscription

        invoice_id = data.get('id')
        customer_id = data.get('customer')

        if not invoice_id or not customer_id:
            return

        try:
            subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        except Subscription.DoesNotExist:
            return

        # Mark subscription as past due
        subscription.status = Subscription.Status.PAST_DUE
        subscription.save(update_fields=['status', 'updated_at'])

        # Update or create invoice record
        Invoice.objects.update_or_create(
            stripe_invoice_id=invoice_id,
            defaults={
                'user': subscription.user,
                'subscription': subscription,
                'amount_cents': data.get('amount_due', 0),
                'currency': data.get('currency', 'usd'),
                'status': Invoice.Status.OPEN,
            },
        )

        logger.warning(f"Invoice payment failed: {invoice_id}")
        # TODO: Send payment failed notification email

    def _handle_invoice_finalized(self, data):
        """Handle invoice.finalized event."""
        from billing.models import Invoice, Subscription

        invoice_id = data.get('id')
        customer_id = data.get('customer')

        if not invoice_id or not customer_id:
            return

        try:
            subscription = Subscription.objects.get(stripe_customer_id=customer_id)
        except Subscription.DoesNotExist:
            return

        Invoice.objects.update_or_create(
            stripe_invoice_id=invoice_id,
            defaults={
                'user': subscription.user,
                'subscription': subscription,
                'amount_cents': data.get('amount_due', 0),
                'currency': data.get('currency', 'usd'),
                'status': Invoice.Status.OPEN,
                'invoice_pdf_url': data.get('invoice_pdf', ''),
                'hosted_invoice_url': data.get('hosted_invoice_url', ''),
                'due_date': (
                    timezone.datetime.fromtimestamp(data['due_date'], tz=timezone.utc).date() if data.get('due_date') else None
                ),
            },
        )
        logger.info(f"Invoice finalized: {invoice_id}")

    def _handle_payment_method_attached(self, data):
        """Handle payment_method.attached event."""
        # Payment methods are handled via API, this is for sync
        logger.info(f"Payment method attached: {data.get('id')}")

    def _handle_payment_method_detached(self, data):
        """Handle payment_method.detached event."""
        from billing.models import PaymentMethod

        pm_id = data.get('id')
        if pm_id:
            PaymentMethod.objects.filter(stripe_payment_method_id=pm_id).delete()
            logger.info(f"Payment method detached: {pm_id}")
