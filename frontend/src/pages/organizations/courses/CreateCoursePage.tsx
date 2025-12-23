import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { createCourse } from '@/api/courses';
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
    is_free: z.boolean().default(true),
    price_cents: z.coerce.number().min(0).default(0),
    enrollment_open: z.boolean().default(true),
    estimated_hours: z.coerce.number().min(0).optional(),
});

type CourseFormValues = any;

const CreateCoursePage = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const { currentOrg } = useOrganization();

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
            is_free: true,
            price_cents: 0,
            enrollment_open: true,
            estimated_hours: 1,
        },
    });

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
        if (!slug) return;

        setIsSubmitting(true);
        setSubmitError(null);

        try {
            const course = await createCourse({
                organization_slug: slug,
                ...values,
                // Ensure numbers are numbers
                price_cents: values.is_free ? 0 : values.price_cents,
            });

            toast({
                title: "Course created",
                description: "Your course has been created successfully.",
            });

            // Navigate to course management/builder
            navigate(`/org/${slug}/courses/${course.slug}`);

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
                <Button variant="ghost" className="pl-0 mb-4" onClick={() => navigate(`/org/${slug}/courses`)}>
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
