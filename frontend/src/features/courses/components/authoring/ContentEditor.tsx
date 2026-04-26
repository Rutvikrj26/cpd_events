import React from 'react';
import { File, Trash2 } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import { toast } from 'sonner';
import { QuizBuilder, QuizData } from '@/components/custom/QuizBuilder';
import ReactQuill from 'react-quill-new';
import 'react-quill-new/dist/quill.snow.css';
import { useCreateContent, useUpdateContent } from '../../hooks';

const QUILL_MODULES = {
    toolbar: [
        [{ header: [1, 2, 3, false] }],
        ['bold', 'italic', 'underline', 'strike', 'blockquote'],
        [{ list: 'ordered' }, { list: 'bullet' }],
        ['link', 'clean'],
    ],
};

const QUILL_FORMATS = [
    'header',
    'bold', 'italic', 'underline', 'strike', 'blockquote',
    'list', 'bullet',
    'link',
];

interface ContentEditorState {
    contentType: 'lesson' | 'quiz';
    title: string;
    videoUrl: string;
    textBody: string;
    newFile: File | null;
    existingFile: { name: string; url: string } | string | null;
    removeFile: boolean;
    quizData: QuizData;
    editingContentUuid: string | null;
}

interface ContentEditorProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    courseUuid: string;
    moduleUuid: string | null;
    state: ContentEditorState;
    onStateChange: (patch: Partial<ContentEditorState>) => void;
    onSaved: () => void;
}

export function ContentEditor({
    open,
    onOpenChange,
    courseUuid,
    moduleUuid,
    state,
    onStateChange,
    onSaved,
}: ContentEditorProps) {
    const { mutate: createContent, isPending: creating } = useCreateContent(courseUuid);
    const { mutate: updateContent, isPending: updating } = useUpdateContent(courseUuid);
    const isPending = creating || updating;

    const handleSave = () => {
        if (!moduleUuid || !state.title.trim()) return;

        const formData = new FormData();
        formData.append('title', state.title);
        formData.append('content_type', state.contentType);

        if (!state.editingContentUuid) {
            formData.append('order', '0');
        }

        let contentData: Record<string, any> = {};
        if (state.contentType === 'lesson') {
            contentData = {
                video: state.videoUrl ? { url: state.videoUrl } : undefined,
                text: state.textBody ? { body: state.textBody } : undefined,
            };
        } else {
            contentData = {
                questions: state.quizData.questions,
                passing_score: state.quizData.passing_score,
            };
        }
        formData.append('content_data', JSON.stringify(contentData));

        if (state.contentType === 'lesson') {
            if (state.newFile) {
                formData.append('file', state.newFile);
            } else if (state.removeFile) {
                formData.append('remove_file', 'true');
            }
        }

        const label = state.contentType === 'quiz' ? 'Quiz' : 'Lesson';

        if (state.editingContentUuid) {
            updateContent(
                { moduleUuid, contentUuid: state.editingContentUuid, data: formData },
                {
                    onSuccess: () => {
                        toast.success(`${label} updated`);
                        onSaved();
                        onOpenChange(false);
                    },
                    onError: () => toast.error(`Failed to update content`),
                },
            );
        } else {
            createContent(
                { moduleUuid, data: formData },
                {
                    onSuccess: () => {
                        toast.success(`${label} added`);
                        onSaved();
                        onOpenChange(false);
                    },
                    onError: () => toast.error(`Failed to add content`),
                },
            );
        }
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(o) => {
                if (!o) onOpenChange(false);
            }}
        >
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>
                        {state.editingContentUuid
                            ? `Edit ${state.contentType === 'quiz' ? 'Quiz' : 'Lesson'}`
                            : 'Add Content'}
                    </DialogTitle>
                    <DialogDescription>
                        {state.editingContentUuid
                            ? `Update the ${state.contentType} content.`
                            : 'Create a new lesson or quiz for this module.'}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="content-type">Content Type</Label>
                            <Select
                                value={state.contentType}
                                onValueChange={(val: 'lesson' | 'quiz') =>
                                    onStateChange({ contentType: val })
                                }
                                disabled={!!state.editingContentUuid}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="lesson">Lesson (Video/Text)</SelectItem>
                                    <SelectItem value="quiz">Quiz</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="content-title">Title</Label>
                            <Input
                                id="content-title"
                                placeholder={`e.g., ${state.contentType === 'quiz' ? 'Module 1 Quiz' : 'Introduction Lesson'}`}
                                value={state.title}
                                onChange={(e) => onStateChange({ title: e.target.value })}
                            />
                        </div>
                    </div>

                    {state.contentType === 'lesson' ? (
                        <>
                            <div className="space-y-2">
                                <Label htmlFor="video-url">Video URL (Optional)</Label>
                                <Input
                                    id="video-url"
                                    placeholder="https://vimeo.com/..."
                                    value={state.videoUrl}
                                    onChange={(e) => onStateChange({ videoUrl: e.target.value })}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Supports Vimeo, YouTube, or direct MP4 links.
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Label>Lesson Content</Label>
                                <div className="bg-background rounded-md">
                                    <ReactQuill
                                        theme="snow"
                                        value={state.textBody}
                                        onChange={(val) => onStateChange({ textBody: val })}
                                        modules={QUILL_MODULES}
                                        formats={QUILL_FORMATS}
                                        className="h-64 mb-12"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="file-upload">Attachment (Optional)</Label>
                                {state.existingFile && !state.removeFile ? (
                                    <div className="flex items-center justify-between p-2 border rounded-md bg-muted/20">
                                        <div className="flex items-center gap-2 overflow-hidden">
                                            <File className="h-4 w-4 flex-shrink-0 text-primary" />
                                            <span className="text-sm truncate max-w-[200px]">
                                                {typeof state.existingFile === 'string'
                                                    ? state.existingFile.split('/').pop()
                                                    : 'Attached File'}
                                            </span>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-6 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                                            onClick={() => onStateChange({ removeFile: true })}
                                        >
                                            <Trash2 className="h-3 w-3 mr-1" /> Remove
                                        </Button>
                                    </div>
                                ) : (
                                    <>
                                        <Input
                                            id="file-upload"
                                            type="file"
                                            onChange={(e) => {
                                                onStateChange({
                                                    newFile: e.target.files ? e.target.files[0] : null,
                                                    removeFile: false,
                                                });
                                            }}
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            {state.editingContentUuid
                                                ? 'Upload new file to replace existing'
                                                : 'Upload a PDF, document, or supplementary file.'}
                                            {state.removeFile && (
                                                <span className="text-destructive ml-2">
                                                    (Existing file will be removed)
                                                </span>
                                            )}
                                        </p>
                                    </>
                                )}
                            </div>
                        </>
                    ) : (
                        <QuizBuilder
                            initialData={state.quizData}
                            onChange={(data) => onStateChange({ quizData: data })}
                        />
                    )}
                </div>

                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={isPending}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleSave}
                        disabled={isPending || !state.title.trim()}
                    >
                        {state.editingContentUuid ? 'Update Item' : 'Add Item'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
