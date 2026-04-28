/**
 * Shared types for the <MediaPlayer> primitive.
 *
 * The player is source-agnostic — `source.kind` discriminates between
 * direct file URLs (mp4/webm), YouTube/Vimeo embeds, and HLS streams.
 * react-player v3 abstracts all of these behind an `HTMLVideoElement`-
 * compatible ref, so the controls overlay and transcript sync use the
 * same API regardless of provider.
 */

import type { ReactNode, RefObject } from 'react';

export type MediaSourceKind = 'file' | 'youtube' | 'hls';

export interface MediaSource {
    kind: MediaSourceKind;
    url: string;
    poster?: string;
    /** MIME type hint for direct files (e.g. 'video/mp4'). Optional. */
    mimeType?: string;
}

/**
 * One row in a transcript. Time is in milliseconds (matches the recording
 * transcript backend); the transcript hook converts to seconds when
 * driving the video element.
 */
export interface TranscriptSegment {
    uuid: string;
    start_ms: number;
    end_ms: number;
    text: string;
    speaker_name?: string;
}

/**
 * Pluggable handlers so the panel works with any data source. Recording
 * viewer wires server endpoints; course content can wire a client-side
 * VTT parser when course transcripts land.
 */
export interface TranscriptSearchHandler {
    (query: string): Promise<{ matchedIds: Set<string> }>;
}

export interface TranscriptExportHandler {
    (format: 'vtt' | 'srt' | 'txt'): Promise<void>;
}

/**
 * The `transcript` prop accepts either segments + handlers directly, OR
 * a `slot` ReactNode for callers that want to render their own panel
 * (e.g. the recording editor with edit/history dialogs).
 */
export interface TranscriptSource {
    /** Pre-loaded segments. Required when `slot` is not provided. */
    segments?: TranscriptSegment[];
    /** Loading state for the segments. */
    isLoading?: boolean;
    /** Render-only error message (no segments). Renders as empty state. */
    errorMessage?: string;
    /** Status banner ("still being generated…"). Optional. */
    statusBanner?: ReactNode;
    /** Optional server-side search; if omitted, panel does client-side substring filter. */
    search?: TranscriptSearchHandler;
    /** Optional VTT/SRT/TXT export menu. If omitted, no export buttons render. */
    export?: TranscriptExportHandler;
    /**
     * Caller-rendered panel content. When provided, we render this in the
     * transcript slot instead of the default panel — used by the recording
     * viewer to surface its edit / history dialogs alongside the standard
     * transcript UX.
     */
    slot?: ReactNode;
}

/** A timeline marker rendered on the scrubber and reachable via menu. */
export interface ChapterMarker {
    id: string;
    title: string;
    start_ms: number;
}

export interface MediaPlayerHandle {
    play(): Promise<void>;
    pause(): void;
    seekTo(seconds: number): void;
    getCurrentTime(): number;
    getElement(): HTMLVideoElement | null;
}

export interface MediaPlayerProps {
    source: MediaSource;
    title?: string;
    chapters?: ChapterMarker[];
    transcript?: TranscriptSource;
    /**
     * Layout hint. `auto` picks side-by-side ≥1280px, tabbed below.
     * `video-only` hides the transcript pane regardless.
     */
    layout?: 'auto' | 'side-by-side' | 'tabs' | 'video-only';
    /** Fired throttled to ~4×/s while playing. Seconds. */
    onTimeUpdate?: (seconds: number) => void;
    /**
     * Fires once when playback crosses `completionThreshold` (default 0.95).
     * Re-arms when the user scrubs back behind the threshold.
     */
    onComplete?: () => void;
    completionThreshold?: number;
    /** Resume from this position (seconds) on mount. */
    initialPosition?: number;
    /**
     * If provided, last position persists to localStorage under this key
     * and is restored on mount (only when `initialPosition` is undefined).
     */
    storageKey?: string;
    /** Forwarded to the wrapper div. */
    className?: string;
    /** Render below the player (e.g. download link, metadata). */
    footer?: ReactNode;
}

export interface MediaPlayerInternalProps extends MediaPlayerProps {
    videoRef: RefObject<HTMLVideoElement | null>;
}
