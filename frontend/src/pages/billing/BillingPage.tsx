import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { getSubscription, getInvoices, getBillingPortal, createCheckoutSession, cancelSubscription, reactivateSubscription, updateSubscription, getPublicPricing, syncSubscription } from '@/api/billing';
import { Subscription, Invoice, PricingProduct } from '@/api/billing/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
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
    CreditCard,
    FileText,
    CheckCircle,
    Zap,
    ArrowRight,
    ExternalLink,
    Loader2,
    Mail,
    Building2,
    User,
    Users,
    Settings
} from 'lucide-react';
import { toast } from 'sonner';
import { CancellationModal } from '@/components/billing/CancellationModal';

// Plan features mapped by plan type (fallback if backend doesn't provide features)
const PLAN_FEATURES: Record<string, string[]> = {
    attendee: [
        'Register for events',
        'Download certificates',
        'Track CPD credits',
    ],
    professional: [
        '30 events per month',
        '500 certificates/month',
        'Zoom integration',
        'Custom certificate templates',
        'Priority email support',
    ],
    organization: [
        'Unlimited events',
        'Unlimited certificates',
        'Multi-user team access',
        'White-label options',
        'API access',
        'Priority support',
        'Team collaboration',
        'Shared templates',
        'Dedicated account manager',
    ],
};

// Helper to convert PricingProduct to plan format
const convertProductToPlan = (product: PricingProduct, index: number) => {
    const monthlyPrice = product.prices.find(p => p.billing_interval === 'month');
    const annualPrice = product.prices.find(p => p.billing_interval === 'year');

    const iconMap: Record<string, any> = {
        professional: Users,
        organization: Building2,
    };

    return {
        id: product.plan,
        name: product.plan_display,
        price: monthlyPrice ? parseFloat(monthlyPrice.amount_display) : 0,
        priceAnnual: annualPrice ? parseFloat(annualPrice.amount_display) : 0,
        description: product.description,
        icon: iconMap[product.plan] || Users,
        features: PLAN_FEATURES[product.plan] || [],
        recommended: index === 0, // First paid plan is recommended
    };
};

