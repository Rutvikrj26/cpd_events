import { ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import type { ContentViewerProps } from './types';

export function ExternalContentViewer({ content }: ContentViewerProps) {
    const url = content.content_data?.url as string | undefined;
    return (
        <Card elevation="rest">
            <CardContent className="space-y-tight pt-6">
                <p className="text-body text-muted-foreground">External resource</p>
                {url ? (
                    <Button variant="outline" asChild>
                        <a href={url} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Open link
                        </a>
                    </Button>
                ) : (
                    <p className="text-muted-foreground">No URL provided.</p>
                )}
            </CardContent>
        </Card>
    );
}
