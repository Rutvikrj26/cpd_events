"""
Unit tests for the Zoom provider (``conferencing.providers.zoom``).

These tests run without a live Zoom account by mocking
``requests.post`` (used by the S2S OAuth client) and ``requests.request``
(used by the API helper). HMAC signatures are computed with the real
algorithm so the tests stay valid if the message format ever changes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from conferencing.provider import RegistrantInfo, RoomResult, WebhookEvent
from conferencing.providers import zoom as zoom_mod
from conferencing.providers.zoom import ZoomProvider, _ZoomTokenClient


ZOOM_SETTINGS = dict(
    ZOOM_ACCOUNT_ID='acct',
    ZOOM_CLIENT_ID='cid',
    ZOOM_CLIENT_SECRET='sec',
    ZOOM_ADMIN_USER_ID='admin@example.com',
    ZOOM_WEBHOOK_SECRET_TOKEN='whsec',
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_token_client():
    """The module-level ``_token_client`` is process-singleton state — swap
    in a fresh instance per test so cached tokens don't leak across tests.
    """
    original = zoom_mod._token_client
    zoom_mod._token_client = _ZoomTokenClient()
    try:
        yield zoom_mod._token_client
    finally:
        zoom_mod._token_client = original


def _ok_token_response(token: str = 'T1', expires_in: int = 3600) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {'access_token': token, 'expires_in': expires_in}
    resp.raise_for_status.return_value = None
    return resp


def _api_response(status_code: int, payload: dict | None = None, text: str = '') -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload or {}
    resp.text = text
    resp.raise_for_status.side_effect = (
        None if status_code < 400 else Exception(f'http {status_code}')
    )
    return resp


def _prime_token(client: _ZoomTokenClient, token: str = 'PRIMED') -> None:
    """Pre-seed the token cache so ``_request`` doesn't need to fetch."""
    client._token = token
    client._expires_at = time.monotonic() + 3600


def _sign(body: bytes, ts: str, secret: str = 'whsec') -> str:
    """Build the ``"<ts>|<sig>"`` auth header the provider expects."""
    message = f'v0:{ts}:{body.decode("utf-8")}'.encode()
    sig = 'v0=' + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f'{ts}|{sig}'


# ---------------------------------------------------------------------------
# 1. S2S token caching
# ---------------------------------------------------------------------------


class TestZoomTokenClient:
    """``_ZoomTokenClient`` caches the bearer token in-process and refreshes
    only on invalidation or near-expiry."""

    def test_get_caches_after_first_fetch(self, reset_token_client):
        client = reset_token_client
        with patch('requests.post', return_value=_ok_token_response('T1', 3600)) as post:
            t1 = client.get(account_id='a', client_id='c', client_secret='s')
            t2 = client.get(account_id='a', client_id='c', client_secret='s')

        assert t1 == 'T1'
        assert t2 == 'T1'
        assert post.call_count == 1, 'cached token must not trigger a second POST'

    def test_get_refetches_after_invalidate(self, reset_token_client):
        client = reset_token_client
        responses = [_ok_token_response('T1', 3600), _ok_token_response('T2', 3600)]
        with patch('requests.post', side_effect=responses) as post:
            assert client.get(account_id='a', client_id='c', client_secret='s') == 'T1'
            client.invalidate()
            assert client.get(account_id='a', client_id='c', client_secret='s') == 'T2'

        assert post.call_count == 2

    def test_get_refetches_when_expired(self, reset_token_client):
        client = reset_token_client
        # First fetch returns a token whose expiry is *inside* the 5-minute
        # skew window — every subsequent .get() should fetch again.
        responses = [_ok_token_response('T1', 60), _ok_token_response('T2', 3600)]
        with patch('requests.post', side_effect=responses) as post:
            assert client.get(account_id='a', client_id='c', client_secret='s') == 'T1'
            assert client.get(account_id='a', client_id='c', client_secret='s') == 'T2'

        assert post.call_count == 2

    def test_get_sends_basic_auth_and_account_id(self, reset_token_client):
        client = reset_token_client
        with patch('requests.post', return_value=_ok_token_response()) as post:
            client.get(account_id='a', client_id='c', client_secret='s')

        _args, kwargs = post.call_args
        expected_basic = base64.b64encode(b'c:s').decode()
        assert kwargs['headers']['Authorization'] == f'Basic {expected_basic}'
        assert kwargs['params']['grant_type'] == 'account_credentials'
        assert kwargs['params']['account_id'] == 'a'