export const BillingPage = () => {
    const [searchParams] = useSearchParams();
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(true);
    const [upgrading, setUpgrading] = useState<string | null>(null);
    const [planDialogOpen, setPlanDialogOpen] = useState(false);
    const [cancelModalOpen, setCancelModalOpen] = useState(false);
    const [plans, setPlans] = useState<any[]>([
        {
            id: 'attendee',
            name: 'Attendee',
            price: 0,
            priceAnnual: 0,
            description: 'For event participants',
            icon: User,
            features: PLAN_FEATURES.attendee,
        },
    ]);

    const checkoutStatus = searchParams.get('checkout');

    useEffect(() => {
        if (checkoutStatus === 'success') {
            toast.success("Payment successful! Updating subscription...");
            // Force a reload of subscription data, potentially with a small delay to allow webhook processing
            // In a real env, webhooks are fast. Locally, they might not exist. 
            // We'll try to re-fetch.
            const timeout = setTimeout(async () => {
                try {
                    const synced = await syncSubscription();
                    setSubscription(synced);
                    toast.success("Your account has been upgraded!");
                    // Navigate to /billing without query params to prevent loop and refresh user context
                    window.location.href = '/billing';
                } catch (e) {
                    console.error("Sync failed, falling back to get", e);
                    const sub = await getSubscription();
                    setSubscription(sub);
                }
            }, 1000);
            return () => clearTimeout(timeout);
        } else if (checkoutStatus === 'canceled') {
            toast.info("Checkout was canceled. No changes were made.");
        }
    }, [checkoutStatus]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [subData, invData, pricingData] = await Promise.all([
                    getSubscription().catch(() => null),
                    getInvoices().catch(() => []),
                    getPublicPricing().catch(() => []),
                ]);

                setSubscription(subData);
                setInvoices(invData);

                // Convert pricing products to plan format
                if (pricingData && pricingData.length > 0) {
                    const dynamicPlans = [
                        {
                            id: 'attendee',
                            name: 'Attendee',
                            price: 0,
                            priceAnnual: 0,
                            description: 'For event participants',
                            icon: User,
                            features: PLAN_FEATURES.attendee,
                        },
                        ...pricingData.map((product, index) => convertProductToPlan(product, index)),
                    ];
                    setPlans(dynamicPlans);
                }
            } catch (error) {
                console.error("Billing load error", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleUpgrade = async (planId: string) => {
        setUpgrading(planId);

        try {
            // Special handling for downgrade to free 'attendee' plan
            if (planId === 'attendee') {
                if (subscription?.stripe_subscription_id) {
                    // Cancel subscription at period end for downgrade to free
                    const updated = await cancelSubscription(false, 'Downgrading to free plan');
                    setSubscription(updated);
                    toast.success("You've been downgraded to the free plan. Access continues until your billing period ends.");
                    // Sync to update account_type
                    await syncSubscription();
                    window.location.href = '/billing';
                } else {
                    toast.info("You're already on the free plan.");
                }
                setUpgrading(null);
                return;
            }

            // Check if user already has an active Stripe subscription
            if (subscription && subscription.stripe_subscription_id) {
                // UPDATE existing subscription (upgrade/downgrade)
                const updated = await updateSubscription(planId, true);
                setSubscription(updated);
                toast.success("Plan updated successfully! Prorated charges will appear on your next invoice.");
            } else {
                // CREATE new subscription via Stripe Checkout
                const result = await createCheckoutSession(
                    planId,
                    `${window.location.origin}/billing?checkout=success`,
                    `${window.location.origin}/billing?checkout=canceled`
                );
                window.location.href = result.url;
            }
        } catch (error: any) {
            console.error('Upgrade error:', error);
            toast.error(error?.response?.data?.error?.message || "Failed to update plan. Please try again.");
        } finally {
            setUpgrading(null);
        }
    };

    const handleManageSubscription = async () => {
        try {
            const { url } = await getBillingPortal(`${window.location.origin}/billing`);
            window.location.href = url;
        } catch (e) {
            toast.error("Failed to open billing portal. Please try again.");
        }
    };

    const handleCancelClick = () => {
        setCancelModalOpen(true);
    };

    const handleCancelComplete = (updated: Subscription) => {
        setSubscription(updated);
        setCancelModalOpen(false);
        toast.success("Subscription will be canceled at period end.");
    };

    const handleReactivate = async () => {
        try {
            const updated = await reactivateSubscription();
            setSubscription(updated);
            toast.success("Subscription reactivated!");
        } catch (e) {
            toast.error("Failed to reactivate subscription.");
        }
    };

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center min-h-[50vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    const currentPlan = subscription?.plan || 'attendee';
    const isOrganizer = currentPlan === 'organizer' || currentPlan === 'organization';
    const currentPlanData = plans.find(p => p.id === currentPlan);

    return (
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-foreground">Billing & Subscription</h1>
                <p className="text-muted-foreground mt-1">Manage your plan and payment methods</p>
            </div>

            {/* Checkout Success Alert */}
            {checkoutStatus === 'success' && (
                <Alert className="bg-success/10 border-success/30">
                    <CheckCircle className="h-4 w-4 text-success" />
                    <AlertTitle>Upgrade Successful!</AlertTitle>
                    <AlertDescription>
                        Your subscription has been upgraded. All features are now available.
                    </AlertDescription>
                </Alert>
            )}

            {/* Current Subscription Card */}
            <Card>
                <CardHeader>
                    <div className="flex justify-between items-start">
                        <div>
                            <CardTitle className="flex items-center gap-2">
                                {currentPlanData && <currentPlanData.icon className="h-5 w-5" />}
                                {subscription?.plan_display || 'Attendee'} Plan
                                {subscription?.status === 'active' && (
                                    <Badge variant="outline" className="bg-success/10 text-success border-success/30">
                                        <CheckCircle className="h-3 w-3 mr-1" />
                                        Active
                                    </Badge>
                                )}
                            </CardTitle>
                            <CardDescription className="mt-1">
                                {currentPlanData?.description}
                                {subscription?.cancel_at_period_end && (
                                    <span className="ml-2 text-destructive">
                                        (Cancels {subscription.current_period_end ? new Date(subscription.current_period_end).toLocaleDateString() : 'soon'})
                                    </span>
                                )}
                            </CardDescription>
                        </div>
                        <div className="flex gap-2">
                            <Dialog open={planDialogOpen} onOpenChange={setPlanDialogOpen}>
                                <DialogTrigger asChild>
                                    <Button variant="outline">
                                        <Settings className="h-4 w-4 mr-2" />
                                        Change Plan
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="max-w-3xl">
                                    <DialogHeader>
                                        <DialogTitle>Choose a Plan</DialogTitle>
                                        <DialogDescription>
                                            Select the plan that best fits your needs
                                        </DialogDescription>
                                    </DialogHeader>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                                        {plans.map(plan => {
                                            const isCurrent = plan.id === currentPlan;
                                            const PlanIcon = plan.icon;

                                            return (
                                                <div
                                                    key={plan.id}
                                                    className={`relative p-4 rounded-lg border ${plan.recommended ? 'border-primary ring-1 ring-primary/20' : 'border-border'
                                                        } ${isCurrent ? 'bg-primary/5' : ''}`}
                                                >
                                                    {plan.recommended && (
                                                        <Badge className="absolute -top-2 left-1/2 -translate-x-1/2 bg-primary text-xs">
                                                            <Zap className="h-3 w-3 mr-1" />
                                                            Recommended
                                                        </Badge>
                                                    )}
                                                    <div className="flex items-center gap-2 mb-2 mt-1">
                                                        <PlanIcon className="h-4 w-4 text-primary" />
                                                        <span className="font-semibold">{plan.name}</span>
                                                        {isCurrent && <Badge variant="secondary" className="text-xs">Current</Badge>}
                                                    </div>
                                                    <div className="mb-3">
                                                        {plan.price !== null ? (
                                                            <>
                                                                <span className="text-2xl font-bold">${plan.price}</span>
                                                                <span className="text-muted-foreground text-sm">/mo</span>
                                                            </>
                                                        ) : (
                                                            <span className="text-lg font-semibold">Custom</span>
                                                        )}
                                                    </div>
                                                    <ul className="space-y-1 text-xs text-muted-foreground mb-4">
                                                        {plan.features.slice(0, 3).map((f: string, i: number) => (
                                                            <li key={i} className="flex items-center gap-1">
                                                                <CheckCircle className="h-3 w-3 text-primary shrink-0" />
                                                                {f}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                    {plan.isEnterprise ? (
                                                        <Link to="/contact" className="w-full" onClick={() => setPlanDialogOpen(false)}>
                                                            <Button variant="secondary" size="sm" className="w-full">
                                                                <Mail className="h-3 w-3 mr-1" />
                                                                Contact Sales
                                                            </Button>
                                                        </Link>
                                                    ) : isCurrent ? (
                                                        <Button variant="outline" size="sm" disabled className="w-full">
                                                            Current Plan
                                                        </Button>
                                                    ) : (
                                                        <Button
                                                            size="sm"
                                                            className="w-full"
                                                            variant={plan.recommended ? 'default' : 'outline'}
                                                            onClick={() => handleUpgrade(plan.id)}
                                                            disabled={upgrading !== null}
                                                        >
                                                            {upgrading === plan.id ? (
                                                                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                                            ) : (
                                                                <ArrowRight className="h-3 w-3 mr-1" />
                                                            )}
                                                            {plan.price === 0 ? 'Downgrade' : 'Upgrade'}
                                                        </Button>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </DialogContent>
                            </Dialog>
                            {subscription?.stripe_subscription_id && (
                                <Button variant="ghost" size="icon" onClick={handleManageSubscription} title="Manage in Stripe">
                                    <ExternalLink className="h-4 w-4" />
                                </Button>
                            )}
                        </div>
                    </div>
                </CardHeader>
                {subscription && isOrganizer && (
                    <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="text-xs font-medium text-muted-foreground uppercase">Events This Month</div>
                                <div className="text-2xl font-bold mt-1">
                                    {subscription.events_created_this_period}
                                    <span className="text-sm font-normal text-muted-foreground">
                                        /{subscription.limits?.events_per_month ?? '∞'}
                                    </span>
                                </div>
                            </div>
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="text-xs font-medium text-muted-foreground uppercase">Certificates Issued</div>
                                <div className="text-2xl font-bold mt-1">
                                    {subscription.certificates_issued_this_period}
                                    <span className="text-sm font-normal text-muted-foreground">
                                        /{subscription.limits?.certificates_per_month ?? '∞'}
                                    </span>
                                </div>
                            </div>
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="text-xs font-medium text-muted-foreground uppercase">Status</div>
                                <div className="text-lg font-semibold mt-1 capitalize">
                                    {subscription.subscription_status_display || subscription.status}
                                </div>
                            </div>
                            <div className="p-4 bg-muted/30 rounded-lg">
                                <div className="text-xs font-medium text-muted-foreground uppercase">Renews On</div>
                                <div className="text-lg font-semibold mt-1">
                                    {subscription.current_period_end
                                        ? new Date(subscription.current_period_end).toLocaleDateString()
                                        : 'N/A'
                                    }
                                </div>
                            </div>
                        </div>
                    </CardContent>
                )}
                <CardFooter className="border-t pt-4 flex gap-2">
                    {subscription?.cancel_at_period_end ? (
                        <Button variant="outline" onClick={handleReactivate}>
                            Reactivate Subscription
                        </Button>
                    ) : isOrganizer && subscription?.status === 'active' && (
                        <Button variant="ghost" className="text-destructive hover:text-destructive" onClick={handleCancelClick}>
                            Cancel Subscription
                        </Button>
                    )}
                </CardFooter>
            </Card>

            {/* Payment Methods - Managed via Stripe */}
            {isOrganizer && (
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CreditCard className="h-5 w-5" />
                            Payment Methods
                        </CardTitle>
                        <CardDescription>
                            Payment methods are securely managed through Stripe
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-center py-4">
                            <p className="text-muted-foreground mb-4">
                                Add, update, or remove payment methods in our secure payment portal.
                            </p>
                            <Button variant="outline" onClick={handleManageSubscription}>
                                <CreditCard className="h-4 w-4 mr-2" />
                                Manage Payment Methods
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Invoice History */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5" />
                        Payment History
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {invoices.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                            No invoices found.
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead className="border-b">
                                    <tr>
                                        <th className="px-4 py-3 font-medium text-muted-foreground">Date</th>
                                        <th className="px-4 py-3 font-medium text-muted-foreground">Amount</th>
                                        <th className="px-4 py-3 font-medium text-muted-foreground">Status</th>
                                        <th className="px-4 py-3 font-medium text-muted-foreground">Invoice</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y">
                                    {invoices.map(inv => (
                                        <tr key={inv.uuid}>
                                            <td className="px-4 py-3">
                                                {inv.created_at
                                                    ? new Date(inv.created_at).toLocaleDateString()
                                                    : '-'
                                                }
                                            </td>
                                            <td className="px-4 py-3 font-medium">
                                                {inv.amount_display || `$${(inv.amount_due / 100).toFixed(2)}`}
                                            </td>
                                            <td className="px-4 py-3">
                                                <Badge variant={inv.status === 'paid' ? 'default' : 'secondary'}>
                                                    {inv.status}
                                                </Badge>
                                            </td>
                                            <td className="px-4 py-3">
                                                {(inv.invoice_pdf_url || inv.pdf_url) && (
                                                    <a
                                                        href={inv.invoice_pdf_url || inv.pdf_url}
                                                        target="_blank"
                                                        rel="noreferrer"
                                                        className="text-primary hover:underline flex items-center gap-1"
                                                    >
                                                        <FileText size={14} /> Download
                                                    </a>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Cancellation Modal */}
            {subscription && (
                <CancellationModal
                    open={cancelModalOpen}
                    onOpenChange={setCancelModalOpen}
                    subscription={subscription}
                    onCanceled={handleCancelComplete}
                />
            )}
        </div>
    );
};
