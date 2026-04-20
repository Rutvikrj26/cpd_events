from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from billing.services import stripe_service
from common.utils import error_response
from learning.models import Course, CourseEnrollment, Program, ProgramEnrollment


class CourseCheckoutView(generics.GenericAPIView):
    """
    POST /api/v1/courses/{uuid}/checkout/

    Initiate Stripe Checkout for a paid course.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, uuid=None):
        course = get_object_or_404(Course, uuid=uuid)

        # Check if already enrolled (Active or Completed)
        if CourseEnrollment.objects.filter(
            user=request.user, course=course, status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED]
        ).exists():
            return error_response('Already enrolled in this course.', code='ALREADY_ENROLLED')

        ok, code, message = course.check_enrollable()
        if not ok:
            return error_response(message, code=code)

        if course.is_free:
            return error_response('Course is free. Use standard enrollment.', code='COURSE_IS_FREE')

        if not course.stripe_price_id:
            return error_response('Payment not configured for this course.', code='PAYMENT_NOT_CONFIGURED')

        # Success/Cancel URLs (Frontend)
        # TODO: removing hardcoded localhost if possible, or assume frontend URL comes from env or request?
        # Typically frontend handles this or we assume standard paths.
        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')

        if not success_url or not cancel_url:
            return error_response('success_url and cancel_url are required.', code='MISSING_URLS')

        result = stripe_service.create_one_time_checkout_session(
            user=request.user,
            price_id=course.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={'course_uuid': str(course.uuid), 'type': 'course_enrollment', 'user_id': request.user.id},
            client_reference_id=str(request.user.uuid),
        )

        if not result['success']:
            return error_response(result['error'], code='STRIPE_ERROR')

        return Response(result)


class ProgramCheckoutView(generics.GenericAPIView):
    """
    POST /api/v1/programs/{uuid}/checkout/

    Initiate Stripe Checkout for a Program bundle. On successful payment, the
    webhook activates a ProgramEnrollment which auto-enrolls the learner in
    every member course.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, uuid=None):
        program = get_object_or_404(Program, uuid=uuid)

        if ProgramEnrollment.objects.filter(
            user=request.user,
            program=program,
            status__in=[ProgramEnrollment.Status.ACTIVE, ProgramEnrollment.Status.COMPLETED],
        ).exists():
            return error_response('Already enrolled in this program.', code='ALREADY_ENROLLED')

        if program.is_free:
            return error_response('Program is free. Use standard enrollment.', code='PROGRAM_IS_FREE')

        if not program.stripe_price_id:
            return error_response('Payment not configured for this program.', code='PAYMENT_NOT_CONFIGURED')

        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')
        if not success_url or not cancel_url:
            return error_response('success_url and cancel_url are required.', code='MISSING_URLS')

        result = stripe_service.create_one_time_checkout_session(
            user=request.user,
            price_id=program.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'program_uuid': str(program.uuid),
                'type': 'program_enrollment',
                'user_id': request.user.id,
            },
            client_reference_id=str(request.user.uuid),
        )

        if not result['success']:
            return error_response(result['error'], code='STRIPE_ERROR')

        return Response(result)
