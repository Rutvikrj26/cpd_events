"""Tests for the contacts CSV import + template endpoints."""

import io

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestImportTemplate:
    URL = '/api/v1/contacts/import-template/'

    def test_returns_csv_with_expected_columns(self, organizer_client):
        response = organizer_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'].startswith('text/csv')
        body = response.content.decode('utf-8-sig')
        header = body.splitlines()[0]
        assert 'email' in header
        assert 'full_name' in header


@pytest.mark.django_db
class TestImportCsv:
    URL = '/api/v1/contacts/import-csv/'

    def _csv(self, rows, header='email,full_name,professional_title,organization_name,phone,notes'):
        payload = header + '\n' + '\n'.join(rows)
        return io.BytesIO(payload.encode('utf-8'))

    def test_imports_valid_rows(self, organizer_client):
        f = self._csv([
            'a@example.com,Alice Adams,MD,Clinic,,',
            'b@example.com,Bob Brown,RN,Hospital,+15550000,New referral',
        ])
        response = organizer_client.post(self.URL, {'file': f}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['created'] == 2
        assert response.data['errors'] == []

    def test_missing_required_column_rejected(self, organizer_client):
        f = self._csv(
            ['foo@example.com,Full Name'],
            header='email,professional_title',  # no full_name
        )
        response = organizer_client.post(self.URL, {'file': f}, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_row_level_errors_reported(self, organizer_client):
        f = self._csv([
            ',Missing Email,MD,,,',
            'not-an-email,Bad Email,,,,',
            'ok@example.com,Ok Row,,,,',
        ])
        response = organizer_client.post(self.URL, {'file': f}, format='multipart')
        assert response.status_code == status.HTTP_200_OK  # partial success
        assert response.data['created'] == 1
        assert len(response.data['errors']) == 2
        rows = [e['row'] for e in response.data['errors']]
        assert 2 in rows and 3 in rows  # header is row 1

    def test_skip_duplicates_default(self, organizer_client, contact):
        existing_email = contact.email
        f = self._csv([f'{existing_email},Duplicate Row,,,,'])
        response = organizer_client.post(self.URL, {'file': f}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['skipped'] == 1
        assert response.data['created'] == 0

    def test_no_file_returns_400(self, organizer_client):
        response = organizer_client.post(self.URL, {}, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
