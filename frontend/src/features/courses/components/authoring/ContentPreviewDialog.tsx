import React from 'react';
import { File } from 'lucide-react';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';

interface ContentPreviewDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    content: any;
}

export function ContentPreviewDialog({ open, onOpenChange, content }: ContentPreviewDialogProps) {
    if (!content) return null;

    let data: any = {};
    try {
        data =
            typeof content.content_data === 'string'
                ? JSON.parse(content.content_data)
                : content.content_data || {};
    } catch {
        data = {};
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>{content.title}</DialogTitle>
                    <Badge variant="outline" className="w-fit mt-1">
                        {content.content_type === 'quiz' ? 'Quiz' : 'Lesson'}
                    </Badge>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {content.content_type === 'quiz' ? (
                        <div className="space-y-4">
                            <div className="flex justify-between items-center p-3 bg-muted/30 rounded-md">
                                <span className="font-medium">
                                    Passing Score: {data.passing_score}%
                                </span>
                                <span className="text-muted-foreground">
                                    {data.questions?.length || 0} Questions
                                </span>
                            </div>
                            <div className="space-y-4">
                                {data.questions?.map((q: any, idx: number) => (
                                    <div key={idx} className="border p-4 rounded-md">
                                        <div className="flex gap-2">
                                            <span className="font-bold text-muted-foreground">
                                                {idx + 1}.
                                            </span>
                                            <div className="flex-1">
                                                <p className="font-medium mb-2">{q.text}</p>
                                                <div className="space-y-1 pl-2">
                                                    {q.options?.map((opt: any, oIdx: number) => (
                                                        <div
                                                            key={oIdx}
                                                            className="flex items-center gap-2 text-sm"
                                                        >
                                                            <div
                                                                className={`h-2 w-2 rounded-full ${opt.isCorrect ? 'bg-success' : 'bg-muted'}`}
                                                            />
                                                            <span
                                                                className={
                                                                    opt.isCorrect
                                                                        ? 'font-medium text-success'
                                                                        : ''
                                                                }
                                                            >
                                                                {opt.text}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                            <Badge variant="secondary" className="h-fit">
                                                {q.type}
                                            </Badge>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <>
                            {data.video?.url && (
                                <div className="aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center">
                                    <iframe
                                        src={data.video.url.replace('watch?v=', 'embed/')}
                                        className="w-full h-full"
                                        allowFullScreen
                                        title="Video Preview"
                                    />
                                </div>
                            )}
                            {data.text?.body && (
                                <div
                                    className="prose prose-sm max-w-none p-4 bg-muted/30 rounded-lg"
                                    dangerouslySetInnerHTML={{ __html: data.text.body }}
                                />
                            )}
                            {content.file && (
                                <div className="flex items-center gap-2 p-3 border rounded-md bg-muted/30">
                                    <File className="h-4 w-4 text-primary" />
                                    <span className="text-sm font-medium">
                                        Attached File (Available for download)
                                    </span>
                                </div>
                            )}
                        </>
                    )}
                </div>

                <DialogFooter>
                    <Button onClick={() => onOpenChange(false)}>Close Preview</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
