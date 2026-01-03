
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from events.models import Event
from factories import OrganizerFactory

@pytest.mark.django_db
def test_debug_create_event():
    organizer = OrganizerFactory()
    client = APIClient()
    client.force_authenticate(user=organizer)
    
    data = {
        'title': 'Debug Event',
        'description': 'A test event',
        'starts_at': (timezone.now() + timezone.timedelta(days=1)).isoformat(),
        'ends_at': (timezone.now() + timezone.timedelta(days=1, hours=2)).isoformat(),
        'timezone': 'UTC',
        'max_attendees': 100,
        'registration_enabled': True,
        'cpd_credit_value': '1.5'
    }
    
    response = client.post('/api/v1/events/', data, format='json')
    
    print("\n--- DEBUG RESPONSE ---")
    print(f"Status Code: {response.status_code}")
    print(f"Data: {response.data}")
    print("----------------------\n")
    
    assert response.status_code == status.HTTP_201_CREATED
