"""
Tests for the Program (course bundle) feature.
"""
import pytest
from django.core.exceptions import ValidationError

from accounts.models import User
from learning.models import (
    Course,
    CourseEnrollment,
    Program,
    ProgramCourse,
    ProgramEnrollment,
)


@pytest.fixture
def user(db):
    return User.objects.create(email='learner@example.com', password='pw')


@pytest.fixture
def organizer(db):
    return User.objects.create(email='organizer@example.com', password='pw')


@pytest.fixture
def courses(db, organizer):
    a = Course.objects.create(
        title='Course A', slug='a', created_by=organizer,
        status=Course.Status.PUBLISHED, price_cents=5000,
    )
    b = Course.objects.create(
        title='Course B', slug='b', created_by=organizer,
        status=Course.Status.PUBLISHED, price_cents=3000,
    )
    return a, b


@pytest.fixture
def program(db, organizer, courses):
    a, b = courses
    p = Program.objects.create(
        title='Bundle', slug='bundle', created_by=organizer,
        price_cents=6000, currency='USD',
    )
    ProgramCourse.objects.create(program=p, course=a, order=1)
    ProgramCourse.objects.create(program=p, course=b, order=2)
    p.update_counts()
    return p


@pytest.mark.django_db
class TestProgramModel:

    def test_publish_requires_at_least_one_course(self, organizer):
        empty = Program.objects.create(title='Empty', slug='empty', created_by=organizer)
        with pytest.raises(ValidationError) as excinfo:
            empty.publish()
        assert 'courses' in excinfo.value.message_dict

    def test_publish_succeeds_with_courses(self, program):
        program.publish()
        program.refresh_from_db()
        assert program.status == Program.Status.PUBLISHED

    def test_sum_individual_price_cents(self, program):
        # Course A 5000 + Course B 3000 = 8000
        assert program.sum_individual_price_cents() == 8000

    def test_bundle_savings_field(self, program):
        # Sum 8000 vs bundle 6000 → 2000 cents saved
        from learning.serializers import ProgramSerializer
        data = ProgramSerializer(program).data
        assert data['bundle_savings_cents'] == 2000

    def test_course_can_belong_to_multiple_programs(self, organizer, courses):
        a, b = courses
        p1 = Program.objects.create(title='P1', slug='p1', created_by=organizer)
        p2 = Program.objects.create(title='P2', slug='p2', created_by=organizer)
        ProgramCourse.objects.create(program=p1, course=a)
        ProgramCourse.objects.create(program=p2, course=a)
        assert a.programs.count() == 2

    def test_unique_program_course(self, program, courses):
        a, _ = courses
        from django.db import IntegrityError, transaction
        with transaction.atomic(), pytest.raises(IntegrityError):
            ProgramCourse.objects.create(program=program, course=a)


@pytest.mark.django_db
class TestProgramEnrollmentSeeding:

    def test_activate_seeds_per_course_enrollments(self, user, program):
        enrollment = ProgramEnrollment.objects.create(user=user, program=program)
        enrollment.activate()
        assert CourseEnrollment.objects.filter(user=user, course__programs=program).count() == 2

    def test_activate_is_idempotent(self, user, program):
        enrollment = ProgramEnrollment.objects.create(user=user, program=program)
        enrollment.activate()
        enrollment.activate()  # second call shouldn't duplicate
        assert CourseEnrollment.objects.filter(user=user).count() == 2

    def test_activate_respects_existing_enrollment(self, user, program, courses):
        a, _ = courses
        existing = CourseEnrollment.objects.create(
            user=user, course=a, status=CourseEnrollment.Status.COMPLETED,
        )
        enrollment = ProgramEnrollment.objects.create(user=user, program=program)
        enrollment.activate()
        existing.refresh_from_db()
        # Existing COMPLETED enrollment must not be downgraded
        assert existing.status == CourseEnrollment.Status.COMPLETED


@pytest.mark.django_db
class TestProgramCompletion:

    def test_check_completion_marks_complete_when_all_required_done(self, user, program):
        enrollment = ProgramEnrollment.objects.create(user=user, program=program)
        enrollment.activate()
        for ce in CourseEnrollment.objects.filter(user=user, course__programs=program):
            ce.status = CourseEnrollment.Status.COMPLETED
            ce.save(update_fields=['status'])
        enrollment.check_completion()
        assert enrollment.status == ProgramEnrollment.Status.COMPLETED
        assert enrollment.completed_at is not None

    def test_check_completion_returns_false_when_partial(self, user, program):
        enrollment = ProgramEnrollment.objects.create(user=user, program=program)
        enrollment.activate()
        # Complete only the first course
        ce = CourseEnrollment.objects.filter(user=user).first()
        ce.status = CourseEnrollment.Status.COMPLETED
        ce.save(update_fields=['status'])
        assert enrollment.check_completion() is False
        enrollment.refresh_from_db()
        assert enrollment.status == ProgramEnrollment.Status.ACTIVE

    def test_completing_member_course_triggers_program_completion(self, user, program):
        """CourseEnrollment.complete() should ripple into ProgramEnrollment.check_completion()."""
        enrollment = ProgramEnrollment.objects.create(user=user, program=program)
        enrollment.activate()
        # Manually complete each member course via .complete() — last call should mark program complete.
        for ce in CourseEnrollment.objects.filter(user=user, course__programs=program).order_by('id'):
            ce.complete()
        enrollment.refresh_from_db()
        assert enrollment.status == ProgramEnrollment.Status.COMPLETED


@pytest.mark.django_db
class TestProgramApi:
    """Smoke-test the public list/detail endpoints."""

    def test_public_list_filters_to_published_public(self, client, organizer, program):
        # Unauth user: program is still draft → not visible
        resp = client.get('/api/v1/programs/')
        assert resp.status_code == 200
        assert all(p['slug'] != 'bundle' for p in resp.json().get('results', resp.json()))

        program.publish()
        resp = client.get('/api/v1/programs/')
        assert resp.status_code == 200
        slugs = [p['slug'] for p in resp.json().get('results', resp.json())]
        assert 'bundle' in slugs

    def test_public_detail_includes_member_courses(self, client, program):
        program.publish()
        resp = client.get(f'/api/v1/programs/?slug=bundle')
        data = resp.json()
        # results may be paginated — handle both
        items = data.get('results', data)
        assert items, items
        assert len(items) == 1
        # detail by uuid for nested data
        program_uuid = items[0]['uuid']
        detail = client.get(f'/api/v1/programs/{program_uuid}/')
        body = detail.json()
        assert body['course_count'] == 2
        assert body['bundle_savings_cents'] == 2000
        assert len(body['program_courses']) == 2
