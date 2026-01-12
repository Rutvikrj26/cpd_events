from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from events.models import Event, Speaker
from feedback.models import EventFeedback
from organizations.models import Organization
from registrations.models import Registration

User = get_user_model()


class FeedbackTests(TestCase):
    def setUp(self):
        # Create User
        self.user = User.objects.create_user(email='test@example.com', password='password123', full_name='Test User')
        self.organizer = User.objects.create_user(email='org@example.com', password='password123', full_name='Org User')

        # Create Organization
        self.org = Organization.objects.create(name='Test Org', created_by=self.organizer)

        # Create Speaker
        self.speaker = Speaker.objects.create(
            name='Dr. Speaker',
            bio='Expert in field',
            qualifications='PhD',
            owner=self.organizer,
        )

        # Create Event
        self.event = Event.objects.create(
            title='Test CPD Event',
            slug='test-cpd-event',
            owner=self.organizer,
            starts_at=timezone.now() + timedelta(days=1),
            learning_objectives=['Learn A', 'Learn B'],
        )
        self.event.speakers.add(self.speaker)

        # Create Registration
        self.registration = Registration.objects.create(
            event=self.event,
            user=self.user,
            email='test@example.com',
            status='confirmed',
        )

    def test_create_feedback(self):
        feedback = EventFeedback.objects.create(
            event=self.event,
            registration=self.registration,
            rating=5,
            content_quality_rating=4,
            speaker_rating=5,
            comments='Great event!',
            is_anonymous=False,
        )

        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.event.speakers.first().name, 'Dr. Speaker')
        self.assertEqual(self.event.learning_objectives, ['Learn A', 'Learn B'])

    def test_anonymous_feedback(self):
        feedback = EventFeedback.objects.create(
            event=self.event,
            registration=self.registration,
            rating=3,
            content_quality_rating=3,
            speaker_rating=3,
            is_anonymous=True,
        )
        self.assertTrue(feedback.is_anonymous)
