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

export async function getVideoRecordings(): Promise<VideoRecording[]> {
  const response = await api.get('/video/recordings/');
  return response.data.results || response.data;
}

export async function startRoomRecording(roomUuid: string): Promise<{ egress_id: string; status: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/start_recording/`);
  return response.data;
}

export async function stopRoomRecording(roomUuid: string): Promise<{ status: string }> {
  const response = await api.post(`/video/rooms/${roomUuid}/stop_recording/`);
  return response.data;
}
