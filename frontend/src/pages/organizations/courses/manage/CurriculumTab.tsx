import React, { useState, useEffect } from "react";
import { Plus, GripVertical, Trash2, Edit2, FileText, File, ChevronRight, ChevronDown, HelpCircle, ClipboardCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { getCourseModules, createCourseModule, deleteCourseModule, createModuleContent, updateModuleContent } from "@/api/courses/modules";
import { createCourseAssignment, deleteCourseAssignment, updateCourseAssignment } from "@/api/courses";
import { Assignment, CourseModule } from "@/api/courses/types";
import { QuizBuilder, QuizData } from "@/components/custom/QuizBuilder";

import client from "@/api/client";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// Import React Quill dynamically or standard import if environment supports it
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';

interface CurriculumTabProps {
    courseUuid: string;
}

export function CurriculumTab({ courseUuid }: CurriculumTabProps) {
    const [modules, setModules] = useState<CourseModule[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [newModuleTitle, setNewModuleTitle] = useState("");

    // Content management state
    const [isAddContentOpen, setIsAddContentOpen] = useState(false);
    const [selectedModuleUuid, setSelectedModuleUuid] = useState<string | null>(null);
    const [editingContentUuid, setEditingContentUuid] = useState<string | null>(null);

    // Assignment management state
    const [isAssignmentOpen, setIsAssignmentOpen] = useState(false);
    const [assignmentModuleUuid, setAssignmentModuleUuid] = useState<string | null>(null);
    const [editingAssignment, setEditingAssignment] = useState<Assignment | null>(null);
    const [assignmentForm, setAssignmentForm] = useState({
        title: "",
        description: "",
        instructions: "",
        due_days_after_release: "",
        max_score: "",
        passing_score: "",
        allow_resubmission: false,
        max_attempts: "",
        submission_type: "text",
        rubric: "",
    });

    // Joint state
    const [contentType, setContentType] = useState<'lesson' | 'quiz'>('lesson');
    const [newContentTitle, setNewContentTitle] = useState("");

    // Lesson state
    const [newVideoUrl, setNewVideoUrl] = useState("");
    const [newTextBody, setNewTextBody] = useState("");
    const [newFile, setNewFile] = useState<File | null>(null);
    const [existingFile, setExistingFile] = useState<{ name: string, url: string } | string | null>(null);
    const [removeFile, setRemoveFile] = useState(false);

    // Quiz state
    const [quizData, setQuizData] = useState<QuizData>({ questions: [], passing_score: 70 });

    // Deletion state
    const [itemToDelete, setItemToDelete] = useState<{ type: 'module' | 'content' | 'assignment', uuid: string, moduleUuid?: string } | null>(null);
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    const [previewContent, setPreviewContent] = useState<any>(null);

    const fetchModules = async () => {
        try {
            const data = await getCourseModules(courseUuid);
            setModules(data);
        } catch (error) {
            toast.error("Failed to load curriculum");
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchModules();
    }, [courseUuid]);

    const handleCreateModule = async () => {
        if (!newModuleTitle.trim()) return;
        try {
            await createCourseModule(courseUuid, { title: newModuleTitle, course_uuid: courseUuid });
            toast.success("Module created");
            setNewModuleTitle("");
            setIsCreateOpen(false);
            fetchModules();
        } catch (error) {
            toast.error("Failed to create module");
        }
    };

    const handleDeleteModule = async (moduleUuid: string) => {
        try {
            await deleteCourseModule(courseUuid, moduleUuid);
            toast.success("Module deleted");
            fetchModules();
        } catch (error) {
            toast.error("Failed to delete module");
        } finally {
            setItemToDelete(null);
        }
    };

    const handleDeleteContent = async (contentUuid: string) => {
        const module = modules.find(m => m.module?.contents?.some((c: any) => c.uuid === contentUuid));
        if (!module) return;

        try {
            await client.delete(`/courses/${courseUuid}/modules/${module.module.uuid}/contents/${contentUuid}/`);
            toast.success("Content deleted");
            fetchModules();
        } catch (error) {
            console.error(error);
            toast.error("Failed to delete content");
        } finally {
            setItemToDelete(null);
        }
    };


    const handleSaveContent = async () => {
        if (!selectedModuleUuid || !newContentTitle) return;

        try {
            const formData = new FormData();
            formData.append('title', newContentTitle);
            formData.append('content_type', contentType);

            if (!editingContentUuid) {
                formData.append('order', '0'); // Backend should handle auto-ordering ideally
            }

            // Construct content_data JSON
            let contentData: any = {};

            if (contentType === 'lesson') {
                contentData = {
                    video: newVideoUrl ? { url: newVideoUrl } : undefined,
                    text: newTextBody ? { body: newTextBody } : undefined
                };
            } else if (contentType === 'quiz') {
                contentData = {
                    questions: quizData.questions,
                    passing_score: quizData.passing_score
                };
            }

            formData.append('content_data', JSON.stringify(contentData));

            if (contentType === 'lesson') {
                if (newFile) {
                    formData.append('file', newFile);
                } else if (removeFile) {
                    formData.append('remove_file', 'true');
                }
            }

            if (editingContentUuid) {
                await updateModuleContent(courseUuid, selectedModuleUuid, editingContentUuid, formData);
                toast.success(`${contentType === 'quiz' ? 'Quiz' : 'Lesson'} updated`);
            } else {
                await createModuleContent(courseUuid, selectedModuleUuid, formData);
                toast.success(`${contentType === 'quiz' ? 'Quiz' : 'Lesson'} added`);
            }

            // Reset form
            resetContentForm();
            setIsAddContentOpen(false);
            fetchModules();
        } catch (error) {
            toast.error(editingContentUuid ? "Failed to update content" : "Failed to add content");
            console.error(error);
        }
    };

    const resetContentForm = () => {
        setNewContentTitle("");
        setContentType('lesson');
        setNewVideoUrl("");
        setNewTextBody("");
        setNewFile(null);
        setExistingFile(null);
        setRemoveFile(false);
        setQuizData({ questions: [], passing_score: 70 });
        setEditingContentUuid(null);
    };

    const resetAssignmentForm = () => {
        setAssignmentForm({
            title: "",
            description: "",
            instructions: "",
            due_days_after_release: "",
            max_score: "",
            passing_score: "",
            allow_resubmission: false,
            max_attempts: "",
            submission_type: "text",
            rubric: "",
        });
        setAssignmentModuleUuid(null);
        setEditingAssignment(null);
    };

    const openAddContentDialog = (moduleUuid: string) => {
        resetContentForm();
        setSelectedModuleUuid(moduleUuid);
        setIsAddContentOpen(true);
    };

    const openAddAssignmentDialog = (moduleUuid: string) => {
        resetAssignmentForm();
        setAssignmentModuleUuid(moduleUuid);
        setIsAssignmentOpen(true);
    };

    const openEditAssignmentDialog = (moduleUuid: string, assignment: Assignment) => {
        setAssignmentModuleUuid(moduleUuid);
        setEditingAssignment(assignment);
        setAssignmentForm({
            title: assignment.title || "",
            description: assignment.description || "",
            instructions: assignment.instructions || "",
            due_days_after_release: assignment.due_days_after_release ? String(assignment.due_days_after_release) : "",
            max_score: assignment.max_score ? String(assignment.max_score) : "",
            passing_score: assignment.passing_score ? String(assignment.passing_score) : "",
            allow_resubmission: Boolean(assignment.allow_resubmission),
            max_attempts: assignment.max_attempts ? String(assignment.max_attempts) : "",
            submission_type: assignment.submission_type || "text",
            rubric: assignment.rubric ? JSON.stringify(assignment.rubric, null, 2) : "",
        });
        setIsAssignmentOpen(true);
    };

    const parseOptionalNumber = (value: string) => {
        const parsed = parseInt(value, 10);
        return Number.isNaN(parsed) ? undefined : parsed;
    };

    const handleSaveAssignment = async () => {
        if (!assignmentModuleUuid || !assignmentForm.title.trim()) {
            return;
        }

        let rubric: Record<string, any> | undefined;
        if (assignmentForm.rubric.trim()) {
            try {
                rubric = JSON.parse(assignmentForm.rubric);
            } catch (error) {
                toast.error("Rubric must be valid JSON");
                return;
            }
        }

        const payload: Partial<Assignment> = {
            title: assignmentForm.title.trim(),
            description: assignmentForm.description || undefined,
            instructions: assignmentForm.instructions || undefined,
            due_days_after_release: parseOptionalNumber(assignmentForm.due_days_after_release),
            max_score: parseOptionalNumber(assignmentForm.max_score),
            passing_score: parseOptionalNumber(assignmentForm.passing_score),
            allow_resubmission: assignmentForm.allow_resubmission,
            max_attempts: parseOptionalNumber(assignmentForm.max_attempts),
            submission_type: assignmentForm.submission_type as Assignment["submission_type"],
            rubric,
        };

        try {
            if (editingAssignment) {
                await updateCourseAssignment(courseUuid, assignmentModuleUuid, editingAssignment.uuid, payload);
                toast.success("Assignment updated");
            } else {
                await createCourseAssignment(courseUuid, assignmentModuleUuid, payload);
                toast.success("Assignment created");
            }
            setIsAssignmentOpen(false);
            resetAssignmentForm();
            fetchModules();
        } catch (error) {
            console.error(error);
            toast.error("Failed to save assignment");
        }
    };

    const handleDeleteAssignment = async (moduleUuid: string, assignmentUuid: string) => {
        try {
            await deleteCourseAssignment(courseUuid, moduleUuid, assignmentUuid);
            toast.success("Assignment deleted");
            fetchModules();
        } catch (error) {
            console.error(error);
            toast.error("Failed to delete assignment");
        } finally {
            setItemToDelete(null);
        }
    };

    const openEditContentDialog = (moduleUuid: string, content: any) => {
        setSelectedModuleUuid(moduleUuid);
        setEditingContentUuid(content.uuid);
        setNewContentTitle(content.title);

        // Determine type
        const type = content.content_type === 'quiz' ? 'quiz' : 'lesson';
        setContentType(type);

        // Parse content_data safely
        let data: any = {};
        try {
            data = typeof content.content_data === 'string'
                ? JSON.parse(content.content_data)
                : content.content_data || {};
        } catch (e) {
            console.error("Error parsing content data", e);
        }

        if (type === 'lesson') {
            setNewVideoUrl(data.video?.url || "");
            setNewTextBody(data.text?.body || "");
            setExistingFile(content.file);
            setNewFile(null);
            setRemoveFile(false);
        } else {
            setQuizData({
                questions: data.questions || [],
                passing_score: data.passing_score || 70
            });
        }

        setIsAddContentOpen(true);
    };

    const openPreviewDialog = (content: any) => {
        setPreviewContent(content);
        setIsPreviewOpen(true);
    };

    if (loading) return <div>Loading curriculum...</div>;

    const quillModules = {
        toolbar: [
            [{ 'header': [1, 2, 3, false] }],
            ['bold', 'italic', 'underline', 'strike', 'blockquote'],
            [{ 'list': 'ordered' }, { 'list': 'bullet' }],
            ['link', 'clean']
        ],
    };

    const quillFormats = [
        'header',
        'bold', 'italic', 'underline', 'strike', 'blockquote',
        'list', 'bullet',
        'link'
    ];

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-semibold">Course Curriculum</h2>
                    <p className="text-muted-foreground text-sm">Organize your course into modules, lessons, and quizzes.</p>
                </div>
                <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                    <DialogTrigger asChild>
                        <Button>
                            <Plus className="mr-2 h-4 w-4" /> Add Module
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Add New Module</DialogTitle>
                            <DialogDescription>Create a new section for your course curriculum.</DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="title">Module Title</Label>
                                <Input
                                    id="title"
                                    placeholder="e.g., Introduction to CPD"
                                    value={newModuleTitle}
                                    onChange={(e) => setNewModuleTitle(e.target.value)}
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                            <Button onClick={handleCreateModule}>Create Module</Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Add/Edit Content Dialog */}
                <Dialog open={isAddContentOpen} onOpenChange={(open) => {
                    if (!open) setIsAddContentOpen(false);
                }}>
                    <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle>{editingContentUuid ? `Edit ${contentType === 'quiz' ? 'Quiz' : 'Lesson'}` : "Add Content"}</DialogTitle>
                            <DialogDescription>
                                {editingContentUuid
                                    ? `Update the ${contentType} content.`
                                    : "Create a new lesson or quiz for this module."}
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-6 py-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="content-type">Content Type</Label>
                                    <Select
                                        value={contentType}
                                        onValueChange={(val: 'lesson' | 'quiz') => setContentType(val)}
                                        disabled={!!editingContentUuid} // Cannot change type when editing
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
                                        placeholder={`e.g., ${contentType === 'quiz' ? 'Module 1 Quiz' : 'Introduction Lesson'}`}
                                        value={newContentTitle}
                                        onChange={(e) => setNewContentTitle(e.target.value)}
                                    />
                                </div>
                            </div>

                            {contentType === 'lesson' ? (
                                <>
                                    <div className="space-y-2">
                                        <Label htmlFor="video-url">Video URL (Optional)</Label>
                                        <Input
                                            id="video-url"
                                            placeholder="https://vimeo.com/..."
                                            value={newVideoUrl}
                                            onChange={(e) => setNewVideoUrl(e.target.value)}
                                        />
                                        <p className="text-xs text-muted-foreground">Supports Vimeo, YouTube, or direct MP4 links.</p>
                                    </div>

                                    <div className="space-y-2">
                                        <Label>Lesson Content</Label>
                                        <div className="bg-background rounded-md">
                                            <ReactQuill
                                                theme="snow"
                                                value={newTextBody}
                                                onChange={setNewTextBody}
                                                modules={quillModules}
                                                formats={quillFormats}
                                                className="h-64 mb-12"
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="file-upload">Attachment (Optional)</Label>
                                        {existingFile && !removeFile ? (
                                            <div className="flex items-center justify-between p-2 border rounded-md bg-muted/20">
                                                <div className="flex items-center gap-2 overflow-hidden">
                                                    <File className="h-4 w-4 flex-shrink-0 text-primary" />
                                                    <span className="text-sm truncate max-w-[200px]">
                                                        {typeof existingFile === 'string' ? existingFile.split('/').pop() : 'Attached File'}
                                                    </span>
                                                </div>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-6 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                                                    onClick={() => setRemoveFile(true)}
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
                                                        setNewFile(e.target.files ? e.target.files[0] : null);
                                                        setRemoveFile(false);
                                                    }}
                                                />
                                                <p className="text-xs text-muted-foreground">
                                                    {editingContentUuid ? "Upload new file to replace existing" : "Upload a PDF, document, or supplementary file."}
                                                    {removeFile && <span className="text-destructive ml-2">(Existing file will be removed)</span>}
                                                </p>
                                            </>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <QuizBuilder
                                    initialData={quizData}
                                    onChange={setQuizData}
                                />
                            )}
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setIsAddContentOpen(false)}>Cancel</Button>
                            <Button onClick={handleSaveContent} disabled={!newContentTitle.trim()}>
                                {editingContentUuid ? "Update Item" : "Add Item"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Add/Edit Assignment Dialog */}
                <Dialog open={isAssignmentOpen} onOpenChange={(open) => {
                    if (!open) {
                        setIsAssignmentOpen(false);
                        resetAssignmentForm();
                    }
                }}>
                    <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle>{editingAssignment ? "Edit Assignment" : "Add Assignment"}</DialogTitle>
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
                                        value={assignmentForm.title}
                                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, title: event.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="assignment-submission-type">Submission Type</Label>
                                    <Select
                                        value={assignmentForm.submission_type}
                                        onValueChange={(value) => setAssignmentForm((prev) => ({ ...prev, submission_type: value }))}
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
                                    value={assignmentForm.description}
                                    onChange={(event) => setAssignmentForm((prev) => ({ ...prev, description: event.target.value }))}
                                    placeholder="Optional summary for the assignment"
                                    className="min-h-[80px]"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="assignment-instructions">Instructions</Label>
                                <Textarea
                                    id="assignment-instructions"
                                    value={assignmentForm.instructions}
                                    onChange={(event) => setAssignmentForm((prev) => ({ ...prev, instructions: event.target.value }))}
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
                                        value={assignmentForm.due_days_after_release}
                                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, due_days_after_release: event.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="assignment-max-score">Max Score</Label>
                                    <Input
                                        id="assignment-max-score"
                                        type="number"
                                        min="0"
                                        value={assignmentForm.max_score}
                                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, max_score: event.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="assignment-passing-score">Passing Score</Label>
                                    <Input
                                        id="assignment-passing-score"
                                        type="number"
                                        min="0"
                                        value={assignmentForm.passing_score}
                                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, passing_score: event.target.value }))}
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
                                        value={assignmentForm.max_attempts}
                                        onChange={(event) => setAssignmentForm((prev) => ({ ...prev, max_attempts: event.target.value }))}
                                    />
                                </div>
                                <div className="flex items-center justify-between border rounded-lg px-3 py-2">
                                    <div>
                                        <Label htmlFor="assignment-resubmission" className="text-sm font-medium">
                                            Allow Resubmission
                                        </Label>
                                        <p className="text-xs text-muted-foreground">
                                            Learners can resubmit if revisions are needed.
                                        </p>
                                    </div>
                                    <Switch
                                        id="assignment-resubmission"
                                        checked={assignmentForm.allow_resubmission}
                                        onCheckedChange={(checked) => setAssignmentForm((prev) => ({ ...prev, allow_resubmission: checked }))}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="assignment-rubric">Rubric (JSON, optional)</Label>
                                <Textarea
                                    id="assignment-rubric"
                                    value={assignmentForm.rubric}
                                    onChange={(event) => setAssignmentForm((prev) => ({ ...prev, rubric: event.target.value }))}
                                    placeholder='{"criteria": []}'
                                    className="min-h-[100px]"
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setIsAssignmentOpen(false)}>
                                Cancel
                            </Button>
                            <Button onClick={handleSaveAssignment} disabled={!assignmentForm.title.trim()}>
                                {editingAssignment ? "Save Assignment" : "Create Assignment"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Preview Dialog */}
                <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
                    <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle>{previewContent?.title}</DialogTitle>
                            <Badge variant="outline" className="w-fit mt-1">
                                {previewContent?.content_type === 'quiz' ? 'Quiz' : 'Lesson'}
                            </Badge>
                        </DialogHeader>
                        <div className="space-y-6 py-4">
                            {/* Parse content data safely */}
                            {(() => {
                                if (!previewContent) return null;
                                const data = typeof previewContent.content_data === 'string'
                                    ? JSON.parse(previewContent.content_data)
                                    : previewContent.content_data || {};

                                if (previewContent.content_type === 'quiz') {
                                    return (
                                        <div className="space-y-4">
                                            <div className="flex justify-between items-center p-3 bg-muted/30 rounded-md">
                                                <span className="font-medium">Passing Score: {data.passing_score}%</span>
                                                <span className="text-muted-foreground">{data.questions?.length || 0} Questions</span>
                                            </div>
                                            <div className="space-y-4">
                                                {data.questions?.map((q: any, idx: number) => (
                                                    <div key={idx} className="border p-4 rounded-md">
                                                        <div className="flex gap-2">
                                                            <span className="font-bold text-muted-foreground">{idx + 1}.</span>
                                                            <div className="flex-1">
                                                                <p className="font-medium mb-2">{q.text}</p>
                                                                <div className="space-y-1 pl-2">
                                                                    {q.options?.map((opt: any, oIdx: number) => (
                                                                        <div key={oIdx} className="flex items-center gap-2 text-sm">
                                                                            <div className={`h-2 w-2 rounded-full ${opt.isCorrect ? 'bg-success' : 'bg-muted'}`} />
                                                                            <span className={opt.isCorrect ? 'font-medium text-success' : ''}>{opt.text}</span>
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
                                    );
                                }

                                return (
                                    <>
                                        {data.video?.url && (
                                            <div className="aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center">
                                                <iframe
                                                    src={data.video.url.replace("watch?v=", "embed/")}
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

                                        {previewContent.file && (
                                            <div className="flex items-center gap-2 p-3 border rounded-md bg-muted/30">
                                                <File className="h-4 w-4 text-primary" />
                                                <span className="text-sm font-medium">Attached File (Available for download)</span>
                                            </div>
                                        )}
                                    </>
                                );
                            })()}
                        </div>
                        <DialogFooter>
                            <Button onClick={() => setIsPreviewOpen(false)}>Close Preview</Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>


            {/* Delete Confirmation Dialog */}
            <AlertDialog open={!!itemToDelete} onOpenChange={(open) => !open && setItemToDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. This will permanently delete the
                            {itemToDelete?.type === 'module'
                                ? ' module and all its contents'
                                : itemToDelete?.type === 'assignment'
                                    ? ' assignment'
                                    : ' content'}.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setItemToDelete(null)}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => {
                                e.preventDefault();
                                if (itemToDelete?.type === 'module') {
                                    handleDeleteModule(itemToDelete.uuid);
                                } else if (itemToDelete?.type === 'content') {
                                    handleDeleteContent(itemToDelete.uuid);
                                } else if (itemToDelete?.type === 'assignment' && itemToDelete.moduleUuid) {
                                    handleDeleteAssignment(itemToDelete.moduleUuid, itemToDelete.uuid);
                                }
                            }}
                            className="bg-destructive hover:bg-destructive/90"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <div className="space-y-4">
                {modules.length === 0 ? (
                    <Card className="border-dashed">
                        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                            <div className="h-12 w-12 bg-muted rounded-full flex items-center justify-center mb-4 text-muted-foreground">
                                <FileText className="h-6 w-6" />
                            </div>
                            <h3 className="font-medium text-lg mb-1">No modules yet</h3>
                            <p className="text-muted-foreground mb-4 max-w-sm">Start building your course by adding your first module.</p>
                            <Button onClick={() => setIsCreateOpen(true)} variant="outline">Add Module</Button>
                        </CardContent>
                    </Card>
                ) : (
                    modules.map((courseModule) => (
                        <ModuleItem
                            key={courseModule.uuid}
                            module={courseModule}
                            onDelete={() => setItemToDelete({ type: 'module', uuid: courseModule.uuid })}
                            courseUuid={courseUuid}
                            onAddContent={openAddContentDialog}
                            onEditContent={openEditContentDialog}
                            onPreviewContent={openPreviewDialog}
                            onDeleteContent={(contentUuid) => setItemToDelete({ type: 'content', uuid: contentUuid })}
                            onAddAssignment={openAddAssignmentDialog}
                            onEditAssignment={openEditAssignmentDialog}
                            onDeleteAssignment={(moduleUuid, assignmentUuid) =>
                                setItemToDelete({ type: 'assignment', uuid: assignmentUuid, moduleUuid })
                            }
                        />
                    ))
                )}
            </div>
        </div >
    );
}

function ModuleItem({
    module,
    onDelete,
    courseUuid,
    onAddContent,
    onEditContent,
    onPreviewContent,
    onDeleteContent,
    onAddAssignment,
    onEditAssignment,
    onDeleteAssignment
}: {
    module: CourseModule,
    onDelete: () => void,
    courseUuid: string,
    onAddContent: (id: string) => void,
    onEditContent: (moduleUuid: string, content: any) => void,
    onPreviewContent: (content: any) => void,
    onDeleteContent: (uuid: string) => void,
    onAddAssignment: (moduleUuid: string) => void,
    onEditAssignment: (moduleUuid: string, assignment: Assignment) => void,
    onDeleteAssignment: (moduleUuid: string, assignmentUuid: string) => void
}) {

    const [isExpanded, setIsExpanded] = useState(false);
    const contents = module.module?.contents || [];
    const assignments = module.module?.assignments || [];

    return (
        <Card className="overflow-hidden">
            <div className="flex items-center p-4 bg-muted/30 border-b border-border">
                <Button variant="ghost" size="icon" className="mr-2 cursor-grab text-muted-foreground hover:text-foreground">
                    <GripVertical className="h-4 w-4" />
                </Button>
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <h3 className="font-medium">{module.module?.title || "Untitled Module"}</h3>
                        {module.is_required && <Badge variant="secondary" className="text-[10px] h-5">Required</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {contents.length} items • {module.module?.cpd_credits || 0} credits
                    </p>
                </div>
                <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)}>
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {isExpanded && (
                <CardContent className="p-0 bg-card">
                    <div className="divide-y divide-border">
                        {contents.length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground italic">
                                No content in this module yet.
                                <div className="mt-2">
                                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => onAddContent(module.module.uuid)}>
                                        <Plus className="mr-1 h-3 w-3" /> Add Content
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            contents.map((content: any) => (
                                <div key={content.uuid} className="flex items-center p-3 pl-12 hover:bg-muted/30 group cursor-pointer" onClick={() => onPreviewContent(content)}>
                                    <div className="mr-3 text-muted-foreground">
                                        {content.content_type === 'quiz' ? <HelpCircle className="h-4 w-4 text-primary" /> : <FileText className="h-4 w-4" />}
                                    </div>
                                    <span className="text-sm flex-1">{content.title} <span className="text-xs text-muted-foreground ml-2">({content.content_type})</span></span>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={(e) => { e.stopPropagation(); onPreviewContent(content); }}>
                                            Preview
                                        </Button>
                                        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onEditContent(module.module.uuid, content); }}>
                                            <Edit2 className="h-3 w-3" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); onDeleteContent(content.uuid); }}>
                                            <Trash2 className="h-3 w-3" />
                                        </Button>
                                    </div>
                                </div>
                            ))
                        )}
                        <div className="p-2 pl-12 bg-muted/20">
                            <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-primary" onClick={() => onAddContent(module.module.uuid)}>
                                <Plus className="mr-1 h-3 w-3" /> Add Content
                            </Button>
                        </div>
                        <div className="border-t border-border" />
                        {assignments.length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground italic">
                                No assignments in this module yet.
                                <div className="mt-2">
                                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => onAddAssignment(module.module.uuid)}>
                                        <Plus className="mr-1 h-3 w-3" /> Add Assignment
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            assignments.map((assignment: Assignment) => (
                                <div key={assignment.uuid} className="flex items-center p-3 pl-12 hover:bg-muted/30 group">
                                    <div className="mr-3 text-muted-foreground">
                                        <ClipboardCheck className="h-4 w-4 text-warning" />
                                    </div>
                                    <span className="text-sm flex-1">
                                        {assignment.title}
                                        <span className="text-xs text-muted-foreground ml-2">
                                            ({assignment.submission_type || 'text'})
                                        </span>
                                    </span>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            onClick={() => onEditAssignment(module.module.uuid, assignment)}
                                        >
                                            <Edit2 className="h-3 w-3" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                            onClick={() => onDeleteAssignment(module.module.uuid, assignment.uuid)}
                                        >
                                            <Trash2 className="h-3 w-3" />
                                        </Button>
                                    </div>
                                </div>
                            ))
                        )}
                        <div className="p-2 pl-12 bg-muted/20">
                            <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-primary" onClick={() => onAddAssignment(module.module.uuid)}>
                                <Plus className="mr-1 h-3 w-3" /> Add Assignment
                            </Button>
                        </div>
                    </div>
                </CardContent>
            )}
        </Card>
    );
}
