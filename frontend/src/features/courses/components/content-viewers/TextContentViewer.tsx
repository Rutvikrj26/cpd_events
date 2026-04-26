import { Card, CardContent } from '@/shared/ui/card';
import type { ContentViewerProps } from './types';

/**
 * TextContentViewer — renders rich-text body (HTML from Quill).
 *
 * Body is `dangerouslySetInnerHTML`'d because authoring uses Quill.
 * Backend sanitizes on save; we don't re-sanitize here. If that
 * assumption changes, drop in DOMPurify between save and render.
 */
export function TextContentViewer({ content }: ContentViewerProps) {
    const body = content.content_data?.body;
    return (
        <Card elevation="rest">
            <CardContent className="prose max-w-none pt-6">
                {body ? (
                    <div dangerouslySetInnerHTML={{ __html: body }} />
                ) : (
                    <p className="text-muted-foreground">No content available.</p>
                )}
            </CardContent>
        </Card>
    );
}
