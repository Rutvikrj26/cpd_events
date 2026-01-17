import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { ArrowLeft, Loader2, Save, Video } from 'lucide-react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';

import { Button } from '@/components/ui/button';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/components/ui/use-toast';
import { createCourse } from '@/api/courses';
import { getAvailableCertificateTemplates, CertificateTemplate } from '@/api/certificates';
import { getBadgeTemplates, BadgeTemplate } from '@/api/badges';
import { useOrganization } from '@/contexts/OrganizationContext';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Schema for course creation
const courseSchema = z.object({
    title: z.string().min(3, { message: 'Title must be at least 3 characters' }),
    slug: z.string().min(3, { message: 'Slug must be at least 3 characters' })
        .regex(/^[a-z0-9-]+$/, { message: 'Slug can only contain lowercase letters, numbers, and hyphens' }),
    short_description: z.string().max(300, { message: 'Short description limited to 300 characters' }).optional(),
    description: z.string().optional(),
    cpd_credits: z.coerce.number().min(0).default(0),
    is_public: z.boolean().default(true),
    price_cents: z.coerce.number().min(0).default(0),
    enrollment_open: z.boolean().default(true),
    estimated_hours: z.coerce.number().min(0).optional(),
    // Format (Online = self-paced, Hybrid = includes live sessions)
    format: z.enum(['online', 'hybrid']).default('online'),
    // Zoom fields (for Hybrid courses)
    zoom_meeting_url: z.string().url().optional().or(z.literal('')),
    zoom_meeting_id: z.string().optional(),
    zoom_meeting_password: z.string().optional(),
    // Certificate & Badge settings
    certificates_enabled: z.boolean().default(false),
    certificate_template: z.string().uuid().optional().nullable(),
    auto_issue_certificates: z.boolean().default(true),
    badges_enabled: z.boolean().default(false),
    badge_template: z.string().uuid().optional().nullable(),
    auto_issue_badges: z.boolean().default(true),
});

type CourseFormValues = z.infer<typeof courseSchema>;

