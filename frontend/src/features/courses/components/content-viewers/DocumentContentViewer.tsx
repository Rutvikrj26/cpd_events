import { ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import type { ContentViewerProps } from './types';

export function DocumentContentViewer({ content }: ContentViewerProps) {
    const file = content.file;
    if (!file) {
        return (
            <Card elevation="rest">
                <CardContent className="pt-6">
                    <p className="text-muted-foreground">No document available.</p>
                </CardContent>
            </Card>
        );
    }
    return (
        <Card elevation="rest">
            <CardContent className="space-y-tight pt-6">
                <iframe
                    src={file}
                    className="h-[600px] w-full rounded border"
                    title={content.title}
                />
                <Button variant="outline" asChild>
                    <a href={file} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="mr-2 h-4 w-4" />
                        Open in new tab
                    </a>
                </Button>
            </CardContent>
        </Card>
    );
}
