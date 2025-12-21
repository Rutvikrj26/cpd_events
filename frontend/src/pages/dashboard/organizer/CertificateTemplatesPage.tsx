import React, { useState, useEffect } from "react";
import {
    Plus,
    MoreHorizontal,
    Star,
    Trash2,
    Edit,
    Copy,
    Award,
    Loader2,
    FileText
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
import { PageHeader } from "@/components/custom/PageHeader";
import {
    getCertificateTemplates,
    createCertificateTemplate,
    updateCertificateTemplate,
    deleteCertificateTemplate,
    setDefaultTemplate
} from "@/api/certificates";
import { CertificateTemplate } from "@/api/certificates/types";
import { toast } from "sonner";

export function CertificateTemplatesPage() {
    const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateDialog, setShowCreateDialog] = useState(false);
    const [showDeleteDialog, setShowDeleteDialog] = useState<string | null>(null);
    const [editingTemplate, setEditingTemplate] = useState<CertificateTemplate | null>(null);
    const [formData, setFormData] = useState({
        name: "",
        description: "",
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        fetchTemplates();
    }, []);

    async function fetchTemplates() {
        try {
            const data = await getCertificateTemplates();
            setTemplates(data);
        } catch (error) {
            toast.error("Failed to load certificate templates");
        } finally {
            setLoading(false);
        }
    }

    const handleCreateTemplate = async () => {
        if (!formData.name.trim()) {
            toast.error("Template name is required");
            return;
        }

        setSubmitting(true);
        try {
            const newTemplate = await createCertificateTemplate({
                name: formData.name,
                description: formData.description,
            });
            setTemplates([newTemplate, ...templates]);
            setShowCreateDialog(false);
            setFormData({ name: "", description: "" });
            toast.success("Template created successfully");
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
            await updateCertificateTemplate(editingTemplate.uuid, {
                name: formData.name,
                description: formData.description,
            });
            // Refetch to get latest data
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
            await deleteCertificateTemplate(uuid);
            setTemplates(templates.filter(t => t.uuid !== uuid));
            setShowDeleteDialog(null);
            toast.success("Template deleted");
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to delete template");
        }
    };

    const handleSetDefault = async (uuid: string) => {
        try {
            await setDefaultTemplate(uuid);
            setTemplates(templates.map(t => ({
                ...t,
                is_default: t.uuid === uuid
            })));
            toast.success("Default template updated");
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to set default");
        }
    };

    const openEditDialog = (template: CertificateTemplate) => {
        setEditingTemplate(template);
        setFormData({
            name: template.name,
            description: template.description || "",
        });
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
            <PageHeader
                title="Certificate Templates"
                description="Create and manage certificate templates for your events."
                actions={
                    <Button onClick={() => setShowCreateDialog(true)}>
                        <Plus className="mr-2 h-4 w-4" /> New Template
                    </Button>
                }
            />

            {templates.length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <div className="h-16 w-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Award className="h-8 w-8 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No templates yet</h3>
                        <p className="text-gray-500 mb-6 max-w-sm mx-auto">
                            Create your first certificate template to start issuing certificates to attendees.
                        </p>
                        <Button onClick={() => setShowCreateDialog(true)}>
                            <Plus className="mr-2 h-4 w-4" /> Create Template
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
                                        <div className="h-10 w-10 bg-amber-100 rounded-lg flex items-center justify-center">
                                            <FileText className="h-5 w-5 text-amber-600" />
                                        </div>
                                        <div>
                                            <CardTitle className="text-base flex items-center gap-2">
                                                {template.name}
                                                {template.is_default && (
                                                    <Badge variant="secondary" className="text-xs">
                                                        <Star className="h-3 w-3 mr-1" /> Default
                                                    </Badge>
                                                )}
                                            </CardTitle>
                                            <CardDescription className="text-xs">
                                                Used {template.usage_count || 0} times
                                            </CardDescription>
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
                                                <Edit className="mr-2 h-4 w-4" /> Edit
                                            </DropdownMenuItem>
                                            {!template.is_default && (
                                                <DropdownMenuItem onClick={() => handleSetDefault(template.uuid)}>
                                                    <Star className="mr-2 h-4 w-4" /> Set as Default
                                                </DropdownMenuItem>
                                            )}
                                            <DropdownMenuItem>
                                                <Copy className="mr-2 h-4 w-4" /> Duplicate
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
                                <p className="text-sm text-gray-500 line-clamp-2">
                                    {template.description || "No description"}
                                </p>
                                <div className="mt-4 flex items-center justify-between text-xs text-gray-400">
                                    <span>v{template.version || 1}</span>
                                    <span>{new Date(template.created_at).toLocaleDateString()}</span>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Create/Edit Dialog */}
            <Dialog
                open={showCreateDialog || !!editingTemplate}
                onOpenChange={(open) => {
                    if (!open) {
                        setShowCreateDialog(false);
                        setEditingTemplate(null);
                        setFormData({ name: "", description: "" });
                    }
                }}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {editingTemplate ? "Edit Template" : "Create Certificate Template"}
                        </DialogTitle>
                        <DialogDescription>
                            {editingTemplate
                                ? "Update the template details."
                                : "Create a new certificate template for your events."}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Template Name *</Label>
                            <Input
                                id="name"
                                placeholder="e.g., Standard CPD Certificate"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="description">Description</Label>
                            <Textarea
                                id="description"
                                placeholder="Describe when this template should be used..."
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                rows={3}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setShowCreateDialog(false);
                                setEditingTemplate(null);
                                setFormData({ name: "", description: "" });
                            }}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={editingTemplate ? handleUpdateTemplate : handleCreateTemplate}
                            disabled={submitting}
                        >
                            {submitting ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : null}
                            {editingTemplate ? "Save Changes" : "Create Template"}
                        </Button>
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
                        <AlertDialogDescription>
                            This action cannot be undone. Templates that have been used to issue certificates cannot be deleted.
                        </AlertDialogDescription>
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
        </div>
    );
}
