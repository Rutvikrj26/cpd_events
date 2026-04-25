"""Tests for the cron tick endpoint."""

from unittest.mock import patch

import pytest
from rest_framework import status


ENDPOINT = '/api/common/cron/tick/'


@pytest.mark.django_db
class TestCronTickAuth:
    def test_rejects_when_secret_set_and_no_auth(self, api_client, settings):
        settings.CRON_SHARED_SECRET = 'test-secret'
        settings.DEBUG = False
        response = api_client.post(ENDPOINT)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_when_secret_set_and_wrong_auth(self, api_client, settings):
        settings.CRON_SHARED_SECRET = 'test-secret'
        settings.DEBUG = False
        response = api_client.post(ENDPOINT, HTTP_AUTHORIZATION='Bearer wrong')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_accepts_when_secret_set_and_correct_auth(self, api_client, settings):
        settings.CRON_SHARED_SECRET = 'test-secret'
        settings.DEBUG = False
        with patch('integrations.tasks.dispatch_scheduled_emails.delay'), \
             patch('events.tasks.send_event_reminders.delay'), \
             patch('events.tasks.auto_complete_events.delay'), \
             patch('integrations.tasks.retry_failed_emails.delay'):
            response = api_client.post(ENDPOINT, HTTP_AUTHORIZATION='Bearer test-secret')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'ok'
        assert set(response.data['tasks'].keys()) == {
            'dispatch_scheduled_emails',
            'send_event_reminders',
            'auto_complete_events',
            'retry_failed_emails',
        }

    def test_rejects_in_prod_when_no_secret_configured(self, api_client, settings):
        # Misconfiguration: no secret + DEBUG off → reject everything.
        settings.CRON_SHARED_SECRET = ''
        settings.DEBUG = False
        response = api_client.post(ENDPOINT)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_accepts_in_dev_from_localhost_with_no_secret(self, api_client, settings):
        settings.CRON_SHARED_SECRET = ''
        settings.DEBUG = True
        with patch('integrations.tasks.dispatch_scheduled_emails.delay'), \
             patch('events.tasks.send_event_reminders.delay'), \
             patch('events.tasks.auto_complete_events.delay'), \
             patch('integrations.tasks.retry_failed_emails.delay'):
            response = api_client.post(ENDPOINT, REMOTE_ADDR='127.0.0.1')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCronTickFanOut:
    def test_invokes_each_periodic_task(self, api_client, settings):
        settings.CRON_SHARED_SECRET = 'tick'
        settings.DEBUG = False
        with patch('integrations.tasks.dispatch_scheduled_emails.delay') as dispatch_mock, \
             patch('events.tasks.send_event_reminders.delay') as reminders_mock, \
             patch('events.tasks.auto_complete_events.delay') as complete_mock, \
             patch('integrations.tasks.retry_failed_emails.delay') as retry_mock:
            response = api_client.post(ENDPOINT, HTTP_AUTHORIZATION='Bearer tick')
        assert response.status_code == status.HTTP_200_OK
        dispatch_mock.assert_called_once()
        reminders_mock.assert_called_once()
        complete_mock.assert_called_once()
        retry_mock.assert_called_once()