# ---------------------------------------------------------------------------
# 2. create_room
# ---------------------------------------------------------------------------


@override_settings(**ZOOM_SETTINGS)
class TestCreateRoom:
    def test_posts_meeting_with_expected_settings(self, reset_token_client):
        _prime_token(reset_token_client)
        api_payload = {
            'id': 12345,
            'uuid': 'meet-uuid-xyz',
            'join_url': 'https://zoom.us/j/12345',
            'start_url': 'https://zoom.us/s/12345',
            'password': 'p4ss',
        }
        provider = ZoomProvider()

        with patch('requests.request', return_value=_api_response(201, api_payload)) as rq:
            result = provider.create_room(
                'My Webinar',
                metadata={
                    'alternative_hosts': 'host1@example.com,host2@example.com',
                    'duration_minutes': 90,
                    'topic': 'Custom Topic',
                    'start_time': '2026-06-01T10:00:00Z',
                    'timezone': 'America/Toronto',
                },
            )

        assert rq.call_count == 1
        method, url = rq.call_args.args
        kwargs = rq.call_args.kwargs
        assert method == 'POST'
        assert url.endswith('/users/admin@example.com/meetings')
        assert kwargs['headers']['Authorization'] == 'Bearer PRIMED'
        assert kwargs['headers']['Content-Type'] == 'application/json'

        body = kwargs['json']
        assert body['topic'] == 'Custom Topic'
        assert body['duration'] == 90
        assert body['start_time'] == '2026-06-01T10:00:00Z'
        assert body['timezone'] == 'America/Toronto'
        s = body['settings']
        assert s['auto_recording'] == 'cloud'
        assert s['approval_type'] == 0
        assert s['registration_type'] == 1
        assert s['join_before_host'] is True
        assert s['alternative_hosts'] == 'host1@example.com,host2@example.com'

        # RoomResult shape
        assert isinstance(result, RoomResult)
        assert result.room_name == 'My Webinar'
        assert result.metadata['zoom_meeting_id'] == '12345'
        assert result.metadata['zoom_uuid'] == 'meet-uuid-xyz'
        assert result.metadata['zoom_join_url'] == 'https://zoom.us/j/12345'
        # caller-supplied metadata is preserved
        assert result.metadata['alternative_hosts'] == 'host1@example.com,host2@example.com'

    def test_falls_back_to_name_when_topic_missing(self, reset_token_client):
        _prime_token(reset_token_client)
        provider = ZoomProvider()
        with patch('requests.request', return_value=_api_response(201, {'id': 1, 'uuid': 'u'})) as rq:
            provider.create_room('Fallback Name', metadata=None)

        body = rq.call_args.kwargs['json']
        assert body['topic'] == 'Fallback Name'
        # No alternative_hosts in metadata → empty string passed through.
        assert body['settings']['alternative_hosts'] == ''

    def test_max_participants_sets_registration_limit(self, reset_token_client):
        _prime_token(reset_token_client)
        provider = ZoomProvider()
        with patch('requests.request', return_value=_api_response(201, {'id': 1, 'uuid': 'u'})) as rq:
            provider.create_room('R', metadata={}, max_participants=42)

        assert rq.call_args.kwargs['json']['settings']['registration_limit'] == 42


# ---------------------------------------------------------------------------
# 3. register_attendee
# ---------------------------------------------------------------------------


@override_settings(**ZOOM_SETTINGS)
class TestRegisterAttendee:
    def test_success_returns_registrant_info(self, reset_token_client):
        _prime_token(reset_token_client)
        provider = ZoomProvider()
        api_payload = {
            'registrant_id': 'reg-abc',
            'join_url': 'https://zoom.us/w/reg-abc',
        }

        with patch('requests.request', return_value=_api_response(201, api_payload)) as rq:
            info = provider.register_attendee(
                '987654321', 'jane@example.com', 'Jane Q Doe',
            )

        method, url = rq.call_args.args
        body = rq.call_args.kwargs['json']
        assert method == 'POST'
        assert url.endswith('/meetings/987654321/registrants')
        assert body == {
            'email': 'jane@example.com',
            'first_name': 'Jane',
            'last_name': 'Q Doe',
            'auto_approve': True,
        }
        assert isinstance(info, RegistrantInfo)
        assert info.registrant_id == 'reg-abc'
        assert info.join_url == 'https://zoom.us/w/reg-abc'
        assert info.email == 'jane@example.com'

    def test_failure_returns_empty_registrant_id(self, reset_token_client):
        _prime_token(reset_token_client)
        provider = ZoomProvider()

        with patch('requests.request', return_value=_api_response(400, text='bad request')):
            info = provider.register_attendee('1', 'x@example.com', 'X')

        assert isinstance(info, RegistrantInfo)
        assert info.registrant_id == ''
        assert info.join_url == ''
        assert info.email == 'x@example.com'

    def test_single_word_name_used_as_first_name(self, reset_token_client):
        _prime_token(reset_token_client)
        provider = ZoomProvider()

        with patch('requests.request', return_value=_api_response(201, {'registrant_id': 'r'})) as rq:
            provider.register_attendee('1', 'a@b.com', 'Cher')

        body = rq.call_args.kwargs['json']
        assert body['first_name'] == 'Cher'
        assert body['last_name'] == ''


