import api from '../client';
import type {
  ActiveMeetingResponse,
  JoinVideoResponse,
  VideoRecording,
  VideoRoom,
  VideoStatus,
} from './types';

export async function getVideoStatus(): Promise<VideoStatus> {
  const response = await api.get('/video/status/');
  return response.data;
}

export async function getVideoRooms(): Promise<VideoRoom[]> {
  const response = await api.get('/video/rooms/');
  return response.data.results || response.data;
}

// ---------------------------------------------------------------------------
// Meetings — Zoom-model lifecycle (start / join / end / active).
//
// Each meeting session is a fresh `VideoRoom` row on the backend.
// `start` is host-only and creates the row; `join` is everyone-else
// and 409s when no meeting is active; `active` is the cheap polling
// endpoint the lobby uses to know when to flip the join button on;
// `end` is the host's "End meeting for all" action.
// ---------------------------------------------------------------------------

export async function startEventMeeting(eventUuid: string): Promise<JoinVideoResponse> {
  const response = await api.post(`/events/${eventUuid}/meetings/start/`);
  return response.data;
}

export async function joinEventMeeting(eventUuid: string): Promise<JoinVideoResponse> {
  const response = await api.post(`/events/${eventUuid}/meetings/join/`);
  return response.data;
}

export async function getEventActiveMeeting(eventUuid: string): Promise<ActiveMeetingResponse> {
  const response = await api.get(`/events/${eventUuid}/meetings/active/`);
  return response.data;
}

export async function startCourseSessionMeeting(
  courseUuid: string,
  sessionUuid: string,
): Promise<JoinVideoResponse> {
  const response = await api.post(
    `/courses/${courseUuid}/sessions/${sessionUuid}/meetings/start/`,
  );
  return response.data;
}

export async function joinCourseSessionMeeting(
  courseUuid: string,
  sessionUuid: string,
): Promise<JoinVideoResponse> {
  const response = await api.post(
    `/courses/${courseUuid}/sessions/${sessionUuid}/meetings/join/`,
  );
  return response.data;
}

export async function getCourseSessionActiveMeeting(
  courseUuid: string,
  sessionUuid: string,
): Promise<ActiveMeetingResponse> {
  const response = await api.get(
    `/courses/${courseUuid}/sessions/${sessionUuid}/meetings/active/`,
  );
  return response.data;
}

/** Host-only "End meeting for all". Boots every participant. */
export async function endMeeting(roomUuid: string): Promise<{ status: string; room_uuid: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/end/`);
  return response.data;
}

// ---------------------------------------------------------------------------
// Recording / participant control — unchanged from previous design.
// ---------------------------------------------------------------------------

export async function getVideoRecordings(
  params?: { event_uuid?: string; course_session_uuid?: string; manage?: boolean },
): Promise<VideoRecording[]> {
  // `manage=true` opts host users into seeing unpublished + non-AVAILABLE rows
  // (used by the EventManagement recording panel).
  const query: Record<string, string> = {};
  if (params?.event_uuid) query.event_uuid = params.event_uuid;
  if (params?.course_session_uuid) query.course_session_uuid = params.course_session_uuid;
  if (params?.manage) query.manage = 'true';
  const response = await api.get('/video/recordings/', { params: query });
  return response.data.results || response.data;
}

export async function publishRecording(uuid: string): Promise<VideoRecording> {
  const response = await api.post(`/video/recordings/${uuid}/publish/`);
  return response.data;
}

export async function unpublishRecording(uuid: string): Promise<VideoRecording> {
  const response = await api.post(`/video/recordings/${uuid}/unpublish/`);
  return response.data;
}

export async function startRoomRecording(roomUuid: string): Promise<{ egress_id: string; status: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/start_recording/`);
  return response.data;
}

export async function stopRoomRecording(roomUuid: string): Promise<{ status: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/stop_recording/`);
  return response.data;
}

export async function admitParticipant(
  roomUuid: string,
  identity: string,
): Promise<{ status: string; identity: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/admit_participant/`, {
    identity,
  });
  return response.data;
}

export async function denyParticipant(
  roomUuid: string,
  identity: string,
): Promise<{ status: string; identity: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/deny_participant/`, {
    identity,
  });
  return response.data;
}
