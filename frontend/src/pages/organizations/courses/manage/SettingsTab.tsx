import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { updateCourse, deleteCourse, publishCourse } from '@/api/courses';
import { Course } from '@/api/courses/types';
import { Loader2, Save, Trash2, Globe, Lock, AlertTriangle } from 'lucide-react';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

interface SettingsTabProps {
    course: Course;
    onCourseUpdated: (course: Course) => void;
    organizationSlug?: string;
}

export function SettingsTab({ course, onCourseUpdated, organizationSlug }: SettingsTabProps) {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [publishing, setPublishing] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        title: course.title,
        slug: course.slug,
        short_description: course.short_description || '',
        description: course.description || '',
        cpd_credits: typeof course.cpd_credits === 'string'
            ? parseFloat(course.cpd_credits) || 0
            : (course.cpd_credits ?? 0),
        estimated_hours: typeof course.estimated_hours === 'string'
            ? parseFloat(course.estimated_hours) || 0
            : (course.estimated_hours ?? 0),
        price_cents: course.price_cents ?? 0,
        is_public: course.is_public ?? true,
        enrollment_open: course.enrollment_open ?? true,
        max_enrollments: course.max_enrollments ?? 0,
        certificates_enabled: course.certificates_enabled ?? false,
    });

    const handleSave = async () => {
        setSaving(true);
        try {
            const updated = await updateCourse(course.uuid, formData);
            onCourseUpdated(updated);
            toast({
                title: 'Settings saved',
                description: 'Course settings have been updated.',
            });
        } catch (error: any) {
            console.error('Failed to save:', error);
            toast({
                variant: 'destructive',
                title: 'Error',
                description: error.response?.data?.message || 'Failed to save settings.',
            });
        } finally {
            setSaving(false);
        }
    };

    const handlePublish = async () => {
        setPublishing(true);
        try {
            const updated = await publishCourse(course.uuid);
            onCourseUpdated({ ...course, status: 'published' });
            toast({
                title: 'Course published',
                description: 'Your course is now live!',
            });
        } catch (error: any) {
            console.error('Failed to publish:', error);
            toast({
                variant: 'destructive',
                title: 'Error',
                description: error.response?.data?.message || 'Failed to publish course.',
            });
        } finally {
            setPublishing(false);
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await deleteCourse(course.uuid);
            toast({
                title: 'Course deleted',
                description: 'The course has been deleted.',
            });
            navigate(organizationSlug ? `/org/${organizationSlug}/courses` : '/courses/manage');
        } catch (error: any) {
            console.error('Failed to delete:', error);
            toast({
                variant: 'destructive',
                title: 'Error',
                description: error.response?.data?.message || 'Failed to delete course.',
            });
            setDeleting(false);
        }
    };

    return (
        <div className="space-y-6 max-w-3xl">
            {/* General Settings */}
            <Card>
                <CardHeader>
                    <CardTitle>General Settings</CardTitle>
                    <CardDescription>Update your course details</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="title">Course Title</Label>
                        <Input
                            id="title"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="slug">URL Slug</Label>
                        <Input
                            id="slug"
                            value={formData.slug}
                            onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                        />
                        <p className="text-xs text-muted-foreground">
                            Will appear as: /courses/{formData.slug}
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="short_description">Short Description</Label>
                        <Textarea
                            id="short_description"
                            value={formData.short_description}
                            onChange={(e) => setFormData({ ...formData, short_description: e.target.value })}
                            rows={3}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="cpd_credits">CPD Credits</Label>
                            <Input
                                id="cpd_credits"
                                type="number"
                                min="0"
                                step="0.5"
                                value={formData.cpd_credits}
                                onChange={(e) => setFormData({ ...formData, cpd_credits: parseFloat(e.target.value) || 0 })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="estimated_hours">Estimated Hours</Label>
                            <Input
                                id="estimated_hours"
                                type="number"
                                min="0"
                                step="0.5"
                                value={formData.estimated_hours}
                                onChange={(e) => setFormData({ ...formData, estimated_hours: parseFloat(e.target.value) || 0 })}
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Pricing */}
            <Card>
                <CardHeader>
                    <CardTitle>Pricing</CardTitle>
                    <CardDescription>Set your course price</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="price">Price (in pence/cents)</Label>
                        <Input
                            id="price"
                            type="number"
                            min="0"
                            value={formData.price_cents}
                            onChange={(e) => setFormData({ ...formData, price_cents: parseInt(e.target.value) || 0 })}
                        />
                        <p className="text-xs text-muted-foreground">
                            {formData.price_cents === 0 ? 'Free course' : `£${(formData.price_cents / 100).toFixed(2)}`}
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Access & Enrollment */}
            <Card>
                <CardHeader>
                    <CardTitle>Access & Enrollment</CardTitle>
                    <CardDescription>Control who can access your course</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-base flex items-center gap-2">
                                {formData.is_public ? <Globe className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
                                Public Visibility
                            </Label>
                            <p className="text-sm text-muted-foreground">
                                Show this course in your public catalog
                            </p>
                        </div>
                        <Switch
                            checked={formData.is_public}
                            onCheckedChange={(checked) => setFormData({ ...formData, is_public: checked })}
                        />
                    </div>

                    <Separator />

                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-base">Open for Enrollment</Label>
                            <p className="text-sm text-muted-foreground">
                                Allow new users to enroll
                            </p>
                        </div>
                        <Switch
                            checked={formData.enrollment_open}
                            onCheckedChange={(checked) => setFormData({ ...formData, enrollment_open: checked })}
                        />
                    </div>

                    <Separator />

                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-base">Certificates Enabled</Label>
                            <p className="text-sm text-muted-foreground">
                                Issue certificates on completion
                            </p>
                        </div>
                        <Switch
                            checked={formData.certificates_enabled}
                            onCheckedChange={(checked) => setFormData({ ...formData, certificates_enabled: checked })}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="max_enrollments">Maximum Enrollments</Label>
                        <Input
                            id="max_enrollments"
                            type="number"
                            min="0"
                            value={formData.max_enrollments}
                            onChange={(e) => setFormData({ ...formData, max_enrollments: parseInt(e.target.value) || 0 })}
                        />
                        <p className="text-xs text-muted-foreground">
                            Set to 0 for unlimited
                        </p>
                    </div>
                </CardContent>
                <CardFooter>
                    <Button onClick={handleSave} disabled={saving}>
                        {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        <Save className="mr-2 h-4 w-4" />
                        Save Changes
                    </Button>
                </CardFooter>
            </Card>

            {/* Publishing / Danger Zone */}
            <Card className="border-destructive/50">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-destructive">
                        <AlertTriangle className="h-5 w-5" />
                        Danger Zone
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {course.status !== 'published' && (
                        <div className="flex items-center justify-between p-4 border rounded-lg">
                            <div>
                                <p className="font-medium">Publish Course</p>
                                <p className="text-sm text-muted-foreground">
                                    Make this course visible to learners
                                </p>
                            </div>
                            <Button onClick={handlePublish} disabled={publishing}>
                                {publishing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Publish
                            </Button>
                        </div>
                    )}

                    <div className="flex items-center justify-between p-4 border border-destructive/30 rounded-lg">
                        <div>
                            <p className="font-medium text-destructive">Delete Course</p>
                            <p className="text-sm text-muted-foreground">
                                Permanently delete this course and all enrollments
                            </p>
                        </div>
                        <AlertDialog>
                            <AlertDialogTrigger asChild>
                                <Button variant="destructive">
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Delete
                                </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                                <AlertDialogHeader>
                                    <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                                    <AlertDialogDescription>
                                        This will permanently delete "{course.title}" and all associated data including enrollments. This action cannot be undone.
                                    </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction onClick={handleDelete} disabled={deleting}>
                                        {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Delete Course
                                    </AlertDialogAction>
                                </AlertDialogFooter>
                            </AlertDialogContent>
                        </AlertDialog>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

export default SettingsTab;