const CreateCoursePage = () => {
    const { slug } = useParams<{ slug?: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const { currentOrg } = useOrganization();
    const isPersonal = !slug;

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);

    const form = useForm<CourseFormValues>({
        resolver: zodResolver(courseSchema) as any,
        defaultValues: {
            title: '',
            slug: '',
            short_description: '',
            description: '',
            cpd_credits: 0,
            is_public: true,
            price_cents: 0,
            enrollment_open: true,
            estimated_hours: 1,
            format: 'online',
            zoom_meeting_url: '',
            zoom_meeting_id: '',
            zoom_meeting_password: '',
            certificates_enabled: false,
            certificate_template: null,
            auto_issue_certificates: true,
            badges_enabled: false,
            badge_template: null,
            auto_issue_badges: true,
        },
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

    // Watch format to show/hide Zoom fields
    const courseFormat = form.watch('format');

    // Auto-generate slug from title
    const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const title = e.target.value;
        form.setValue('title', title);

        if (!form.getFieldState('slug').isTouched) {
            const generatedSlug = title
                .toLowerCase()
                .replace(/[^a-z0-9\s-]/g, '')
                .trim()
                .replace(/\s+/g, '-');
            form.setValue('slug', generatedSlug);
        }
    };

    const onSubmit = async (values: CourseFormValues) => {
        setIsSubmitting(true);
        setSubmitError(null);

        try {
            const course = await createCourse({
                ...(isPersonal ? {} : { organization_slug: slug }),
                ...values,
                // Backend computes is_free from price_cents
            });

            toast({
                title: "Course created",
                description: "Your course has been created successfully.",
            });

            // Navigate to course management/builder
            navigate(isPersonal ? `/courses/manage/${course.slug}` : `/org/${slug}/courses/${course.slug}`);

        } catch (error: any) {
            console.error('Failed to create course:', error);
            setSubmitError(error.response?.data?.message || 'Failed to create course. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="container mx-auto py-8 px-4 max-w-3xl">
            <div className="mb-6">
                <Button
                    variant="ghost"
                    className="pl-0 mb-4"
                    onClick={() => navigate(isPersonal ? `/courses/manage` : `/org/${slug}/courses`)}
                >
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Courses
                </Button>
                <h1 className="text-3xl font-bold tracking-tight">Create New Course</h1>
                <p className="text-muted-foreground mt-1">Start by defining the basics of your course.</p>
            </div>

            {submitError && (
                <Alert variant="destructive" className="mb-6">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{submitError}</AlertDescription>
                </Alert>
            )}

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">

                    <Card>
                        <CardHeader>
                            <CardTitle>Course Details</CardTitle>
                            <CardDescription>
                                Basic information about your course.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <FormField
                                control={form.control}
                                name="title"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Course Title</FormLabel>
                                        <FormControl>
                                            <Input
                                                placeholder="e.g. Advanced Leadership Principles"
                                                {...field}
                                                onChange={(e) => {
                                                    field.onChange(e);
                                                    handleTitleChange(e);
                                                }}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="slug"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>URL Slug</FormLabel>
                                        <FormControl>
                                            <div className="flex items-center">
                                                <span className="bg-muted px-3 py-2 border border-r-0 rounded-l-md text-muted-foreground text-sm">
                                                    /courses/
                                                </span>
                                                <Input className="rounded-l-none" {...field} />
                                            </div>
                                        </FormControl>
                                        <FormDescription>
                                            Unique identifier for your course URL.
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="short_description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Short Description</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Brief summary for course cards (max 300 chars)" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Full Description</FormLabel>
                                        <FormControl>
                                            <ReactQuill
                                                theme="snow"
                                                className="bg-white mb-4"
                                                {...field}
                                                onChange={(content) => field.onChange(content)}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Settings</CardTitle>
                            <CardDescription>
                                Configure accreditation and access.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <FormField
                                    control={form.control}
                                    name="cpd_credits"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>CPD Credits</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="number"
                                                    step="0.5"
                                                    min="0"
                                                    {...field}
                                                    onChange={e => field.onChange(parseFloat(e.target.value) || 0)}
                                                />
                                            </FormControl>
                                            <FormDescription>
                                                Number of credits awarded.
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <FormField
                                    control={form.control}
                                    name="estimated_hours"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Estimated Hours</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="number"
                                                    step="0.5"
                                                    min="0"
                                                    {...field}
                                                    onChange={e => field.onChange(parseFloat(e.target.value) || 0)}
                                                />
                                            </FormControl>
                                            <FormDescription>
                                                Expected time to complete.
                                            </FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <Separator />

                            <FormField
                                control={form.control}
                                name="is_public"
                                render={({ field }) => (
                                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                                        <div className="space-y-0.5">
                                            <FormLabel className="text-base">Public Visibility</FormLabel>
                                            <FormDescription>
                                                Make this course visible in your organization's public catalog.
                                            </FormDescription>
                                        </div>
                                        <FormControl>
                                            <Switch
                                                checked={field.value}
                                                onCheckedChange={field.onChange}
                                            />
                                        </FormControl>
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="enrollment_open"
                                render={({ field }) => (
                                    <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                                        <div className="space-y-0.5">
                                            <FormLabel className="text-base">Open for Enrollment</FormLabel>
                                            <FormDescription>
                                                Allow users to enroll in this course.
                                            </FormDescription>
                                        </div>
                                        <FormControl>
                                            <Switch
                                                checked={field.value}
                                                onCheckedChange={field.onChange}
                                            />
                                        </FormControl>
                                    </FormItem>
                                )}
                            />
                        </CardContent>
                    </Card>

                    {/* Format & Virtual Settings Card */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Course Format</CardTitle>
                            <CardDescription>
                                Choose how this course will be delivered.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <FormField
                                control={form.control}
                                name="format"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Delivery Format</FormLabel>
                                        <FormControl>
                                            <div className="flex gap-4">
                                                <Button
                                                    type="button"
                                                    variant={field.value === 'online' ? 'default' : 'outline'}
                                                    onClick={() => field.onChange('online')}
                                                    className="flex-1"
                                                >
                                                    Online (Self-Paced)
                                                </Button>
                                                <Button
                                                    type="button"
                                                    variant={field.value === 'hybrid' ? 'default' : 'outline'}
                                                    onClick={() => field.onChange('hybrid')}
                                                    className="flex-1"
                                                >
                                                    <Video className="mr-2 h-4 w-4" />
                                                    Hybrid (Live Sessions)
                                                </Button>
                                            </div>
                                        </FormControl>
                                        <FormDescription>
                                            Hybrid courses include scheduled live sessions via Zoom.
                                        </FormDescription>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            {/* Zoom fields - only shown for Hybrid */}
                            {courseFormat === 'hybrid' && (
                                <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
                                    <div className="flex items-center gap-2 font-medium">
                                        <Video className="h-4 w-4" />
                                        Zoom Meeting Details
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <FormField
                                            control={form.control}
                                            name="zoom_meeting_url"
                                            render={({ field }) => (
                                                <FormItem className="col-span-2">
                                                    <FormLabel>Zoom Meeting URL</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="https://zoom.us/j/..." {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                        <FormField
                                            control={form.control}
                                            name="zoom_meeting_id"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Meeting ID</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="123 456 7890" {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                        <FormField
                                            control={form.control}
                                            name="zoom_meeting_password"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Meeting Password</FormLabel>
                                                    <FormControl>
                                                        <Input placeholder="Optional password" {...field} />
                                                    </FormControl>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Recognition Settings (Certificates & Badges) */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Recognition & Completion</CardTitle>
                            <CardDescription>
                                Reward learners with certificates and badges upon completion.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Certificate Section */}
                            <div className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="certificates_enabled"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                                            <div className="space-y-0.5">
                                                <FormLabel className="text-base">Enable Certificates</FormLabel>
                                                <FormDescription>
                                                    Issue a PDF certificate when learners complete the course.
                                                </FormDescription>
                                            </div>
                                            <FormControl>
                                                <Switch
                                                    checked={field.value}
                                                    onCheckedChange={field.onChange}
                                                />
                                            </FormControl>
                                        </FormItem>
                                    )}
                                />

                                {form.watch('certificates_enabled') && (
                                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                                        <FormField
                                            control={form.control}
                                            name="certificate_template"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Certificate Template</FormLabel>
                                                    <Select
                                                        value={field.value || ''}
                                                        onValueChange={field.onChange}
                                                    >
                                                        <FormControl>
                                                            <SelectTrigger>
                                                                <SelectValue placeholder={loadingCerts ? "Loading..." : "Select a template"} />
                                                            </SelectTrigger>
                                                        </FormControl>
                                                        <SelectContent>
                                                            {certTemplates.map(t => (
                                                                <SelectItem key={t.uuid} value={t.uuid}>
                                                                    {t.name}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        <FormField
                                            control={form.control}
                                            name="auto_issue_certificates"
                                            render={({ field }) => (
                                                <FormItem className="flex flex-row items-center justify-between">
                                                    <div className="space-y-0.5">
                                                        <FormLabel>Auto-issue Certificate</FormLabel>
                                                        <FormDescription className="text-xs">
                                                            Issue automatically upon 100% course completion.
                                                        </FormDescription>
                                                    </div>
                                                    <FormControl>
                                                        <Switch
                                                            checked={field.value}
                                                            onCheckedChange={field.onChange}
                                                        />
                                                    </FormControl>
                                                </FormItem>
                                            )}
                                        />
                                    </div>
                                )}
                            </div>

                            <Separator />

                            {/* Badge Section */}
                            <div className="space-y-4">
                                <FormField
                                    control={form.control}
                                    name="badges_enabled"
                                    render={({ field }) => (
                                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                                            <div className="space-y-0.5">
                                                <FormLabel className="text-base">Enable Digital Badges</FormLabel>
                                                <FormDescription>
                                                    Award a verifiable digital badge for course completion.
                                                </FormDescription>
                                            </div>
                                            <FormControl>
                                                <Switch
                                                    checked={field.value}
                                                    onCheckedChange={field.onChange}
                                                />
                                            </FormControl>
                                        </FormItem>
                                    )}
                                />

                                {form.watch('badges_enabled') && (
                                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                                        <FormField
                                            control={form.control}
                                            name="badge_template"
                                            render={({ field }) => (
                                                <FormItem>
                                                    <FormLabel>Badge Template</FormLabel>
                                                    <Select
                                                        value={field.value || ''}
                                                        onValueChange={field.onChange}
                                                    >
                                                        <FormControl>
                                                            <SelectTrigger>
                                                                <SelectValue placeholder={loadingBadges ? "Loading..." : "Select a template"} />
                                                            </SelectTrigger>
                                                        </FormControl>
                                                        <SelectContent>
                                                            {badgeTemplates.map(t => (
                                                                <SelectItem key={t.uuid} value={t.uuid}>
                                                                    {t.name}
                                                                </SelectItem>
                                                            ))}
                                                        </SelectContent>
                                                    </Select>
                                                    <FormMessage />
                                                </FormItem>
                                            )}
                                        />

                                        <FormField
                                            control={form.control}
                                            name="auto_issue_badges"
                                            render={({ field }) => (
                                                <FormItem className="flex flex-row items-center justify-between">
                                                    <div className="space-y-0.5">
                                                        <FormLabel>Auto-issue Badge</FormLabel>
                                                        <FormDescription className="text-xs">
                                                            Issue automatically upon 100% course completion.
                                                        </FormDescription>
                                                    </div>
                                                    <FormControl>
                                                        <Switch
                                                            checked={field.value}
                                                            onCheckedChange={field.onChange}
                                                        />
                                                    </FormControl>
                                                </FormItem>
                                            )}
                                        />
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    <div className="flex justify-end gap-4">
                        <Button type="button" variant="outline" onClick={() => navigate(`/org/${slug}/courses`)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Create Course
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
};

export default CreateCoursePage;
