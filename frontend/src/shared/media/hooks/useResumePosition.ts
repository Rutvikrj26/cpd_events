/**
 * Persist + restore playback position in localStorage.
 *
 * Course content already tracks completion via the backend
 * (`updateContentProgress`) but doesn't store sub-completion playback
 * position; this hook fills the gap so users who close the tab
 * mid-lesson resume where they left off.
 *
 * We store position only when the user has watched >5s, and never when
 * within 5s of the end (prevents "resume" jumping back to credits).
 *
 * Implementation note: react-player v3 mounts the video element after
 * the source resolves. We poll for the element with a short interval
 * and attach listeners exactly once when it appears, instead of using
 * a no-deps effect that re-attaches every render (which can race with
 * the controls' own state updates and cause an infinite loop).
 */

import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

const SAVE_THROTTLE_MS = 5000;
const MIN_WATCHED_SECONDS = 5;
const RESUME_BUFFER_SECONDS = 5;
const ATTACH_POLL_MS = 100;
const ATTACH_TIMEOUT_MS = 30000;

function storageKey(key: string) {
    return `media-position:${key}`;
}

export function loadResumePosition(key?: string): number | undefined {
    if (!key) return undefined;
    try {
        const raw = localStorage.getItem(storageKey(key));
        if (!raw) return undefined;
        const n = parseFloat(raw);
        return isFinite(n) && n > 0 ? n : undefined;
    } catch {
        return undefined;
    }
}

export function clearResumePosition(key?: string) {
    if (!key) return;
    try {
        localStorage.removeItem(storageKey(key));
    } catch {
        // ignore
    }
}

export function useResumePosition(
    videoRef: RefObject<HTMLVideoElement | null>,
    options: { storageKey?: string; initialPosition?: number },
) {
    const { storageKey: key, initialPosition } = options;

    // Snapshot the latest options into a ref so the attach effect can
    // run with empty deps (no re-attach when initialPosition changes).
    const optionsRef = useRef(options);
    optionsRef.current = options;

    useEffect(() => {
        let restored = false;
        let lastSaved = 0;
        let detach: (() => void) | null = null;
        let pollHandle: number | null = null;
        let pollDeadline = performance.now() + ATTACH_TIMEOUT_MS;

        const attach = (v: HTMLVideoElement) => {
            const restore = () => {
                if (restored) return;
                const init = optionsRef.current.initialPosition;
                const saved = loadResumePosition(optionsRef.current.storageKey);
                const target = init !== undefined ? init : saved;
                if (
                    target !== undefined &&
                    isFinite(v.duration) &&
                    target < v.duration - RESUME_BUFFER_SECONDS
                ) {
                    v.currentTime = target;
                }
                restored = true;
            };

            if (v.readyState >= 1 && isFinite(v.duration) && v.duration > 0) {
                restore();
            } else {
                v.addEventListener('loadedmetadata', restore, { once: true });
            }

            const onTimeUpdate = () => {
                const k = optionsRef.current.storageKey;
                if (!k) return;
                const now = performance.now();
                if (now - lastSaved < SAVE_THROTTLE_MS) return;
                lastSaved = now;
                const t = v.currentTime;
                if (t < MIN_WATCHED_SECONDS) return;
                if (isFinite(v.duration) && t > v.duration - RESUME_BUFFER_SECONDS) {
                    clearResumePosition(k);
                    return;
                }
                try {
                    localStorage.setItem(storageKey(k), t.toFixed(1));
                } catch {
                    // localStorage may be full or disabled; non-fatal.
                }
            };
            const onEnded = () => clearResumePosition(optionsRef.current.storageKey);

            v.addEventListener('timeupdate', onTimeUpdate);
            v.addEventListener('ended', onEnded);

            detach = () => {
                v.removeEventListener('loadedmetadata', restore);
                v.removeEventListener('timeupdate', onTimeUpdate);
                v.removeEventListener('ended', onEnded);
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
        // The hook intentionally only runs once per mount — option changes
        // are read via optionsRef on the next listener invocation.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [videoRef]);

    // The two values are read via the optionsRef closure above; reference
    // them here so eslint doesn't flag them as unused inputs.
    void key;
    void initialPosition;
}
