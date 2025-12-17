import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    user = User.objects.create_user(
        email='test@example.com',
        full_name='Test User',
        password='testpassword123',
        account_type='attendee'
    )
    return user

@pytest.fixture
def organizer(db):
    user = User.objects.create_user(
        email='organizer@example.com',
        full_name='Test Organizer',
        password='testpassword123',
        account_type='organizer'
    )
    return user

@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def organizer_client(organizer):
    client = APIClient()
    client.force_authenticate(user=organizer)
    return client
