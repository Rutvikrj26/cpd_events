import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Textarea } from '@/shared/ui/textarea';
import { Switch } from '@/shared/ui/switch';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/shared/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/shared/ui/alert';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/shared/ui/form';
import { useToast } from '@/shared/ui/use-toast';
import { useZodForm } from '@/shared/lib/forms';
import {
    createProgramSchema,
    useCreateProgram,
    type CreateProgramFormValues,
} from '@/features/programs';

const CreateProgramPage: React.FC = () => {
    const navigate = useNavigate();
    const { toast } = useToast();
    const createProgram = useCreateProgram();
    const [submitError, setSubmitError] = React.useState<string | null>(null);

    const form = useZodForm(createProgramSchema, {
        defaultValues: {
            title: '',
            slug: '',
            short_description: '',
            description: '',
            price_cents: 0,
            currency: 'USD',
            is_public: true,
        },
    });

    // Auto-generate slug from title until the slug field is touched manually.
    const handleTitleChange = (value: string) => {
        form.setValue('title', value, { shouldValidate: true });
        if (!form.getFieldState('slug').isTouched) {
            const generated = value
                .toLowerCase()
                .replace(/[^a-z0-9\s-]/g, '')
                .trim()
                .replace(/\s+/g, '-');
            form.setValue('slug', generated, { shouldValidate: true });
        }
    };

    const onSubmit = async (values: CreateProgramFormValues) => {
        setSubmitError(null);
        try {
            const program = await createProgram.mutateAsync({
                title: values.title.trim(),
                slug: values.slug.trim(),
                short_description: values.short_description?.trim() || '',
                description: values.description?.trim() || '',
                price_cents: Math.round(values.price_cents),
                currency: values.currency,
                is_public: values.is_public,
            });
            toast({
                title: 'Program created',
                description: 'Now add some courses to it.',
            });
            navigate(`/programs/manage/${program.slug}`);
        } catch (err: any) {
            setSubmitError(
                err?.response?.data?.detail || err?.message || 'Failed to create program.',
            );
        }
    };

    const submitting = createProgram.isPending || form.formState.isSubmitting;

    return (
        <div className="container mx-auto py-8 px-4 max-w-3xl">
            <Button variant="ghost" className="pl-0 mb-4" onClick={() => navigate('/programs/manage')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back to programs
            </Button>
            <h1 className="text-3xl font-bold mb-1">Create new program</h1>
            <p className="text-muted-foreground mb-6">Bundle existing courses for a discounted purchase.</p>

            {submitError && (
                <Alert variant="destructive" className="mb-6">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{submitError}</AlertDescription>
                </Alert>
            )}

            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Program details</CardTitle>
                            <CardDescription>The basics learners will see.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <FormField
                                control={form.control as any}
                                name="title"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Title</FormLabel>
                                        <FormControl>
                                            <Input
                                                placeholder="e.g. Advanced Leadership Track"
                                                {...field}
                                                onChange={(e) => handleTitleChange(e.target.value)}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control as any}
                                name="slug"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>URL slug</FormLabel>
                                        <FormControl>
                                            <div className="flex items-center">
                                                <span className="bg-muted px-3 py-2 border border-r-0 rounded-l-md text-muted-foreground text-sm">
                                                    /programs/
                                                </span>
                                                <Input className="rounded-l-none" {...field} />
                                            </div>
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control as any}
                                name="short_description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Short description</FormLabel>
                                        <FormControl>
                                            <Input
                                                placeholder="One-line summary for cards (max 300 chars)"
                                                maxLength={300}
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control as any}
                                name="description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Full description</FormLabel>
                                        <FormControl>
                                            <Textarea
                                                rows={6}
                                                placeholder="Describe what learners will get from this program."
                                                {...field}
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
                            <CardTitle>Bundle pricing</CardTitle>
                            <CardDescription>
                                Set a single price for the whole bundle. Learners can still buy each course individually.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control as any}
                                    name="price_cents"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Price (in cents)</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="number"
                                                    min={0}
                                                    {...field}
                                                    onChange={(e) =>
                                                        field.onChange(parseInt(e.target.value, 10) || 0)
                                                    }
                                                />
                                            </FormControl>
                                            <FormDescription>Set to 0 for free.</FormDescription>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control as any}
                                    name="currency"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Currency</FormLabel>
                                            <FormControl>
                                                <Input
                                                    maxLength={3}
                                                    {...field}
                                                    onChange={(e) =>
                                                        field.onChange(e.target.value.toUpperCase())
                                                    }
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control as any}
                                name="is_public"
                                render={({ field }) => (
                                    <FormItem className="flex items-center justify-between rounded-lg border p-4 space-y-0">
                                        <div>
                                            <FormLabel className="text-base">Public visibility</FormLabel>
                                            <FormDescription>
                                                Show in the public Programs catalog (once published).
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

                    <div className="flex justify-end gap-3">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => navigate('/programs/manage')}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={submitting}>
                            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Create program
                        </Button>
                    </div>
                </form>
            </Form>
        </div>
    );
};

export default CreateProgramPage;
