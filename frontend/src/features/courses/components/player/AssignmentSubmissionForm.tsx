import { useState } from 'react';
import ReactQuill from 'react-quill-new';
import 'react-quill-new/dist/quill.snow.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { useToast } from '@/shared/ui/use-toast';
import {
    useCreateSubmission,
    useUpdateSubmission,
    useFinalizeSubmission,
} from '../../hooks';
import type { Assignment, AssignmentSubmission } from '@/api/courses/types';

interface AssignmentSubmissionFormProps {
    assignment: Assignment;
    /** Latest submission for this assignment (highest attempt_number), if any. */
    latestSubmission?: AssignmentSubmission;
}

interface DraftState {
    text: string;
    url: string;
    file_url: string;
}

function getSubmissionBadge(status?: AssignmentSubmission['status']) {
    switch (status) {
        case 'submitted':
            return <Badge className="bg-info">Submitted</Badge>;
        case 'in_review':
            return <Badge className="bg-warning">In Review</Badge>;
        case 'needs_revision':
            return <Badge variant="destructive">Needs Revision</Badge>;
        case 'graded':
            return <Badge className="bg-success">Graded</Badge>;
        case 'approved':
            return <Badge className="bg-success">Approved</Badge>;
        case 'draft':
            return <Badge variant="secondary">Draft</Badge>;
        default:
            return <Badge variant="outline">Not Submitted</Badge>;
    }
}

/**
 * AssignmentSubmissionForm — the assignment-submission UX in the player.
 *
 * Why raw `useState` instead of `useZodForm`?
 *   The schema would have to be conditional on `assignment.submission_type`
 *   (`text` | `url` | `file` | `mixed`), and the `text` field is a Quill
 *   rich-text payload that doesn't fit cleanly into a `<FormField>` /
 *   `<input>` story. The form state is three strings; raw state is the
 *   simpler abstraction here.
 *
 * Submission flow uses the existing RQ mutations
 * (`useCreateSubmission`, `useUpdateSubmission`, `useFinalizeSubmission`)
 * so cache invalidation is handled by the hooks.
 */
