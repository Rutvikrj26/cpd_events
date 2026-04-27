"""Tests for the typed-contract redesign.

Three concerns locked down here:

1. ``learning.view_states`` — pure derivation functions for the three
   ``view_state`` projections (course enrollment, program enrollment,
   registration). Each kind round-trips correctly given the right
   underlying entity state.

2. ``CourseViewSet.player_bootstrap`` — the discriminated ``access``
   envelope (granted / pending_approval / redirect_to_detail) is
   produced for the right learner-vs-course combination, and
   non-granted responses don't leak full course data.

3. ``learning.content_schemas`` — strict per-content_type validation
   rejects the legacy ``{q, choices, answer}`` quiz shape (the bug
   class that escaped the previous hand-rolled validator) and accepts
   the canonical ``{id, text, type, options, points}`` shape.

Each test states the invariant it pins in its docstring so a future
refactor that "just makes the test pass" still preserves the user-
visible behaviour.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import APIClient

from accounts.models import User
from events.models import Event
from learning.content_schemas import (
    ContentSchemaError,
    validate_content_data,
)
from learning.models import (
    Course,
    CourseEnrollment,
    CourseModule,
    EventModule,
    Program,
    ProgramCourse,
    ProgramEnrollment,
)
from learning.view_states import (
    derive_course_access,
    derive_course_enrollment_view_state,
    derive_program_enrollment_view_state,
    derive_registration_view_state,
)
from registrations.models import Registration


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def learner(db):
    user = User.objects.create_user(email='learner@example.com', password='pw', full_name='Learner')
    user.groups.add(Group.objects.get_or_create(name='learner')[0])
    return user


@pytest.fixture
def instructor(db):
    user = User.objects.create_user(email='instructor@example.com', password='pw', full_name='Instructor')
    user.groups.add(Group.objects.get_or_create(name='instructor')[0])
    return user


@pytest.fixture
def free_course(instructor):
    return Course.objects.create(
        title='Free Course',
        slug='free-course',
        price_cents=0,
        currency='USD',
        status=Course.Status.PUBLISHED,
        is_public=True,
        enrollment_open=True,
        created_by=instructor,
    )


@pytest.fixture
def paid_course(instructor):
    return Course.objects.create(
        title='Paid Course',
        slug='paid-course',
        price_cents=4900,
        currency='USD',
        status=Course.Status.PUBLISHED,
        is_public=True,
        enrollment_open=True,
        created_by=instructor,
    )


# ---------------------------------------------------------------------------
# 1. CourseEnrollment view_state — six kinds
# ---------------------------------------------------------------------------


class TestCourseEnrollmentViewState:
    """The six kinds of CourseEnrollment.view_state are produced from the
    right (status, progress, completed_at) tuple. The legacy consumer
    pattern (interpret status enum locally) reproduces these states with
    different code; this projection centralises it."""

    def test_pending_status_yields_awaiting_approval(self, learner, free_course):
        """status=PENDING → kind='awaiting_approval'."""
        enrollment = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.PENDING,
        )
        vs = derive_course_enrollment_view_state(enrollment)
        assert vs['kind'] == 'awaiting_approval'
        assert vs['requested_at'] is not None

    def test_active_zero_progress_yields_ready_to_start(self, learner, free_course):
        """Active enrollment with no progress → ready_to_start (distinct
        from in_progress so the My Learning card can render "Start" not
        "Continue")."""
        enrollment = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.ACTIVE,
            progress_percent=0,
            started_at=None,
        )
        vs = derive_course_enrollment_view_state(enrollment)
        assert vs['kind'] == 'ready_to_start'

    def test_active_with_progress_yields_in_progress(self, learner, free_course):
        """Active + progress > 0 OR started_at set → in_progress with the
        learner's percent."""
        enrollment = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.ACTIVE,
            progress_percent=42,
            started_at=timezone.now(),
        )
        vs = derive_course_enrollment_view_state(enrollment)
        assert vs['kind'] == 'in_progress'
        assert vs['percent'] == 42

    def test_completed_yields_completed(self, learner, free_course):
        """status=COMPLETED → kind='completed'. completed_at and
        certificate_uuid (when issued) ride along for the UI."""
        enrollment = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.COMPLETED,
            progress_percent=100,
            completed_at=timezone.now(),
        )
        vs = derive_course_enrollment_view_state(enrollment)
        assert vs['kind'] == 'completed'
        assert vs['completed_at'] is not None

    def test_dropped_yields_revoked(self, learner, free_course):
        """status=DROPPED → kind='revoked', reason='dropped'. The card
        shows 'Dropped' instead of misleading "Continue"."""
        enrollment = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.DROPPED,
        )
        vs = derive_course_enrollment_view_state(enrollment)
        assert vs['kind'] == 'revoked'
        assert vs['reason'] == 'dropped'

    def test_expired_yields_revoked(self, learner, free_course):
        """status=EXPIRED → revoked with reason='expired'."""
        enrollment = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.EXPIRED,
        )
        vs = derive_course_enrollment_view_state(enrollment)
        assert vs['kind'] == 'revoked'
        assert vs['reason'] == 'expired'


