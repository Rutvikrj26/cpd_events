import pytest
from rest_framework import status

from learning.models import Course


@pytest.mark.django_db
class TestLmsPlanAccess:
    def test_course_manager_subscription_defaults_to_lms_plan(self, course_manager):
        subscription = course_manager.subscription
        assert subscription.plan == "lms"

    def test_course_manager_can_create_personal_course(self, course_manager_client, course_manager):
        data = {
            "title": "Personal LMS Course",
            "slug": "personal-lms-course",
            "description": "Personal course description",
        }
        response = course_manager_client.post("/api/v1/courses/", data)
        assert response.status_code == status.HTTP_201_CREATED

        course = Course.objects.get(slug="personal-lms-course")
        assert course.owner_id == course_manager.id

    def test_course_manager_owned_filter_lists_only_personal_courses(self, course_manager_client, course_manager):
        from factories import CourseFactory, UserFactory

        CourseFactory(owner=course_manager, slug="owned-course")
        other_user = UserFactory()
        CourseFactory(owner=other_user, slug="other-course")

        response = course_manager_client.get("/api/v1/courses/?owned=true")
        assert response.status_code == status.HTTP_200_OK

        results = response.data.get("results", response.data)
        slugs = {item["slug"] for item in results}
        assert "owned-course" in slugs
        assert "other-course" not in slugs

    def test_organizer_cannot_create_personal_course(self, organizer_client):
        data = {
            "title": "Organizer LMS Course",
            "slug": "organizer-lms-course",
        }
        response = organizer_client.post("/api/v1/courses/", data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_course_manager_cannot_create_event(self, course_manager_client, event_create_data):
        response = course_manager_client.post("/api/v1/events/", event_create_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_course_manager_course_limit_enforced(self, course_manager_client, course_manager):
        from billing.models import StripeProduct

        product, _ = StripeProduct.objects.update_or_create(
            plan="lms",
            defaults={
                "name": "LMS",
                "stripe_product_id": "prod_test_lms_limit",
                "is_active": True,
                "courses_per_month": 1,
            },
        )

        subscription = course_manager.subscription
        subscription.courses_created_this_period = product.courses_per_month
        subscription.save(update_fields=["courses_created_this_period", "updated_at"])

        response = course_manager_client.post(
            "/api/v1/courses/",
            {
                "title": "Limited Course",
                "slug": "limited-course",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
