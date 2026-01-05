import pytest
from rest_framework import status
from events.models import Event
from django.utils import timezone

@pytest.mark.django_db
def test_swagger_docs_accessible(api_client):
    """Swagger UI is disabled by default."""
    response = api_client.get('/api/docs/')
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_create_event(organizer_client):
    """Test creating an event."""
    data = {
        'title': 'Test Event',
        'description': 'A test event',
        'starts_at': (timezone.now() + timezone.timedelta(days=1)).isoformat(),
        'ends_at': (timezone.now() + timezone.timedelta(days=1, hours=2)).isoformat(),
        'timezone': 'UTC',
        'max_attendees': 100,
        'registration_enabled': True,
        'cpd_credit_value': '1.5'
    }
    response = organizer_client.post('/api/v1/events/', data)
    if response.status_code != status.HTTP_201_CREATED:
        pytest.fail(f"Failed to create event: {response.data}")
    assert response.status_code == status.HTTP_201_CREATED
    assert Event.objects.count() == 1
    assert Event.objects.get().title == 'Test Event'

@pytest.mark.django_db
def test_unauthenticated_access_denied(api_client):
    """Test that unauthenticated users cannot create events."""
    data = {
        'title': 'Unauthorized Event',
    }
    response = api_client.post('/api/v1/events/', data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
