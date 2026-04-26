from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from events.models import Event, Speaker
from feedback.models import EventFeedback, FeedbackField, FeedbackFieldResponse
from registrations.models import Registration

User = get_user_model()


class FeedbackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com', password='password123', full_name='Test User'
        )
        self.organizer = User.objects.create_user(
            email='org@example.com', password='password123', full_name='Org User'
        )

        self.speaker = Speaker.objects.create(
            name='Dr. Speaker',
            bio='Expert in field',
            qualifications='PhD',
            owner=self.organizer,
        )

        self.event = Event.objects.create(
            title='Test CPD Event',
            slug='test-cpd-event',
            owner=self.organizer,
            starts_at=timezone.now() + timedelta(days=1),
            learning_objectives=['Learn A', 'Learn B'],
        )
        self.event.speakers.add(self.speaker)

        self.registration = Registration.objects.create(
            event=self.event,
            user=self.user,
            email='test@example.com',
            status='confirmed',
        )

        self.rating_field = FeedbackField.objects.create(
            event=self.event,
            label='Overall rating',
            field_type=FeedbackField.FieldType.RATING,
            required=True,
            min_value=1,
            max_value=5,
            order=0,
        )
        self.comments_field = FeedbackField.objects.create(
            event=self.event,
            label='Comments',
            field_type=FeedbackField.FieldType.TEXTAREA,
            required=False,
            order=1,
        )

    def test_create_feedback_with_dynamic_responses(self):
        feedback = EventFeedback.objects.create(
            event=self.event,
            registration=self.registration,
            is_anonymous=False,
        )
        FeedbackFieldResponse.objects.create(feedback=feedback, field=self.rating_field, value=5)
        FeedbackFieldResponse.objects.create(
            feedback=feedback, field=self.comments_field, value='Great event!'
        )

        self.assertEqual(feedback.field_responses.count(), 2)
        self.assertEqual(
            feedback.field_responses.get(field=self.rating_field).value, 5
        )
        self.assertEqual(
            feedback.field_responses.get(field=self.comments_field).value, 'Great event!'
        )

    def test_anonymous_feedback(self):
        feedback = EventFeedback.objects.create(
            event=self.event,
            registration=self.registration,
            is_anonymous=True,
        )
        self.assertTrue(feedback.is_anonymous)

    def test_session_level_feedback_is_independent_of_event_level(self):
        """With a nullable session FK, (event, null, registration) and
        (event, session, registration) are separate rows."""
        from events.models import EventSession

        session = EventSession.objects.create(
            event=self.event,
            title='Session 1',
            starts_at=self.event.starts_at,
            duration_minutes=60,
        )
        event_level = EventFeedback.objects.create(
            event=self.event, registration=self.registration
        )
        session_level = EventFeedback.objects.create(
            event=self.event, registration=self.registration, session=session
        )
        self.assertNotEqual(event_level.pk, session_level.pk)
