import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
    addOrganizationSeats,
    confirmOrganizationSubscription,
    createOrganizationPortalSession,
    getOrganizationBySlug,
    getOrganizationPlans,
    removeOrganizationSeats,
    upgradeOrganizationSubscription,
} from '@/api/organizations';
import { Organization } from '@/api/organizations/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { CreditCard, Plus, Minus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

export const OrganizationBillingPage: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    const [org, setOrg] = useState<Organization | null>(null);
    const [plans, setPlans] = useState<Record<string, any> | null>(null);
    const [loading, setLoading] = useState(true);
    const [isUpdating, setIsUpdating] = useState(false);
    const [seatCount, setSeatCount] = useState(1);

    const load = async () => {
        if (!slug) return;
        setLoading(true);
        try {
            const [orgData, planData] = await Promise.all([
                getOrganizationBySlug(slug),
                getOrganizationPlans().catch(() => null),
            ]);
            setOrg(orgData);
            setPlans(planData);
        } catch (error) {
            console.error('Failed to load billing data', error);
            toast.error('Failed to load organization billing data.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, [slug]);

    useEffect(() => {
        const sessionId = searchParams.get('session_id');
        const success = searchParams.get('success');
        if (!sessionId || !success || !slug || !org?.uuid) return;
        const confirm = async () => {
            try {
                await confirmOrganizationSubscription(org.uuid, sessionId);
                toast.success('Subscription updated successfully.');
            } catch (error) {
                console.error('Failed to confirm subscription', error);
                toast.error('Failed to confirm subscription.');
            } finally {
                await load();
                navigate(`/org/${slug}/billing`, { replace: true });
            }
        };
        confirm();
    }, [searchParams, slug, org?.uuid]);

    const handleUpgrade = async () => {
        if (!org) return;
        setIsUpdating(true);
        try {
            const result = await upgradeOrganizationSubscription(org.uuid, 'organization');
            if (result.url) {
                window.location.href = result.url;
                return;
            }
            await upgradeOrganizationSubscription(org.uuid, 'organization');
            toast.success('Upgrade initiated.');
        } catch (error) {
            console.error('Failed to upgrade subscription', error);
            toast.error('Failed to start upgrade.');
        } finally {
            setIsUpdating(false);
        }
    };

    const handlePortal = async () => {
        if (!org) return;
        setIsUpdating(true);
        try {
            const { url } = await createOrganizationPortalSession(org.uuid);
            window.location.href = url;
        } catch (error) {
            console.error('Failed to open billing portal', error);
            toast.error('Failed to open billing portal.');
        } finally {
            setIsUpdating(false);
        }
    };

    const handleAddSeats = async () => {
        if (!org) return;
        setIsUpdating(true);
        try {
            await addOrganizationSeats(org.uuid, seatCount);
            toast.success('Seats added successfully.');
            await load();
        } catch (error) {
            console.error('Failed to add seats', error);
            toast.error('Failed to add seats.');
        } finally {
            setIsUpdating(false);
        }
    };

    const handleRemoveSeats = async () => {
        if (!org) return;
        setIsUpdating(true);
        try {
            await removeOrganizationSeats(org.uuid, seatCount);
            toast.success('Seats removed successfully.');
            await load();
        } catch (error: any) {
            console.error('Failed to remove seats', error);
            toast.error(error?.response?.data?.detail || 'Failed to remove seats.');
        } finally {
            setIsUpdating(false);
        }
    };

    if (loading) {
        return (
            <div className="container mx-auto py-8 px-4 max-w-4xl">
                <Skeleton className="h-10 w-48 mb-4" />
                <Skeleton className="h-6 w-96 mb-8" />
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-40" />
                    </CardHeader>
                    <CardContent>
                        <Skeleton className="h-24 w-full" />
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!org || !org.subscription) {
        return (
            <div className="container mx-auto py-8 px-4 max-w-4xl">
                <Card>
                    <CardHeader>
                        <CardTitle>Organization Billing</CardTitle>
                        <CardDescription>No subscription data available.</CardDescription>
                    </CardHeader>
                </Card>
            </div>
        );
    }

    const subscription = org.subscription;
    const planConfig = plans?.[subscription.plan] || {};

    return (
        <div className="container mx-auto py-8 px-4 max-w-4xl space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Organization Billing</h1>
                <p className="text-muted-foreground">Manage your plan, seats, and billing details.</p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Current Plan</CardTitle>
                    <CardDescription>Your active organization subscription.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                        <div>
                            <p className="text-lg font-semibold capitalize">{subscription.plan} Plan</p>
                            <p className="text-sm text-muted-foreground">Status: {subscription.status}</p>
                        </div>
                        <div className="flex items-center gap-2">
                            {subscription.status === 'trialing' && (
                                <Badge variant="secondary">Trialing</Badge>
                            )}
                            <Button variant="outline" onClick={handlePortal} disabled={isUpdating}>
                                {isUpdating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CreditCard className="h-4 w-4 mr-2" />}
                                Billing Portal
                            </Button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 border rounded-lg">
                            <p className="text-sm text-muted-foreground">Organizer Seats</p>
                            <p className="text-2xl font-bold">{subscription.active_organizer_seats} / {subscription.total_seats}</p>
                            <p className="text-sm text-muted-foreground">{subscription.available_seats} available</p>
                        </div>
                        <div className="p-4 border rounded-lg">
                            <p className="text-sm text-muted-foreground">Events This Month</p>
                            <p className="text-2xl font-bold">{subscription.events_created_this_period}</p>
                            <p className="text-sm text-muted-foreground">Limit: {planConfig.events_per_month ?? 'Unlimited'}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Seat Management</CardTitle>
                    <CardDescription>Add or remove organizer seats.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex flex-wrap items-center gap-3">
                        <Input
                            type="number"
                            min={1}
                            value={seatCount}
                            onChange={(e) => setSeatCount(Math.max(1, Number(e.target.value)))}
                            className="w-32"
                        />
                        <Button onClick={handleAddSeats} disabled={isUpdating}>
                            {isUpdating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
                            Add Seats
                        </Button>
                        <Button variant="outline" onClick={handleRemoveSeats} disabled={isUpdating}>
                            <Minus className="h-4 w-4 mr-2" />
                            Remove Seats
                        </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                        Additional seats are billed per organizer. Remove seats only if they are unused.
                    </p>
                </CardContent>
            </Card>

            {subscription.status !== 'active' && (
                <Card>
                    <CardHeader>
                        <CardTitle>Upgrade</CardTitle>
                        <CardDescription>Activate your organization subscription.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Button onClick={handleUpgrade} disabled={isUpdating}>
                            {isUpdating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CreditCard className="h-4 w-4 mr-2" />}
                            Upgrade Plan
                        </Button>
                    </CardContent>
                </Card>
            )}
        </div>
    );
};
