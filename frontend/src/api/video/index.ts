import api from '../client';
import type { JoinVideoResponse, VideoRecording, VideoRoom, VideoStatus } from './types';

export async function getVideoStatus(): Promise<VideoStatus> {
  const response = await api.get('/video/status/');
  return response.data;
}

export async function getVideoRooms(): Promise<VideoRoom[]> {
  const response = await api.get('/video/rooms/');
  return response.data.results || response.data;
}

export async function joinEventVideo(eventUuid: string): Promise<JoinVideoResponse> {
  const response = await api.post(`/events/${eventUuid}/join-video/`);
  return response.data;
}

export async function joinCourseSessionVideo(
  courseUuid: string,
  sessionUuid: string
): Promise<JoinVideoResponse> {
  const response = await api.post(
    `/courses/${courseUuid}/sessions/${sessionUuid}/join-video/`
  );
  return response.data;
}

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
  identity: string
): Promise<{ status: string; identity: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/admit_participant/`, {
    identity,
  });
  return response.data;
}

export async function denyParticipant(
  roomUuid: string,
  identity: string
): Promise<{ status: string; identity: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/deny_participant/`, {
    identity,
  });
  return response.data;
}