# ---------------------------------------------------------------------------
# 2. derive_course_access — the bootstrap discriminator
# ---------------------------------------------------------------------------


class TestDeriveCourseAccess:
    """The three access kinds are produced for the right learner/course/
    enrollment combination. This is the function that decides whether the
    player renders, the pending shell renders, or the client redirects to
    the catalog page."""

    def test_no_enrollment_paid_course_returns_redirect_with_payment_required(
        self, learner, paid_course
    ):
        """Not enrolled + paid course → redirect_to_detail with
        reason=PAYMENT_REQUIRED. The catalog page shows the buy CTA."""
        access = derive_course_access(paid_course, user=learner, enrollment=None)
        assert access['kind'] == 'redirect_to_detail'
        assert access['reason'] == 'PAYMENT_REQUIRED'
        assert access['slug'] == 'paid-course'

    def test_no_enrollment_free_course_returns_redirect(self, learner, free_course):
        """Not enrolled + free course → redirect_to_detail (the catalog
        page is the source of truth for the Enroll CTA)."""
        access = derive_course_access(free_course, user=learner, enrollment=None)
        assert access['kind'] == 'redirect_to_detail'
        # No payment, just navigate.
        assert access['reason'] != 'PAYMENT_REQUIRED'

    def test_pending_enrollment_returns_pending_approval(self, learner, free_course):
        """Pending enrollment → kind=pending_approval. The shell renders
        instead of the player."""
        enr = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.PENDING,
        )
        access = derive_course_access(free_course, user=learner, enrollment=enr)
        assert access['kind'] == 'pending_approval'
        assert access['enrollment_uuid'] == str(enr.uuid)
        # Slim course payload — only what the shell renders.
        assert set(access['course'].keys()) == {'uuid', 'title', 'slug', 'featured_image_url'}

    def test_active_enrollment_returns_granted_as_learner(self, learner, free_course):
        """Active enrollment → kind=granted, audience=learner. Player
        renders the curriculum."""
        enr = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.ACTIVE,
        )
        access = derive_course_access(free_course, user=learner, enrollment=enr)
        assert access['kind'] == 'granted'
        assert access['audience'] == 'learner'
        assert access['enrollment_uuid'] == str(enr.uuid)

    def test_instructor_no_enrollment_returns_granted_as_staff_preview(
        self, instructor, free_course
    ):
        """Course staff get granted access without an enrollment row.
        audience=staff_preview so the player can hide mark-complete UI
        and the like."""
        # Instructor is the course creator → can_manage. Make sure the
        # staff_role lookup picks them up.
        access = derive_course_access(free_course, user=instructor, enrollment=None)
        assert access['kind'] == 'granted'
        assert access['audience'] == 'staff_preview'
        assert access['enrollment_uuid'] is None

    def test_dropped_enrollment_returns_redirect(self, learner, free_course):
        """Dropped enrollment is not "you can re-enter" — the catalog
        is the recovery path."""
        enr = CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.DROPPED,
        )
        access = derive_course_access(free_course, user=learner, enrollment=enr)
        assert access['kind'] == 'redirect_to_detail'
        assert access['reason'] == 'ENROLLMENT_DROPPED'


# ---------------------------------------------------------------------------
# 3. End-to-end: GET /api/v1/courses/{uuid}/player-bootstrap/
# ---------------------------------------------------------------------------


