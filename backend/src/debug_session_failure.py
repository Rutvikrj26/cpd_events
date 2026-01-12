import os
import sys

import django
from rest_framework.test import APIRequestFactory, force_authenticate

# Setup Django source
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from events.models import Event
from events.views import EventSessionViewSet


def investigate_session_creation():
    event_uuid = 'ade08fa1-c34d-4dc6-a55a-66170113908f'
    try:
        event = Event.objects.get(uuid=event_uuid)
    except Event.DoesNotExist:
        print(f"Event {event_uuid} not found. Using first available event owned by a user.")
        event = Event.objects.first()
        if not event:
            print("No events found to test.")
            return

    user = event.owner
    print(f"Testing session creation for Event: {event.title} ({event.uuid})")
    print(f"Owner: {user.email}")

    # Mock request data
    session_data = {
        "title": "Test Session Debug",
        "starts_at": "2026-02-01T10:00:00Z",
        "duration_minutes": 60,
        "session_type": "live",
        "is_mandatory": True,
        "is_published": True,
    }

    factory = APIRequestFactory()
    request = factory.post(f'/api/v1/events/{event.uuid}/sessions/', session_data, format='json')
    force_authenticate(request, user=user)

    view = EventSessionViewSet.as_view({'post': 'create'})

    try:
        response = view(request, event_uuid=event.uuid)
        print(f"Response Status Code: {response.status_code}")
        if response.status_code == 201:
            print("SUCCESS: Session created successfully.")
            print(response.data)
        else:
            print("FAILURE: Session creation failed.")
            print(f"Error Data: {response.data}")

    except Exception as e:
        print(f"EXCEPTION during view execution: {e}")


if __name__ == "__main__":
    investigate_session_creation()
