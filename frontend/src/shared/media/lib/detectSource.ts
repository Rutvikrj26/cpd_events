/**
 * Detect MediaSource shape from a URL string. Encapsulates the
 * "is this a YouTube URL?" check so callers don't repeat the regex
 * dance and so adding new providers (Vimeo, Wistia, etc.) is one place.
 */

import type { MediaSource } from '../types';

export function detectMediaSource(url: string, poster?: string): MediaSource {
    if (/youtube\.com|youtu\.be/i.test(url)) {
        return { kind: 'youtube', url, poster };
    }
    if (/\.m3u8(\?|$)/i.test(url)) {
        return { kind: 'hls', url, poster };
    }
    return { kind: 'file', url, poster };
}
