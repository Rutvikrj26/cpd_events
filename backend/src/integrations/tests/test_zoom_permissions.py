import pytest
from rest_framework import status
from factories import UserFactory
from unittest.mock import patch

@pytest.mark.django_db
class TestZoomPermissions:
    def test_course_manager_can_access_zoom_status(self, api_client):
        user = UserFactory(account_type='course_manager')
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/integrations/zoom/status/')
        assert response.status_code == status.HTTP_200_OK

    def test_course_manager_can_initiate_zoom(self, api_client):
        user = UserFactory(account_type='course_manager')
        api_client.force_authenticate(user=user)
        
        with patch('accounts.services.zoom_service.initiate_oauth') as mock_init:
            mock_init.return_value = {'success': True, 'authorization_url': 'http://zoom.us/oauth'}
            response = api_client.get('/api/v1/integrations/zoom/initiate/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['url'] == 'http://zoom.us/oauth'

    def test_attendee_cannot_access_zoom_status(self, api_client):
        user = UserFactory(account_type='attendee')
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/integrations/zoom/status/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
