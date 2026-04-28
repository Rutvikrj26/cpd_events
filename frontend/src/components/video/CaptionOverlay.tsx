/**
 * CaptionOverlay — live captions rendered over the in-meeting video grid.
 *
 * Subscribes to LiveKit's transcription stream via the built-in
 * `useTrackTranscription` hook (or a `RoomEvent.TranscriptionReceived`
 * listener — same wire underneath). The agent service feeds STT output
 * onto LiveKit's `lk.transcription` topic, which all room participants
 * receive without our backend in the loop. Browser ↔ STT latency is
 * the LiveKit data-channel hop plus the provider's segment cadence
 * (~300ms with Deepgram).
 *
 * Why we listen client-side instead of polling our backend:
 *   - End-to-end latency stays at LiveKit's level. Going through Django
 *     would add tail-latency from Cloud Run cold-starts and Postgres
 *     writes — ~1-2 seconds added to "speak → see caption".
 *   - The frontend works even if the Django service is degraded —
 *     captions still flow from LiveKit, the durable record just lags.
 *   - One source of truth for "what was said in the room" — our backend
 *     mirrors a SUBSET of these segments (finals only, by design).
 *
 * Display strategy:
 *   - Track the last N segments to keep the overlay readable.
 *   - Interim segments render italic; LiveKit reuses the same `id`
 *     when an interim becomes final, so React's reconciler swaps the
 *     row in place without flicker.
 *   - We never render more than 3 lines at a time — captions are an
 *     accessibility surface, not a transcript.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import {
    useMaybeRoomContext,
} from '@livekit/components-react';
import {
    RoomEvent,
    TranscriptionSegment,
    Participant,
} from 'livekit-client';

interface DisplaySegment {
    id: string;
    text: string;
    final: boolean;
    speakerLabel: string;
    receivedAt: number;
}

interface CaptionOverlayProps {
    /** Master toggle from the TopBar — false hides the overlay entirely. */
    enabled: boolean;
    /** ms — segments older than this fall out of view */
    windowMs?: number;
    /** Max simultaneous lines (top of stack). 3 is the readable cap. */
    maxLines?: number;
}

const DEFAULT_WINDOW_MS = 6000;
const DEFAULT_MAX_LINES = 3;

export function CaptionOverlay({
    enabled,
    windowMs = DEFAULT_WINDOW_MS,
    maxLines = DEFAULT_MAX_LINES,
}: CaptionOverlayProps) {
    const room = useMaybeRoomContext();
    const [segments, setSegments] = useState<Map<string, DisplaySegment>>(
        () => new Map(),
    );

    // Drop old segments on a tick. Without this, segments persist as
    // long as new ones arrive — fine for a normal stream but visually
    // noisy when someone pauses speaking. The interval is short enough
    // that the user perceives the overlay as "live" rather than sticky.
    const tickRef = useRef<number | null>(null);
    useEffect(() => {
        if (!enabled) return;
        const tick = () => {
            const cutoff = Date.now() - windowMs;
            setSegments((prev) => {
                let changed = false;
                const next = new Map(prev);
                for (const [id, seg] of next) {
                    if (seg.receivedAt < cutoff) {
                        next.delete(id);
                        changed = true;
                    }
                }
                return changed ? next : prev;
            });
        };
        tickRef.current = window.setInterval(tick, 1000);
        return () => {
            if (tickRef.current !== null) {
                window.clearInterval(tickRef.current);
                tickRef.current = null;
            }
        };
    }, [enabled, windowMs]);

    // Subscribe to TranscriptionReceived. The hook-based API
    // (`useTrackTranscription`) is per-track; for an overlay that
    // covers all participants, the room-level event is simpler.
    useEffect(() => {
        if (!enabled || !room) return;

        const onSegments = (
            received: TranscriptionSegment[],
            participant?: Participant,
        ) => {
            const speakerLabel = participant?.name || participant?.identity || '';
            const now = Date.now();
            setSegments((prev) => {
                const next = new Map(prev);
                for (const s of received) {
                    next.set(s.id, {
                        id: s.id,
                        text: s.text,
                        final: s.final,
                        speakerLabel,
                        receivedAt: now,
                    });
                }
                return next;
            });
        };

        room.on(RoomEvent.TranscriptionReceived, onSegments);
        return () => {
            room.off(RoomEvent.TranscriptionReceived, onSegments);
        };
    }, [enabled, room]);

    const visible = useMemo(() => {
        const arr = Array.from(segments.values()).sort(
            (a, b) => a.receivedAt - b.receivedAt,
        );
        return arr.slice(-maxLines);
    }, [segments, maxLines]);

    if (!enabled || visible.length === 0) return null;

    return (
        // pointer-events-none so the overlay never steals clicks from
        // the video grid (e.g. clicking a participant tile to pin them).
        <div className="pointer-events-none absolute inset-x-0 bottom-24 flex justify-center px-4 z-10">
            <div
                className="max-w-3xl w-full rounded-lg bg-black/80 px-4 py-3 text-white shadow-lg"
                role="region"
                aria-live="polite"
                aria-label="Live captions"
            >
                {visible.map((s) => (
                    <p
                        key={s.id}
                        className={`text-base leading-snug ${
                            s.final ? 'opacity-100' : 'opacity-70 italic'
                        }`}
                    >
                        {s.speakerLabel && (
                            <span className="text-xs font-medium text-white/70 mr-2">
                                {s.speakerLabel}:
                            </span>
                        )}
                        {s.text}
                    </p>
                ))}
            </div>
        </div>
    );
}
