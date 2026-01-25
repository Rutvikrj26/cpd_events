import React, { useEffect, useState } from "react";
import { format } from "date-fns";
import { Loader2, Megaphone, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
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
    createCourseAnnouncement,
    deleteCourseAnnouncement,
    getCourseAnnouncements,
    updateCourseAnnouncement,
} from "@/api/courses";
import { CourseAnnouncement } from "@/api/courses/types";

interface AnnouncementsTabProps {
    courseUuid: string;
}

export function AnnouncementsTab({ courseUuid }: AnnouncementsTabProps) {
    const [announcements, setAnnouncements] = useState<CourseAnnouncement[]>([]);
    const [loading, setLoading] = useState(true);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingAnnouncement, setEditingAnnouncement] = useState<CourseAnnouncement | null>(null);
    const [announcementToDelete, setAnnouncementToDelete] = useState<CourseAnnouncement | null>(null);

    const [title, setTitle] = useState("");
    const [body, setBody] = useState("");
    const [isPublished, setIsPublished] = useState(true);

    const loadAnnouncements = async () => {
        setLoading(true);
        try {
            const data = await getCourseAnnouncements(courseUuid);
            setAnnouncements(data);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load announcements");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAnnouncements();
    }, [courseUuid]);

    const resetForm = () => {
        setTitle("");
        setBody("");
        setIsPublished(true);
        setEditingAnnouncement(null);
    };

    const openCreateDialog = () => {
        resetForm();
        setDialogOpen(true);
    };

    const openEditDialog = (announcement: CourseAnnouncement) => {
        setEditingAnnouncement(announcement);
        setTitle(announcement.title);
        setBody(announcement.body);
        setIsPublished(announcement.is_published);
        setDialogOpen(true);
    };

    const handleSave = async () => {
        if (!title.trim()) {
            toast.error("Title is required");
            return;
        }

        try {
            if (editingAnnouncement) {
                const updated = await updateCourseAnnouncement(courseUuid, editingAnnouncement.uuid, {
                    title,
                    body,
                    is_published: isPublished,
                });
                setAnnouncements((prev) => prev.map((item) => (item.uuid === updated.uuid ? updated : item)));
                toast.success("Announcement updated");
            } else {
                const created = await createCourseAnnouncement(courseUuid, {
                    title,
                    body,
                    is_published: isPublished,
                });
                setAnnouncements((prev) => [created, ...prev]);
                toast.success("Announcement created");
            }
            setDialogOpen(false);
            resetForm();
        } catch (error) {
            console.error(error);
            toast.error("Failed to save announcement");
        }
    };

    const handleDelete = async () => {
        if (!announcementToDelete) return;
        try {
            await deleteCourseAnnouncement(courseUuid, announcementToDelete.uuid);
            setAnnouncements((prev) => prev.filter((item) => item.uuid !== announcementToDelete.uuid));
            toast.success("Announcement deleted");
        } catch (error) {
            console.error(error);
            toast.error("Failed to delete announcement");
        } finally {
            setAnnouncementToDelete(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="text-xl font-semibold">Announcements</h2>
                    <p className="text-sm text-muted-foreground">
                        Share updates and reminders with enrolled learners.
                    </p>
                </div>
                <Button onClick={openCreateDialog}>
                    <Plus className="mr-2 h-4 w-4" />
                    New Announcement
                </Button>
            </div>

            {announcements.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                        <Megaphone className="h-12 w-12 text-muted-foreground/40 mb-4" />
                        <p className="text-muted-foreground">No announcements yet.</p>
                        <Button variant="outline" className="mt-4" onClick={openCreateDialog}>
                            Create your first announcement
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-4">
                    {announcements.map((announcement) => (
                        <Card key={announcement.uuid}>
                            <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                <div>
                                    <CardTitle className="text-base">{announcement.title}</CardTitle>
                                    <CardDescription>
                                        {format(new Date(announcement.created_at), "MMM d, yyyy")}
                                        {announcement.created_by_name ? ` - ${announcement.created_by_name}` : ""}
                                    </CardDescription>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Badge variant={announcement.is_published ? "default" : "secondary"}>
                                        {announcement.is_published ? "Published" : "Draft"}
                                    </Badge>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => openEditDialog(announcement)}
                                    >
                                        <Pencil className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="text-red-500 hover:text-red-600"
                                        onClick={() => setAnnouncementToDelete(announcement)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent className="text-sm text-muted-foreground whitespace-pre-wrap">
                                {announcement.body || "No message provided."}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            <Dialog open={dialogOpen} onOpenChange={(open) => {
                if (!open) {
                    resetForm();
                }
                setDialogOpen(open);
            }}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>{editingAnnouncement ? "Edit Announcement" : "New Announcement"}</DialogTitle>
                        <DialogDescription>
                            Draft announcements can be published later for learners.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-2">
                            <Label htmlFor="announcement-title">Title</Label>
                            <Input
                                id="announcement-title"
                                value={title}
                                onChange={(event) => setTitle(event.target.value)}
                                placeholder="Course update"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="announcement-body">Message</Label>
                            <Textarea
                                id="announcement-body"
                                value={body}
                                onChange={(event) => setBody(event.target.value)}
                                placeholder="Share important context or reminders..."
                                className="min-h-[160px]"
                            />
                        </div>
                        <div className="flex items-center justify-between border rounded-lg px-3 py-2">
                            <div>
                                <Label htmlFor="announcement-published" className="text-sm font-medium">
                                    Publish now
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                    Learners can see published announcements in the course player.
                                </p>
                            </div>
                            <Switch
                                id="announcement-published"
                                checked={isPublished}
                                onCheckedChange={setIsPublished}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleSave}>
                            {editingAnnouncement ? "Save Changes" : "Create Announcement"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog open={!!announcementToDelete} onOpenChange={(open) => !open && setAnnouncementToDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete this announcement?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. Learners will no longer see this message.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setAnnouncementToDelete(null)}>Cancel</AlertDialogCancel>
                        <AlertDialogAction className="bg-red-600 hover:bg-red-700" onClick={handleDelete}>
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

export default AnnouncementsTab;
