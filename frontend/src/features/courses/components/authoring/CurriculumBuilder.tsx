import React, { useState } from 'react';
import { FileText } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/shared/ui/alert-dialog';
import { toast } from 'sonner';
import type { Assignment } from '@/api/courses/types';
import type { QuizData } from '@/components/custom/QuizBuilder';
import { useCourseModules, useDeleteModule, useDeleteContent, useDeleteAssignment } from '../../hooks';
import { ModuleEditor } from './ModuleEditor';
import { ModuleList } from './ModuleList';
import { ContentEditor } from './ContentEditor';
import { AssignmentEditor } from './AssignmentEditor';
import { ContentPreviewDialog } from './ContentPreviewDialog';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DeleteTarget {
    type: 'module' | 'content' | 'assignment';
    uuid: string;
    moduleUuid?: string;
}

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

const BLANK_CONTENT_STATE: ContentEditorState = {
    contentType: 'lesson',
    title: '',
    videoUrl: '',
    textBody: '',
    newFile: null,
    existingFile: null,
    removeFile: false,
    quizData: { questions: [], passing_score: 70 },
    editingContentUuid: null,
};

const BLANK_ASSIGNMENT_FORM: AssignmentForm = {
    title: '',
    description: '',
    instructions: '',
    due_days_after_release: '',
    max_score: '',
    passing_score: '',
    allow_resubmission: false,
    max_attempts: '',
    submission_type: 'text',
    rubric: '',
};

// ---------------------------------------------------------------------------
// CurriculumBuilder
// ---------------------------------------------------------------------------

interface CurriculumBuilderProps {
    courseUuid: string;
}

