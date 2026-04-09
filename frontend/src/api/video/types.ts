export interface VideoStatus {
  configured: boolean;
  provider: string;
}

export interface JoinVideoResponse {
  token: string;
  ws_url: string;
  room_name: string;
}

export interface VideoRoom {
  uuid: string;
  room_name: string;
  status: 'scheduled' | 'active' | 'ended' | 'error';
  provider: string;
  started_at: string | null;
  ended_at: string | null;
  max_participants: number;
  settings: Record<string, unknown>;
  created_at: string;
}

export interface VideoRecording {
  uuid: string;
  title: string;
  description: string;
  status: 'recording' | 'processing' | 'available' | 'error' | 'deleted';
  recording_start: string | null;
  recording_end: string | null;
  duration_seconds: number;
  duration_display: string;
  total_size_bytes: number;
  access_level: 'registrants' | 'attendees' | 'certificate_holders' | 'public';
  is_published: boolean;
  published_at: string | null;
  view_count: number;
  unique_viewers: number;
  files: VideoRecordingFile[];
  created_at: string;
}

export interface VideoRecordingFile {
  uuid: string;
  file_type: 'video' | 'audio' | 'chat' | 'transcript';
  file_name: string;
  file_extension: string;
  file_size_bytes: number;
  storage_url: string;
}
