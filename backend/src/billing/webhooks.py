"""
Stripe webhook handlers.
"""

import logging
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db import transaction
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
            'payment_intent.succeeded': self._handle_payment_intent_succeeded,
            'payment_intent.payment_failed': self._handle_payment_intent_payment_failed,
            'account.updated': self._handle_account_updated,
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
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                data['current_period_start'], tz=dt_timezone.utc
            )
        if data.get('current_period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                data['current_period_end'], tz=dt_timezone.utc
            )

        subscription.save()
        
        # Upgrade user account_type based on plan
        user = subscription.user
        if subscription.plan in ['professional', 'organization']:
            user.upgrade_to_organizer()
            logger.info(f"Upgraded user {user.email} to organizer via webhook")
        
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
            subscription.current_period_start = timezone.datetime.fromtimestamp(
                data['current_period_start'], tz=dt_timezone.utc
            )
        if data.get('current_period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(
                data['current_period_end'], tz=dt_timezone.utc
            )
        if data.get('canceled_at'):
            subscription.canceled_at = timezone.datetime.fromtimestamp(
                data['canceled_at'], tz=dt_timezone.utc
            )

        subscription.save()
        
        # Upgrade/downgrade user account_type based on plan changes
        user = subscription.user
        if subscription.plan in ['professional', 'organization']:
            user.upgrade_to_organizer()
        elif subscription.plan == 'attendee' and subscription.status == 'canceled':
            user.downgrade_to_attendee()
        
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
                    timezone.datetime.fromtimestamp(
                        data['period_start'], tz=dt_timezone.utc
                    )
                    if data.get('period_start')
                    else None
                ),
                'period_end': (
                    timezone.datetime.fromtimestamp(
                        data['period_end'], tz=dt_timezone.utc
                    )
                    if data.get('period_end')
                    else None
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
        # Send payment failed notification email
        from integrations.services import email_service
        
        email_service.send_email(
            template='payment_failed',
            recipient=subscription.user.email,
            context={
                'invoice_number': data.get('number', ''),
                'amount_due': f"{data.get('amount_due', 0) / 100:.2f}",
                'currency': data.get('currency', 'usd').upper(),
                'pay_url': data.get('hosted_invoice_url', ''),
                'user_name': subscription.user.full_name,
            }
        )

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
                    timezone.datetime.fromtimestamp(data['due_date'], tz=dt_timezone.utc).date()
                    if data.get('due_date')
                    else None
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

    # =========================================================================
    # Payment Intent Handlers (for One-time Payments)
    # =========================================================================

    def _handle_payment_intent_succeeded(self, data):
        """
        Handle payment_intent.succeeded - fallback for sync confirmation.

        This is now a FALLBACK handler. Primary payment confirmation happens
        via the synchronous /confirm-payment/ endpoint. This webhook ensures
        payments are eventually confirmed even if frontend call fails.
        """
        from registrations.models import Registration
        from billing.services import stripe_payment_service
        from events.models import Event
        from decimal import Decimal

        metadata = data.get('metadata', {})
        registration_id = metadata.get('registration_id')

        if not registration_id:
            logger.warning(f"PaymentIntent succeeded ({data['id']}) but no registration_id in metadata.")
            return

        try:
            registration = Registration.objects.get(uuid=registration_id)
        except Registration.DoesNotExist:
            logger.error(f"Registration {registration_id} not found for payment {data['id']}")
            return

        # Update registration status (fallback path)
        try:
            with transaction.atomic():
                # Lock the row
                locked_reg = Registration.objects.select_for_update().get(pk=registration.pk)
                event = Event.objects.select_for_update().get(pk=locked_reg.event_id)

                charges = data.get('charges', {}).get('data', [])
                transfer_id = charges[0].get('transfer') if charges else None
                if not isinstance(transfer_id, str) or not transfer_id.strip():
                    transfer_id = None
                
                # Check idempotency again under lock
                if locked_reg.payment_status == Registration.PaymentStatus.PAID:
                    logger.info(f"Registration {registration_id} already PAID, skipping webhook update")
                    return

                amount_received = data.get('amount_received', 0)
                confirmed_count = Registration.objects.filter(
                    event=event,
                    status=Registration.Status.CONFIRMED,
                    deleted_at__isnull=True,
                ).count()

                if event.max_attendees and confirmed_count >= event.max_attendees:
                    refund_result = stripe_payment_service.refund_payment_intent(
                        data['id'],
                        registration=locked_reg,
                    )

                    if refund_result['success']:
                        locked_reg.payment_status = Registration.PaymentStatus.REFUNDED
                        locked_reg.total_amount = Decimal(amount_received) / Decimal('100')
                        locked_reg.save(update_fields=['payment_status', 'total_amount', 'updated_at'])
                        logger.info(
                            f"Registration {registration_id} refunded due to capacity limits via webhook"
                        )
                        return

                    logger.error(
                        f"Refund failed for registration {registration_id} via webhook: {refund_result['error']}"
                    )
                    return

                locked_reg.total_amount = Decimal(amount_received) / Decimal('100')
                locked_reg.payment_status = Registration.PaymentStatus.PAID

                # Update status from PENDING to CONFIRMED after payment
                status_changed = False
                if locked_reg.status == Registration.Status.PENDING:
                    locked_reg.status = Registration.Status.CONFIRMED
                    status_changed = True

                update_fields = ['total_amount', 'payment_status', 'status', 'updated_at']
                if transfer_id and not locked_reg.stripe_transfer_id:
                    locked_reg.stripe_transfer_id = transfer_id
                    update_fields.append('stripe_transfer_id')
                locked_reg.save(update_fields=update_fields)
                logger.info(f"Registration {registration_id} marked as PAID via webhook fallback {data['id']}")

                tax_result = stripe_payment_service.create_tax_transaction_for_registration(locked_reg)
                if not tax_result.get('success'):
                    logger.warning(
                        "Failed to create tax transaction for registration %s via webhook: %s",
                        registration_id,
                        tax_result.get('error'),
                    )

                # Trigger Zoom registrant addition if status changed to CONFIRMED
                if status_changed:
                    from registrations.tasks import add_zoom_registrant
                    add_zoom_registrant.delay(locked_reg.id)
        except Exception as e:
            logger.error(f"Error locking registration {registration_id} in webhook: {e}")
            raise

    def _handle_payment_intent_payment_failed(self, data):
        """
        Handle payment_intent.payment_failed - fallback for sync confirmation.

        This is now a FALLBACK handler. Primary failure handling happens
        via the synchronous /confirm-payment/ endpoint.
        """
        from registrations.models import Registration

        metadata = data.get('metadata', {})
        registration_id = metadata.get('registration_id')

        if not registration_id:
            return

        try:
            registration = Registration.objects.get(uuid=registration_id)
        except Registration.DoesNotExist:
            return

        # IDEMPOTENT: Skip if already failed or paid
        if registration.payment_status in [Registration.PaymentStatus.FAILED, Registration.PaymentStatus.PAID]:
            logger.info(f"Registration {registration_id} already {registration.payment_status}, skipping webhook update")
            return

        registration.payment_status = Registration.PaymentStatus.FAILED
        registration.save(update_fields=['payment_status', 'updated_at'])

        error_msg = data.get('last_payment_error', {}).get('message', 'Unknown error') if data.get('last_payment_error') else 'Unknown error'
        logger.warning(f"Payment failed for registration {registration_id} via webhook: {error_msg}")

    # =========================================================================
    # Connect Account Handlers
    # =========================================================================

    def _handle_account_updated(self, data):
        """Handle account.updated (for Connect accounts)."""
        from organizations.models import Organization
        from accounts.models import User

        account_id = data.get('id')
        if not account_id:
            return

        # Helper to update status
        def update_status(obj):
            charges_enabled = data.get('charges_enabled', False)
            details_submitted = data.get('details_submitted', False)

            obj.stripe_charges_enabled = charges_enabled
            
            if charges_enabled:
                obj.stripe_account_status = 'active'
            elif details_submitted:
                obj.stripe_account_status = 'pending_verification'
            else:
                obj.stripe_account_status = 'restricted'
                
            obj.save(update_fields=['stripe_charges_enabled', 'stripe_account_status'])
            logger.info(f"Updated Connect account status for {obj.__class__.__name__} {obj.uuid}: {obj.stripe_account_status}")

        # Try Organization first
        try:
            org = Organization.objects.get(stripe_connect_id=account_id)
            update_status(org)
            return
        except Organization.DoesNotExist:
            pass
            
        # Try User
        try:
            user = User.objects.get(stripe_connect_id=account_id)
            update_status(user)
            return
        except User.DoesNotExist:
            logger.warning(f"Received account.updated for unknown Connect account: {account_id}")
