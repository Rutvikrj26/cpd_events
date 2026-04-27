import React from 'react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Textarea } from '@/shared/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select';
import { Switch } from '@/shared/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import { toast } from 'sonner';
import type { Assignment } from '@/api/courses/types';
import { RubricEditor } from './RubricEditor';
import { useCreateAssignment, useUpdateAssignment } from '../../hooks';

interface AssignmentForm {
    title: string;
    description: string;
    instructions: string;
    due_days_after_release: string;
    max_score: string;
    passing_score: string;
    allow_resubmission: boolean;
    max_attempts: string;
    submission_type: string;
    rubric: string;
}

interface AssignmentEditorProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    courseUuid: string;
    moduleUuid: string | null;
    editingAssignment: Assignment | null;
    form: AssignmentForm;
    onFormChange: (patch: Partial<AssignmentForm>) => void;
    onSaved: () => void;
}

function parseOptionalNumber(value: string): number | undefined {
    const parsed = parseInt(value, 10);
    return Number.isNaN(parsed) ? undefined : parsed;
}

export function AssignmentEditor({
    open,
    onOpenChange,
    courseUuid,
    moduleUuid,
    editingAssignment,
    form,
    onFormChange,
    onSaved,
}: AssignmentEditorProps) {
    const { mutate: createAssignment, isPending: creating } = useCreateAssignment(courseUuid);
    const { mutate: updateAssignment, isPending: updating } = useUpdateAssignment(courseUuid);
    const isPending = creating || updating;

    const handleSave = () => {
        if (!moduleUuid || !form.title.trim()) return;

        let rubric: Record<string, any> | undefined;
        if (form.rubric.trim()) {
            try {
                rubric = JSON.parse(form.rubric);
            } catch {
                toast.error('Rubric must be valid JSON');
                return;
            }
        }

        const payload: Partial<Assignment> = {
            title: form.title.trim(),
            description: form.description || undefined,
            instructions: form.instructions || undefined,
            due_days_after_release: parseOptionalNumber(form.due_days_after_release),
            max_score: parseOptionalNumber(form.max_score),
            passing_score: parseOptionalNumber(form.passing_score),
            allow_resubmission: form.allow_resubmission,
            max_attempts: parseOptionalNumber(form.max_attempts),
            submission_type: form.submission_type as Assignment['submission_type'],
            rubric,
        };

        if (editingAssignment) {
            updateAssignment(
                { moduleUuid, assignmentUuid: editingAssignment.uuid, data: payload },
                {
                    onSuccess: () => {
                        toast.success('Assignment updated');
                        onSaved();
                        onOpenChange(false);
                    },
                    onError: () => toast.error('Failed to save assignment'),
                },
            );
        } else {
            createAssignment(
                { moduleUuid, data: payload },
                {
                    onSuccess: () => {
                        toast.success('Assignment created');
                        onSaved();
                        onOpenChange(false);
                    },
                    onError: () => toast.error('Failed to save assignment'),
                },
            );
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>
                        {editingAssignment ? 'Edit Assignment' : 'Add Assignment'}
                    </DialogTitle>
                    <DialogDescription>
                        Create graded work for learners to submit.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="assignment-title">Title</Label>
                            <Input
                                id="assignment-title"
                                placeholder="Assignment title"
                                value={form.title}
                                onChange={(e) => onFormChange({ title: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="assignment-submission-type">Submission Type</Label>
                            <Select
                                value={form.submission_type}
                                onValueChange={(value) => onFormChange({ submission_type: value })}
                            >
                                <SelectTrigger id="assignment-submission-type">
                                    <SelectValue placeholder="Select type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="text">Text Response</SelectItem>
                                    <SelectItem value="url">URL Submission</SelectItem>
                                    <SelectItem value="file">File Link</SelectItem>
                                    <SelectItem value="mixed">Mixed</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="assignment-description">Description</Label>
                        <Textarea
                            id="assignment-description"
                            value={form.description}
                            onChange={(e) => onFormChange({ description: e.target.value })}
                            placeholder="Optional summary for the assignment"
                            className="min-h-[80px]"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="assignment-instructions">Instructions</Label>
                        <Textarea
                            id="assignment-instructions"
                            value={form.instructions}
                            onChange={(e) => onFormChange({ instructions: e.target.value })}
                            placeholder="Detailed steps or grading guidance"
                            className="min-h-[120px]"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="assignment-due-days">Due Days After Release</Label>
                            <Input
                                id="assignment-due-days"
                                type="number"
                                min="0"
                                value={form.due_days_after_release}
                                onChange={(e) => onFormChange({ due_days_after_release: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="assignment-max-score">Max Score</Label>
                            <Input
                                id="assignment-max-score"
                                type="number"
                                min="0"
                                value={form.max_score}
                                onChange={(e) => onFormChange({ max_score: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="assignment-passing-score">Passing Score</Label>
                            <Input
                                id="assignment-passing-score"
                                type="number"
                                min="0"
                                value={form.passing_score}
                                onChange={(e) => onFormChange({ passing_score: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="assignment-max-attempts">Max Attempts</Label>
                            <Input
                                id="assignment-max-attempts"
                                type="number"
                                min="1"
                                value={form.max_attempts}
                                onChange={(e) => onFormChange({ max_attempts: e.target.value })}
                            />
                        </div>
                        <div className="flex items-center justify-between border rounded-lg px-3 py-2">
                            <div>
                                <Label
                                    htmlFor="assignment-resubmission"
                                    className="text-sm font-medium"
                                >
                                    Allow Resubmission
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                    Learners can resubmit if revisions are needed.
                                </p>
                            </div>
                            <Switch
                                id="assignment-resubmission"
                                checked={form.allow_resubmission}
                                onCheckedChange={(checked) =>
                                    onFormChange({ allow_resubmission: checked })
                                }
                            />
                        </div>
                    </div>

                    <RubricEditor
                        value={form.rubric}
                        onChange={(value) => onFormChange({ rubric: value })}
                    />
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
                        Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={isPending || !form.title.trim()}>
                        {editingAssignment ? 'Save Assignment' : 'Create Assignment'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
