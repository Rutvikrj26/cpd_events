"""Serializers for the typed-contract bootstrap endpoints.

Kept separate from ``learning.serializers`` so the bootstrap shapes don't
get tangled up with the existing CRUD serializers used by drf-yasg-era
endpoints. drf-spectacular reads each one's ``Meta.fields`` (or the
explicit field list) and emits a discriminated union into the OpenAPI
schema, which openapi-typescript turns into a TypeScript discriminated
union the frontend can ``switch`` on.

Three response shapes for the player bootstrap, all served as HTTP 200:

- ``CoursePlayerGrantedSerializer`` — ``access.kind == "granted"``: the
  full curriculum + progress + sessions + announcements + submissions
  the player needs to render in one paint.
- ``CoursePlayerPendingApprovalSerializer`` — ``access.kind ==
  "pending_approval"``: a slim response carrying the data the
  pending-approval shell needs.
- ``CoursePlayerRedirectSerializer`` — ``access.kind ==
  "redirect_to_detail"``: tells the client to navigate to
  ``/courses/{slug}`` with a reason. No course data; the catalog page
  fetches what it needs.

The discriminator at the wire level is ``access.kind``. The Python
union is expressed via ``PolymorphicProxySerializer``.
"""

from __future__ import annotations

from rest_framework import serializers

from .serializers import (
    CourseAnnouncementSerializer,
    CourseModuleSerializer,
    CourseSerializer,
    LiveSessionSerializer,
)


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------


class _SlimCourseSerializer(serializers.Serializer):
    """Minimum course fields for non-granted shells.

    Just enough for "you're enrolled in X, awaiting approval" / "navigate
    to X" UIs to render without fetching the full course payload. The full
    ``CourseSerializer`` is overkill for shells that don't render the
    curriculum.
    """

    uuid = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.CharField()
    featured_image_url = serializers.URLField(allow_null=True)


# ---------------------------------------------------------------------------
# Access discriminator variants (one Serializer per kind)
# ---------------------------------------------------------------------------


class _AccessGrantedSerializer(serializers.Serializer):
    """access.kind == 'granted' — learner OR staff_preview.

    The ``audience`` field tells the player whether the viewer is the
    enrolled learner or a staff member previewing the curriculum. Drives
    UI affordances (mark-complete buttons hidden for staff, etc.).
    """

    kind = serializers.ChoiceField(choices=['granted'])
    audience = serializers.ChoiceField(choices=['learner', 'staff_preview'])
    enrollment_uuid = serializers.UUIDField(allow_null=True)
    staff_role = serializers.CharField(allow_null=True)


class _AccessPendingApprovalSerializer(serializers.Serializer):
    """access.kind == 'pending_approval' — enrollment exists but inactive."""

    kind = serializers.ChoiceField(choices=['pending_approval'])
    enrollment_uuid = serializers.UUIDField()
    requested_at = serializers.DateTimeField(allow_null=True)
    course = _SlimCourseSerializer()


class _AccessRedirectSerializer(serializers.Serializer):
    """access.kind == 'redirect_to_detail' — client should navigate."""

    REASONS = [
        'PAYMENT_REQUIRED',
        'NOT_ENROLLED',
        'ENROLLMENT_UPCOMING',
        'ENROLLMENT_CLOSED',
        'COURSE_FULL',
        'ENROLLMENT_DROPPED',
        'ENROLLMENT_EXPIRED',
    ]

    kind = serializers.ChoiceField(choices=['redirect_to_detail'])
    slug = serializers.CharField()
    reason = serializers.ChoiceField(choices=REASONS)


# ---------------------------------------------------------------------------
# Granted-payload nested shapes
# ---------------------------------------------------------------------------


class _ModuleProgressSliceSerializer(serializers.Serializer):
    """Per-module progress slice surfaced in the bootstrap.

    Mirrors what the legacy /progress/ endpoint returned per module, but
    flattened into the bootstrap so the client does not have to compose
    the two responses.
    """

    module_uuid = serializers.UUIDField()
    is_available = serializers.BooleanField()
    progress_status = serializers.CharField()
    progress_percent = serializers.IntegerField(min_value=0, max_value=100)
    contents_completed = serializers.IntegerField()
    contents_total = serializers.IntegerField()
    completed_content_uuids = serializers.ListField(child=serializers.UUIDField())


class _CourseEnrollmentViewStateSerializer(serializers.Serializer):
    """Discriminated UI state for a single CourseEnrollment.

    Six kinds. The frontend exhaustively switches on ``kind``. Optional
    fields are set per-kind by the producer and unused fields are absent.
    """

    KINDS = [
        'awaiting_approval',
        'payment_pending',
        'ready_to_start',
        'in_progress',
        'completed',
        'revoked',
    ]
    kind = serializers.ChoiceField(choices=KINDS)
    # awaiting_approval
    requested_at = serializers.DateTimeField(required=False, allow_null=True)
    # payment_pending
    purchase_uuid = serializers.UUIDField(required=False, allow_null=True)
    amount_cents = serializers.IntegerField(required=False, allow_null=True)
    currency = serializers.CharField(required=False, allow_null=True)
    # ready_to_start
    first_module_uuid = serializers.UUIDField(required=False, allow_null=True)
    # in_progress
    percent = serializers.IntegerField(required=False, allow_null=True)
    next_content_uuid = serializers.UUIDField(required=False, allow_null=True)
    # completed
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    certificate_uuid = serializers.UUIDField(required=False, allow_null=True)
    # revoked
    reason = serializers.CharField(required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Top-level response shapes
# ---------------------------------------------------------------------------


class CoursePlayerGrantedSerializer(serializers.Serializer):
    """The 'granted' bootstrap response — full payload to paint the player."""

    access = _AccessGrantedSerializer()
    course = CourseSerializer()
    modules = CourseModuleSerializer(many=True)
    module_progress = _ModuleProgressSliceSerializer(many=True)
    sessions = LiveSessionSerializer(many=True, required=False)
    announcements = CourseAnnouncementSerializer(many=True)
    view_state = _CourseEnrollmentViewStateSerializer(allow_null=True)


class CoursePlayerPendingApprovalSerializer(serializers.Serializer):
    """The 'pending_approval' bootstrap response — slim shell payload."""

    access = _AccessPendingApprovalSerializer()


class CoursePlayerRedirectSerializer(serializers.Serializer):
    """The 'redirect_to_detail' bootstrap response — navigation hint only."""

    access = _AccessRedirectSerializer()