export function CurriculumBuilder({ courseUuid }: CurriculumBuilderProps) {
    // Fetch
    const { data: modules = [], isLoading } = useCourseModules(courseUuid);

    // Mutation hooks for delete operations
    const { mutate: deleteModule } = useDeleteModule(courseUuid);
    const { mutate: deleteContent } = useDeleteContent(courseUuid);
    const { mutate: deleteAssignment } = useDeleteAssignment(courseUuid);

    // Delete confirmation
    const [itemToDelete, setItemToDelete] = useState<DeleteTarget | null>(null);

    // Content editor
    const [contentEditorOpen, setContentEditorOpen] = useState(false);
    const [selectedModuleUuid, setSelectedModuleUuid] = useState<string | null>(null);
    const [contentState, setContentState] = useState<ContentEditorState>(BLANK_CONTENT_STATE);

    // Assignment editor
    const [assignmentEditorOpen, setAssignmentEditorOpen] = useState(false);
    const [assignmentModuleUuid, setAssignmentModuleUuid] = useState<string | null>(null);
    const [editingAssignment, setEditingAssignment] = useState<Assignment | null>(null);
    const [assignmentForm, setAssignmentForm] = useState<AssignmentForm>(BLANK_ASSIGNMENT_FORM);

    // Preview
    const [previewOpen, setPreviewOpen] = useState(false);
    const [previewContent, setPreviewContent] = useState<any>(null);

    // ---------------------------------------------------------------------------
    // Handlers
    // ---------------------------------------------------------------------------

    const openAddContent = (moduleUuid: string) => {
        setSelectedModuleUuid(moduleUuid);
        setContentState(BLANK_CONTENT_STATE);
        setContentEditorOpen(true);
    };

    const openEditContent = (moduleUuid: string, content: any) => {
        setSelectedModuleUuid(moduleUuid);
        let data: any = {};
        try {
            data =
                typeof content.content_data === 'string'
                    ? JSON.parse(content.content_data)
                    : content.content_data || {};
        } catch {
            data = {};
        }
        const type: 'lesson' | 'quiz' = content.content_type === 'quiz' ? 'quiz' : 'lesson';
        setContentState({
            contentType: type,
            title: content.title,
            videoUrl: type === 'lesson' ? data.video?.url || '' : '',
            textBody: type === 'lesson' ? data.text?.body || '' : '',
            newFile: null,
            existingFile: content.file ?? null,
            removeFile: false,
            quizData:
                type === 'quiz'
                    ? { questions: data.questions || [], passing_score: data.passing_score || 70 }
                    : { questions: [], passing_score: 70 },
            editingContentUuid: content.uuid,
        });
        setContentEditorOpen(true);
    };

    const openAddAssignment = (moduleUuid: string) => {
        setAssignmentModuleUuid(moduleUuid);
        setEditingAssignment(null);
        setAssignmentForm(BLANK_ASSIGNMENT_FORM);
        setAssignmentEditorOpen(true);
    };

    const openEditAssignment = (moduleUuid: string, assignment: Assignment) => {
        setAssignmentModuleUuid(moduleUuid);
        setEditingAssignment(assignment);
        setAssignmentForm({
            title: assignment.title || '',
            description: assignment.description || '',
            instructions: assignment.instructions || '',
            due_days_after_release: assignment.due_days_after_release
                ? String(assignment.due_days_after_release)
                : '',
            max_score: assignment.max_score ? String(assignment.max_score) : '',
            passing_score: assignment.passing_score ? String(assignment.passing_score) : '',
            allow_resubmission: Boolean(assignment.allow_resubmission),
            max_attempts: assignment.max_attempts ? String(assignment.max_attempts) : '',
            submission_type: assignment.submission_type || 'text',
            rubric: assignment.rubric ? JSON.stringify(assignment.rubric, null, 2) : '',
        });
        setAssignmentEditorOpen(true);
    };

    const handleConfirmDelete = () => {
        if (!itemToDelete) return;
        if (itemToDelete.type === 'module') {
            deleteModule(itemToDelete.uuid, {
                onSuccess: () => toast.success('Module deleted'),
                onError: () => toast.error('Failed to delete module'),
            });
        } else if (itemToDelete.type === 'content') {
            // We need the moduleUuid to delete content — find it from the module list
            const parentModule = (modules as any[]).find((m: any) =>
                m.module?.contents?.some((c: any) => c.uuid === itemToDelete.uuid),
            );
            if (!parentModule) return;
            deleteContent(
                { moduleUuid: parentModule.module.uuid, contentUuid: itemToDelete.uuid },
                {
                    onSuccess: () => toast.success('Content deleted'),
                    onError: () => toast.error('Failed to delete content'),
                },
            );
        } else if (itemToDelete.type === 'assignment' && itemToDelete.moduleUuid) {
            deleteAssignment(
                { moduleUuid: itemToDelete.moduleUuid, assignmentUuid: itemToDelete.uuid },
                {
                    onSuccess: () => toast.success('Assignment deleted'),
                    onError: () => toast.error('Failed to delete assignment'),
                },
            );
        }
        setItemToDelete(null);
    };

    // ---------------------------------------------------------------------------
    // Render
    // ---------------------------------------------------------------------------

    if (isLoading) {
        return <div>Loading curriculum...</div>;
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-semibold">Course Curriculum</h2>
                    <p className="text-muted-foreground text-sm">
                        Organize your course into modules, lessons, and quizzes.
                    </p>
                </div>
                <ModuleEditor courseUuid={courseUuid} onCreated={() => {}} />
            </div>

            {/* Module list or empty state */}
            {(modules as any[]).length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                        <div className="h-12 w-12 bg-muted rounded-full flex items-center justify-center mb-4 text-muted-foreground">
                            <FileText className="h-6 w-6" />
                        </div>
                        <h3 className="font-medium text-lg mb-1">No modules yet</h3>
                        <p className="text-muted-foreground mb-4 max-w-sm">
                            Start building your course by adding your first module.
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <ModuleList
                    modules={modules as any}
                    onDeleteModule={(uuid) => setItemToDelete({ type: 'module', uuid })}
                    onAddContent={openAddContent}
                    onEditContent={openEditContent}
                    onPreviewContent={(content) => {
                        setPreviewContent(content);
                        setPreviewOpen(true);
                    }}
                    onDeleteContent={(uuid) => setItemToDelete({ type: 'content', uuid })}
                    onAddAssignment={openAddAssignment}
                    onEditAssignment={openEditAssignment}
                    onDeleteAssignment={(moduleUuid, assignmentUuid) =>
                        setItemToDelete({ type: 'assignment', uuid: assignmentUuid, moduleUuid })
                    }
                />
            )}

            {/* Delete confirmation */}
            <AlertDialog
                open={!!itemToDelete}
                onOpenChange={(open) => !open && setItemToDelete(null)}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. This will permanently delete the{' '}
                            {itemToDelete?.type === 'module'
                                ? 'module and all its contents'
                                : itemToDelete?.type === 'assignment'
                                ? 'assignment'
                                : 'content'}
                            .
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setItemToDelete(null)}>
                            Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => {
                                e.preventDefault();
                                handleConfirmDelete();
                            }}
                            className="bg-destructive hover:bg-destructive/90"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Content editor dialog */}
            <ContentEditor
                open={contentEditorOpen}
                onOpenChange={setContentEditorOpen}
                courseUuid={courseUuid}
                moduleUuid={selectedModuleUuid}
                state={contentState}
                onStateChange={(patch) => setContentState((prev) => ({ ...prev, ...patch }))}
                onSaved={() => {}}
            />

            {/* Assignment editor dialog */}
            <AssignmentEditor
                open={assignmentEditorOpen}
                onOpenChange={setAssignmentEditorOpen}
                courseUuid={courseUuid}
                moduleUuid={assignmentModuleUuid}
                editingAssignment={editingAssignment}
                form={assignmentForm}
                onFormChange={(patch) => setAssignmentForm((prev) => ({ ...prev, ...patch }))}
                onSaved={() => {}}
            />

            {/* Preview dialog */}
            <ContentPreviewDialog
                open={previewOpen}
                onOpenChange={setPreviewOpen}
                content={previewContent}
            />
        </div>
    );
}
