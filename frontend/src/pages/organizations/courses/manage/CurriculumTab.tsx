import React, { useState, useEffect } from "react";
import { Plus, GripVertical, Trash2, Edit2, Video, FileText, File, ChevronRight, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { getCourseModules, createCourseModule, deleteCourseModule, createModuleContent, updateModuleContent, CreateModuleRequest } from "@/api/courses/modules";
import { CourseModule } from "@/api/courses/types";

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
    const [newContentTitle, setNewContentTitle] = useState("");
    const [newVideoUrl, setNewVideoUrl] = useState("");
    const [newTextBody, setNewTextBody] = useState("");
    const [newFile, setNewFile] = useState<File | null>(null);
    const [existingFile, setExistingFile] = useState<{ name: string, url: string } | null>(null);
    const [removeFile, setRemoveFile] = useState(false);

    // Deletion state
    const [itemToDelete, setItemToDelete] = useState<{ type: 'module' | 'content', uuid: string } | null>(null);
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
        // Need parent module UUID. 
        // We can find it from modules list or pass it. 
        // For simplicity, let's look it up.
        const module = modules.find(m => m.module?.contents?.some((c: any) => c.uuid === contentUuid));
        if (!module) return;

        try {
            await client.delete(`/courses/${courseUuid}/modules/${module.module.uuid}/contents/${contentUuid}/`);
            toast.success("Lesson deleted");
            fetchModules();
        } catch (error) {
            console.error(error);
            toast.error("Failed to delete lesson");
        } finally {
            setItemToDelete(null);
        }
    };


    const handleSaveContent = async () => {
        if (!selectedModuleUuid || !newContentTitle) return;

        try {
            const formData = new FormData();
            formData.append('title', newContentTitle);
            formData.append('content_type', 'lesson');
            if (!editingContentUuid) {
                formData.append('order', '0');
            }

            // Construct content_data JSON
            const contentData = {
                video: newVideoUrl ? { url: newVideoUrl } : undefined,
                text: newTextBody ? { body: newTextBody } : undefined
            };
            formData.append('content_data', JSON.stringify(contentData));

            if (newFile) {
                formData.append('file', newFile);
            } else if (removeFile) {
                formData.append('remove_file', 'true');
            }

            if (editingContentUuid) {
                await updateModuleContent(courseUuid, selectedModuleUuid, editingContentUuid, formData);
                toast.success("Lesson updated");
            } else {
                await createModuleContent(courseUuid, selectedModuleUuid, formData);
                toast.success("Lesson added");
            }

            // Reset form
            setNewContentTitle("");
            setNewVideoUrl("");
            setNewTextBody("");
            setNewFile(null);
            setExistingFile(null);
            setRemoveFile(false);
            setEditingContentUuid(null);
            setIsAddContentOpen(false);
            fetchModules();
        } catch (error) {
            toast.error(editingContentUuid ? "Failed to update lesson" : "Failed to add lesson");
            console.error(error);
        }
    };

    const openAddContentDialog = (moduleUuid: string) => {
        setSelectedModuleUuid(moduleUuid);
        setEditingContentUuid(null);
        setNewContentTitle("");
        setNewVideoUrl("");
        setNewTextBody("");
        setNewFile(null);
        setExistingFile(null);
        setRemoveFile(false);
        setIsAddContentOpen(true);
    };

    const openEditContentDialog = (moduleUuid: string, content: any) => {
        setSelectedModuleUuid(moduleUuid);
        setEditingContentUuid(content.uuid);
        setNewContentTitle(content.title);

        // Parse content_data safely
        let data = {};
        try {
            data = typeof content.content_data === 'string'
                ? JSON.parse(content.content_data)
                : content.content_data || {};
        } catch (e) {
            console.error("Error parsing content data", e);
        }

        // @ts-ignore
        setNewVideoUrl(data.video?.url || "");
        // @ts-ignore
        setNewTextBody(data.text?.body || "");

        // Handle file
        setExistingFile(content.file);
        setNewFile(null);
        setRemoveFile(false);

        setIsAddContentOpen(true);
    };

    const openPreviewDialog = (content: any) => {
        setPreviewContent(content);
        setIsPreviewOpen(true);
    };

    if (loading) return <div>Loading curriculum...</div>;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-xl font-semibold">Course Curriculum</h2>
                    <p className="text-muted-foreground text-sm">Organize your course into modules and lessons.</p>
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
                <Dialog open={isAddContentOpen} onOpenChange={setIsAddContentOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>{editingContentUuid ? "Edit Lesson" : "Add Lesson"}</DialogTitle>
                            <DialogDescription>
                                {editingContentUuid ? "Update the lesson content." : "Create a comprehensive lesson with video, text, and resources."}
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="content-title">Lesson Title</Label>
                                <Input
                                    id="content-title"
                                    placeholder="e.g., Introduction to the Course"
                                    value={newContentTitle}
                                    onChange={(e) => setNewContentTitle(e.target.value)}
                                />
                            </div>

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
                                <Label htmlFor="text-body">Lesson Content (Optional)</Label>
                                <textarea
                                    id="text-body"
                                    className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                                    placeholder="Enter text content, instructions, or reading material..."
                                    value={newTextBody}
                                    onChange={(e) => setNewTextBody(e.target.value)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="file-upload">Attachment (Optional)</Label>
                                {existingFile && !removeFile ? (
                                    <div className="flex items-center justify-between p-2 border rounded-md bg-muted/20">
                                        <div className="flex items-center gap-2 overflow-hidden">
                                            <File className="h-4 w-4 flex-shrink-0 text-blue-500" />
                                            <span className="text-sm truncate max-w-[200px]">
                                                {typeof existingFile === 'string' ? existingFile.split('/').pop() : 'Attached File'}
                                            </span>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-6 text-xs text-red-500 hover:text-red-700 hover:bg-red-50"
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
                                                setRemoveFile(false); // If they upload new, implicit replacement, not removal
                                            }}
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            {editingContentUuid ? "Upload new file to replace existing" : "Upload a PDF, document, or supplementary file."}
                                            {removeFile && <span className="text-red-500 ml-2">(Existing file will be removed)</span>}
                                        </p>
                                    </>
                                )}
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setIsAddContentOpen(false)}>Cancel</Button>
                            <Button onClick={handleSaveContent} disabled={!newContentTitle.trim()}>
                                {editingContentUuid ? "Update Lesson" : "Add Lesson"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Preview Dialog */}
                <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
                    <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle>{previewContent?.title}</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-6 py-4">
                            {/* Parse content data safely */}
                            {(() => {
                                if (!previewContent) return null;
                                const data = typeof previewContent.content_data === 'string'
                                    ? JSON.parse(previewContent.content_data)
                                    : previewContent.content_data || {};

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
                                            <div className="prose prose-sm max-w-none p-4 bg-gray-50 rounded-lg whitespace-pre-wrap">
                                                {data.text.body}
                                            </div>
                                        )}

                                        {previewContent.file && (
                                            <div className="flex items-center gap-2 p-3 border rounded-md bg-gray-50">
                                                <File className="h-4 w-4 text-blue-500" />
                                                <span className="text-sm font-medium">Attached File (Available for download)</span>
                                            </div>
                                        )}

                                        {!data.video?.url && !data.text?.body && !previewContent.file && (
                                            <p className="text-center text-gray-400 italic">No content details available.</p>
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
                            {itemToDelete?.type === 'module' ? ' module and all its lessons' : ' lesson'}.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setItemToDelete(null)}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(e) => {
                                e.preventDefault(); // Prevent closing immediately if async
                                if (itemToDelete?.type === 'module') {
                                    handleDeleteModule(itemToDelete.uuid);
                                } else if (itemToDelete?.type === 'content') {
                                    // Need to implement content deletion handler
                                    handleDeleteContent(itemToDelete.uuid);
                                }
                            }}
                            className="bg-red-600 hover:bg-red-700"
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
                            <div className="h-12 w-12 bg-muted rounded-full flex items-center justify-center mb-4 text-gray-400">
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
    onDeleteContent
}: {
    module: CourseModule,
    onDelete: () => void,
    courseUuid: string,
    onAddContent: (id: string) => void,
    onEditContent: (moduleUuid: string, content: any) => void,
    onPreviewContent: (content: any) => void,
    onDeleteContent: (uuid: string) => void
}) {

    const [isExpanded, setIsExpanded] = useState(false);
    // Real implementation would fetch contents here or pass them down if nested
    const contents = module.module?.contents || [];

    return (
        <Card className="overflow-hidden">
            <div className="flex items-center p-4 bg-gray-50/50 border-b border-gray-100">
                <Button variant="ghost" size="icon" className="mr-2 cursor-grab text-gray-400 hover:text-gray-600">
                    <GripVertical className="h-4 w-4" />
                </Button>
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <h3 className="font-medium">{module.module?.title || "Untitled Module"}</h3>
                        {module.is_required && <Badge variant="secondary" className="text-[10px] h-5">Required</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {contents.length} lessons • {module.module?.cpd_credits || 0} credits
                    </p>
                </div>
                <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)}>
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-red-500" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {isExpanded && (
                <CardContent className="p-0 bg-white">
                    <div className="divide-y divide-gray-100">
                        {contents.length === 0 ? (
                            <div className="p-8 text-center text-sm text-gray-400 italic">
                                No content in this module yet.
                                <div className="mt-2">
                                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => onAddContent(module.module.uuid)}>
                                        <Plus className="mr-1 h-3 w-3" /> Add Lesson
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            contents.map((content: any) => (
                                <div key={content.uuid} className="flex items-center p-3 pl-12 hover:bg-gray-50 group cursor-pointer" onClick={() => onPreviewContent(content)}>
                                    <div className="mr-3 text-gray-400">
                                        <FileText className="h-4 w-4" />
                                    </div>
                                    <span className="text-sm flex-1">{content.title} <span className="text-xs text-muted-foreground ml-2">({content.content_type === 'lesson' ? 'Mixed' : content.content_type})</span></span>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={(e) => { e.stopPropagation(); onPreviewContent(content); }}>
                                            Preview
                                        </Button>
                                        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onEditContent(module.module.uuid, content); }}>
                                            <Edit2 className="h-3 w-3" />
                                        </Button>
                                        <Button variant="ghost" size="icon" className="h-6 w-6 text-gray-500 hover:text-red-500" onClick={(e) => { e.stopPropagation(); onDeleteContent(content.uuid); }}>
                                            <Trash2 className="h-3 w-3" />
                                        </Button>
                                    </div>
                                </div>
                            ))
                        )}
                        <div className="p-2 pl-12 bg-gray-50/30">
                            <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-primary" onClick={() => onAddContent(module.module.uuid)}>
                                <Plus className="mr-1 h-3 w-3" /> Add Lesson
                            </Button>
                        </div>
                    </div>
                </CardContent>
            )}
        </Card>
    );
}
