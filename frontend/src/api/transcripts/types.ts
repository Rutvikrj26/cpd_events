/**
 * Transcript types — mirrors `conferencing.serializers` on the backend.
 *
 * Read shapes (TranscriptSegment, Transcript) are what the UI consumes.
 * Write shapes (TranscriptSegmentEdit) live next to the action that uses
 * them so each call site is self-contained.
 */

export type TranscriptStatus = 'streaming' | 'finalized' | 'error';

export type TranscriptSegmentSource = 'live' | 'edit' | 'batch_repair';

/**
 * Public read shape for a single segment.
 *
 * `participant_identity` is the LiveKit identity (the user's uuid for
 * authenticated participants); use it to dedupe consecutive segments
 * from the same speaker in display. `speaker_name` is the snapshot
 * captured at recording time so the transcript reads correctly even
 * after a user changes their display name later.
 */
export interface TranscriptSegment {
    uuid: string;
    start_ms: number;
    end_ms: number;
    text: string;
    is_final: boolean;
    participant_identity: string;
    speaker_name: string;
    confidence: number | null;
}

/**
 * Read shape for the audit-trail (history) endpoint. Includes the same
 * fields as `TranscriptSegment` plus provenance for compliance review.
 */
export interface TranscriptSegmentHistoryItem extends TranscriptSegment {
    source: TranscriptSegmentSource;
    edited_at: string | null;
    edited_by_name: string;
    created_at: string;
}

export interface Transcript {
    uuid: string;
    provider: string;
    provider_model: string;
    language_code: string;
    status: TranscriptStatus;
    started_at: string | null;
    finalized_at: string | null;
    word_count: number;
    error_message: string;
    /**
     * Current (non-superseded) segments in chronological order. Edits
     * are flattened — to view edit history, fetch the segment-history
     * endpoint for a specific segment uuid.
     */
    segments: TranscriptSegment[];
}

/** Response shape for the search endpoint. */
export interface TranscriptSearchResponse {
    q: string;
    results: TranscriptSegment[];
}
