"""
Tests for quiz submission and attempt history.
"""

import pytest
from rest_framework import status
from django.utils import timezone

from learning.models import CourseModule, ModuleContent, CourseEnrollment, QuizAttempt
from factories import CourseFactory, EventModuleFactory, ModuleContentFactory


@pytest.fixture
def quiz_course(db, course_manager):
    """Create a published course for quiz testing."""
    return CourseFactory(
        owner=course_manager,
        title="Quiz Test Course",
        status="published",
    )


@pytest.fixture
def quiz_event_module(db):
    """Create an EventModule (without linking to a specific event)."""
    return EventModuleFactory(
        event=None,  # Can be used in courses without being linked to an event
        title="Quiz Module",
        description="Module containing quizzes",
    )


@pytest.fixture
def quiz_course_module(db, quiz_course, quiz_event_module):
    """Link the EventModule to the Course via CourseModule."""
    return CourseModule.objects.create(
        course=quiz_course,
        module=quiz_event_module,
        order=1,
        is_required=True,
    )


@pytest.fixture
def quiz_content(db, quiz_event_module):
    """Create a quiz content within the EventModule."""
    return ModuleContentFactory(
        module=quiz_event_module,
        title="Test Quiz",
        content_type="quiz",
        content_data={
            "questions": [
                {
                    "id": "q1",
                    "text": "What is 2+2?",
                    "type": "single",
                    "correctAnswer": "b",  # Added correct answer
                    "options": [
                        {"id": "a", "text": "3"},
                        {"id": "b", "text": "4"},
                        {"id": "c", "text": "5"},
                    ],
                }
            ],
            "passing_score": 70,
            "max_attempts": 3,
        },
        order=1,
        is_required=True,
    )


@pytest.fixture
def enrollment(db, user, quiz_course, quiz_course_module):
    """Create a course enrollment."""
    return CourseEnrollment.objects.create(
        user=user,
        course=quiz_course,
        status="active",
    )


@pytest.mark.django_db
class TestQuizSubmission:
    """Tests for quiz submission endpoint."""

    def test_submit_quiz_correct_answer(self, auth_client, enrollment, quiz_content):
        """Test submitting a quiz with correct answers."""
        data = {
            "content_uuid": str(quiz_content.uuid),
            "submitted_answers": {"q1": "b"},
            "time_spent_seconds": 60,
        }
        response = auth_client.post("/api/v1/learning/quiz/submit/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "attempt" in response.data
        assert float(response.data["attempt"]["score"]) == 100
        assert response.data["attempt"]["passed"] is True
        assert response.data["attempt"]["attempt_number"] == 1

    def test_submit_quiz_wrong_answer(self, auth_client, enrollment, quiz_content):
        """Test submitting a quiz with wrong answers."""
        data = {
            "content_uuid": str(quiz_content.uuid),
            "submitted_answers": {"q1": "a"},
            "time_spent_seconds": 45,
        }
        response = auth_client.post("/api/v1/learning/quiz/submit/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert float(response.data["attempt"]["score"]) == 0
        assert response.data["attempt"]["passed"] is False

    def test_submit_quiz_max_attempts_reached(self, auth_client, enrollment, quiz_content):
        """Test that max attempts limit is enforced."""
        # Submit 3 failed attempts
        for i in range(3):
            data = {
                "content_uuid": str(quiz_content.uuid),
                "submitted_answers": {"q1": "a"},
                "time_spent_seconds": 30,
            }
            response = auth_client.post("/api/v1/learning/quiz/submit/", data, format="json")
            assert response.status_code == status.HTTP_201_CREATED

        # 4th attempt should be blocked
        data = {
            "content_uuid": str(quiz_content.uuid),
            "submitted_answers": {"q1": "b"},
            "time_spent_seconds": 30,
        }
        response = auth_client.post("/api/v1/learning/quiz/submit/", data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "MAX_ATTEMPTS_REACHED" in response.data.get("error", {}).get("code", "")

    def test_submit_quiz_not_enrolled(self, auth_client, quiz_content):
        """Test that non-enrolled users cannot submit quiz."""
        data = {
            "content_uuid": str(quiz_content.uuid),
            "submitted_answers": {"q1": "b"},
            "time_spent_seconds": 60,
        }
        response = auth_client.post("/api/v1/learning/quiz/submit/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_submit_quiz_unauthenticated(self, client, quiz_content):
        """Test that unauthenticated users cannot submit quiz."""
        data = {
            "content_uuid": str(quiz_content.uuid),
            "submitted_answers": {"q1": "b"},
            "time_spent_seconds": 60,
        }
        response = client.post("/api/v1/learning/quiz/submit/", data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestQuizAttemptHistory:
    """Tests for quiz attempt history endpoint."""

    def test_get_quiz_attempts_empty(self, auth_client, enrollment, quiz_content):
        """Test getting attempt history when no attempts exist."""
        response = auth_client.get(f"/api/v1/learning/quiz/{quiz_content.uuid}/attempts/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_attempts"] == 0
        assert response.data["max_attempts"] == 3
        assert response.data["remaining_attempts"] == 3
        assert len(response.data["attempts"]) == 0

    def test_get_quiz_attempts_with_history(self, auth_client, enrollment, quiz_content):
        """Test getting attempt history with existing attempts."""
        # Create 2 attempts
        QuizAttempt.objects.create(
            content=quiz_content,
            course_enrollment=enrollment,
            attempt_number=1,
            submitted_answers={"q1": "a"},
            score=0,
            passed=False,
            status="graded",
            time_spent_seconds=30,
            submitted_at=timezone.now(),
        )
        QuizAttempt.objects.create(
            content=quiz_content,
            course_enrollment=enrollment,
            attempt_number=2,
            submitted_answers={"q1": "b"},
            score=100,
            passed=True,
            status="graded",
            time_spent_seconds=45,
            submitted_at=timezone.now(),
        )

        response = auth_client.get(f"/api/v1/learning/quiz/{quiz_content.uuid}/attempts/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_attempts"] == 2
        assert response.data["remaining_attempts"] == 1
        assert len(response.data["attempts"]) == 2

        # Check that attempts are ordered by most recent first
        assert response.data["attempts"][0]["attempt_number"] == 2
        assert response.data["attempts"][1]["attempt_number"] == 1

    def test_get_quiz_attempts_not_enrolled(self, auth_client, quiz_content):
        """Test that non-enrolled users cannot access attempt history."""
        response = auth_client.get(f"/api/v1/learning/quiz/{quiz_content.uuid}/attempts/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_quiz_attempts_not_quiz_content(self, auth_client, enrollment, quiz_event_module):
        """Test that attempt history only works for quiz content."""
        text_content = ModuleContent.objects.create(
            module=quiz_event_module,
            title="Text Content",
            content_type="text",
            content_data={"text": "Sample text"},
            order=2,
        )

        response = auth_client.get(f"/api/v1/learning/quiz/{text_content.uuid}/attempts/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "NOT_A_QUIZ" in response.data.get("error", {}).get("code", "")

    def test_get_quiz_attempts_unauthenticated(self, client, quiz_content):
        """Test that unauthenticated users cannot access attempt history."""
        response = client.get(f"/api/v1/learning/quiz/{quiz_content.uuid}/attempts/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
