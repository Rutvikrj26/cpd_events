import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, BookOpen, CheckCircle, Layers, Loader2, TrendingDown } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Separator } from '@/shared/ui/separator';
import { useToast } from '@/shared/ui/use-toast';
import { useAuth } from '@/features/auth';
import {
    getProgramBySlug,
    programCheckout,
    programEnrollFree,
    type Program,
} from '@/api/programs';

const formatPrice = (cents: number, currency: string): string => {
    if (cents === 0) return 'Free';
    const value = cents / 100;
    try {
        return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value);
    } catch {
        return `${currency} ${value.toFixed(2)}`;
    }
};

export const PublicProgramDetailPage: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const { isAuthenticated } = useAuth();

    const [program, setProgram] = useState<Program | null>(null);
    const [loading, setLoading] = useState(true);
    const [checkoutLoading, setCheckoutLoading] = useState(false);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            if (!slug) return;
            setLoading(true);
            try {
                const data = await getProgramBySlug(slug);
                if (cancelled) return;
                if (!data) {
                    navigate('/programs');
                    return;
                }
                setProgram(data);
            } catch (err) {
                console.error('Failed to load program', err);
                toast({
                    variant: 'destructive',
                    title: 'Error',
                    description: 'Failed to load program details.',
                });
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => {
            cancelled = true;
        };
    }, [slug, navigate, toast]);

    const sortedCourses = useMemo(
        () => [...(program?.program_courses ?? [])].sort((a, b) => a.order - b.order),
        [program],
    );

    const handleFreeEnroll = async () => {
        if (!program) return;
        if (!isAuthenticated) {
            navigate(`/login?next=/programs/${program.slug}`);
            return;
        }
        setCheckoutLoading(true);
        try {
            await programEnrollFree(program.uuid);
            toast({
                title: 'Enrolled',
                description: 'You are enrolled in every course in this program.',
            });
            navigate('/my-programs');
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Enrollment failed',
                description:
                    err?.response?.data?.error?.message ||
                    err?.message ||
                    'Could not enroll.',
            });
        } finally {
            setCheckoutLoading(false);
        }
    };

    const handleBundlePurchase = async () => {
        if (!program) return;
        if (!isAuthenticated) {
            navigate(`/login?next=/programs/${program.slug}`);
            return;
        }
        setCheckoutLoading(true);
        try {
            const successUrl = `${window.location.origin}/programs/${program.slug}?purchased=1`;
            const cancelUrl = `${window.location.origin}/programs/${program.slug}`;
            const result = await programCheckout(program.uuid, successUrl, cancelUrl);
            if (result.url) {
                window.location.href = result.url;
            } else {
                toast({
                    variant: 'destructive',
                    title: 'Checkout error',
                    description: result.error || 'Could not start checkout.',
                });
            }
        } catch (err: any) {
            toast({
                variant: 'destructive',
                title: 'Checkout error',
                description:
                    err?.response?.data?.error?.message ||
                    err?.response?.data?.detail ||
                    err?.message ||
                    'Could not start checkout.',
            });
        } finally {
            setCheckoutLoading(false);
        }
    };

    if (loading || !program) {
        return (
            <div className="flex items-center justify-center min-h-[40vh]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8 px-4 max-w-6xl space-y-8">
            {/* Header */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                    <Badge variant="secondary" className="w-fit">
                        <Layers className="mr-1 h-3 w-3" /> Program
                    </Badge>
                    <h1 className="text-3xl md:text-4xl font-bold">{program.title}</h1>
                    {program.short_description && (
                        <p className="text-lg text-muted-foreground">{program.short_description}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                            <BookOpen className="h-4 w-4" />
                            {program.course_count} course{program.course_count === 1 ? '' : 's'}
                        </span>
                        {program.enrollment_count > 0 && (
                            <span>{program.enrollment_count} enrolled</span>
                        )}
                    </div>
                </div>

                {/* Pricing card */}
                <Card className="self-start sticky top-6">
                    <CardHeader>
                        <CardTitle className="text-2xl">
                            {formatPrice(program.price_cents, program.currency)}
                        </CardTitle>
                        {program.bundle_savings_cents > 0 && (
                            <div className="flex items-center gap-2 text-sm">
                                <span className="line-through text-muted-foreground">
                                    {formatPrice(program.sum_individual_price_cents, program.currency)}
                                </span>
                                <Badge variant="default" className="bg-green-100 text-green-800 hover:bg-green-100">
                                    <TrendingDown className="mr-1 h-3 w-3" />
                                    Save {formatPrice(program.bundle_savings_cents, program.currency)}
                                </Badge>
                            </div>
                        )}
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {program.viewer_enrollment ? (
                            program.viewer_enrollment.status === 'completed' ? (
                                <>
                                    <Badge
                                        variant="default"
                                        className="w-full justify-center bg-green-100 text-green-800 hover:bg-green-100 py-2"
                                    >
                                        <CheckCircle className="mr-1 h-3.5 w-3.5" />
                                        Completed
                                    </Badge>
                                    <Button asChild className="w-full" size="lg" variant="outline">
                                        <Link to="/my-programs">View progress</Link>
                                    </Button>
                                </>
                            ) : program.viewer_enrollment.status === 'dropped' ? (
                                program.is_free ? (
                                    <Button
                                        className="w-full"
                                        size="lg"
                                        onClick={handleFreeEnroll}
                                        disabled={checkoutLoading}
                                    >
                                        {checkoutLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Re-enroll for free
                                    </Button>
                                ) : (
                                    <Button
                                        className="w-full"
                                        size="lg"
                                        onClick={handleBundlePurchase}
                                        disabled={checkoutLoading}
                                    >
                                        {checkoutLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Purchase bundle
                                    </Button>
                                )
                            ) : (
                                <Button asChild className="w-full" size="lg">
                                    <Link to="/my-programs">Continue learning</Link>
                                </Button>
                            )
                        ) : (
                            <>
                                {(program.already_paid_for_courses?.length ?? 0) > 0 && !program.is_free && (
                                    <div className="rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm">
                                        <p className="font-medium text-amber-700 dark:text-amber-400 mb-1">
                                            You already paid for{' '}
                                            {program.already_paid_for_courses!.length} course
                                            {program.already_paid_for_courses!.length === 1 ? '' : 's'} in this bundle
                                        </p>
                                        <ul className="list-disc list-inside text-xs text-muted-foreground space-y-0.5">
                                            {program.already_paid_for_courses!.map((c) => (
                                                <li key={c.course_uuid}>{c.course_title}</li>
                                            ))}
                                        </ul>
                                        <p className="text-xs text-muted-foreground mt-2">
                                            Purchasing the program won't refund those earlier purchases.
                                        </p>
                                    </div>
                                )}
                                {program.is_free ? (
                                    <Button
                                        className="w-full"
                                        size="lg"
                                        onClick={handleFreeEnroll}
                                        disabled={checkoutLoading}
                                    >
                                        {checkoutLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Enroll for free
                                    </Button>
                                ) : (
                                    <Button
                                        className="w-full"
                                        size="lg"
                                        onClick={handleBundlePurchase}
                                        disabled={checkoutLoading}
                                    >
                                        {checkoutLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                        Purchase bundle
                                    </Button>
                                )}
                                <p className="text-xs text-muted-foreground text-center">
                                    Enrolling gives you access to every course in this program.
                                </p>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Description */}
            {program.description && (
                <Card>
                    <CardContent className="pt-6 prose prose-sm max-w-none dark:prose-invert">
                        <div dangerouslySetInnerHTML={{ __html: program.description }} />
                    </CardContent>
                </Card>
            )}

            <Separator />

            {/* Included Courses */}
            <div className="space-y-4">
                <h2 className="text-2xl font-semibold flex items-center gap-2">
                    <BookOpen className="h-5 w-5" />
                    Included courses
                </h2>
                <div className="space-y-3">
                    {sortedCourses.map((entry, idx) => {
                        const c = entry.course;
                        return (
                            <Card key={entry.uuid}>
                                <CardContent className="p-4 flex items-center gap-4">
                                    <div className="text-2xl font-mono text-muted-foreground/50 w-8 text-center">
                                        {(idx + 1).toString().padStart(2, '0')}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <Link
                                            to={`/courses/${c.slug}`}
                                            className="font-medium text-base hover:underline"
                                        >
                                            {c.title}
                                        </Link>
                                        {c.short_description && (
                                            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                                                {c.short_description}
                                            </p>
                                        )}
                                        <div className="flex flex-wrap gap-2 mt-2">
                                            {entry.is_required && (
                                                <Badge variant="outline" className="text-xs">
                                                    <CheckCircle className="mr-1 h-3 w-3" />
                                                    Required
                                                </Badge>
                                            )}
                                            <Badge variant="secondary" className="text-xs">
                                                {formatPrice(c.price_cents, c.currency)}
                                            </Badge>
                                            {c.format && c.format !== 'online' && (
                                                <Badge variant="outline" className="text-xs capitalize">
                                                    {c.format}
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                    <Button variant="ghost" size="sm" asChild>
                                        <Link to={`/courses/${c.slug}`}>
                                            View <ArrowRight className="ml-1 h-3.5 w-3.5" />
                                        </Link>
                                    </Button>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default PublicProgramDetailPage;
