/**
 * useTranscriptSync — derives "active segment" from current playback time.
 *
 * Binary-search rather than linear scan: a 2-hour transcript ≈ 4800 rows;
 * the timeupdate handler runs ~4×/s. Linear would be 19,200 comparisons/s
 * for nothing — binary keeps it under 60.
 *
 * Returns -1 when there's no segment (empty transcript) or before the
 * first segment starts. The clamp at the end returns the closest-prior
 * segment so the highlight never disappears mid-playback because of a
 * gap in the segment timeline.
 */

import { useMemo } from 'react';
import type { TranscriptSegment } from '../types';

export function useActiveSegmentIndex(
    segments: TranscriptSegment[],
    currentMs: number,
): number {
    return useMemo(() => {
        if (segments.length === 0) return -1;
        let lo = 0;
        let hi = segments.length - 1;
        while (lo <= hi) {
            const mid = (lo + hi) >> 1;
            const s = segments[mid];
            if (currentMs < s.start_ms) hi = mid - 1;
            else if (currentMs > s.end_ms) lo = mid + 1;
            else return mid;
        }
        return Math.max(0, hi);
    }, [segments, currentMs]);
}
