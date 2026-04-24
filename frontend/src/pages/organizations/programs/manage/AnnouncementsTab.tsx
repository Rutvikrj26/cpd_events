import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { Loader2, Trash2, Megaphone } from 'lucide-react';
import { format } from 'date-fns';
import {
    createProgramAnnouncement,
    deleteProgramAnnouncement,
    listProgramAnnouncements,
    type ProgramAnnouncement,
} from '@/api/programs';

export function AnnouncementsTab({ programUuid }: { programUuid: string }) {
    const { toast } = useToast();
    const [items, setItems] = useState<ProgramAnnouncement[]>([]);
    const [loading, setLoading] = useState(true);
    const [title, setTitle] = useState('');
    const [body, setBody] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const data = await listProgramAnnouncements(programUuid);
            setItems(data);
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Failed to load', description: err?.message });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [programUuid]);

    const handleCreate = async () => {
        if (!title.trim() || !body.trim()) return;
        setSubmitting(true);
        try {
            await createProgramAnnouncement(programUuid, { title: title.trim(), body: body.trim() });
            toast({ title: 'Announcement posted' });
            setTitle('');
            setBody('');
            await load();
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Post failed',
                description: err?.response?.data?.detail || err?.message,
            });
        } finally {
            setSubmitting(false);
        }
    };

    const handleDelete = async (uuid: string) => {
        if (!confirm('Delete this announcement?')) return;
        try {
            await deleteProgramAnnouncement(programUuid, uuid);
            await load();
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Delete failed', description: err?.message });
        }
    };

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>New announcement</CardTitle>
                    <CardDescription>Visible to every active program enrollee.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="space-y-1">
                        <Label htmlFor="ann-title">Title</Label>
                        <Input
                            id="ann-title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="e.g. Cohort kick-off call is Tuesday"
                        />
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="ann-body">Body</Label>
                        <Textarea
                            id="ann-body"
                            value={body}
                            onChange={(e) => setBody(e.target.value)}
                            rows={4}
                        />
                    </div>
                    <div className="flex justify-end">
                        <Button onClick={handleCreate} disabled={submitting || !title.trim() || !body.trim()}>
                            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Post announcement
                        </Button>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Posted</CardTitle>
                    <CardDescription>{items.length} announcement(s)</CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        </div>
                    ) : items.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                            <Megaphone className="h-10 w-10 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No announcements yet.</p>
                        </div>
                    ) : (
                        <div className="divide-y">
                            {items.map((a) => (
                                <div key={a.uuid} className="py-4 flex items-start justify-between gap-4">
                                    <div className="flex-1">
                                        <p className="font-medium">{a.title}</p>
                                        <p className="text-sm text-muted-foreground whitespace-pre-wrap mt-1">
                                            {a.body}
                                        </p>
                                        <p className="text-xs text-muted-foreground mt-2">
                                            Posted {format(new Date(a.created_at), 'MMM d, yyyy')}
                                            {a.created_by?.full_name ? ` by ${a.created_by.full_name}` : ''}
                                        </p>
                                    </div>
                                    <Button variant="ghost" size="sm" onClick={() => handleDelete(a.uuid)}>
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default AnnouncementsTab;
