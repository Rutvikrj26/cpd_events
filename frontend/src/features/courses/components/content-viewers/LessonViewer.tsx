import { ExternalLink } from 'lucide-react';

import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { MediaPlayer } from '@/shared/media';
import { detectMediaSource } from '@/shared/media/lib/detectSource';
import type { ContentViewerProps } from './types';

/**
 * LessonViewer — composite viewer that may have a video, rich-text
 * body, and an attachment. The "lesson" content_type bundles them so
 * authors can mix media in one unit.
 *
 * Video portion uses the shared <MediaPlayer> primitive (see
 * `VideoContentViewer`). Body HTML is rendered with the existing
 * `prose` styling — sanitization is handled at the API boundary.
 */
export function LessonViewer({ content }: ContentViewerProps) {
    const data = content.content_data || {};
    const videoUrl: string | undefined = data.video?.url || data.video_url;
    const bodyHtml: string | undefined = data.text?.body || data.body;

    return (
        <Card elevation="rest">
            <CardContent className="space-y-card pt-6">
                {videoUrl && (
                    <MediaPlayer
                        source={detectMediaSource(videoUrl)}
                        title={content.title}
                        storageKey={`course-content:${content.uuid}`}
                        layout="video-only"
                    />
                )}

                {bodyHtml && (
                    <div
                        className="prose max-w-none"
                        dangerouslySetInnerHTML={{ __html: bodyHtml }}
                    />
                )}

                {content.file && (
                    <Button variant="outline" asChild>
                        <a href={content.file} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Open attachment
                        </a>
                    </Button>
                )}
            </CardContent>
        </Card>
    );
}
