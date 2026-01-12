import pytest
from rest_framework import status

from learning.models import Course


@pytest.mark.django_db
class TestLmsPlanAccess:
    def test_course_manager_subscription_defaults_to_lms_plan(self, course_manager):
        subscription = course_manager.subscription
        assert subscription.plan == 'lms'

    def test_course_manager_can_create_personal_course(self, course_manager_client, course_manager):
        data = {
            'title': 'Personal LMS Course',
            'slug': 'personal-lms-course',
            'description': 'Personal course description',
        }
        response = course_manager_client.post('/api/v1/courses/', data)
        assert response.status_code == status.HTTP_201_CREATED

        course = Course.objects.get(slug='personal-lms-course')
        assert course.organization is None
        assert course.created_by_id == course_manager.id

    def test_course_manager_owned_filter_lists_only_personal_courses(self, course_manager_client, course_manager):
        from factories import CourseFactory, UserFactory

        CourseFactory(organization=None, created_by=course_manager, slug='owned-course')
        other_user = UserFactory()
        CourseFactory(organization=None, created_by=other_user, slug='other-course')

        response = course_manager_client.get('/api/v1/courses/?owned=true')
        assert response.status_code == status.HTTP_200_OK

        results = response.data.get('results', response.data)
        slugs = {item['slug'] for item in results}
        assert 'owned-course' in slugs
        assert 'other-course' not in slugs

    def test_organizer_cannot_create_personal_course(self, organizer_client):
        data = {
            'title': 'Organizer LMS Course',
            'slug': 'organizer-lms-course',
        }
        response = organizer_client.post('/api/v1/courses/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_course_manager_cannot_create_event(self, course_manager_client, event_create_data):
        response = course_manager_client.post('/api/v1/events/', event_create_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_course_manager_course_limit_enforced(self, course_manager_client, course_manager):
        from billing.models import StripeProduct

        product, _ = StripeProduct.objects.update_or_create(
            plan='lms',
            defaults={
                'name': 'LMS',
                'stripe_product_id': 'prod_test_lms_limit',
                'is_active': True,
                'courses_per_month': 1,
            },
        )

        subscription = course_manager.subscription
        subscription.courses_created_this_period = product.courses_per_month
        subscription.save(update_fields=['courses_created_this_period', 'updated_at'])

        response = course_manager_client.post(
            '/api/v1/courses/',
            {
                'title': 'Limited Course',
                'slug': 'limited-course',
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_org_course_limit_enforced(self, organizer_client, organization):
        from billing.models import StripeProduct
        from organizations.models import OrganizationMembership, OrganizationSubscription

        membership = OrganizationMembership.objects.get(
            organization=organization,
            user=organization.created_by,
        )
        membership.role = OrganizationMembership.Role.COURSE_MANAGER
        membership.save(update_fields=['role'])

        StripeProduct.objects.update_or_create(
            plan='organization',
            defaults={
                'name': 'Organization',
                'stripe_product_id': 'prod_test_org_limit',
                'is_active': True,
                'courses_per_month': 1,
            },
        )

        org_subscription, _ = OrganizationSubscription.objects.update_or_create(
            organization=organization,
            defaults={
                'plan': 'organization',
                'status': 'active',
                'courses_created_this_period': 1,
            },
        )
        if org_subscription.courses_created_this_period != 1:
            org_subscription.courses_created_this_period = 1
            org_subscription.save(update_fields=['courses_created_this_period', 'updated_at'])

        response = organizer_client.post(
            '/api/v1/courses/',
            {
                'title': 'Org Limited Course',
                'slug': 'org-limited-course',
                'organization_slug': organization.slug,
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
