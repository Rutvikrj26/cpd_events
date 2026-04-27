"""Course / Program checkout endpoints.

Thin pass-through to ``billing.checkout.CheckoutService``. Webhooks fulfil
on ``checkout.session.completed``.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from billing.checkout import checkout_service
from common.utils import error_response
from learning.models import Course, CourseEnrollment, Program, ProgramEnrollment


class CourseCheckoutView(generics.GenericAPIView):
    """POST /api/v1/courses/{uuid}/checkout/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, uuid=None):
        course = get_object_or_404(Course, uuid=uuid)

        if CourseEnrollment.objects.filter(
            user=request.user,
            course=course,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).exists():
            return error_response('Already enrolled in this course.', code='ALREADY_ENROLLED')

        ok, code, message = course.check_enrollable()
        if not ok:
            return error_response(message, code=code)

        if course.is_free:
            return error_response('Course is free. Use standard enrollment.', code='COURSE_IS_FREE')

        try:
            result = checkout_service.for_course_enrollment(
                request.user,
                course,
                success_url=request.data.get('success_url'),
                cancel_url=request.data.get('cancel_url'),
            )
        except Exception as exc:
            return error_response(str(exc), code='STRIPE_ERROR')

        return Response({'success': True, 'session_id': result.session_id, 'url': result.url})


class ProgramCheckoutView(generics.GenericAPIView):
    """POST /api/v1/programs/{uuid}/checkout/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, uuid=None):
        program = get_object_or_404(Program, uuid=uuid)

        if program.status != Program.Status.PUBLISHED:
            return error_response(
                'This program is not open for new enrollments.',
                code='NOT_PUBLISHED',
            )

        if ProgramEnrollment.objects.filter(
            user=request.user,
            program=program,
            status__in=[ProgramEnrollment.Status.ACTIVE, ProgramEnrollment.Status.COMPLETED],
        ).exists():
            return error_response('Already enrolled in this program.', code='ALREADY_ENROLLED')

        if program.is_free:
            return error_response('Program is free. Use standard enrollment.', code='PROGRAM_IS_FREE')

        try:
            result = checkout_service.for_program_enrollment(
                request.user,
                program,
                success_url=request.data.get('success_url'),
                cancel_url=request.data.get('cancel_url'),
            )
        except Exception as exc:
            return error_response(str(exc), code='STRIPE_ERROR')

        return Response({'success': True, 'session_id': result.session_id, 'url': result.url})
