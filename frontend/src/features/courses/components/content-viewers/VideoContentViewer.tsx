import { PlayCircle } from 'lucide-react';
import type { ContentViewerProps } from './types';

/**
 * VideoContentViewer — handles native MP4 + YouTube embed URLs.
 *
 * For YouTube, replaces `watch?v=` with `embed/`. Other providers (Vimeo
 * etc.) need their own iframe pattern; add as cases here when needed.
 */
export function VideoContentViewer({ content }: ContentViewerProps) {
    const data = content.content_data || {};
    const videoUrl = data.video_url as string | undefined;
    const youtubeUrl = data.youtube_url as string | undefined;

    return (
        <div className="aspect-video overflow-hidden rounded-lg bg-black">
            {videoUrl ? (
                <video src={videoUrl} controls className="h-full w-full" />
            ) : youtubeUrl ? (
                <iframe
                    src={youtubeUrl.replace('watch?v=', 'embed/')}
                    className="h-full w-full"
                    title={content.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                />
            ) : (
                <div className="flex h-full w-full items-center justify-center text-white/60">
                    <PlayCircle className="h-16 w-16" />
                </div>
            )}
        </div>
    );
}
