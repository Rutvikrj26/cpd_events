import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, Layers, Loader2, Plus, Trash2, Users, Eye, ChevronUp, ChevronDown } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { EnrollmentsTab } from './manage/EnrollmentsTab';
import { AnalyticsTab } from './manage/AnalyticsTab';
import { AnnouncementsTab } from './manage/AnnouncementsTab';
import { DiscussionTab } from './manage/DiscussionTab';
import { useToast } from '@/components/ui/use-toast';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

import {
    addProgramCourse,
    archiveProgram,
    deleteProgram,
    getProgramBySlug,
    publishProgram,
    removeProgramCourse,
    syncProgramToStripe,
    updateProgram,
    updateProgramCourse,
    type Program,
} from '@/api/programs';
import { getOwnedCourses, type Course } from '@/api/courses';

const formatPrice = (cents: number, currency: string): string => {
    if (cents === 0) return 'Free';
    try {
        return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(cents / 100);
    } catch {
        return `${currency} ${(cents / 100).toFixed(2)}`;
    }
};

const ProgramManagementPage: React.FC = () => {
    const { programSlug } = useParams<{ programSlug: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();

    const [program, setProgram] = useState<Program | null>(null);
    const [loading, setLoading] = useState(true);
    const [ownedCourses, setOwnedCourses] = useState<Course[]>([]);
    const [selectedCourseUuid, setSelectedCourseUuid] = useState<string>('');
    const [isMutating, setIsMutating] = useState(false);

    const reload = async () => {
        if (!programSlug) return;
        const data = await getProgramBySlug(programSlug, true);
        setProgram(data);
    };

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            try {
                const [data, courses] = await Promise.all([
                    getProgramBySlug(programSlug!, true),
                    getOwnedCourses(),
                ]);
                if (cancelled) return;
                if (!data) {
                    navigate('/programs/manage');
                    return;
                }
                setProgram(data);
                setOwnedCourses(courses);
            } catch (err) {
                console.error('Failed to load program', err);
                toast({ variant: 'destructive', title: 'Error', description: 'Failed to load program.' });
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => {
            cancelled = true;
        };
    }, [programSlug, navigate, toast]);

    const handlePublish = async () => {
        if (!program) return;
        setIsMutating(true);
        try {
            await publishProgram(program.uuid);
            toast({ title: 'Program published' });
            await reload();
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Could not publish',
                description: err?.response?.data?.courses || err?.response?.data?.detail || 'Add at least one course first.',
            });
        } finally {
            setIsMutating(false);
        }
    };

    const handleArchive = async () => {
        if (!program) return;
        if (!confirm(
            'Archive this program? It will be hidden from discovery and no new enrollments can be created. Existing learners keep access.',
        )) return;
        setIsMutating(true);
        try {
            await archiveProgram(program.uuid);
            toast({ title: 'Program archived' });
            await reload();
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Could not archive',
                description: err?.response?.data?.detail || err?.message,
            });
        } finally {
            setIsMutating(false);
        }
    };

    const handleDelete = async () => {
        if (!program) return;
        if (!confirm('Delete this program? Courses inside will not be deleted.')) return;
        try {
            await deleteProgram(program.uuid);
            toast({ title: 'Program deleted' });
            navigate('/programs/manage');
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Delete failed', description: err?.message });
        }
    };

    const handleAddCourse = async () => {
        if (!program || !selectedCourseUuid) return;
        setIsMutating(true);
        try {
            await addProgramCourse(program.uuid, {
                course_uuid: selectedCourseUuid,
                order: program.program_courses.length + 1,
            });
            setSelectedCourseUuid('');
            await reload();
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Could not add course',
                description: err?.response?.data?.detail || err?.message,
            });
        } finally {
            setIsMutating(false);
        }
    };

    const handleRemoveCourse = async (entryUuid: string) => {
        if (!program) return;
        if (!confirm('Remove this course from the program?')) return;
        try {
            await removeProgramCourse(program.uuid, entryUuid);
            await reload();
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Remove failed', description: err?.message });
        }
    };

    const handleMove = async (entryUuid: string, direction: 'up' | 'down') => {
        if (!program) return;
        const sorted = [...program.program_courses].sort((a, b) => a.order - b.order);
        const idx = sorted.findIndex((e) => e.uuid === entryUuid);
        if (idx < 0) return;
        const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
        if (targetIdx < 0 || targetIdx >= sorted.length) return;

        const current = sorted[idx];
        const other = sorted[targetIdx];
        try {
            // Swap their order values via two PATCHes. Server stores canonical order.
            await Promise.all([
                updateProgramCourse(program.uuid, current.uuid, { order: other.order }),
                updateProgramCourse(program.uuid, other.uuid, { order: current.order }),
            ]);
            await reload();
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Reorder failed', description: err?.message });
        }
    };

    const handleToggleRequired = async (entryUuid: string, next: boolean) => {
        if (!program) return;
        try {
            await updateProgramCourse(program.uuid, entryUuid, { is_required: next });
            await reload();
        } catch (err: any) {
            toast({ variant: 'destructive', title: 'Update failed', description: err?.message });
        }
    };

    if (loading || !program) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    const memberCourseUuids = new Set(program.program_courses.map(pc => pc.course.uuid));
    const availableCourses = ownedCourses.filter(c => !memberCourseUuids.has(c.uuid));

    return (
        <div className="container mx-auto py-8 px-4 max-w-5xl">
            <Button variant="ghost" className="pl-0 mb-4" onClick={() => navigate('/programs/manage')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back to programs
            </Button>

            <div className="flex items-start justify-between mb-6 gap-4">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <h1 className="text-3xl font-bold">{program.title}</h1>
                        <Badge variant={program.status === 'published' ? 'default' : 'secondary'} className="capitalize">
                            {program.status}
                        </Badge>
                    </div>
                    {program.short_description && (
                        <p className="text-muted-foreground">{program.short_description}</p>
                    )}
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" asChild>
                        <Link to={`/programs/${program.slug}`} target="_blank">
                            <Eye className="mr-2 h-4 w-4" /> View public page
                        </Link>
                    </Button>
                    {program.status !== 'published' && (
                        <Button onClick={handlePublish} disabled={isMutating || program.course_count === 0}>
                            {program.status === 'archived' ? 'Unarchive & publish' : 'Publish'}
                        </Button>
                    )}
                    {program.status === 'published' && (
                        <Button
                            variant="outline"
                            onClick={handleArchive}
                            disabled={isMutating}
                        >
                            Archive
                        </Button>
                    )}
                </div>
            </div>

            <Tabs defaultValue="overview">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="courses">Courses ({program.course_count})</TabsTrigger>
                    <TabsTrigger value="enrollments">Enrollments ({program.enrollment_count})</TabsTrigger>
                    <TabsTrigger value="announcements">Announcements</TabsTrigger>
                    <TabsTrigger value="discussion">Discussion</TabsTrigger>
                    <TabsTrigger value="analytics">Analytics</TabsTrigger>
                    <TabsTrigger value="settings">Settings</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="mt-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard label="Courses" value={program.course_count} icon={BookOpen} />
                        <StatCard label="Enrollments" value={program.enrollment_count} icon={Users} />
                        <StatCard
                            label="Bundle savings"
                            value={formatPrice(program.bundle_savings_cents, program.currency)}
                            icon={Layers}
                        />
                    </div>
                    <Card className="mt-6">
                        <CardHeader>
                            <CardTitle>Pricing summary</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm">
                            <Row label="Bundle price" value={formatPrice(program.price_cents, program.currency)} />
                            <Row
                                label="Sum of individual course prices"
                                value={formatPrice(program.sum_individual_price_cents, program.currency)}
                            />
                            <Row
                                label="Saving vs. individual"
                                value={formatPrice(program.bundle_savings_cents, program.currency)}
                            />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="courses" className="mt-6 space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Add a course</CardTitle>
                            <CardDescription>
                                Pick from courses you own. A course can be in multiple programs.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="flex gap-2">
                            <Select value={selectedCourseUuid} onValueChange={setSelectedCourseUuid}>
                                <SelectTrigger className="flex-1">
                                    <SelectValue
                                        placeholder={availableCourses.length === 0 ? 'No courses available' : 'Choose a course'}
                                    />
                                </SelectTrigger>
                                <SelectContent>
                                    {availableCourses.map(c => (
                                        <SelectItem key={c.uuid} value={c.uuid}>
                                            {c.title} {c.status !== 'published' && `(${c.status})`}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Button
                                onClick={handleAddCourse}
                                disabled={!selectedCourseUuid || isMutating}
                            >
                                <Plus className="mr-2 h-4 w-4" /> Add
                            </Button>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Member courses</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {program.program_courses.length === 0 ? (
                                <p className="text-sm text-muted-foreground py-4 text-center">
                                    No courses yet. Add one above.
                                </p>
                            ) : (
                                <div className="divide-y">
                                    {[...program.program_courses]
                                        .sort((a, b) => a.order - b.order)
                                        .map((entry, idx, arr) => (
                                            <div
                                                key={entry.uuid}
                                                className="py-3 flex items-center justify-between gap-4"
                                            >
                                                <div className="flex items-center gap-3 min-w-0">
                                                    <div className="flex flex-col">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-5 w-5 p-0"
                                                            disabled={idx === 0}
                                                            onClick={() => handleMove(entry.uuid, 'up')}
                                                            aria-label="Move up"
                                                        >
                                                            <ChevronUp className="h-3 w-3" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            className="h-5 w-5 p-0"
                                                            disabled={idx === arr.length - 1}
                                                            onClick={() => handleMove(entry.uuid, 'down')}
                                                            aria-label="Move down"
                                                        >
                                                            <ChevronDown className="h-3 w-3" />
                                                        </Button>
                                                    </div>
                                                    <span className="font-mono text-xs text-muted-foreground w-6">
                                                        {entry.order}
                                                    </span>
                                                    <div className="min-w-0">
                                                        <Link
                                                            to={`/courses/manage/${entry.course.slug}`}
                                                            className="font-medium hover:underline truncate"
                                                        >
                                                            {entry.course.title}
                                                        </Link>
                                                        <div className="text-xs text-muted-foreground">
                                                            {formatPrice(entry.course.price_cents, entry.course.currency)}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <div className="flex items-center gap-2">
                                                        <Switch
                                                            id={`required-${entry.uuid}`}
                                                            checked={entry.is_required}
                                                            onCheckedChange={(v) => handleToggleRequired(entry.uuid, v)}
                                                        />
                                                        <Label
                                                            htmlFor={`required-${entry.uuid}`}
                                                            className="text-xs text-muted-foreground cursor-pointer"
                                                        >
                                                            Required
                                                        </Label>
                                                    </div>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleRemoveCourse(entry.uuid)}
                                                    >
                                                        <Trash2 className="h-4 w-4 text-destructive" />
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="enrollments" className="mt-6">
                    <EnrollmentsTab programUuid={program.uuid} />
                </TabsContent>

                <TabsContent value="announcements" className="mt-6">
                    <AnnouncementsTab programUuid={program.uuid} />
                </TabsContent>

                <TabsContent value="discussion" className="mt-6">
                    <DiscussionTab programUuid={program.uuid} />
                </TabsContent>

                <TabsContent value="analytics" className="mt-6">
                    <AnalyticsTab programUuid={program.uuid} />
                </TabsContent>

                <TabsContent value="settings" className="mt-6">
                    <SettingsTab program={program} onSaved={reload} onDelete={handleDelete} />
                </TabsContent>
            </Tabs>
        </div>
    );
};

const Row: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
    <div className="flex justify-between border-b py-2 last:border-b-0">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value}</span>
    </div>
);

const StatCard: React.FC<{ label: string; value: React.ReactNode; icon: React.ElementType }> = ({
    label,
    value,
    icon: Icon,
}) => (
    <Card>
        <CardContent className="pt-6 flex items-center justify-between">
            <div>
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="text-2xl font-bold">{value}</p>
            </div>
            <Icon className="h-8 w-8 text-muted-foreground/50" />
        </CardContent>
    </Card>
);

const SettingsTab: React.FC<{ program: Program; onSaved: () => void; onDelete: () => void }> = ({
    program,
    onSaved,
    onDelete,
}) => {
    const { toast } = useToast();
    const [title, setTitle] = useState(program.title);
    const [shortDescription, setShortDescription] = useState(program.short_description);
    const [description, setDescription] = useState(program.description);
    const [priceCents, setPriceCents] = useState(program.price_cents);
    const [currency, setCurrency] = useState(program.currency);
    const [isPublic, setIsPublic] = useState(program.is_public);
    const [saving, setSaving] = useState(false);
    const [syncing, setSyncing] = useState(false);

    const handleSave = async () => {
        setSaving(true);
        try {
            await updateProgram(program.uuid, {
                title,
                short_description: shortDescription,
                description,
                price_cents: Math.round(priceCents),
                currency,
                is_public: isPublic,
            });
            toast({ title: 'Saved' });
            await onSaved();
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Save failed',
                description: err?.response?.data?.detail || err?.message,
            });
        } finally {
            setSaving(false);
        }
    };

    const handleSyncStripe = async () => {
        setSyncing(true);
        try {
            await syncProgramToStripe(program.uuid);
            toast({ title: 'Synced with Stripe' });
            await onSaved();
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Sync failed',
                description:
                    err?.response?.data?.error?.message ||
                    err?.response?.data?.detail ||
                    err?.message,
            });
        } finally {
            setSyncing(false);
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Program settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <Label>Title</Label>
                    <Input value={title} onChange={e => setTitle(e.target.value)} />
                </div>
                <div className="space-y-2">
                    <Label>Short description</Label>
                    <Input
                        value={shortDescription}
                        onChange={e => setShortDescription(e.target.value)}
                        maxLength={300}
                    />
                </div>
                <div className="space-y-2">
                    <Label>Description</Label>
                    <Textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        rows={6}
                    />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label>Bundle price (cents)</Label>
                        <Input
                            type="number"
                            min={0}
                            value={priceCents}
                            onChange={e => setPriceCents(parseInt(e.target.value, 10) || 0)}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label>Currency</Label>
                        <Input value={currency} onChange={e => setCurrency(e.target.value.toUpperCase())} maxLength={3} />
                    </div>
                </div>
                <div className="flex items-center justify-between rounded-lg border p-4">
                    <div>
                        <Label className="text-base">Public visibility</Label>
                        <p className="text-sm text-muted-foreground">
                            Show in the public Programs catalog when published.
                        </p>
                    </div>
                    <Switch checked={isPublic} onCheckedChange={setIsPublic} />
                </div>

                {program.price_cents > 0 && (
                    <div className="flex items-center justify-between rounded-lg border p-4">
                        <div>
                            <Label className="text-base flex items-center gap-2">
                                Stripe sync
                                {program.stripe_price_id ? (
                                    <Badge className="bg-emerald-600">Synced</Badge>
                                ) : (
                                    <Badge variant="secondary">Not synced</Badge>
                                )}
                            </Label>
                            <p className="text-sm text-muted-foreground">
                                {program.stripe_price_id
                                    ? `Price ID: ${program.stripe_price_id}`
                                    : 'Create a Stripe Product + Price so checkout uses a canonical price record.'}
                            </p>
                        </div>
                        <Button variant="outline" onClick={handleSyncStripe} disabled={syncing}>
                            {syncing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {program.stripe_price_id ? 'Re-sync' : 'Sync now'}
                        </Button>
                    </div>
                )}

                <div className="flex justify-between pt-4">
                    <Button variant="destructive" onClick={onDelete}>
                        Delete program
                    </Button>
                    <Button onClick={handleSave} disabled={saving}>
                        {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save changes
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
};

export default ProgramManagementPage;