# ---------------------------------------------------------------------------
# 4. verify_webhook
# ---------------------------------------------------------------------------


@override_settings(**ZOOM_SETTINGS)
class TestVerifyWebhook:
    def test_valid_signature_passes(self):
        provider = ZoomProvider()
        body = b'{"event":"meeting.started"}'
        ts = '1700000000'
        auth = _sign(body, ts, secret='whsec')
        assert provider.verify_webhook(body, auth) is True

    def test_tampered_body_fails(self):
        provider = ZoomProvider()
        body = b'{"event":"meeting.started"}'
        ts = '1700000000'
        auth = _sign(body, ts, secret='whsec')
        # Body changed after signing — signature must no longer match.
        tampered = b'{"event":"meeting.ended"}'
        assert provider.verify_webhook(tampered, auth) is False

    def test_wrong_secret_fails(self):
        provider = ZoomProvider()
        body = b'{"event":"meeting.started"}'
        ts = '1700000000'
        auth = _sign(body, ts, secret='not-the-real-secret')
        assert provider.verify_webhook(body, auth) is False

    def test_missing_timestamp_or_sig_fails(self):
        provider = ZoomProvider()
        body = b'{}'
        # No pipe → ts present, sig empty
        assert provider.verify_webhook(body, 'just-a-sig') is False
        # Empty ts
        assert provider.verify_webhook(body, '|v0=abc') is False

    @override_settings(ZOOM_WEBHOOK_SECRET_TOKEN='')
    def test_no_secret_configured_returns_false(self):
        provider = ZoomProvider()
        body = b'{}'
        ts = '1700000000'
        auth = _sign(body, ts, secret='whsec')  # any signature
        assert provider.verify_webhook(body, auth) is False


# ---------------------------------------------------------------------------
# 5. parse_webhook — CRC challenge
# ---------------------------------------------------------------------------


@override_settings(**ZOOM_SETTINGS)
class TestParseWebhookCrc:
    def test_url_validation_returns_crc_challenge(self):
        provider = ZoomProvider()
        plain = 'plain-token-from-zoom'
        body_dict = {
            'event': 'endpoint.url_validation',
            'payload': {'plainToken': plain},
        }
        body = json.dumps(body_dict).encode()
        ts = '1700000000'
        auth = _sign(body, ts)

        event = provider.parse_webhook(body, auth)

        expected_encrypted = hmac.new(
            b'whsec', plain.encode(), hashlib.sha256,
        ).hexdigest()

        assert isinstance(event, WebhookEvent)
        assert event.type == 'crc_challenge'
        assert event.metadata['plain_token'] == plain
        assert event.metadata['encrypted_token'] == expected_encrypted


# ---------------------------------------------------------------------------
# 6. parse_webhook — event mapping
# ---------------------------------------------------------------------------


def _signed_event(body_dict: dict) -> tuple[bytes, str]:
    body = json.dumps(body_dict).encode()
    ts = '1700000000'
    return body, _sign(body, ts)


