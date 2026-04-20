import { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, Loader2, Tag as TagIcon } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Tag,
    createTag,
    deleteTag,
    getTags,
    updateTag,
} from '@/api/contacts';

const PRESET_COLORS = ['#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#6B7280'];

export function TagLibraryPage() {
    const [tags, setTags] = useState<Tag[]>([]);
    const [loading, setLoading] = useState(true);
    const [editingTag, setEditingTag] = useState<Tag | null>(null);
    const [showCreate, setShowCreate] = useState(false);
    const [pendingDelete, setPendingDelete] = useState<Tag | null>(null);

    const refresh = async () => {
        try {
            const resp = await getTags();
            setTags(resp.results);
        } catch {
            toast.error('Failed to load tags');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        refresh();
    }, []);

    const handleDelete = async () => {
        if (!pendingDelete) return;
        try {
            await deleteTag(pendingDelete.uuid);
            toast.success(`Tag "${pendingDelete.name}" deleted`);
            setPendingDelete(null);
            await refresh();
        } catch {
            toast.error('Failed to delete tag');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Tags</h1>
                    <p className="text-sm text-muted-foreground">
                        Organize contacts into segments for import, invitation, and re-engagement.
                    </p>
                </div>
                <Button onClick={() => setShowCreate(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    New Tag
                </Button>
            </div>

            {tags.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center space-y-3">
                        <TagIcon className="h-10 w-10 mx-auto text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">No tags yet.</p>
                        <Button variant="outline" onClick={() => setShowCreate(true)}>
                            Create your first tag
                        </Button>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">{tags.length} tag{tags.length === 1 ? '' : 's'}</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="divide-y">
                            {tags.map((tag) => (
                                <div key={tag.uuid} className="flex items-center gap-3 px-4 py-3">
                                    <div
                                        className="w-4 h-4 rounded-full shrink-0 border"
                                        style={{ backgroundColor: tag.color || '#888' }}
                                    />
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium text-sm truncate">{tag.name}</div>
                                        {tag.description && (
                                            <div className="text-xs text-muted-foreground truncate">{tag.description}</div>
                                        )}
                                    </div>
                                    <div className="text-xs text-muted-foreground shrink-0 w-20 text-right">
                                        {tag.contact_count} contact{tag.contact_count === 1 ? '' : 's'}
                                    </div>
                                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setEditingTag(tag)}>
                                        <Edit2 className="h-3.5 w-3.5" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-8 w-8 text-destructive hover:text-destructive"
                                        onClick={() => setPendingDelete(tag)}
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {(showCreate || editingTag) && (
                <TagEditDialog
                    open
                    tag={editingTag}
                    onClose={() => {
                        setShowCreate(false);
                        setEditingTag(null);
                    }}
                    onSaved={() => {
                        setShowCreate(false);
                        setEditingTag(null);
                        refresh();
                    }}
                />
            )}

            <AlertDialog open={!!pendingDelete} onOpenChange={(o) => !o && setPendingDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete this tag?</AlertDialogTitle>
                        <AlertDialogDescription>
                            {pendingDelete?.contact_count
                                ? `"${pendingDelete?.name}" is applied to ${pendingDelete?.contact_count} contact${pendingDelete?.contact_count === 1 ? '' : 's'}. Deleting will unapply it — contacts are not removed.`
                                : `"${pendingDelete?.name}" will be permanently deleted.`}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleDelete} className="bg-destructive hover:bg-destructive/90">
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

interface TagEditDialogProps {
    open: boolean;
    tag: Tag | null;
    onClose: () => void;
    onSaved: () => void;
}

function TagEditDialog({ open, tag, onClose, onSaved }: TagEditDialogProps) {
    const isEdit = !!tag;
    const [name, setName] = useState(tag?.name ?? '');
    const [color, setColor] = useState(tag?.color || PRESET_COLORS[0]);
    const [description, setDescription] = useState(tag?.description ?? '');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        setName(tag?.name ?? '');
        setColor(tag?.color || PRESET_COLORS[0]);
        setDescription(tag?.description ?? '');
    }, [tag]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim()) {
            toast.error('Name is required');
            return;
        }
        setSaving(true);
        try {
            if (isEdit && tag) {
                await updateTag(tag.uuid, { name: name.trim(), color, description: description.trim() });
                toast.success('Tag updated');
            } else {
                await createTag({ name: name.trim(), color, description: description.trim() });
                toast.success('Tag created');
            }
            onSaved();
        } catch (err: any) {
            toast.error(err?.response?.data?.error?.message || 'Failed to save tag');
        } finally {
            setSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
            <DialogContent className="max-w-md">
                <form onSubmit={handleSave}>
                    <DialogHeader>
                        <DialogTitle>{isEdit ? 'Edit Tag' : 'New Tag'}</DialogTitle>
                        <DialogDescription>
                            Tags let you segment contacts for targeted invitations and re-engagement.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="tag-name">Name *</Label>
                            <Input
                                id="tag-name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., Q2 Conference Attendees"
                                disabled={saving}
                                autoFocus
                            />
                        </div>

                        <div className="space-y-2">
                            <Label>Color</Label>
                            <div className="flex items-center gap-2 flex-wrap">
                                {PRESET_COLORS.map((c) => (
                                    <button
                                        type="button"
                                        key={c}
                                        onClick={() => setColor(c)}
                                        className={`w-8 h-8 rounded-full border-2 transition-all ${
                                            color === c ? 'border-foreground scale-110' : 'border-transparent'
                                        }`}
                                        style={{ backgroundColor: c }}
                                        aria-label={`Color ${c}`}
                                    />
                                ))}
                                <input
                                    type="color"
                                    value={color}
                                    onChange={(e) => setColor(e.target.value)}
                                    className="w-8 h-8 rounded cursor-pointer"
                                    aria-label="Custom color"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="tag-description">Description</Label>
                            <Textarea
                                id="tag-description"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Optional — when to use this tag"
                                rows={2}
                                disabled={saving}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={saving || !name.trim()}>
                            {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                            {isEdit ? 'Save' : 'Create'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
