import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getOrganization, getOrganizationPlans, upgradeOrganizationSubscription } from '@/api/organizations';
import { Organization, OrganizationSubscription } from '@/api/organizations/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import {
    Users,
    CheckCircle,
    Zap,
    ArrowRight,
    Loader2,
    Building2,
    TrendingUp,
    Calendar,
    Award
} from 'lucide-react';
import { toast } from 'sonner';
import { Progress } from '@/components/ui/progress';

// Plan features configuration will be fetched from the backend
interface PlanConfig {
    name: string;
    features: string[];
    price?: number;
    seats?: number;
    seatPrice?: number;
    included_seats?: number;
    seat_price_cents?: number;
}

export const OrganizationBillingPage: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const orgSlug = slug;
    const [organization, setOrganization] = useState<Organization | null>(null);
    const [plans, setPlans] = useState<Record<string, PlanConfig>>({});
    const [loading, setLoading] = useState(true);
    const [planDialogOpen, setPlanDialogOpen] = useState(false);
    const [upgrading, setUpgrading] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            if (!orgSlug) return;
            try {
                const [org, fetchedPlans] = await Promise.all([
                    getOrganization(orgSlug),
                    getOrganizationPlans()
                ]);
                setOrganization(org);
                setPlans(fetchedPlans);
            } catch (error) {
                console.error('Failed to load data', error);
                toast.error('Failed to load organization details');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [orgSlug]);

    const handleUpgrade = async (planId: string) => {
        setUpgrading(planId);

        try {
            if (!organization) return;
            const result = await upgradeOrganizationSubscription(organization.uuid, planId);
            if (result.url) {
                window.location.href = result.url;
            } else {
                toast.error('Failed to initiate upgrade');
            }
        } catch (error: any) {
            console.error('Upgrade error:', error);
            // Check for specific error message structure from backend
            const message = error?.response?.data?.detail || error?.response?.data?.error?.message || 'Failed to update plan';
            toast.error(message);
        } finally {
            setUpgrading(null);
        }
    };

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center min-h-[50vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!organization) {
        return (
            <div className="p-8">
                <Alert variant="destructive">
                    <AlertTitle>Organization Not Found</AlertTitle>
                    <AlertDescription>
                        The organization you're looking for doesn't exist or you don't have access.
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    const subscription = organization.subscription;
    const currentPlan = subscription?.plan || 'free';
    const currentPlanData = plans[currentPlan];
    const seatUtilization = subscription
        ? Math.round((subscription.active_organizer_seats / subscription.total_seats) * 100)
        : 0;

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <Building2 className="h-8 w-8 text-primary" />
                    <h1 className="text-3xl font-bold text-foreground">{organization.name} - Billing</h1>
                </div>
                <p className="text-muted-foreground">Manage your organization's subscription and team seats</p>
            </div>

            {/* Current Subscription Card */}
            <Card>
                <CardHeader>
                    <div className="flex justify-between items-start">
                        <div>
                            <CardTitle className="flex items-center gap-2">
                                <Users className="h-5 w-5" />
                                {subscription?.plan_display || 'Free'} Plan
                                {subscription?.status === 'active' && (
                                    <Badge variant="outline" className="bg-success/10 text-success border-success/30">
                                        <CheckCircle className="h-3 w-3 mr-1" />
                                        Active
                                    </Badge>
                                )}
                            </CardTitle>
                            <CardDescription className="mt-1">
                                {currentPlanData?.name} - Organization Subscription
                            </CardDescription>
                        </div>
                        <Dialog open={planDialogOpen} onOpenChange={setPlanDialogOpen}>
                            <DialogTrigger asChild>
                                <Button>
                                    <TrendingUp className="h-4 w-4 mr-2" />
                                    Upgrade Plan
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                                <DialogHeader>
                                    <DialogTitle>Choose Your Organization Plan</DialogTitle>
                                    <DialogDescription>
                                        Select the plan that best fits your team size and needs
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
                                    {Object.entries(plans).map(([planId, plan]) => {
                                        const isCurrent = planId === currentPlan;
                                        // Simple heuristic for "recommended" - usually the middle paid plan
                                        const isRecommended = planId === 'team';

                                        // Calculate display prices from backend data if available, or fallbacks
                                        // Backend structure: { included_seats: number, seat_price_cents: number, ... }
                                        const seats = plan.included_seats || plan.seats || 0;
                                        const seatPriceCents = plan.seat_price_cents || (plan.seatPrice ? plan.seatPrice * 100 : 0);
                                        const seatPrice = seatPriceCents / 100;
                                        const totalPrice = plan.price || (seatPrice * seats);

                                        return (
                                            <div
                                                key={planId}
                                                className={`relative p-6 rounded-lg border ${isRecommended
                                                    ? 'border-primary ring-2 ring-primary/20'
                                                    : 'border-border'
                                                    } ${isCurrent ? 'bg-primary/5' : ''}`}
                                            >
                                                {isRecommended && (
                                                    <Badge className="absolute -top-2 left-1/2 -translate-x-1/2 bg-primary text-xs">
                                                        <Zap className="h-3 w-3 mr-1" />
                                                        Popular
                                                    </Badge>
                                                )}
                                                <div className="mb-4">
                                                    <h3 className="font-semibold text-lg">{plan.name}</h3>
                                                    {isCurrent && (
                                                        <Badge variant="secondary" className="text-xs mt-1">
                                                            Current Plan
                                                        </Badge>
                                                    )}
                                                </div>
                                                <div className="mb-4">
                                                    {seatPrice > 0 ? (
                                                        <>
                                                            <span className="text-3xl font-bold">${totalPrice}</span>
                                                            <span className="text-muted-foreground text-sm">/mo</span>
                                                            <div className="text-xs text-muted-foreground mt-1">
                                                                ${seatPrice}/seat × {seats} seats
                                                            </div>
                                                        </>
                                                    ) : planId === 'free' ? (
                                                        <span className="text-3xl font-bold">Free</span>
                                                    ) : (
                                                        <span className="text-lg font-semibold">Custom</span>
                                                    )}
                                                </div>
                                                <ul className="space-y-2 text-sm text-muted-foreground mb-6">
                                                    {plan.features.map((feature, i) => (
                                                        <li key={i} className="flex items-start gap-2">
                                                            <CheckCircle className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                                                            {feature}
                                                        </li>
                                                    ))}
                                                </ul>
                                                {planId === 'enterprise' ? (
                                                    <Button variant="secondary" size="sm" className="w-full">
                                                        Contact Sales
                                                    </Button>
                                                ) : isCurrent ? (
                                                    <Button variant="outline" size="sm" disabled className="w-full">
                                                        Current Plan
                                                    </Button>
                                                ) : (
                                                    <Button
                                                        size="sm"
                                                        className="w-full"
                                                        variant={isRecommended ? 'default' : 'outline'}
                                                        onClick={() => handleUpgrade(planId)}
                                                        disabled={upgrading !== null}
                                                    >
                                                        {upgrading === planId ? (
                                                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                                        ) : (
                                                            <ArrowRight className="h-3 w-3 mr-1" />
                                                        )}
                                                        Upgrade
                                                    </Button>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </DialogContent>
                        </Dialog>
                    </div>
                </CardHeader>

                {subscription && (
                    <CardContent className="space-y-6">
                        {/* Seat Usage */}
                        <div>
                            <div className="flex justify-between items-center mb-2">
                                <h3 className="text-sm font-medium">Organizer Seats</h3>
                                <span className="text-sm text-muted-foreground">
                                    {subscription.active_organizer_seats} of {subscription.total_seats} seats used
                                </span>
                            </div>
                            <Progress value={seatUtilization} className="h-2" />
                            <div className="flex justify-between items-center mt-2 text-xs text-muted-foreground">
                                <span>{subscription.included_seats} included seats</span>
                                {subscription.additional_seats > 0 && (
                                    <span>+ {subscription.additional_seats} additional seats</span>
                                )}
                                <span>{subscription.available_seats} available</span>
                            </div>
                        </div>

                        {/* Usage Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase mb-1">
                                    <Calendar className="h-3 w-3" />
                                    Events
                                </div>
                                <div className="text-2xl font-bold">
                                    {subscription.events_created_this_period}
                                    <span className="text-sm font-normal text-muted-foreground ml-1">
                                        this month
                                    </span>
                                </div>
                            </div>
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase mb-1">
                                    <Award className="h-3 w-3" />
                                    Courses
                                </div>
                                <div className="text-2xl font-bold">
                                    {subscription.courses_created_this_period}
                                    <span className="text-sm font-normal text-muted-foreground ml-1">
                                        this month
                                    </span>
                                </div>
                            </div>
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase mb-1">
                                    <Users className="h-3 w-3" />
                                    Team Members
                                </div>
                                <div className="text-2xl font-bold">{organization.members_count}</div>
                            </div>
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="text-xs font-medium text-muted-foreground uppercase mb-1">Status</div>
                                <div className="text-lg font-semibold capitalize">
                                    {subscription.status_display || subscription.status}
                                </div>
                            </div>
                        </div>

                        {/* Billing Period */}
                        {subscription.current_period_end && (
                            <div className="p-4 bg-muted/20 rounded-lg border">
                                <div className="flex justify-between items-center">
                                    <div>
                                        <p className="text-sm font-medium">Next Billing Date</p>
                                        <p className="text-xs text-muted-foreground mt-1">
                                            Your subscription renews on{' '}
                                            {new Date(subscription.current_period_end).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <Button variant="outline" size="sm">
                                        Manage Billing
                                    </Button>
                                </div>
                            </div>
                        )}
                    </CardContent>
                )}
            </Card>

            {/* Seat Management Info */}
            <Card>
                <CardHeader>
                    <CardTitle>Seat Management</CardTitle>
                    <CardDescription>
                        Only Owner, Admin, and Manager roles count toward billable seats. Members are free and unlimited.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-muted/30 rounded-lg">
                            <div>
                                <p className="font-medium">Add More Seats</p>
                                <p className="text-sm text-muted-foreground">
                                    Additional seats: ${currentPlanData?.seatPrice || (currentPlanData?.seat_price_cents ? currentPlanData.seat_price_cents / 100 : 0)}/seat per month
                                </p>
                            </div>
                            <Button variant="outline" disabled>
                                Coming Soon
                            </Button>
                        </div>

                        <Alert>
                            <Users className="h-4 w-4" />
                            <AlertTitle>Need Help?</AlertTitle>
                            <AlertDescription>
                                To change your plan or add seats, please contact our support team at{' '}
                                <a href="mailto:billing@accredit.com" className="text-primary underline">
                                    billing@accredit.com
                                </a>
                            </AlertDescription>
                        </Alert>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};