@override_settings(**ZOOM_SETTINGS)
class TestParseWebhookEventMap:
    def test_meeting_started(self):
        provider = ZoomProvider()
        body, auth = _signed_event({
            'event': 'meeting.started',
            'payload': {'object': {'id': 555, 'uuid': 'uuid-555', 'topic': 'Hello'}},
        })
        event = provider.parse_webhook(body, auth)
        assert event.type == 'room_started'
        assert event.room_name == 'Hello'
        assert event.room_id == 'uuid-555'
        assert event.metadata['zoom_meeting_id'] == '555'
        assert event.metadata['zoom_uuid'] == 'uuid-555'

    def test_meeting_ended(self):
        provider = ZoomProvider()
        body, auth = _signed_event({
            'event': 'meeting.ended',
            'payload': {'object': {'id': 5, 'uuid': 'u', 'topic': 't'}},
        })
        event = provider.parse_webhook(body, auth)
        assert event.type == 'room_finished'

    def test_participant_joined_pulls_email_and_registrant(self):
        provider = ZoomProvider()
        body, auth = _signed_event({
            'event': 'meeting.participant_joined',
            'payload': {
                'object': {
                    'id': 99,
                    'uuid': 'u-99',
                    'topic': 'T',
                    'participant': {
                        'user_id': 'p1',
                        'user_name': 'Alice',
                        'email': 'alice@example.com',
                        'registrant_id': 'reg-1',
                        'join_time': '2026-06-01T10:00:00Z',
                    },
                },
            },
        })
        event = provider.parse_webhook(body, auth)
        assert event.type == 'participant_joined'
        assert event.participant_identity == 'p1'
        assert event.participant_name == 'Alice'
        assert event.metadata['email'] == 'alice@example.com'
        assert event.metadata['registrant_id'] == 'reg-1'
        assert event.metadata['zoom_meeting_id'] == '99'
        assert event.metadata['zoom_uuid'] == 'u-99'

    def test_recording_completed_attaches_files(self):
        provider = ZoomProvider()
        recording_files = [{'id': 'f1', 'file_type': 'MP4'}]
        body, auth = _signed_event({
            'event': 'recording.completed',
            'download_token': 'dlt',
            'payload': {
                'object': {
                    'id': 7,
                    'uuid': 'u-7',
                    'topic': 'Class',
                    'recording_files': recording_files,
                },
            },
        })
        event = provider.parse_webhook(body, auth)
        assert event.type == 'recording_ended'
        assert event.metadata['recording_files'] == recording_files
        assert event.metadata['download_token'] == 'dlt'

    def test_invalid_signature_raises(self):
        provider = ZoomProvider()
        body = json.dumps({'event': 'meeting.started', 'payload': {'object': {}}}).encode()
        with pytest.raises(PermissionError):
            provider.parse_webhook(body, '1700000000|v0=deadbeef')


# ---------------------------------------------------------------------------
# 7. get_webhook_dedup_key
# ---------------------------------------------------------------------------


@override_settings(**ZOOM_SETTINGS)
class TestDedupKey:
    @pytest.mark.parametrize(
        'header_key',
        ['x-zm-trackingid', 'X-Zm-Trackingid', 'X-ZM-TRACKINGID'],
    )
    def test_returns_tracking_id(self, header_key):
        provider = ZoomProvider()
        key = provider.get_webhook_dedup_key({header_key: 'track-123'})
        assert key == 'track-123'

    def test_empty_when_missing(self):
        provider = ZoomProvider()
        assert provider.get_webhook_dedup_key({}) == ''
        assert provider.get_webhook_dedup_key(None) == ''


# ---------------------------------------------------------------------------
# 8. 401 retry path
# ---------------------------------------------------------------------------


@override_settings(**ZOOM_SETTINGS)
class TestRequestRetryOn401:
    def test_invalidates_token_and_retries_once(self, reset_token_client):
        _prime_token(reset_token_client, token='OLD')
        provider = ZoomProvider()

        first = _api_response(401, text='unauthorized')
        second = _api_response(200, {'id': 1, 'uuid': 'u'})

        # The retry path calls _headers() again, which calls _token().
        # Since the cache was just invalidated, _token_client.get() would hit
        # requests.post; we mock that to return a fresh token.
        with patch('requests.post', return_value=_ok_token_response('NEW', 3600)) as post, \
                patch('requests.request', side_effect=[first, second]) as rq:
            resp = provider.create_room('R', metadata={})

        assert rq.call_count == 2, 'expected exactly one retry after 401'
        # First call used the OLD token; second call must use the freshly fetched NEW token.
        first_auth = rq.call_args_list[0].kwargs['headers']['Authorization']
        second_auth = rq.call_args_list[1].kwargs['headers']['Authorization']
        assert first_auth == 'Bearer OLD'
        assert second_auth == 'Bearer NEW'
        # The token cache was invalidated, so a fresh fetch should have happened.
        assert post.call_count == 1
        # Final response is the 200 — create_room must succeed and return RoomResult.
        assert isinstance(resp, RoomResult)
        assert resp.metadata['zoom_meeting_id'] == '1'
