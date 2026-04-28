import { PlayCircle } from 'lucide-react';

import { MediaPlayer } from '@/shared/media';
import { detectMediaSource } from '@/shared/media/lib/detectSource';
import type { ContentViewerProps } from './types';

/**
 * VideoContentViewer — handles MP4 + YouTube + HLS URLs uniformly via
 * the shared <MediaPlayer> primitive. The primitive auto-detects the
 * source kind and renders our custom controls overlay (no native
 * browser/YouTube chrome) so the player looks identical regardless
 * of provider.
 *
 * Resume-position is keyed on the content uuid so closing the tab
 * mid-lesson restores you to the same point on next load.
 */
export function VideoContentViewer({ content }: ContentViewerProps) {
    const data = content.content_data || {};
    const url = (data.video_url as string | undefined) ?? (data.youtube_url as string | undefined);

    if (!url) {
        return (
            <div className="flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg bg-black text-white/60">
                <PlayCircle className="h-16 w-16" />
            </div>
        );
    }

    const source = detectMediaSource(url);

    return (
        <MediaPlayer
            source={source}
            title={content.title}
            storageKey={`course-content:${content.uuid}`}
            layout="video-only"
        />
    );
}
