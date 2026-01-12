"""
Stripe webhook handlers.
"""

import logging
from datetime import UTC

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
            'checkout.session.completed': self._handle_checkout_session_completed,
            'account.updated': self._handle_account_updated,
            'charge.refunded': self._handle_charge_refunded,
            'charge.dispute.created': self._handle_charge_dispute_created,
            'charge.dispute.closed': self._handle_charge_dispute_closed,
            'customer.updated': self._handle_customer_updated,
            'account.external_account.created': self._handle_external_account_created,
            'account.external_account.deleted': self._handle_external_account_deleted,
            'payout.paid': self._handle_payout_paid,
            'payout.failed': self._handle_payout_failed,
        }

        return handlers.get(event_type)

    def _handle_subscription_created(self, data):
        """Handle subscription.created event."""
        from django.contrib.auth import get_user_model

        from billing.models import StripePrice, StripeProduct, Subscription

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
            subscription.current_period_start = timezone.datetime.fromtimestamp(data['current_period_start'], tz=UTC)
        if data.get('current_period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(data['current_period_end'], tz=UTC)

        plan = None
        billing_interval = None
        metadata = data.get('metadata') or {}
        items = data.get('items', {}).get('data', [])
        if items:
            item = items[0]
            price = item.get('price') if isinstance(item, dict) else getattr(item, 'price', None)
            if price:
                product_id = price.get('product') if isinstance(price, dict) else getattr(price, 'product', None)
                if product_id:
                    product = StripeProduct.objects.filter(stripe_product_id=product_id).first()
                    if product:
                        plan = product.plan
                price_id = price.get('id') if isinstance(price, dict) else getattr(price, 'id', None)
                if not plan and price_id:
                    stripe_price = StripePrice.objects.filter(stripe_price_id=price_id).select_related('product').first()
                    if stripe_price:
                        plan = stripe_price.product.plan
                recurring = price.get('recurring') if isinstance(price, dict) else getattr(price, 'recurring', None)
                if recurring:
                    billing_interval = (
                        recurring.get('interval') if isinstance(recurring, dict) else getattr(recurring, 'interval', None)
                    )

        plan = plan or metadata.get('plan') or subscription.plan
        billing_interval = billing_interval or metadata.get('billing_interval') or subscription.billing_interval

        subscription.plan = plan
        subscription.billing_interval = billing_interval
        subscription.pending_plan = None
        subscription.pending_billing_interval = None
        subscription.pending_change_at = None
        subscription.save()

        # Upgrade user account_type based on plan
        user = subscription.user
        if subscription.plan in ['organizer', 'organization']:
            user.upgrade_to_organizer()
            logger.info(f"Upgraded user {user.email} to organizer via webhook")
        elif subscription.plan == 'lms':
            user.upgrade_to_course_manager()
            logger.info(f"Upgraded user {user.email} to course manager via webhook")

        logger.info(f"Subscription created for customer {customer_id}")

    def _handle_subscription_updated(self, data):
        """Handle subscription.updated event."""
        from billing.models import StripePrice, StripeProduct, Subscription

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
            subscription.current_period_start = timezone.datetime.fromtimestamp(data['current_period_start'], tz=UTC)
        if data.get('current_period_end'):
            subscription.current_period_end = timezone.datetime.fromtimestamp(data['current_period_end'], tz=UTC)
        if data.get('canceled_at'):
            subscription.canceled_at = timezone.datetime.fromtimestamp(data['canceled_at'], tz=UTC)

        if data.get('trial_end'):
            subscription.trial_ends_at = timezone.datetime.fromtimestamp(data['trial_end'], tz=UTC)

        plan = None
        billing_interval = None
        metadata = data.get('metadata') or {}
        items = data.get('items', {}).get('data', [])
        if items:
            item = items[0]
            price = item.get('price') if isinstance(item, dict) else getattr(item, 'price', None)
            if price:
                product_id = price.get('product') if isinstance(price, dict) else getattr(price, 'product', None)
                if product_id:
                    product = StripeProduct.objects.filter(stripe_product_id=product_id).first()
                    if product:
                        plan = product.plan
                price_id = price.get('id') if isinstance(price, dict) else getattr(price, 'id', None)
                if not plan and price_id:
                    stripe_price = StripePrice.objects.filter(stripe_price_id=price_id).select_related('product').first()
                    if stripe_price:
                        plan = stripe_price.product.plan
                recurring = price.get('recurring') if isinstance(price, dict) else getattr(price, 'recurring', None)
                if recurring:
                    billing_interval = (
                        recurring.get('interval') if isinstance(recurring, dict) else getattr(recurring, 'interval', None)
                    )

        plan = plan or metadata.get('plan') or subscription.plan
        billing_interval = billing_interval or metadata.get('billing_interval') or subscription.billing_interval

        subscription.plan = plan
        subscription.billing_interval = billing_interval
        subscription.pending_plan = None
        subscription.pending_billing_interval = None
        subscription.pending_change_at = None
        subscription.save()

        # Upgrade/downgrade user account_type based on plan changes
        user = subscription.user
        if subscription.plan in ['organizer', 'organization']:
            user.upgrade_to_organizer()
        elif subscription.plan == 'lms':
            user.upgrade_to_course_manager()
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
        subscription.user.downgrade_to_attendee()
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
                    timezone.datetime.fromtimestamp(data['period_start'], tz=UTC) if data.get('period_start') else None
                ),
                'period_end': (timezone.datetime.fromtimestamp(data['period_end'], tz=UTC) if data.get('period_end') else None),
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
            },
        )
        try:
            from accounts.notifications import create_notification

            create_notification(
                user=subscription.user,
                notification_type='payment_failed',
                title='Payment failed',
                message='We could not process your latest payment. Please update your billing details.',
                action_url='/billing',
                metadata={
                    'invoice_number': data.get('number', ''),
                    'amount_due_cents': data.get('amount_due', 0),
                    'currency': data.get('currency', 'usd'),
                },
            )
        except Exception as exc:
            logger.warning("Failed to create payment failed notification: %s", exc)

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
                    timezone.datetime.fromtimestamp(data['due_date'], tz=UTC).date() if data.get('due_date') else None
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
        from decimal import Decimal

        from billing.services import stripe_payment_service
        from events.models import Event
        from registrations.models import Registration

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
                        logger.info(f"Registration {registration_id} refunded due to capacity limits via webhook")
                        return

                    logger.error(f"Refund failed for registration {registration_id} via webhook: {refund_result['error']}")
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

                if transfer_id:
                    try:
                        from billing.models import TransferRecord

                        metadata = data.get('metadata', {}) if isinstance(data.get('metadata', {}), dict) else {}
                        ticket_amount_cents = metadata.get('ticket_amount_cents')
                        if ticket_amount_cents is None:
                            ticket_amount_cents = int((locked_reg.amount_paid or 0) * 100)

                        TransferRecord.objects.get_or_create(
                            stripe_transfer_id=transfer_id,
                            defaults={
                                'event': event,
                                'registration': locked_reg,
                                'recipient': event.owner,
                                'stripe_payment_intent_id': locked_reg.payment_intent_id,
                                'amount_cents': int(ticket_amount_cents),
                                'currency': event.currency.lower(),
                                'description': f"Transfer for {event.title}",
                            },
                        )
                    except Exception as exc:
                        logger.warning("Failed to create transfer record for %s: %s", locked_reg.uuid, exc)

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
        try:
            from promo_codes.models import PromoCodeUsage

            PromoCodeUsage.release_for_registration(registration)
        except Exception as e:
            logger.warning("Failed to release promo code usage for %s: %s", registration.uuid, e)

        error_msg = (
            data.get('last_payment_error', {}).get('message', 'Unknown error')
            if data.get('last_payment_error')
            else 'Unknown error'
        )
        logger.warning(f"Payment failed for registration {registration_id} via webhook: {error_msg}")

    def _handle_checkout_session_completed(self, data):
        """
        Handle checkout.session.completed.
        Used for Course Enrollments (and potentially other one-time purchases).
        """
        from django.contrib.auth import get_user_model

        from learning.models import Course, CourseEnrollment

        session_id = data.get('id', 'unknown')
        metadata = data.get('metadata', {})
        txn_type = metadata.get('type')

        if txn_type != 'course_enrollment':
            # Not a course enrollment, skip (may be subscription checkout handled elsewhere)
            return

        course_uuid = metadata.get('course_uuid')
        user_id = metadata.get('user_id')

        if not course_uuid or not user_id:
            logger.error(f"Checkout session {session_id}: Missing course_uuid or user_id in metadata")
            return

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            course = Course.objects.get(uuid=course_uuid)

            # Create or activate enrollment
            enrollment, created = CourseEnrollment.objects.get_or_create(
                user=user, course=course, defaults={'status': CourseEnrollment.Status.ACTIVE}
            )

            if not created and enrollment.status != CourseEnrollment.Status.ACTIVE:
                enrollment.status = CourseEnrollment.Status.ACTIVE
                enrollment.save(update_fields=['status', 'updated_at'])

            logger.info(
                f"Checkout {session_id}: Course enrollment {'created' if created else 'activated'} "
                f"for user_id={user_id} course={course.title}"
            )

        except User.DoesNotExist:
            logger.error(f"Checkout {session_id}: User {user_id} not found")
        except Course.DoesNotExist:
            logger.error(f"Checkout {session_id}: Course {course_uuid} not found")
        except Exception as e:
            logger.error(f"Checkout {session_id}: Error processing course enrollment: {e}")

    # =========================================================================
    # Connect Account Handlers
    # =========================================================================

    def _handle_account_updated(self, data):
        """Handle account.updated (for Connect accounts)."""
        from accounts.models import User
        from organizations.models import Organization

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

    # =========================================================================
    # Refund & Payout Handlers
    # =========================================================================

    def _handle_charge_refunded(self, data):
        """Handle charge.refunded event."""
        from billing.models import RefundRecord
        from registrations.models import Registration

        payment_intent_id = data.get('payment_intent')
        refunds = (data.get('refunds') or {}).get('data') or []

        registration = None
        if payment_intent_id:
            registration = Registration.objects.filter(payment_intent_id=payment_intent_id).first()

        for refund in refunds:
            refund_id = refund.get('id')
            if not refund_id:
                continue

            status = refund.get('status')
            if status == 'succeeded':
                status_value = RefundRecord.Status.SUCCEEDED
            elif status == 'failed':
                status_value = RefundRecord.Status.FAILED
            elif status == 'canceled':
                status_value = RefundRecord.Status.CANCELED
            else:
                status_value = RefundRecord.Status.PENDING

            defaults = {
                'registration': registration,
                'stripe_payment_intent_id': payment_intent_id or '',
                'amount_cents': refund.get('amount', 0),
                'currency': refund.get('currency', 'usd'),
                'status': status_value,
                'reason': refund.get('reason') or RefundRecord.Reason.REQUESTED_BY_CUSTOMER,
                'description': 'Recorded via Stripe webhook',
            }

            refund_record, created = RefundRecord.objects.get_or_create(
                stripe_refund_id=refund_id,
                defaults=defaults,
            )
            if not created:
                refund_record.status = status_value
                refund_record.error_message = refund.get('failure_reason', '') or refund_record.error_message
                refund_record.save(update_fields=['status', 'error_message', 'updated_at'])

        # Update Registration if full refund
        if registration:
            amount = data.get('amount', 0)
            amount_refunded = data.get('amount_refunded', 0)
            if amount and amount_refunded >= amount:
                registration.payment_status = Registration.PaymentStatus.REFUNDED
                registration.status = Registration.Status.CANCELLED
                registration.save(update_fields=['payment_status', 'status', 'updated_at'])
                try:
                    from promo_codes.models import PromoCodeUsage

                    PromoCodeUsage.release_for_registration(registration)
                except Exception as e:
                    logger.warning("Failed to release promo code usage for %s: %s", registration.uuid, e)
                if registration.stripe_transfer_id:
                    from billing.models import TransferRecord

                    TransferRecord.objects.filter(
                        stripe_transfer_id=registration.stripe_transfer_id,
                        reversed=False,
                    ).update(reversed=True, reversed_at=timezone.now(), updated_at=timezone.now())
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

        logger.info(f"Charge refunded for payment_intent_id={payment_intent_id}")

    def _handle_payout_paid(self, data):
        """Handle payout.paid event."""
        from billing.models import PayoutRequest

        payout_id = data.get('id')
        if not payout_id:
            return

        try:
            payout_req = PayoutRequest.objects.get(stripe_payout_id=payout_id)
            payout_req.status = PayoutRequest.Status.PAID
            payout_req.arrival_date = (
                timezone.datetime.fromtimestamp(data.get('arrival_date'), tz=UTC) if data.get('arrival_date') else None
            )
            payout_req.save(update_fields=['status', 'arrival_date', 'updated_at'])
            logger.info(f"Payout confirmed paid: {payout_id}")
        except PayoutRequest.DoesNotExist:
            pass

    def _handle_payout_failed(self, data):
        """Handle payout.failed event."""
        from billing.models import PayoutRequest

        payout_id = data.get('id')
        if not payout_id:
            return

        try:
            payout_req = PayoutRequest.objects.get(stripe_payout_id=payout_id)
            payout_req.status = PayoutRequest.Status.FAILED
            payout_req.error_message = data.get('failure_message', 'Payout failed')
            payout_req.save(update_fields=['status', 'error_message', 'updated_at'])
            logger.warning(f"Payout failed: {payout_id}")
        except PayoutRequest.DoesNotExist:
            pass

    # =========================================================================
    # Dispute & Customer Handlers
    # =========================================================================

    def _handle_charge_dispute_created(self, data):
        """Handle charge.dispute.created event."""
        from billing.models import DisputeRecord
        from registrations.models import Registration

        dispute_id = data.get('id')
        if not dispute_id:
            return

        payment_intent_id = data.get('payment_intent')
        registration = None
        if payment_intent_id:
            registration = Registration.objects.filter(payment_intent_id=payment_intent_id).first()

        DisputeRecord.objects.update_or_create(
            stripe_dispute_id=dispute_id,
            defaults={
                'registration': registration,
                'stripe_charge_id': data.get('charge', ''),
                'stripe_payment_intent_id': payment_intent_id or '',
                'amount_cents': data.get('amount', 0),
                'currency': data.get('currency', 'usd'),
                'reason': data.get('reason', ''),
                'status': data.get('status', DisputeRecord.Status.NEEDS_RESPONSE),
                'evidence_due_by': (
                    timezone.datetime.fromtimestamp(data['evidence_details']['due_by'], tz=UTC)
                    if data.get('evidence_details', {}).get('due_by')
                    else None
                ),
            },
        )
        logger.warning(f"Dispute created: {dispute_id}")

    def _handle_charge_dispute_closed(self, data):
        """Handle charge.dispute.closed event."""
        from billing.models import DisputeRecord

        dispute_id = data.get('id')
        if not dispute_id:
            return

        DisputeRecord.objects.filter(stripe_dispute_id=dispute_id).update(
            status=data.get('status', DisputeRecord.Status.LOST),
            closed_at=timezone.now(),
            updated_at=timezone.now(),
        )
        logger.info(f"Dispute closed: {dispute_id}")

    def _handle_customer_updated(self, data):
        """Handle customer.updated event."""
        customer_id = data.get('id')
        if not customer_id:
            return

        logger.info("Customer updated: %s", customer_id)

    def _handle_external_account_created(self, data):
        """Handle account.external_account.created event."""
        account_id = data.get('account')
        logger.info("External account created for %s", account_id)

    def _handle_external_account_deleted(self, data):
        """Handle account.external_account.deleted event."""
        account_id = data.get('account')
        logger.warning("External account deleted for %s", account_id)
