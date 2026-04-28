/**
 * Public API for the shared media player.
 *
 * Consumers import from `@/shared/media` — the internal layout
 * (transcript/, hooks/) is an implementation detail.
 */

export { MediaPlayer } from './MediaPlayer';
export { MediaPlayerCore } from './MediaPlayerCore';
export { TranscriptPanel } from './transcript/TranscriptPanel';
export { useActiveSegmentIndex } from './transcript/useTranscriptSync';
export { formatDurationMs, formatDurationSeconds } from './lib/formatDuration';
export { clearResumePosition, loadResumePosition } from './hooks/useResumePosition';
export type {
    ChapterMarker,
    MediaPlayerHandle,
    MediaPlayerProps,
    MediaSource,
    MediaSourceKind,
    TranscriptExportHandler,
    TranscriptSearchHandler,
    TranscriptSegment,
    TranscriptSource,
} from './types';
