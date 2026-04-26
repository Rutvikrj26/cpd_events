"""
Regression tests for the concurrent webhook race that put VideoRecording
rows into PROCESSING after they had already been finalized.

Bug history (April 2026):
- Django's threaded WSGI processed `room_finished` and `recording_ended`
  concurrently. `_stop_active_recordings` did a Python read/write of
  `recording.status = PROCESSING` after `_handle_recording_ended` had already
  written `AVAILABLE`, clobbering the terminal state.

Fix:
- All VideoRecording state mutations go through `advance_recording(...)`,
  which uses an SQL `UPDATE ... WHERE status IN (allowed_predecessors)`.
- The webhook dispatcher takes a per-room Postgres advisory lock so handlers
  for the same room serialize. This module's tests run on SQLite and so only
  exercise the state-machine guards — the lock is a no-op there. Both layers
  are present in production.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.contenttypes.models import ContentType

from conferencing.models import VideoRecording, VideoRoom
from conferencing.state_machine import advance_recording, advance_room


@pytest.fixture
def event_room(db, event):
    ct = ContentType.objects.get_for_model(event)
    return VideoRoom.objects.create(
        content_type=ct,
        object_id=event.id,
        room_id='RM_state_machine',
        room_name=f'event-{event.uuid}',
        provider='livekit',
        status=VideoRoom.Status.ACTIVE,
    )


@pytest.fixture
def active_recording(db, event_room):
    return VideoRecording.objects.create(
        video_room=event_room,
        egress_id='EG_test_state',
        status=VideoRecording.Status.RECORDING,
    )


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.stop_recording.return_value = True
    # Patch at the source module — tasks.py imports get_video_provider lazily
    # inside helpers, so the mock has to land on the original definition.
    with patch('conferencing.service.get_video_provider', return_value=provider):
        yield provider


@pytest.mark.django_db
class TestRecordingStateMachine:
    """advance_recording enforces the allowed transitions."""

    def test_recording_to_processing(self, active_recording):
        ok = advance_recording(active_recording.id, to_status=VideoRecording.Status.PROCESSING)
        active_recording.refresh_from_db()
        assert ok is True
        assert active_recording.status == VideoRecording.Status.PROCESSING

    def test_recording_to_available(self, active_recording):
        ok = advance_recording(active_recording.id, to_status=VideoRecording.Status.AVAILABLE)
        active_recording.refresh_from_db()
        assert ok is True
        assert active_recording.status == VideoRecording.Status.AVAILABLE

    def test_processing_to_available(self, active_recording):
        active_recording.status = VideoRecording.Status.PROCESSING
        active_recording.save(update_fields=['status', 'updated_at'])

        ok = advance_recording(active_recording.id, to_status=VideoRecording.Status.AVAILABLE)
        active_recording.refresh_from_db()
        assert ok is True
        assert active_recording.status == VideoRecording.Status.AVAILABLE

    def test_available_cannot_regress_to_processing(self, active_recording):
        """Terminal → non-terminal must not fire (the original bug)."""
        active_recording.status = VideoRecording.Status.AVAILABLE
        active_recording.save(update_fields=['status', 'updated_at'])

        ok = advance_recording(active_recording.id, to_status=VideoRecording.Status.PROCESSING)
        active_recording.refresh_from_db()
        assert ok is False, "Guard should reject AVAILABLE → PROCESSING"
        assert active_recording.status == VideoRecording.Status.AVAILABLE

    def test_available_cannot_regress_to_recording(self, active_recording):
        active_recording.status = VideoRecording.Status.AVAILABLE
        active_recording.save(update_fields=['status', 'updated_at'])

        # Trying to set ERROR from a terminal AVAILABLE should fail too.
        ok = advance_recording(active_recording.id, to_status=VideoRecording.Status.ERROR)
        active_recording.refresh_from_db()
        assert ok is False
        assert active_recording.status == VideoRecording.Status.AVAILABLE

    def test_error_is_terminal(self, active_recording):
        active_recording.status = VideoRecording.Status.ERROR
        active_recording.save(update_fields=['status', 'updated_at'])

        ok = advance_recording(active_recording.id, to_status=VideoRecording.Status.AVAILABLE)
        active_recording.refresh_from_db()
        assert ok is False
        assert active_recording.status == VideoRecording.Status.ERROR


@pytest.mark.django_db
class TestRoomStateMachine:
    def test_scheduled_to_active(self, event_room):
        event_room.status = VideoRoom.Status.SCHEDULED
        event_room.save(update_fields=['status', 'updated_at'])

        ok = advance_room(event_room.id, to_status=VideoRoom.Status.ACTIVE)
        event_room.refresh_from_db()
        assert ok is True
        assert event_room.status == VideoRoom.Status.ACTIVE

    def test_active_to_ended(self, event_room):
        ok = advance_room(event_room.id, to_status=VideoRoom.Status.ENDED)
        event_room.refresh_from_db()
        assert ok is True
        assert event_room.status == VideoRoom.Status.ENDED


@pytest.mark.django_db
class TestConcurrentBugRepro:
    """
    Reproduce the original bug: recording_ended completes first, then
    room_finished's _stop_active_recordings runs with stale Python state.
    Before the fix, this clobbered AVAILABLE → PROCESSING. After the fix,
    the terminal state is preserved.
    """

    def test_stop_active_after_finalize_keeps_available(self, event_room, active_recording, mock_provider):
        from conferencing.tasks import _handle_recording_ended, _stop_active_recordings

        # Step 1: recording_ended arrives first and finalizes.
        payload = {
            'egressInfo': {
                'egressId': active_recording.egress_id,
                'status': 'EGRESS_COMPLETE',
                'fileResults': [{
                    'filename': '/out/test.mp4',
                    'size': 12345,
                    'duration': 30_000_000_000,  # 30s in ns
                }],
            }
        }
        _handle_recording_ended(event_room, payload)

        active_recording.refresh_from_db()
        assert active_recording.status == VideoRecording.Status.AVAILABLE
        # File row created with streaming URL
        files = list(active_recording.files.all())
        assert len(files) == 1
        assert files[0].storage_url.startswith('/api/v1/video/recordings/')

        # Step 2: room_finished's stop_active_recordings runs *after* — with
        # stale Python state. Before the fix this would clobber to PROCESSING.
        _stop_active_recordings(event_room)

        active_recording.refresh_from_db()
        assert active_recording.status == VideoRecording.Status.AVAILABLE, \
            "Terminal AVAILABLE must not be regressed to PROCESSING"

    def test_stop_active_first_then_finalize_lands_available(self, event_room, active_recording, mock_provider):
        from conferencing.tasks import _handle_recording_ended, _stop_active_recordings

        # Step 1: room_finished arrives first → PROCESSING
        _stop_active_recordings(event_room)
        active_recording.refresh_from_db()
        assert active_recording.status == VideoRecording.Status.PROCESSING

        # Step 2: recording_ended completes → AVAILABLE
        payload = {
            'egressInfo': {
                'egressId': active_recording.egress_id,
                'status': 'EGRESS_COMPLETE',
                'fileResults': [{'filename': '/out/test.mp4', 'size': 1, 'duration': 1_000_000_000}],
            }
        }
        _handle_recording_ended(event_room, payload)

        active_recording.refresh_from_db()
        assert active_recording.status == VideoRecording.Status.AVAILABLE

    def test_egress_aborted_lands_error_not_available(self, event_room, active_recording, mock_provider):
        from conferencing.tasks import _handle_recording_ended

        payload = {
            'egressInfo': {
                'egressId': active_recording.egress_id,
                'status': 'EGRESS_ABORTED',
                'fileResults': [{'filename': '/out/aborted.mp4', 'size': 0, 'duration': 0}],
            }
        }
        _handle_recording_ended(event_room, payload)

        active_recording.refresh_from_db()
        assert active_recording.status == VideoRecording.Status.ERROR
        # Aborted should NOT auto-publish even when auto_publish_recording=true.
        assert active_recording.is_published is False

    def test_re_delivered_recording_ended_is_idempotent(self, event_room, active_recording, mock_provider):
        from conferencing.tasks import _handle_recording_ended

        payload = {
            'egressInfo': {
                'egressId': active_recording.egress_id,
                'status': 'EGRESS_COMPLETE',
                'fileResults': [{'filename': '/out/test.mp4', 'size': 1, 'duration': 1_000_000_000}],
            }
        }
        # First delivery
        _handle_recording_ended(event_room, payload)
        active_recording.refresh_from_db()
        assert active_recording.status == VideoRecording.Status.AVAILABLE
        first_uuid = active_recording.uuid

        # Re-delivery — should not crash, should not flip to anything else,
        # should not duplicate file rows.
        _handle_recording_ended(event_room, payload)
        active_recording.refresh_from_db()
        assert active_recording.status == VideoRecording.Status.AVAILABLE
        assert active_recording.uuid == first_uuid
        assert active_recording.files.count() == 1
