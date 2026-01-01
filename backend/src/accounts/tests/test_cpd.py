"""
Tests for CPD requirements endpoints.

Endpoints tested:
- GET /api/v1/cpd-requirements/
- POST /api/v1/cpd-requirements/
- GET /api/v1/cpd-requirements/{uuid}/
- PATCH /api/v1/cpd-requirements/{uuid}/
- DELETE /api/v1/cpd-requirements/{uuid}/
- GET /api/v1/cpd-requirements/progress/
"""

import pytest
from rest_framework import status
from datetime import date


# =============================================================================
# CPD Requirements ViewSet Tests
# =============================================================================


@pytest.mark.django_db
class TestCPDRequirementViewSet:
    """Tests for CPD requirements CRUD operations."""

    base_endpoint = '/api/v1/cpd-requirements/'

    def test_list_cpd_requirements(self, auth_client, user, db):
        """User can list their CPD requirements."""
        from accounts.models import CPDRequirement
        # Create some requirements
        CPDRequirement.objects.create(
            user=user,
            name='Medical CPD',
            required_credits=30,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        response = auth_client.get(self.base_endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_create_cpd_requirement(self, auth_client):
        """User can create a CPD requirement."""
        data = {
            'name': 'Medical CPD 2024',
            'required_credits': 25,
            'period_start': '2024-01-01',
            'period_end': '2024-12-31',
            'cpd_type': 'medical',
        }
        response = auth_client.post(self.base_endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Medical CPD 2024'

    def test_retrieve_cpd_requirement(self, auth_client, user, db):
        """User can retrieve a specific CPD requirement."""
        from accounts.models import CPDRequirement
        req = CPDRequirement.objects.create(
            user=user,
            name='Test Requirement',
            required_credits=20,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        response = auth_client.get(f'{self.base_endpoint}{req.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Requirement'

    def test_update_cpd_requirement(self, auth_client, user, db):
        """User can update their CPD requirement."""
        from accounts.models import CPDRequirement
        req = CPDRequirement.objects.create(
            user=user,
            name='Original Name',
            required_credits=20,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        response = auth_client.patch(f'{self.base_endpoint}{req.uuid}/', {
            'name': 'Updated Name',
            'required_credits': 30,
        })
        assert response.status_code == status.HTTP_200_OK
        req.refresh_from_db()
        assert req.name == 'Updated Name'
        assert req.required_credits == 30

    def test_delete_cpd_requirement(self, auth_client, user, db):
        """User can delete their CPD requirement."""
        from accounts.models import CPDRequirement
        req = CPDRequirement.objects.create(
            user=user,
            name='To Delete',
            required_credits=20,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        response = auth_client.delete(f'{self.base_endpoint}{req.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CPDRequirement.objects.filter(uuid=req.uuid).exists()

    def test_cannot_access_others_requirements(self, auth_client, other_organizer, db):
        """User cannot access another user's CPD requirements."""
        from accounts.models import CPDRequirement
        other_req = CPDRequirement.objects.create(
            user=other_organizer,
            name='Other User Requirement',
            required_credits=20,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        response = auth_client.get(f'{self.base_endpoint}{other_req.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.base_endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# CPD Progress Tests
# =============================================================================


@pytest.mark.django_db
class TestCPDProgressView:
    """Tests for GET /api/v1/cpd-requirements/progress/"""

    endpoint = '/api/v1/cpd-requirements/progress/'

    def test_get_cpd_progress(self, auth_client, user, db):
        """User can get their CPD progress summary."""
        from accounts.models import CPDRequirement
        # Create a requirement
        CPDRequirement.objects.create(
            user=user,
            name='Medical CPD',
            required_credits=30,
            earned_credits=15,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
        )
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_progress_empty(self, auth_client):
        """Progress works even with no requirements."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# CPD Requirements Validation Tests
# =============================================================================


@pytest.mark.django_db
class TestCPDRequirementValidation:
    """Tests for CPD requirement validation rules."""

    base_endpoint = '/api/v1/cpd-requirements/'

    def test_period_end_after_start(self, auth_client):
        """Period end must be after period start."""
        data = {
            'name': 'Invalid Period',
            'required_credits': 25,
            'period_start': '2024-12-31',
            'period_end': '2024-01-01',  # Before start
        }
        response = auth_client.post(self.base_endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_required_credits_positive(self, auth_client):
        """Required credits must be positive."""
        data = {
            'name': 'Invalid Credits',
            'required_credits': -5,
            'period_start': '2024-01-01',
            'period_end': '2024-12-31',
        }
        response = auth_client.post(self.base_endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_fields(self, auth_client):
        """Required fields must be provided."""
        data = {
            'name': 'Missing Fields',
            # Missing required_credits, period_start, period_end
        }
        response = auth_client.post(self.base_endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
