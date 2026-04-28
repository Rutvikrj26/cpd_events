/**
 * useMediaTime — surface the underlying media element's currentTime and
 * duration as React state, throttled, for the transcript binary search
 * + onTimeUpdate forwarding.
 *
 * Why event listeners (not Media Chrome's `useMediaSelector`):
 *   - The transcript only needs `currentTime` and `duration` — pulling
 *     in the full Media Chrome store + Context provider is more than
 *     we need.
 *   - Native `timeupdate` / `loadedmetadata` events are reliable across
 *     all source kinds (HTMLVideoElement, youtube-video-element,
 *     hls-video-element) since each implements the HTMLMediaElement
 *     interface.
 *   - `addEventListener` works even when the tab is hidden — unlike
 *     requestAnimationFrame which Chrome throttles to 0.
 *
 * Implementation: same poll-then-attach pattern as `useResumePosition`
 * to handle Media Chrome's deferred element mounting (the slotted
 * media element appears async after the source loads).
 */

import { useEffect, useState } from 'react';
import type { RefObject } from 'react';

const TIME_THROTTLE_MS = 250;
const ATTACH_POLL_MS = 100;
const ATTACH_TIMEOUT_MS = 30000;

interface MediaTimeState {
    currentTime: number;
    duration: number;
}

const DEFAULT: MediaTimeState = { currentTime: 0, duration: 0 };

export function useMediaTime(
    videoRef: RefObject<HTMLVideoElement | null>,
): MediaTimeState {
    const [state, setState] = useState<MediaTimeState>(DEFAULT);

    useEffect(() => {
        let detach: (() => void) | null = null;
        let pollHandle: number | null = null;
        const pollDeadline = performance.now() + ATTACH_TIMEOUT_MS;

        const attach = (v: HTMLVideoElement) => {
            let lastTimeUpdate = 0;

            const onLoadedMetadata = () =>
                setState((prev) => ({
                    currentTime: v.currentTime,
                    duration: isFinite(v.duration) ? v.duration : prev.duration,
                }));

            const onTimeUpdate = () => {
                const now = performance.now();
                if (now - lastTimeUpdate < TIME_THROTTLE_MS) return;
                lastTimeUpdate = now;
                setState((prev) => ({
                    currentTime: v.currentTime,
                    duration: isFinite(v.duration) ? v.duration : prev.duration,
                }));
            };

            const onSeeked = () =>
                setState((prev) => ({ ...prev, currentTime: v.currentTime }));

            v.addEventListener('loadedmetadata', onLoadedMetadata);
            v.addEventListener('durationchange', onLoadedMetadata);
            v.addEventListener('timeupdate', onTimeUpdate);
            v.addEventListener('seeked', onSeeked);

            // Initial snapshot.
            setState({
                currentTime: v.currentTime,
                duration: isFinite(v.duration) ? v.duration : 0,
            });

            detach = () => {
                v.removeEventListener('loadedmetadata', onLoadedMetadata);
                v.removeEventListener('durationchange', onLoadedMetadata);
                v.removeEventListener('timeupdate', onTimeUpdate);
                v.removeEventListener('seeked', onSeeked);
            };
        };

        const poll = () => {
            const v = videoRef.current;
            if (v) {
                attach(v);
                return;
            }
            if (performance.now() > pollDeadline) return;
            pollHandle = window.setTimeout(poll, ATTACH_POLL_MS);
        };
        poll();

        return () => {
            if (pollHandle !== null) window.clearTimeout(pollHandle);
            detach?.();
        };
    }, [videoRef]);

    return state;
}
