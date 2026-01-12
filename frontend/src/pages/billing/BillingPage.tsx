import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { getSubscription, getInvoices, getBillingPortal, createCheckoutSession, cancelSubscription, reactivateSubscription, updateSubscription, getPublicPricing, syncSubscription, confirmCheckout } from '@/api/billing';
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
    organizer: [
        '30 events per month',
        '500 certificates/month',
        'Zoom integration',
        'Custom certificate templates',
        'Priority email support',
    ],
    lms: [
        '30 courses per month',
        '500 certificates/month',
        'Self-paced course builder',
        'Learner progress tracking',
        'Priority email support',
    ],
    organization: [
        'Unlimited events',
        'Unlimited courses',
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
    const features = product.features || [];
    const trialFeature = product.trial_days > 0 ? [`${product.trial_days}-day free trial`] : [];

    const iconMap: Record<string, any> = {
        organizer: Users,
        lms: FileText,
        organization: Building2,
    };

    return {
        id: product.plan,
        name: product.plan_display,
        priceMonthly: product.show_contact_sales ? null : (monthlyPrice ? parseFloat(monthlyPrice.amount_display) : 0),
        priceAnnual: product.show_contact_sales ? null : (annualPrice ? parseFloat(annualPrice.amount_display) : null),
        description: product.description,
        icon: iconMap[product.plan] || Users,
        features: [...features, ...trialFeature],
        recommended: index === 0 && !product.show_contact_sales, // First paid plan is recommended
        showContactSales: product.show_contact_sales,
        isEnterprise: product.show_contact_sales,
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
            priceMonthly: 0,
            priceAnnual: 0,
            description: 'For event participants',
            icon: User,
            features: PLAN_FEATURES.attendee,
            showContactSales: false,
            isEnterprise: false,
        },
    ]);
    const [billingInterval, setBillingInterval] = useState<'month' | 'year'>('month');

    const checkoutStatus = searchParams.get('checkout');

    useEffect(() => {
        if (checkoutStatus === 'success') {
            const sessionId = searchParams.get('session_id');

            if (sessionId) {
                // Atomic confirmation via new endpoint
                toast.success("Payment successful! Confirming subscription...");
                confirmCheckout(sessionId)
                    .then(sub => {
                        setSubscription(sub);
                        toast.success("Your account has been upgraded!");
                        // Clear query params and refresh
                        window.history.replaceState({}, '', '/billing');
                    })
                    .catch(async (err) => {
                        console.error("Checkout confirmation failed, falling back to sync", err);
                        // Fallback to sync if confirm-checkout fails
                        try {
                            const synced = await syncSubscription();
                            setSubscription(synced);
                            toast.success("Your account has been upgraded!");
                            window.history.replaceState({}, '', '/billing');
                        } catch (syncErr) {
                            console.error("Sync also failed", syncErr);
                            toast.error("Failed to confirm subscription. Please refresh the page or contact support.");
                        }
                    });
            } else {
                // No session_id, try legacy sync approach (backwards compatibility)
                toast.success("Payment successful! Updating subscription...");
                syncSubscription()
                    .then(synced => {
                        setSubscription(synced);
                        toast.success("Your account has been upgraded!");
                        window.history.replaceState({}, '', '/billing');
                    })
                    .catch(async (e) => {
                        console.error("Sync failed, falling back to get", e);
                        const sub = await getSubscription();
                        setSubscription(sub);
                    });
            }
        } else if (checkoutStatus === 'canceled') {
            toast.info("Checkout was canceled. No changes were made.");
        }
    }, [checkoutStatus, searchParams]);

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
                            priceMonthly: 0,
                            priceAnnual: 0,
                            description: 'For event participants',
                            icon: User,
                            features: PLAN_FEATURES.attendee,
                            showContactSales: false,
                            isEnterprise: false,
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

    const getPlanInterval = (plan: any) => {
        if (plan?.showContactSales) return 'month';
        if (billingInterval === 'year' && plan?.priceAnnual != null) {
            return 'year';
        }
        return 'month';
    };

    const getPlanPrice = (plan: any) => {
        if (!plan || plan.showContactSales) return null;
        if (billingInterval === 'year' && plan.priceAnnual != null) {
            return plan.priceAnnual;
        }
        return plan.priceMonthly;
    };

    const handleUpgrade = async (planId: string) => {
        setUpgrading(planId);

        try {
            const targetPlan = plans.find(p => p.id === planId);
            const targetInterval = getPlanInterval(targetPlan);

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
                const currentPlan = plans.find(p => p.id === (subscription.plan || 'attendee'));
                const currentInterval = subscription.billing_interval || 'month';
                const currentPrice =
                    currentInterval === 'year' && currentPlan?.priceAnnual != null
                        ? currentPlan.priceAnnual
                        : currentPlan?.priceMonthly;
                const targetPrice = getPlanPrice(targetPlan);
                const isDowngrade = typeof currentPrice === 'number' && typeof targetPrice === 'number'
                    ? targetPrice < currentPrice
                    : false;
                const updated = await updateSubscription(planId, !isDowngrade, targetInterval as 'month' | 'year');
                setSubscription(updated);
                toast.success(
                    isDowngrade
                        ? "Plan change scheduled for the end of your billing period."
                        : "Plan updated successfully! Prorated charges will appear on your next invoice."
                );
            } else {
                // CREATE new subscription via Stripe Checkout
                const result = await createCheckoutSession(
                    planId,
                    `${window.location.origin}/billing?checkout=success`,
                    `${window.location.origin}/billing?checkout=canceled`,
                    targetInterval as 'month' | 'year'
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
    const isOrganizerPlan = currentPlan === 'organizer' || currentPlan === 'organization';
    const isLmsPlan = currentPlan === 'lms' || currentPlan === 'organization';
    const showUsageMetrics = isOrganizerPlan || isLmsPlan;
    const gridColsClass = isOrganizerPlan && isLmsPlan ? "md:grid-cols-5" : "md:grid-cols-4";
    const currentPlanData = plans.find(p => p.id === currentPlan);
    const pendingPlanData = subscription?.pending_plan
        ? plans.find(p => p.id === subscription.pending_plan)
        : null;
    const hasAnnualPricing = plans.some(p => p.priceAnnual != null);

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
                                {subscription?.pending_plan && subscription.pending_change_at && (
                                    <span className="ml-2 text-muted-foreground">
                                        (Changes to {pendingPlanData?.name || subscription.pending_plan} on {new Date(subscription.pending_change_at).toLocaleDateString()})
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
                                    {hasAnnualPricing && (
                                        <div className="flex justify-center gap-2 mt-2">
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant={billingInterval === 'month' ? 'default' : 'outline'}
                                                onClick={() => setBillingInterval('month')}
                                            >
                                                Monthly
                                            </Button>
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant={billingInterval === 'year' ? 'default' : 'outline'}
                                                onClick={() => setBillingInterval('year')}
                                            >
                                                Annual
                                            </Button>
                                        </div>
                                    )}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                                        {plans.map(plan => {
                                            const isCurrent = plan.id === currentPlan;
                                            const PlanIcon = plan.icon;
                                            const planInterval = getPlanInterval(plan);
                                            const planPrice = getPlanPrice(plan);

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
                                                        {planPrice !== null ? (
                                                            <>
                                                                <span className="text-2xl font-bold">${planPrice}</span>
                                                                <span className="text-muted-foreground text-sm">
                                                                    {planInterval === 'year' ? '/yr' : '/mo'}
                                                                </span>
                                                                {planInterval === 'month' && billingInterval === 'year' && plan.priceAnnual == null && (
                                                                    <span className="text-xs text-muted-foreground block">Monthly only</span>
                                                                )}
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
                                                            {planPrice === 0 ? 'Downgrade' : 'Upgrade'}
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
                {subscription && showUsageMetrics && (
                    <CardContent>
                        <div className={`grid grid-cols-2 ${gridColsClass} gap-4`}>
                            {isOrganizerPlan && (
                                <div className="p-4 bg-muted/30 rounded-lg">
                                    <div className="text-xs font-medium text-muted-foreground uppercase">Events This Month</div>
                                    <div className="text-2xl font-bold mt-1">
                                        {subscription.events_created_this_period}
                                        <span className="text-sm font-normal text-muted-foreground">
                                            /{subscription.limits?.events_per_month ?? '∞'}
                                        </span>
                                    </div>
                                </div>
                            )}
                            {isLmsPlan && (
                                <div className="p-4 bg-muted/30 rounded-lg">
                                    <div className="text-xs font-medium text-muted-foreground uppercase">Courses This Month</div>
                                    <div className="text-2xl font-bold mt-1">
                                        {subscription.courses_created_this_period}
                                        <span className="text-sm font-normal text-muted-foreground">
                                            /{subscription.limits?.courses_per_month ?? '∞'}
                                        </span>
                                    </div>
                                </div>
                            )}
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
                    ) : showUsageMetrics && subscription?.status === 'active' && (
                        <Button variant="ghost" className="text-destructive hover:text-destructive" onClick={handleCancelClick}>
                            Cancel Subscription
                        </Button>
                    )}
                </CardFooter>
            </Card>

            {/* Payment Methods - Managed via Stripe */}
            {showUsageMetrics && (
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
