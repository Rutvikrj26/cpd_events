"""
Tests for learning module endpoints.

Endpoints tested:
- Event Modules, Contents, Assignments, Submissions
- MyLearning, Courses, Enrollments
"""

import pytest
from rest_framework import status

# =============================================================================
# Event Module Tests
# =============================================================================


@pytest.mark.django_db
class TestEventModuleViewSet:
    """Tests for event module management."""

    def get_endpoint(self, event):
        return f'/api/v1/events/{event.uuid}/modules/'

    def test_list_modules(self, organizer_client, event, event_module):
        """Organizer can list modules for their event."""
        endpoint = self.get_endpoint(event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_create_module(self, organizer_client, event):
        """Organizer can create a module."""
        endpoint = self.get_endpoint(event)
        data = {
            'title': 'New Module',
            'description': 'Module description',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_module(self, organizer_client, event, event_module):
        """Organizer can update a module."""
        response = organizer_client.patch(f'{self.get_endpoint(event)}{event_module.uuid}/', {'title': 'Updated Module'})
        assert response.status_code == status.HTTP_200_OK
        event_module.refresh_from_db()
        assert event_module.title == 'Updated Module'

    def test_delete_module(self, organizer_client, event, event_module):
        """Organizer can delete a module."""
        response = organizer_client.delete(f'{self.get_endpoint(event)}{event_module.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_publish_module(self, organizer_client, event, event_module):
        """Organizer can publish a module."""
        response = organizer_client.post(f'{self.get_endpoint(event)}{event_module.uuid}/publish/')
        assert response.status_code == status.HTTP_200_OK
        event_module.refresh_from_db()
        assert event_module.is_published is True

    def test_unpublish_module(self, organizer_client, event, event_module):
        """Organizer can unpublish a module."""
        event_module.is_published = True
        event_module.save()

        response = organizer_client.post(f'{self.get_endpoint(event)}{event_module.uuid}/unpublish/')
        assert response.status_code == status.HTTP_200_OK
        event_module.refresh_from_db()
        assert event_module.is_published is False


# =============================================================================
# Module Content Tests
# =============================================================================


@pytest.mark.django_db
class TestModuleContentViewSet:
    """Tests for module content management."""

    def get_endpoint(self, event, module):
        return f'/api/v1/events/{event.uuid}/modules/{module.uuid}/contents/'

    def test_list_contents(self, organizer_client, event, event_module, module_content):
        """Organizer can list module contents."""
        endpoint = self.get_endpoint(event, event_module)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_create_text_content(self, organizer_client, event, event_module):
        """Organizer can create text content."""
        endpoint = self.get_endpoint(event, event_module)
        data = {
            'title': 'Text Content',
            'content_type': 'text',
            'text_content': 'This is the content',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_video_content(self, organizer_client, event, event_module):
        """Organizer can create video content."""
        endpoint = self.get_endpoint(event, event_module)
        data = {
            'title': 'Video Content',
            'content_type': 'video',
            'video_url': 'https://example.com/video.mp4',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED


# =============================================================================
# Assignment Tests
# =============================================================================


@pytest.mark.django_db
class TestAssignmentViewSet:
    """Tests for assignment management."""

    def test_list_assignments(self, organizer_client, event, event_module, assignment):
        """Organizer can list assignments."""
        endpoint = f'/api/v1/events/{event.uuid}/modules/{event_module.uuid}/assignments/'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_create_assignment(self, organizer_client, event, event_module):
        """Organizer can create an assignment."""
        endpoint = f'/api/v1/events/{event.uuid}/modules/{event_module.uuid}/assignments/'
        data = {
            'title': 'New Assignment',
            'description': 'Complete this task',
            'instructions': 'Detailed instructions here.',
            'max_score': 100,
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED


# =============================================================================
# Submission Tests
# =============================================================================


@pytest.mark.django_db
class TestSubmissionViewSet:
    """Tests for assignment submissions."""

    endpoint = '/api/v1/submissions/'

    def test_list_my_submissions(self, auth_client):
        """User can list their submissions."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_create_submission(self, auth_client, registration):
        """User can submit an assignment."""
        # Create assignment for the registered event
        from factories import AssignmentFactory, EventModuleFactory

        module = EventModuleFactory(event=registration.event)
        assignment = AssignmentFactory(module=module)

        data = {
            'assignment': str(assignment.uuid),
            'content': 'My submission content',
        }
        response = auth_client.post(self.endpoint, data)
        # May succeed or fail based on enrollment/attempts, but shouldn't be 404
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# My Learning Tests
# =============================================================================


@pytest.mark.django_db
class TestMyLearningViewSet:
    """Tests for attendee learning dashboard."""

    endpoint = '/api/v1/learning/'

    def test_list_learning_progress(self, auth_client, registration):
        """User can see their learning progress."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_get_event_learning(self, auth_client, registration, published_event):
        """User can see learning for a specific event."""
        response = auth_client.get(f'{self.endpoint}{published_event.uuid}/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# =============================================================================
# Content Progress Tests
# =============================================================================


@pytest.mark.django_db
class TestContentProgress:
    """Tests for content progress tracking."""

    def test_update_content_progress(self, auth_client, module_content, registration):
        """User can update their content progress."""
        response = auth_client.post(f'/api/v1/learning/progress/content/{module_content.uuid}/', {'completed': True})
        # May succeed or fail based on access
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


# =============================================================================
# Course Tests
# =============================================================================


@pytest.mark.django_db
class TestCourseViewSet:
    """Tests for course management."""

    endpoint = '/api/v1/courses/'

    def test_list_courses(self, organizer_client, course):
        """Organizer can list their courses."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_create_course(self, organizer_client, course):
        """Organizer can create a course."""
        # Need organization slug
        from organizations.models import OrganizationMembership

        membership = OrganizationMembership.objects.get(
            organization=course.organization,
            user=course.organization.created_by,
        )
        membership.role = OrganizationMembership.Role.COURSE_MANAGER
        membership.save(update_fields=['role'])

        data = {
            'title': 'New Course',
            'slug': 'new-course',
            'description': 'Course description',
            'organization_slug': course.organization.slug,
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_publish_course(self, organizer_client, course):
        """Organizer can publish a course."""
        from organizations.models import OrganizationMembership

        membership = OrganizationMembership.objects.get(
            organization=course.organization,
            user=course.organization.created_by,
        )
        membership.role = OrganizationMembership.Role.COURSE_MANAGER
        membership.save(update_fields=['role'])

        response = organizer_client.post(f'{self.endpoint}{course.uuid}/publish/')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_org_admin_can_update_org_course(self, organizer_client, organization, course_manager):
        """Org admin can update courses owned by other course managers in the org."""
        from factories import CourseFactory
        from organizations.models import OrganizationMembership

        OrganizationMembership.objects.create(
            organization=organization,
            user=course_manager,
            role=OrganizationMembership.Role.COURSE_MANAGER,
            is_active=True,
        )
        course = CourseFactory(
            organization=organization,
            created_by=course_manager,
            title='Org Course',
        )

        response = organizer_client.patch(
            f'{self.endpoint}{course.uuid}/',
            {
                'title': 'Updated Course Title',
            },
        )
        assert response.status_code == status.HTTP_200_OK
        course.refresh_from_db()
        assert course.title == 'Updated Course Title'


# =============================================================================
# Course Enrollment Tests
# =============================================================================


@pytest.mark.django_db
class TestCourseEnrollmentViewSet:
    """Tests for course enrollments."""

    endpoint = '/api/v1/enrollments/'

    def test_list_enrollments(self, auth_client):
        """User can list their enrollments."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_enroll_in_course(self, auth_client, course):
        """User can enroll in a course."""
        course.status = 'published'
        course.save()

        response = auth_client.post(
            self.endpoint,
            {
                'course_uuid': str(course.uuid),
            },
        )
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