export function AssignmentSubmissionForm({
    assignment,
    latestSubmission,
}: AssignmentSubmissionFormProps) {
    const { toast } = useToast();
    const createMut = useCreateSubmission();
    const updateMut = useUpdateSubmission();
    const finalizeMut = useFinalizeSubmission();

    // Initial draft seeds from the latest submission. The parent passes
    // `key={assignment.uuid}` on this form, so a different assignment
    // remounts and re-runs this initializer — no useEffect-reset needed.
    const [draft, setDraft] = useState<DraftState>({
        text: (latestSubmission?.content as any)?.text || '',
        url: (latestSubmission?.content as any)?.url || '',
        file_url: latestSubmission?.file_url || '',
    });

    const isSubmitting = createMut.isPending || updateMut.isPending || finalizeMut.isPending;
    const canEdit =
        !latestSubmission ||
        latestSubmission.status === 'draft' ||
        latestSubmission.status === 'needs_revision';

    const buildPayload = (): { content?: Record<string, any>; file_url?: string } => {
        const content: Record<string, any> = {};
        const submissionType = assignment.submission_type || 'text';
        if (submissionType === 'text' || submissionType === 'mixed') {
            if (draft.text) content.text = draft.text;
        }
        if (submissionType === 'url' || submissionType === 'mixed') {
            if (draft.url) content.url = draft.url;
        }
        const payload: { content?: Record<string, any>; file_url?: string } = {};
        if (Object.keys(content).length > 0) payload.content = content;
        if (draft.file_url) payload.file_url = draft.file_url;
        return payload;
    };

    const handleSaveDraft = async () => {
        try {
            const payload = buildPayload();
            if (latestSubmission && latestSubmission.status === 'draft') {
                await updateMut.mutateAsync({ submissionUuid: latestSubmission.uuid, data: payload });
            } else {
                await createMut.mutateAsync({ assignmentUuid: assignment.uuid, data: payload });
            }
            toast({ title: 'Draft saved', description: 'Your progress has been saved.' });
        } catch (error) {
            console.error('Failed to save draft:', error);
            toast({
                variant: 'destructive',
                title: 'Error',
                description: 'Failed to save draft.',
            });
        }
    };

    const handleSubmit = async () => {
        try {
            const payload = buildPayload();
            let submissionUuid: string;
            if (latestSubmission && latestSubmission.status === 'draft') {
                const updated = await updateMut.mutateAsync({
                    submissionUuid: latestSubmission.uuid,
                    data: payload,
                });
                submissionUuid = updated.uuid;
            } else {
                const created = await createMut.mutateAsync({
                    assignmentUuid: assignment.uuid,
                    data: payload,
                });
                submissionUuid = created.uuid;
            }
            await finalizeMut.mutateAsync(submissionUuid);
            toast({
                title: 'Assignment submitted',
                description: 'Your submission has been sent for review.',
            });
        } catch (error: any) {
            console.error('Failed to submit assignment:', error);
            toast({
                variant: 'destructive',
                title: 'Submission failed',
                description:
                    error?.response?.data?.error?.message || 'Could not submit assignment.',
            });
        }
    };

    const submissionType = assignment.submission_type;
    const showText = submissionType === 'text' || submissionType === 'mixed' || !submissionType;
    const showUrl = submissionType === 'url' || submissionType === 'mixed';
    const showFile = submissionType === 'file' || submissionType === 'mixed';

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>{assignment.title}</CardTitle>
                        <p className="text-sm text-muted-foreground">
                            {assignment.submission_type_display}
                        </p>
                    </div>
                    {getSubmissionBadge(latestSubmission?.status)}
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {assignment.instructions && (
                    <div className="text-sm whitespace-pre-wrap">{assignment.instructions}</div>
                )}

                {latestSubmission?.feedback && (
                    <Card className="border-warning bg-warning-subtle">
                        <CardContent className="pt-4 text-sm">
                            <p className="font-medium text-warning mb-1">Instructor Feedback</p>
                            <p className="text-warning">{latestSubmission.feedback}</p>
                        </CardContent>
                    </Card>
                )}

                {latestSubmission?.score !== undefined && latestSubmission?.score !== null && (
                    <div className="text-sm text-muted-foreground">
                        Score: <span className="font-medium">{latestSubmission.score}</span>
                    </div>
                )}

                {showText && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">Response</p>
                        {canEdit ? (
                            <ReactQuill
                                theme="snow"
                                value={draft.text}
                                onChange={(value) => setDraft((d) => ({ ...d, text: value }))}
                                className="bg-background rounded-md"
                            />
                        ) : (
                            <div
                                className="border rounded-md p-4 bg-muted/30 text-sm prose prose-sm max-w-none opacity-80"
                                dangerouslySetInnerHTML={{
                                    __html:
                                        draft.text ||
                                        latestSubmission?.content?.text ||
                                        '<em>No response submitted</em>',
                                }}
                            />
                        )}
                    </div>
                )}

                {showUrl && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">Reference URL</p>
                        <input
                            className="w-full border rounded-md p-2 text-sm"
                            value={draft.url}
                            disabled={!canEdit}
                            onChange={(event) =>
                                setDraft((d) => ({ ...d, url: event.target.value }))
                            }
                        />
                    </div>
                )}

                {showFile && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">File URL</p>
                        <input
                            className="w-full border rounded-md p-2 text-sm"
                            value={draft.file_url}
                            disabled={!canEdit}
                            onChange={(event) =>
                                setDraft((d) => ({ ...d, file_url: event.target.value }))
                            }
                        />
                        <p className="text-xs text-muted-foreground">Paste a shareable file link.</p>
                    </div>
                )}

                {canEdit ? (
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={handleSaveDraft} disabled={isSubmitting}>
                            Save Draft
                        </Button>
                        <Button onClick={handleSubmit} disabled={isSubmitting}>
                            Submit Assignment
                        </Button>
                    </div>
                ) : (
                    <div className="rounded-md bg-muted/50 border p-3 text-sm text-muted-foreground">
                        {latestSubmission?.status === 'submitted' &&
                            'Your submission is under review by the instructor.'}
                        {latestSubmission?.status === 'graded' &&
                            `Graded — Score: ${latestSubmission.score ?? 'N/A'}`}
                        {latestSubmission?.status === 'approved' &&
                            'Your submission has been approved.'}
                        {!['submitted', 'graded', 'approved'].includes(
                            latestSubmission?.status || ''
                        ) && 'Contact your instructor if you need to resubmit.'}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
