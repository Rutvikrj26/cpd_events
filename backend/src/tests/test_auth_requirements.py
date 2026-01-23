"""
Tests to verify that events and courses listing endpoints require authentication.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestEventListingAuth:
    """Test that event listing endpoints require authentication."""

    def test_list_events_requires_authentication(self, api_client):
        """Unauthenticated users cannot list events."""
        response = api_client.get("/api/v1/events/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "credentials were not provided" in str(response.data).lower() or "authentication" in str(response.data).lower()

    def test_retrieve_event_requires_authentication(self, api_client, event):
        """Unauthenticated users cannot retrieve event details."""
        response = api_client.get(f"/api/v1/events/{event.uuid}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_events_with_attendee_auth_requires_organizer_role(self, auth_client):
        """Authenticated attendees (non-organizers) cannot list events."""
        response = auth_client.get("/api/v1/events/")
        # Should return 200 but empty results since attendee doesn't own any events
        # OR 403 if they don't have organizer capability
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
        if response.status_code == status.HTTP_200_OK:
            # Empty results for attendees
            assert len(response.data.get("results", [])) == 0

    def test_list_events_with_organizer_auth_succeeds(self, organizer_client, event):
        """Authenticated organizers can list their events."""
        response = organizer_client.get("/api/v1/events/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get("results", [])) >= 1


@pytest.mark.django_db
class TestCourseListingAuth:
    """Test that course listing endpoints require authentication."""

    def test_list_courses_requires_authentication(self, api_client):
        """Unauthenticated users cannot list courses."""
        response = api_client.get("/api/v1/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "credentials were not provided" in str(response.data).lower() or "authentication" in str(response.data).lower()

    def test_retrieve_course_requires_authentication(self, api_client, course):
        """Unauthenticated users cannot retrieve course details."""
        response = api_client.get(f"/api/v1/courses/{course.uuid}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_courses_with_attendee_auth_shows_only_public_published(self, auth_client, course, organizer):
        """Authenticated attendees can only see public published courses."""
        # Ensure course is public and published
        course.is_public = True
        course.status = "published"
        course.save()

        response = auth_client.get("/api/v1/courses/")
        assert response.status_code == status.HTTP_200_OK
        # Should see the public course
        assert len(response.data.get("results", [])) >= 1

    def test_list_courses_with_attendee_auth_hides_draft_courses(self, auth_client, course):
        """Authenticated attendees cannot see draft courses they don't own."""
        # Ensure course is draft
        course.status = "draft"
        course.save()

        response = auth_client.get("/api/v1/courses/")
        assert response.status_code == status.HTTP_200_OK
        # Should not see draft courses
        draft_courses = [c for c in response.data.get("results", []) if c.get("status") == "draft"]
        assert len(draft_courses) == 0

    def test_list_courses_with_owner_auth_shows_own_courses(self, course_manager_client, course):
        """Course owners can see their own courses regardless of status."""
        # Ensure course is draft (not public)
        course.status = "draft"
        course.save()

        response = course_manager_client.get("/api/v1/courses/")
        assert response.status_code == status.HTTP_200_OK
        # Owner should see their own draft course
        course_uuids = [c.get("uuid") for c in response.data.get("results", [])]
        assert str(course.uuid) in course_uuids


@pytest.mark.django_db
class TestPublicEndpointsRemainPublic:
    """Verify that public endpoints remain accessible without authentication."""

    def test_public_event_list_no_auth_required(self, api_client, published_event):
        """Public event listing does not require authentication."""
        # Ensure event is public
        published_event.is_public = True
        published_event.save()

        response = api_client.get("/api/v1/public/events/")
        # Public endpoint should work without auth
        assert response.status_code == status.HTTP_200_OK

    def test_public_event_detail_no_auth_required(self, api_client, published_event):
        """Public event detail does not require authentication."""
        # Ensure event is public
        published_event.is_public = True
        published_event.save()

        response = api_client.get(f"/api/v1/public/events/{published_event.uuid}/")
        # Public endpoint should work without auth
        assert response.status_code == status.HTTP_200_OK
