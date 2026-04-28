/**
 * Transcripts API client.
 *
 * Read endpoints are keyed on the `recording_uuid` (the entity the user
 * is navigating to in the UI) — the backend resolves the linked
 * transcript and applies the same access rules as VideoRecording.
 *
 * The agent service writes transcripts via a separate internal endpoint
 * authenticated by HMAC; the frontend never touches that path.
 */

import client from '../client';
import {
    Transcript,
    TranscriptSearchResponse,
    TranscriptSegment,
    TranscriptSegmentHistoryItem,
} from './types';

/**
 * Fetch the transcript for a recording. Throws 404 when no transcript
 * exists for the recording (or the user lacks access to the parent
 * recording — backend doesn't disambiguate to avoid leaking which
 * recordings have transcripts).
 */
export const getRecordingTranscript = async (
    recordingUuid: string,
): Promise<Transcript> => {
    const response = await client.get<Transcript>(
        `/video/recordings/${recordingUuid}/transcript/`,
    );
    return response.data;
};

/**
 * Search a recording's transcript. Returns segments matching the query
 * in chronological order (start_ms ascending) so the UI can render the
 * results inline in the panel rather than as a separate list. Cap is
 * 200 results — the backend assumes UI-driven navigation, not
 * search-results-page semantics.
 */
export const searchRecordingTranscript = async (
    recordingUuid: string,
    q: string,
): Promise<TranscriptSearchResponse> => {
    const response = await client.get<TranscriptSearchResponse>(
        `/video/recordings/${recordingUuid}/transcript/search/`,
        { params: { q } },
    );
    return response.data;
};

/**
 * Download a transcript export file (VTT / SRT / TXT) by fetching it
 * through the authenticated API client and triggering a browser
 * download.
 *
 * Why not a plain `<a href>`: the export endpoint is auth-gated (DRF
 * IsAuthenticated). A bare anchor opens the URL in a new tab without
 * the JWT, which 401s. Going through `client.get` attaches our auth
 * header, then we synthesize a one-off Blob URL and click() a hidden
 * anchor so the browser handles the file save.
 *
 * The query param is `as=` (not `format=`) because DRF reserves
 * `?format=` for content-negotiation; the backend renames here too.
 */
export const downloadTranscriptExport = async (
    recordingUuid: string,
    format: 'vtt' | 'srt' | 'txt' = 'vtt',
): Promise<void> => {
    const response = await client.get<Blob>(
        `/video/recordings/${recordingUuid}/transcript/export/`,
        { params: { as: format }, responseType: 'blob' },
    );
    const blobUrl = URL.createObjectURL(response.data);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `transcript-${recordingUuid}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    // Free the Blob URL on the next tick — Chrome holds it until the
    // download completes; a timeout ensures we don't revoke prematurely.
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
};

/**
 * Edit a transcript segment (organiser-only).
 *
 * Backend creates a new segment row with `source='edit'`, links the
 * superseded row's `replaced_by` to it, and returns the new current
 * version. Caller invalidates the transcript query to pick up the
 * change immediately.
 *
 * 409 means the transcript is still STREAMING — the agent might be
 * about to revise this segment, so we lock edits until finalised.
 * 404 means either the segment was already superseded by another
 * concurrent edit, or the user lacks edit permission. Either way the
 * UI should re-fetch the transcript and surface a message.
 */
export const editTranscriptSegment = async (
    transcriptUuid: string,
    segmentUuid: string,
    text: string,
): Promise<TranscriptSegment> => {
    const response = await client.patch<TranscriptSegment>(
        `/transcripts/${transcriptUuid}/segments/${segmentUuid}/`,
        { text },
    );
    return response.data;
};

/**
 * Fetch a segment's full edit history. Returns oldest → newest. The
 * last item is the current version (matches the panel's view); earlier
 * items are previous versions. Use for compliance review — show the
 * STT-original alongside the human-corrected text.
 */
export const getTranscriptSegmentHistory = async (
    transcriptUuid: string,
    segmentUuid: string,
): Promise<{ segments: TranscriptSegmentHistoryItem[] }> => {
    const response = await client.get<{ segments: TranscriptSegmentHistoryItem[] }>(
        `/transcripts/${transcriptUuid}/segments/${segmentUuid}/history/`,
    );
    return response.data;
};
