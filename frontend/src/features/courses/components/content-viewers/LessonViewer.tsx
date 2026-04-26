import { ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import type { ContentViewerProps } from './types';

/**
 * LessonViewer — composite viewer that may have a video, rich-text
 * body, and an attachment. The "lesson" content_type bundles them so
 * authors can mix media in one unit.
 */
export function LessonViewer({ content }: ContentViewerProps) {
    const data = content.content_data || {};
    const videoUrl: string | undefined = data.video?.url || data.video_url;
    const bodyHtml: string | undefined = data.text?.body || data.body;

    return (
        <Card elevation="rest">
            <CardContent className="space-y-card pt-6">
                {videoUrl && (
                    <div className="aspect-video overflow-hidden rounded-lg bg-black">
                        {videoUrl.includes('youtube') ? (
                            <iframe
                                src={videoUrl.replace('watch?v=', 'embed/')}
                                className="h-full w-full"
                                title={content.title}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowFullScreen
                            />
                        ) : (
                            <video src={videoUrl} controls className="h-full w-full" />
                        )}
                    </div>
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