class TestPlayerBootstrapEndpoint:
    """The bootstrap endpoint returns one of three discriminated shapes,
    all as HTTP 200, scoped to the requesting user. The previous design
    had the player composing 6 fetches with independent permission
    checks, which produced 4 toasts on a not-enrolled course; this
    endpoint replaced that orchestration with a single round-trip."""

    def test_granted_response_includes_full_player_payload(
        self, learner, free_course
    ):
        """Active learner → granted + course/modules/sessions/announcements/
        view_state all present in one response."""
        CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.ACTIVE,
        )
        client = APIClient()
        client.force_authenticate(user=learner)
        url = reverse('learning:course-player-bootstrap', kwargs={'uuid': free_course.uuid})
        response = client.get(url)
        assert response.status_code == http_status.HTTP_200_OK
        body = response.json()
        assert body['access']['kind'] == 'granted'
        assert body['access']['audience'] == 'learner'
        # All composite payload sections present (announcements may be []
        # for a brand-new course; the key still exists).
        for key in ('course', 'modules', 'module_progress', 'sessions',
                    'announcements', 'view_state'):
            assert key in body, f'missing {key} in granted payload'

    def test_pending_response_omits_curriculum(self, learner, free_course):
        """Pending enrollment → response carries ONLY access+slim course;
        no modules, no progress. Client renders the shell."""
        CourseEnrollment.objects.create(
            user=learner, course=free_course,
            status=CourseEnrollment.Status.PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=learner)
        url = reverse('learning:course-player-bootstrap', kwargs={'uuid': free_course.uuid})
        response = client.get(url)
        assert response.status_code == http_status.HTTP_200_OK
        body = response.json()
        assert body['access']['kind'] == 'pending_approval'
        # Confidentiality: a pending learner doesn't see the curriculum.
        assert 'modules' not in body
        assert 'module_progress' not in body

    def test_redirect_response_for_paid_no_enrollment(self, learner, paid_course):
        """Paid course + no enrollment → redirect_to_detail with reason."""
        client = APIClient()
        client.force_authenticate(user=learner)
        url = reverse('learning:course-player-bootstrap', kwargs={'uuid': paid_course.uuid})
        response = client.get(url)
        assert response.status_code == http_status.HTTP_200_OK
        body = response.json()
        assert body['access']['kind'] == 'redirect_to_detail'
        assert body['access']['reason'] == 'PAYMENT_REQUIRED'
        assert body['access']['slug'] == 'paid-course'

    def test_unauthenticated_request_is_rejected(self, free_course):
        """No JWT → 401 (transport-layer auth bug, not a domain
        condition). The toast policy still toasts on 5xx but is silent
        on 4xx — 401 is the special-cased token-refresh path."""
        client = APIClient()
        url = reverse('learning:course-player-bootstrap', kwargs={'uuid': free_course.uuid})
        response = client.get(url)
        assert response.status_code in (
            http_status.HTTP_401_UNAUTHORIZED, http_status.HTTP_403_FORBIDDEN
        )


# ---------------------------------------------------------------------------
# 4. Pydantic content_data validation
# ---------------------------------------------------------------------------


class TestContentSchemas:
    """Pydantic per-content_type schemas enforce field-level shapes that
    the legacy hand-rolled validator silently accepted. The original
    bug was a quiz with ``{q, choices, answer}`` keys (vs the canonical
    ``{id, text, type, options, points}``) that rendered an empty Q1
    badge with no question text and no options. This test pins the
    invariant: that exact legacy shape is now rejected."""

    def test_legacy_quiz_shape_is_rejected(self):
        """The exact bug we just fixed: ``{q, choices, answer}`` must
        now raise. Each missing canonical field surfaces as a discrete
        error path so the authoring UI can attribute them."""
        bad = {
            'questions': [
                {'q': 'Beneficence means?', 'choices': ['a', 'b'], 'answer': 0},
            ],
            'passing_score': 70,
        }
        with pytest.raises(ContentSchemaError) as exc_info:
            validate_content_data('quiz', bad)
        # Field-level errors call out what's missing, not just "bad shape".
        paths = {'.'.join(str(p) for p in err['loc']) for err in exc_info.value.errors()}
        assert 'questions.0.id' in paths
        assert 'questions.0.text' in paths
        assert 'questions.0.type' in paths
        assert 'questions.0.options' in paths

    def test_canonical_quiz_shape_is_accepted(self):
        """The shape QuizBuilder writes and QuizTaker reads."""
        good = {
            'questions': [
                {
                    'id': 'q1',
                    'text': 'Which principle?',
                    'type': 'single',
                    'points': 10,
                    'options': [
                        {'id': 'q1o1', 'text': 'A', 'isCorrect': True},
                        {'id': 'q1o2', 'text': 'B', 'isCorrect': False},
                    ],
                },
            ],
            'passing_score': 70,
        }
        validate_content_data('quiz', good)

    def test_text_content_requires_body(self):
        """``text`` must have a ``body`` string; the rich-text editor
        emits HTML there."""
        with pytest.raises(ContentSchemaError):
            validate_content_data('text', {'wrong_key': 'x'})
        validate_content_data('text', {'body': '<p>ok</p>'})

    def test_video_content_requires_url(self):
        """``video`` must have ``url``; provider/thumbnail are optional."""
        with pytest.raises(ContentSchemaError):
            validate_content_data('video', {'provider': 'demo'})
        validate_content_data('video', {'url': 'https://x.invalid/v.mp4'})

    def test_empty_payload_is_accepted(self):
        """Document content (and similar) commonly persists with no
        JSON. Validation must not break those rows."""
        validate_content_data('document', {})
        validate_content_data('document', None)

    def test_non_dict_payload_is_rejected(self):
        """A list / string at the top level isn't a content_data shape."""
        with pytest.raises(ContentSchemaError):
            validate_content_data('text', ['not', 'a', 'dict'])
