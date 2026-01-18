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
import { getAvailableCertificateTemplates, CertificateTemplate } from '@/api/certificates';
import { getBadgeTemplates, BadgeTemplate } from '@/api/badges';
import { Loader2, Save, Trash2, Globe, Lock, AlertTriangle } from 'lucide-react';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
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
        certificate_template: course.certificate_template || null,
        auto_issue_certificates: course.auto_issue_certificates ?? true,
        badges_enabled: course.badges_enabled ?? false,
        badge_template: course.badge_template || null,
        auto_issue_badges: course.auto_issue_badges ?? true,
    });

    const [certTemplates, setCertTemplates] = useState<CertificateTemplate[]>([]);
    const [badgeTemplates, setBadgeTemplates] = useState<BadgeTemplate[]>([]);
    const [loadingCerts, setLoadingCerts] = useState(false);
    const [loadingBadges, setLoadingBadges] = useState(false);

    // Fetch templates
    React.useEffect(() => {
        async function fetchTemplates() {
            setLoadingCerts(true);
            try {
                const response = await getAvailableCertificateTemplates();
                setCertTemplates(response.templates);
            } catch (error) {
                console.error('Failed to fetch certificate templates:', error);
            } finally {
                setLoadingCerts(false);
            }

            setLoadingBadges(true);
            try {
                const response = await getBadgeTemplates();
                setBadgeTemplates(response.results);
            } catch (error) {
                console.error('Failed to fetch badge templates:', error);
            } finally {
                setLoadingBadges(false);
            }
        }
        fetchTemplates();
    }, []);

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
        <div className="space-y-6">
            {/* Header Actions */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className="text-lg font-medium">Course Settings</h2>
                    <p className="text-sm text-muted-foreground">Manage your course details and configuration.</p>
                </div>
                <Button onClick={handleSave} disabled={saving}>
                    {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Column: Content & Pricing */}
                <div className="lg:col-span-2 space-y-6">
                    {/* General Settings */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Course Details</CardTitle>
                            <CardDescription>Basic information about your course</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                                    <p className="text-xs text-muted-foreground truncate">
                                        /courses/{formData.slug}
                                    </p>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="short_description">Short Description</Label>
                                <Textarea
                                    id="short_description"
                                    value={formData.short_description}
                                    onChange={(e) => setFormData({ ...formData, short_description: e.target.value })}
                                    rows={2}
                                    placeholder="Brief summary for cards and lists"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="description">Full Description</Label>
                                <Textarea
                                    id="description"
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    rows={6}
                                    placeholder="Detailed course description..."
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
                                <div className="flex items-center gap-4">
                                    <Input
                                        id="price"
                                        type="number"
                                        min="0"
                                        className="max-w-[200px]"
                                        value={formData.price_cents}
                                        onChange={(e) => setFormData({ ...formData, price_cents: parseInt(e.target.value) || 0 })}
                                    />
                                    <p className="text-sm font-medium">
                                        {formData.price_cents === 0 ? (
                                            <Badge variant="secondary">Free Course</Badge>
                                        ) : (
                                            `£${(formData.price_cents / 100).toFixed(2)}`
                                        )}
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Certs & Badges */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Rewards</CardTitle>
                            <CardDescription>Completion certificates and digital badges</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Certificates */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <Label className="text-base font-medium">Certificates</Label>
                                        <p className="text-sm text-muted-foreground">Issue certificates on completion</p>
                                    </div>
                                    <Switch
                                        checked={formData.certificates_enabled}
                                        onCheckedChange={(checked) => setFormData({ ...formData, certificates_enabled: checked })}
                                    />
                                </div>

                                {formData.certificates_enabled && (
                                    <div className="pl-4 border-l-2 border-primary/20 space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="certificate_template">Template</Label>
                                            <Select
                                                value={formData.certificate_template || ''}
                                                onValueChange={(val) => setFormData({ ...formData, certificate_template: val })}
                                            >
                                                <SelectTrigger id="certificate_template">
                                                    <SelectValue placeholder={loadingCerts ? "Loading..." : "Select a template"} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {certTemplates.map(t => (
                                                        <SelectItem key={t.uuid} value={t.uuid}>{t.name}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <Label className="text-sm cursor-pointer" htmlFor="auto_cert">Auto-issue upon completion</Label>
                                            <Switch
                                                id="auto_cert"
                                                checked={formData.auto_issue_certificates}
                                                onCheckedChange={(checked) => setFormData({ ...formData, auto_issue_certificates: checked })}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            <Separator />

                            {/* Badges */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="space-y-0.5">
                                        <Label className="text-base font-medium">Digital Badges</Label>
                                        <p className="text-sm text-muted-foreground">Award verifiable digital badges</p>
                                    </div>
                                    <Switch
                                        checked={formData.badges_enabled}
                                        onCheckedChange={(checked) => setFormData({ ...formData, badges_enabled: checked })}
                                    />
                                </div>

                                {formData.badges_enabled && (
                                    <div className="pl-4 border-l-2 border-primary/20 space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="badge_template">Template</Label>
                                            <Select
                                                value={formData.badge_template || ''}
                                                onValueChange={(val) => setFormData({ ...formData, badge_template: val })}
                                            >
                                                <SelectTrigger id="badge_template">
                                                    <SelectValue placeholder={loadingBadges ? "Loading..." : "Select a template"} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {badgeTemplates.map(t => (
                                                        <SelectItem key={t.uuid} value={t.uuid}>{t.name}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <Label className="text-sm cursor-pointer" htmlFor="auto_badge">Auto-issue upon completion</Label>
                                            <Switch
                                                id="auto_badge"
                                                checked={formData.auto_issue_badges}
                                                onCheckedChange={(checked) => setFormData({ ...formData, auto_issue_badges: checked })}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column: Visibility & Danger Zone */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Visibility</CardTitle>
                            <CardDescription>Control access</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label className="text-sm font-medium flex items-center gap-2">
                                        {formData.is_public ? <Globe className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
                                        Public
                                    </Label>
                                </div>
                                <Switch
                                    checked={formData.is_public}
                                    onCheckedChange={(checked) => setFormData({ ...formData, is_public: checked })}
                                />
                            </div>

                            <Separator />

                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label className="text-sm font-medium">Enrollment Open</Label>
                                </div>
                                <Switch
                                    checked={formData.enrollment_open}
                                    onCheckedChange={(checked) => setFormData({ ...formData, enrollment_open: checked })}
                                />
                            </div>

                            <div className="space-y-2 pt-2">
                                <Label htmlFor="max_enrollments">Max Enrollments</Label>
                                <Input
                                    id="max_enrollments"
                                    type="number"
                                    min="0"
                                    value={formData.max_enrollments}
                                    onChange={(e) => setFormData({ ...formData, max_enrollments: parseInt(e.target.value) || 0 })}
                                />
                                <p className="text-xs text-muted-foreground">0 = Unlimited</p>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-destructive/50">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-destructive text-base">
                                <AlertTriangle className="h-4 w-4" />
                                Danger Zone
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {course.status !== 'published' && (
                                <div className="space-y-2">
                                    <Button onClick={handlePublish} disabled={publishing} className="w-full" variant="outline">
                                        {publishing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Publish Course
                                    </Button>
                                    <p className="text-xs text-muted-foreground text-center">
                                        Make visible to learners
                                    </p>
                                </div>
                            )}

                            <div className="space-y-2">
                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button variant="destructive" className="w-full">
                                            <Trash2 className="mr-2 h-4 w-4" />
                                            Delete Course
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

                    <div className="text-xs text-muted-foreground text-center">
                        Last updated {new Date().toLocaleDateString()}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default SettingsTab;
