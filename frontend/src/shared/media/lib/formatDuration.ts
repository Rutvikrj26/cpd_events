/**
 * Format a duration (ms or seconds) as `M:SS` or `H:MM:SS`.
 *
 * Lives next to the player rather than in `lib/datetime.ts` because that
 * module deals with calendar dates/times in user locale + timezone — a
 * duration is neither. Keeping it here also avoids pulling locale code
 * into a hot render path (timeupdate fires ~4×/s).
 */

export function formatDurationMs(ms: number): string {
    return formatDurationSeconds(Math.floor(ms / 1000));
}

export function formatDurationSeconds(totalSeconds: number): string {
    const s = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) {
        return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
    }
    return `${m}:${sec.toString().padStart(2, '0')}`;
}
