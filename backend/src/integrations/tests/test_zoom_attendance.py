import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from integrations.services import WebhookProcessor
from learning.models import Course, CourseEnrollment, CourseSession, CourseSessionAttendance

User = get_user_model()


@pytest.fixture
def course_setup(db):
    owner = User.objects.create_user(email="owner@test.com", password="testpass123")
    course = Course.objects.create(owner=owner, title="Test Course", format="hybrid")
    session = CourseSession.objects.create(
        course=course,
        title="Test Session",
        starts_at=timezone.now(),
        duration_minutes=60,
        zoom_meeting_id="123456789",
        is_published=True,
    )
    return course, session


@pytest.mark.django_db
def test_attendance_accumulates_on_rejoin(course_setup):
    from django.contrib.auth import get_user_model

    User = get_user_model()

    course, session = course_setup
    student = User.objects.create_user(email="student@example.com", password="password123")
    enrollment = CourseEnrollment.objects.create(course=course, user=student, status="active")

    processor = WebhookProcessor()

    # 1. Join 1 (10:00)
    join_time_1 = timezone.now()
    payload_join_1 = _get_join_payload(session.zoom_meeting_id, student.email, "uuid-1", join_time_1)
    processor._handle_participant_joined(payload_join_1)

    # Verify created
    att = CourseSessionAttendance.objects.get(session=session, enrollment=enrollment)
    assert att.zoom_participant_id == "uuid-1"
    assert att.attendance_minutes == 0

    # 2. Leave 1 (10:10) - 10 minutes duration
    leave_time_1 = join_time_1 + timezone.timedelta(minutes=10)
    payload_leave_1 = _get_leave_payload(session.zoom_meeting_id, student.email, "uuid-1", leave_time_1)
    processor._handle_participant_left(payload_leave_1)

    # Verify minutes
    att.refresh_from_db()
    assert att.attendance_minutes == 10

    # 3. Join 2 (10:20) - SAME student, NEW UUID (rejoin)
    join_time_2 = join_time_1 + timezone.timedelta(minutes=20)  # 10:20
    payload_join_2 = _get_join_payload(session.zoom_meeting_id, student.email, "uuid-2", join_time_2)
    processor._handle_participant_joined(payload_join_2)

    # Verify updated UUID - CRITICAL for next leave event
    att.refresh_from_db()
    assert att.zoom_participant_id == "uuid-2"

    # 4. Leave 2 (10:30) - 10 minutes duration
    leave_time_2 = join_time_2 + timezone.timedelta(minutes=10)  # 10:30
    payload_leave_2 = _get_leave_payload(session.zoom_meeting_id, student.email, "uuid-2", leave_time_2)
    processor._handle_participant_left(payload_leave_2)

    # Verify accumulation (10 + 10 = 20)
    att.refresh_from_db()
    assert att.attendance_minutes == 20


def _get_join_payload(meeting_id, email, user_id, join_time):
    return {
        "object": {
            "id": meeting_id,
            "participant": {
                "user_id": "zoom-uid",
                "user_name": "Student",
                "email": email,
                "id": user_id,
                "join_time": join_time.isoformat(),
            },
        }
    }


def _get_leave_payload(meeting_id, email, user_id, leave_time):
    return {"object": {"id": meeting_id, "participant": {"email": email, "id": user_id, "leave_time": leave_time.isoformat()}}}
