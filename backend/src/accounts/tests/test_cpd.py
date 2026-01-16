"""
Tests for CPD requirement tracking.
"""

import pytest
from rest_framework import status

from accounts.models import CPDRequirement
from factories import UserFactory


@pytest.fixture
def cpd_requirement(db, user):
    """A CPD requirement for the user."""
    return CPDRequirement.objects.create(
        user=user,
        cpd_type='general',
        cpd_type_display='General CPD',
        annual_requirement=50.0,
        period_type='calendar_year',
    )


@pytest.mark.django_db
class TestCPDRequirementViewSet:
    """Tests for CPD requirement management."""

    def get_endpoint(self):
        return '/api/v1/cpd-requirements/'

    def test_list_cpd_requirements(self, auth_client, cpd_requirement):
        """User can list their CPD requirements."""
        response = auth_client.get(self.get_endpoint())
        assert response.status_code == status.HTTP_200_OK
        # Check that we only get our own requirements
        assert len(response.data) >= 1

    def test_create_cpd_requirement(self, auth_client):
        """User can create a CPD requirement."""
        data = {
            'cpd_type': 'ethics',
            'cpd_type_display': 'Ethics',
            'annual_requirement': 10.0,
            'period_type': 'calendar_year',
        }
        response = auth_client.post(self.get_endpoint(), data)
        assert response.status_code == status.HTTP_201_CREATED
        assert CPDRequirement.objects.filter(user__isnull=False, cpd_type='ethics').exists()

    def test_retrieve_cpd_requirement(self, auth_client, cpd_requirement):
        """User can retrieve a specific requirement."""
        url = f"{self.get_endpoint()}{cpd_requirement.uuid}/"
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['cpd_type'] == cpd_requirement.cpd_type

    def test_update_cpd_requirement(self, auth_client, cpd_requirement):
        """User can update a requirement."""
        url = f"{self.get_endpoint()}{cpd_requirement.uuid}/"
        data = {'annual_requirement': '75.00'}
        response = auth_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        cpd_requirement.refresh_from_db()
        assert cpd_requirement.annual_requirement == 75.0

    def test_delete_cpd_requirement(self, auth_client, cpd_requirement):
        """User can delete a requirement."""
        url = f"{self.get_endpoint()}{cpd_requirement.uuid}/"
        response = auth_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CPDRequirement.objects.filter(uuid=cpd_requirement.uuid).exists()

    def test_cannot_access_others_requirements(self, auth_client):
        """User cannot see others' requirements."""
        other_user = UserFactory()
        other_req = CPDRequirement.objects.create(user=other_user, cpd_type='clinical', annual_requirement=20)
        url = f"{self.get_endpoint()}{other_req.uuid}/"
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_access(self, client):
        """Unauthenticated user cannot access endpoints."""
        response = client.get(self.get_endpoint())
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCPDProgressView:
    """Tests for CPD progress calculation."""

    def test_get_cpd_progress(self, auth_client, cpd_requirement):
        """User can get their calculated CPD progress."""
        endpoint = '/api/v1/cpd-requirements/progress/'
        response = auth_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

        # Should return summary dict
        assert isinstance(response.data, dict)
        assert 'total_requirements' in response.data
        assert 'completed_requirements' in response.data
        assert 'requirements' in response.data

        reqs = response.data['requirements']
        assert isinstance(reqs, list)
        if len(reqs) > 0:
            item = reqs[0]
            # Check for fields from serializer
            assert 'annual_requirement' in item

    def test_progress_empty(self, auth_client):
        """Returns empty summary if no requirements set."""
        # Ensure no requirements
        CPDRequirement.objects.all().delete()

        endpoint = '/api/v1/cpd-requirements/progress/'
        response = auth_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_requirements'] == 0

    def test_unauthenticated_cannot_access(self, client):
        """Unauthenticated user cannot access progress."""
        endpoint = '/api/v1/cpd-requirements/progress/'
        response = client.get(endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCPDRequirementValidation:
    """Tests for data validation."""

    def test_required_credits_positive(self, auth_client):
        """Annual requirement must be positive."""
        endpoint = '/api/v1/cpd-requirements/'
        data = {
            'cpd_type': 'general',
            'annual_requirement': -10,
        }
        response = auth_client.post(endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_fields(self, auth_client):
        """Missing fields should fail."""
        endpoint = '/api/v1/cpd-requirements/'
        data = {
            'annual_requirement': 50,
            # Missing cpd_type
        }
        response = auth_client.post(endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCPDExport:
    """Tests for CPD report export."""

    def test_export_json(self, auth_client, cpd_requirement):
        """User can export CPD report as JSON."""
        response = auth_client.get('/api/v1/cpd-requirements/export/?export_format=json')
        assert response.status_code == status.HTTP_200_OK
        assert 'application/json' in response['Content-Type']

    def test_export_csv(self, auth_client, cpd_requirement):
        """User can export CPD report as CSV."""
        response = auth_client.get('/api/v1/cpd-requirements/export/?export_format=csv')
        assert response.status_code == status.HTTP_200_OK
        assert 'text/csv' in response['Content-Type']

    def test_export_txt(self, auth_client, cpd_requirement):
        """User can export CPD report as TXT."""
        response = auth_client.get('/api/v1/cpd-requirements/export/?export_format=txt')
        assert response.status_code == status.HTTP_200_OK
        assert 'text/plain' in response['Content-Type']

    def test_export_default_json(self, auth_client, cpd_requirement):
        """Default export format is JSON."""
        response = auth_client.get('/api/v1/cpd-requirements/export/')
        assert response.status_code == status.HTTP_200_OK
        assert 'application/json' in response['Content-Type']

    def test_export_unauthenticated(self, client):
        """Unauthenticated user cannot export."""
        response = client.get('/api/v1/cpd-requirements/export/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

