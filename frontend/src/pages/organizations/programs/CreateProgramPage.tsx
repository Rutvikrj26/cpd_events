import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useToast } from '@/components/ui/use-toast';
import { createProgram } from '@/api/programs';

const CreateProgramPage: React.FC = () => {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [title, setTitle] = useState('');
    const [slug, setSlug] = useState('');
    const [shortDescription, setShortDescription] = useState('');
    const [description, setDescription] = useState('');
    const [priceCents, setPriceCents] = useState(0);
    const [currency, setCurrency] = useState('USD');
    const [isPublic, setIsPublic] = useState(true);
    const [slugTouched, setSlugTouched] = useState(false);

    const handleTitleChange = (value: string) => {
        setTitle(value);
        if (!slugTouched) {
            setSlug(
                value
                    .toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .trim()
                    .replace(/\s+/g, '-'),
            );
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        if (!title.trim() || !slug.trim()) {
            setError('Title and slug are required.');
            return;
        }
        setSubmitting(true);
        try {
            const program = await createProgram({
                title: title.trim(),
                slug: slug.trim(),
                short_description: shortDescription.trim(),
                description: description.trim(),
                price_cents: Math.round(priceCents),
                currency,
                is_public: isPublic,
            });
            toast({ title: 'Program created', description: 'Now add some courses to it.' });
            navigate(`/programs/manage/${program.slug}`);
        } catch (err: any) {
            setError(err?.response?.data?.detail || err?.message || 'Failed to create program.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="container mx-auto py-8 px-4 max-w-3xl">
            <Button variant="ghost" className="pl-0 mb-4" onClick={() => navigate('/programs/manage')}>
                <ArrowLeft className="mr-2 h-4 w-4" /> Back to programs
            </Button>
            <h1 className="text-3xl font-bold mb-1">Create new program</h1>
            <p className="text-muted-foreground mb-6">Bundle existing courses for a discounted purchase.</p>

            {error && (
                <Alert variant="destructive" className="mb-6">
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Program details</CardTitle>
                        <CardDescription>The basics learners will see.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="title">Title</Label>
                            <Input
                                id="title"
                                value={title}
                                onChange={e => handleTitleChange(e.target.value)}
                                placeholder="e.g. Advanced Leadership Track"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="slug">URL slug</Label>
                            <div className="flex items-center">
                                <span className="bg-muted px-3 py-2 border border-r-0 rounded-l-md text-muted-foreground text-sm">
                                    /programs/
                                </span>
                                <Input
                                    id="slug"
                                    className="rounded-l-none"
                                    value={slug}
                                    onChange={e => {
                                        setSlugTouched(true);
                                        setSlug(e.target.value);
                                    }}
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="shortDescription">Short description</Label>
                            <Input
                                id="shortDescription"
                                value={shortDescription}
                                onChange={e => setShortDescription(e.target.value)}
                                placeholder="One-line summary for cards (max 300 chars)"
                                maxLength={300}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="description">Full description</Label>
                            <Textarea
                                id="description"
                                value={description}
                                onChange={e => setDescription(e.target.value)}
                                rows={6}
                                placeholder="Describe what learners will get from this program."
                            />
                        </div>
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
                            <div className="space-y-2">
                                <Label htmlFor="price">Price (in cents)</Label>
                                <Input
                                    id="price"
                                    type="number"
                                    min={0}
                                    value={priceCents}
                                    onChange={e => setPriceCents(parseInt(e.target.value, 10) || 0)}
                                />
                                <p className="text-xs text-muted-foreground">Set to 0 for free.</p>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="currency">Currency</Label>
                                <Input
                                    id="currency"
                                    value={currency}
                                    onChange={e => setCurrency(e.target.value.toUpperCase())}
                                    maxLength={3}
                                />
                            </div>
                        </div>
                        <div className="flex items-center justify-between rounded-lg border p-4">
                            <div>
                                <Label htmlFor="public" className="text-base">Public visibility</Label>
                                <p className="text-sm text-muted-foreground">
                                    Show in the public Programs catalog (once published).
                                </p>
                            </div>
                            <Switch id="public" checked={isPublic} onCheckedChange={setIsPublic} />
                        </div>
                    </CardContent>
                </Card>

                <div className="flex justify-end gap-3">
                    <Button type="button" variant="outline" onClick={() => navigate('/programs/manage')}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={submitting}>
                        {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create program
                    </Button>
                </div>
            </form>
        </div>
    );
};

export default CreateProgramPage;
