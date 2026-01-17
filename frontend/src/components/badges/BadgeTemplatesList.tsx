import React, { useState, useEffect } from "react";
import {
    Plus,
    MoreHorizontal,
    Trash2,
    Edit,
    Award,
    Loader2,
    Upload,
    Settings,
    Image as ImageIcon
} from "lucide-react";
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle
} from "@/components/ui/dialog";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import {
    getBadgeTemplates,
    createBadgeTemplate,
    updateBadgeTemplate,
    deleteBadgeTemplate,
    uploadBadgeTemplateImage
} from "@/api/badges";
import { BadgeTemplate } from "@/api/badges/types";
import { toast } from "sonner";
import { BadgeDesigner } from "@/components/badges/BadgeDesigner";

export function BadgeTemplatesList() {
    const [templates, setTemplates] = useState<BadgeTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateDialog, setShowCreateDialog] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null);
    const [editingTemplate, setEditingTemplate] = useState<BadgeTemplate | null>(null);
    const [formData, setFormData] = useState({
        name: "",
        description: "",
    });
    const [submitting, setSubmitting] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [showDesigner, setShowDesigner] = useState<string | null>(null);
    const [createStep, setCreateStep] = useState(1);
    const [newTemplateUuid, setNewTemplateUuid] = useState<string | null>(null);
    const [pendingFile, setPendingFile] = useState<File | null>(null);

    useEffect(() => {
        fetchTemplates();
    }, []);

    async function fetchTemplates() {
        try {
            const response = await getBadgeTemplates();
            setTemplates(response.results);
        } catch (error) {
            toast.error("Failed to load badge templates");
        } finally {
            setLoading(false);
        }
    }

    const handleCreateTemplate = async () => {
        if (!formData.name.trim()) {
            toast.error("Template name is required");
            return;
        }
        if (!pendingFile) {
            toast.error("Please upload a badge image");
            return;
        }

        setSubmitting(true);
        try {
            const data = new FormData();
            data.append('name', formData.name);
            data.append('description', formData.description);
            data.append('start_image', pendingFile);

            const newTemplate = await createBadgeTemplate(data);
            setTemplates([newTemplate, ...templates]);
            setShowCreateDialog(false);
            setFormData({ name: "", description: "" });
            setPendingFile(null);
            setCreateStep(1);
            toast.success("Template created successfully");
            setShowDesigner(newTemplate.uuid);
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to create template");
        } finally {
            setSubmitting(false);
        }
    };

    const handleUpdateTemplate = async () => {
        if (!editingTemplate) return;

        setSubmitting(true);
        try {
            await updateBadgeTemplate(editingTemplate.uuid, {
                name: formData.name,
                description: formData.description,
            });
            await fetchTemplates();
            setEditingTemplate(null);
            setFormData({ name: "", description: "" });
            toast.success("Template updated successfully");
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to update template");
        } finally {
            setSubmitting(false);
        }
    };

    const handleDeleteTemplate = async (uuid: string) => {
        try {
            await deleteBadgeTemplate(uuid);
            setTemplates(templates.filter(t => t.uuid !== uuid));
            setShowDeleteDialog(null);
            toast.success("Template deleted");
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to delete template");
        }
    };

    const openEditDialog = (template: BadgeTemplate) => {
        setEditingTemplate(template);
        setFormData({
            name: template.name,
            description: template.description || "",
        });
    };

    const handleFileUpload = async (templateUuid: string, file: File) => {
        setUploading(true);
        try {
            await uploadBadgeTemplateImage(templateUuid, file);
            await fetchTemplates();
            toast.success("Image uploaded successfully!");
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to upload image");
        } finally {
            setUploading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div></div>
                <Button onClick={() => setShowCreateDialog(true)}>
                    <Plus className="mr-2 h-4 w-4" /> New Badge
                </Button>
            </div>

            {templates.length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                            <Award className="h-8 w-8 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-medium text-foreground mb-2">No badges yet</h3>
                        <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
                            Create your first badge template to start issuing badges to attendees.
                        </p>
                        <Button onClick={() => setShowCreateDialog(true)}>
                            <Plus className="mr-2 h-4 w-4" /> Create Badge
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {templates.map((template) => (
                        <Card key={template.uuid} className="hover:shadow-md transition-shadow">
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className="h-10 w-10 bg-purple-100 rounded-lg flex items-center justify-center overflow-hidden">
                                            {template.start_image ? (
                                                <img src={template.start_image} alt="" className="w-full h-full object-cover" />
                                            ) : (
                                                <ImageIcon className="h-5 w-5 text-purple-600" />
                                            )}
                                        </div>
                                        <div>
                                            <CardTitle className="text-base">{template.name}</CardTitle>
                                        </div>
                                    </div>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-8 w-8">
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem onClick={() => openEditDialog(template)}>
                                                <Edit className="mr-2 h-4 w-4" /> Edit Details
                                            </DropdownMenuItem>
                                            <DropdownMenuItem
                                                onClick={() => {
                                                    const input = document.createElement('input');
                                                    input.type = 'file';
                                                    input.accept = 'image/*';
                                                    input.onchange = (e) => {
                                                        const file = (e.target as HTMLInputElement).files?.[0];
                                                        if (file) handleFileUpload(template.uuid, file);
                                                    };
                                                    input.click();
                                                }}
                                                disabled={uploading}
                                            >
                                                <Upload className="mr-2 h-4 w-4" /> Upload Image
                                            </DropdownMenuItem>
                                            <DropdownMenuItem
                                                onClick={() => setShowDesigner(template.uuid)}
                                                disabled={!template.start_image}
                                            >
                                                <Settings className="mr-2 h-4 w-4" /> Design Badge
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem
                                                className="text-red-600"
                                                onClick={() => setShowDeleteDialog(template.uuid)}
                                            >
                                                <Trash2 className="mr-2 h-4 w-4" /> Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="text-sm text-muted-foreground line-clamp-2" dangerouslySetInnerHTML={{ __html: template.description || "" }} />
                                <div className="mt-4 flex items-center justify-between text-xs text-gray-400">
                                    <span>{template.start_image ? 'Ready to issue' : 'Draft'}</span>
                                    <span>{new Date(template.created_at).toLocaleDateString()}</span>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Create Dialog */}
            <Dialog
                open={showCreateDialog || !!editingTemplate}
                onOpenChange={(open) => {
                    if (!open) {
                        setShowCreateDialog(false);
                        setEditingTemplate(null);
                        setFormData({ name: "", description: "" });
                        setCreateStep(1);
                        setNewTemplateUuid(null);
                        setPendingFile(null);
                    }
                }}
            >
                <DialogContent className="max-w-xl">
                    <DialogHeader>
                        <DialogTitle>
                            {editingTemplate ? "Edit Template" : "Create Badge Template"}
                        </DialogTitle>
                        <DialogDescription>
                            {createStep === 1 && "Start by naming your badge."}
                            {createStep === 2 && "Upload the base image for your badge."}
                        </DialogDescription>
                    </DialogHeader>

                    {createStep === 1 && (
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Badge Name *</Label>
                                <Input
                                    id="name"
                                    placeholder="e.g., Certified Expert"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="description">Description (Optional)</Label>
                                <ReactQuill
                                    theme="snow"
                                    value={formData.description}
                                    onChange={(content) => setFormData({ ...formData, description: content })}
                                    className="bg-white mb-4"
                                />
                            </div>
                        </div>
                    )}

                    {createStep === 2 && (
                        <div className="py-6">
                            <div
                                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${pendingFile ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-blue-400'
                                    }`}
                                onClick={() => {
                                    const input = document.createElement('input');
                                    input.type = 'file';
                                    input.accept = 'image/*';
                                    input.onchange = (e) => {
                                        const file = (e.target as HTMLInputElement).files?.[0];
                                        if (file) setPendingFile(file);
                                    };
                                    input.click();
                                }}
                            >
                                {pendingFile ? (
                                    <div className="space-y-2">
                                        <p className="text-green-700 font-medium">{pendingFile.name}</p>
                                        <p className="text-sm text-muted-foreground">Click to change file</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <Upload className="h-12 w-12 text-gray-400 mx-auto" />
                                        <p className="text-gray-600">Click to upload badge image (PNG/JPG)</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    <DialogFooter>
                        {createStep === 2 && (
                            <Button variant="outline" onClick={() => setCreateStep(1)}>Back</Button>
                        )}

                        <Button
                            variant="outline"
                            onClick={() => {
                                setShowCreateDialog(false);
                                setEditingTemplate(null);
                            }}
                        >
                            Cancel
                        </Button>

                        {createStep === 1 && !editingTemplate && (
                            <Button
                                onClick={() => {
                                    if (!formData.name.trim()) {
                                        toast.error("Template name is required");
                                        return;
                                    }
                                    setCreateStep(2);
                                }}
                            >
                                Next
                            </Button>
                        )}

                        {createStep === 1 && editingTemplate && (
                            <Button onClick={handleUpdateTemplate} disabled={submitting}>
                                {submitting ? "Saving..." : "Save Changes"}
                            </Button>
                        )}

                        {createStep === 2 && (
                            <Button
                                onClick={handleCreateTemplate}
                                disabled={submitting || !pendingFile}
                            >
                                {submitting ? "Creating..." : "Finish & Design"}
                            </Button>
                        )}
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation */}
            <AlertDialog
                open={!!showDeleteDialog}
                onOpenChange={() => setShowDeleteDialog(null)}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Template?</AlertDialogTitle>
                        <AlertDialogDescription>This cannot be undone.</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-red-600 hover:bg-red-700"
                            onClick={() => showDeleteDialog && handleDeleteTemplate(showDeleteDialog)}
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {showDesigner && (
                <BadgeDesigner
                    open={!!showDesigner}
                    onClose={() => setShowDesigner(null)}
                    template={templates.find(t => t.uuid === showDesigner)!}
                    onSave={fetchTemplates}
                />
            )}
        </div>
    );
}
