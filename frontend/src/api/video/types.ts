export interface VideoStatus {
  configured: boolean;
  provider: string;
}

export interface JoinVideoResponse {
  token: string;
  ws_url: string;
  room_name: string;
  room_uuid: string;
  is_host: boolean;
  waiting: boolean;
  waiting_room_enabled: boolean;
  recording_enabled_default: boolean;
  recording_active: boolean;
}

/**
 * GET `/meetings/active/` payload. Returned by the lobby polling loop
 * every ~10s.
 *
 * `status` reflects the most recent VideoRoom for the content object:
 *   - `none`      — no meeting has ever been created. Host sees
 *                   "Start meeting"; attendee sees "Waiting for host".
 *   - `scheduled` — host clicked Start but no participant has connected
 *                   yet. Host can join their own pending room; attendee
 *                   keeps waiting until status flips to `active`.
 *   - `active`    — meeting is live; host gets "Join as host", attendee
 *                   gets "Join now".
 *   - `ended`     — most recent session has finalized. Host sees "Start
 *                   a new meeting"; attendee sees "Meeting has ended".
 *
 * The endpoint never returns a token. The frontend POSTs to
 * `/meetings/start/` or `/meetings/join/` to actually get one.
 */
export type ActiveMeetingStatus = 'none' | 'scheduled' | 'active' | 'ended';

export interface ActiveMeetingResponse {
  status: ActiveMeetingStatus;
  room_uuid?: string;
  started_at?: string | null;
  ended_at?: string | null;
  is_host?: boolean;
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
  event_uuid?: string | null;
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
