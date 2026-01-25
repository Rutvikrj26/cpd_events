import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ArrowRight, Building2, Users, User, Loader2, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getPublicPricing } from "@/api/billing";
import type { PricingProduct } from "@/api/billing/types";

const PLAN_ICONS = {
    attendee: User,
    organizer: Users,
    lms: BookOpen,
};

export function PricingPage() {
    const [products, setProducts] = useState<PricingProduct[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [billingInterval, setBillingInterval] = useState<'month' | 'year'>('month');

    useEffect(() => {
        fetchPricing();
    }, []);

    const fetchPricing = async () => {
        try {
            setLoading(true);
            const data = await getPublicPricing();
            setProducts(data);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch pricing:', err);
            setError('Failed to load pricing. Please try again later.');
        } finally {
            setLoading(false);
        }
    };

    // Helper to get monthly price
    const getMonthlyPrice = (product: PricingProduct) => {
        const monthlyPrice = product.prices.find(p => p.billing_interval === 'month');
        return monthlyPrice ? parseFloat(monthlyPrice.amount_display) : 0;
    };

    // Helper to get annual price (monthly equivalent)
    const getAnnualPrice = (product: PricingProduct) => {
        const annualPrice = product.prices.find(p => p.billing_interval === 'year');
        return annualPrice ? parseFloat(annualPrice.amount_display) : null;
    };

    const faqs = [
        {
            question: "Can I switch plans anytime?",
            answer: "Yes! You can upgrade or downgrade your plan at any time. When upgrading, you'll be charged the prorated difference. When downgrading, the change takes effect at the end of your billing period.",
        },
        {
            question: "What payment methods do you accept?",
            answer: "We accept all major credit cards (Visa, Mastercard, American Express) through our secure payment partner, Stripe. All payment data is handled by Stripe - we never store your card details.",
        },
        {
            question: "Is there a free trial?",
            answer: loading
                ? "Loading trial information..."
                : products[0]?.trial_days
                    ? `The Attendee plan is completely free forever. All paid plans include a ${products[0].trial_days}-day free trial with full access to all features - no credit card required to start!`
                    : "The Attendee plan is completely free forever. All paid plans include a free trial with full access to all features - no credit card required to start!",
        },
        {
            question: "What happens to my data if I downgrade?",
            answer: "Your data is always safe. If you downgrade, you'll retain access to all your existing events and certificates. You just won't be able to create new events beyond the plan limits.",
        },
        {
            question: "Do you offer discounts for nonprofits or educational institutions?",
            answer: "Yes! We offer special pricing for verified nonprofits and educational institutions. Contact our sales team to learn more about our discounted plans.",
        },
    ];

    const hasAnnualPricing = products.some(product =>
        product.prices.some(price => price.billing_interval === 'year')
    );

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen">
                <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
                <p className="text-muted-foreground">Loading pricing...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen">
                <p className="text-destructive mb-4">{error}</p>
                <Button onClick={fetchPricing}>Try Again</Button>
            </div>
        );
    }

    // Helper to get category label
    const getCategoryLabel = (planType: string) => {
        switch (planType) {
            case 'attendee': return 'For Learners';
            case 'organizer': return 'For Event Hosts';
            case 'lms': return 'For Course Creators';
            default: return 'Plan';
        }
    };

    // Build plans array: Attendee (hardcoded free tier) + fetched products
    const allPlans = [
        {
            name: "Attendee",
            plan: "attendee",
            icon: PLAN_ICONS.attendee,
            description: "For professionals who want to attend events and track their learning history.",
            monthlyPrice: 0,
            annualPrice: null,
            features: [
                "Browse & register for events",
                "Track attendance history",
                "Download earned certificates",
                "Manage your profile",
                "Email notifications",
            ],
            cta: "Get Started",
            ctaLink: "/signup",
            variant: "outline" as const,
            trialDays: 0,
            showContactSales: false,
            categoryLabel: getCategoryLabel('attendee'),
        },
        ...products.map((product, index) => {
            const features = product.features || [];

            return {
                name: product.plan_display,
                plan: product.plan,
                icon: PLAN_ICONS[product.plan as keyof typeof PLAN_ICONS] || Users,
                description: product.description,
                monthlyPrice: product.show_contact_sales ? null : getMonthlyPrice(product),
                annualPrice: product.show_contact_sales ? null : getAnnualPrice(product),
                features: [
                    ...features,
                    ...(product.trial_days > 0 ? [`${product.trial_days}-day free trial`] : []),
                ],
                cta: product.show_contact_sales ? "Contact Sales" : "Start Free Trial",
                ctaLink: product.show_contact_sales
                    ? "/contact"
                    : `/signup?role=${product.plan === 'lms' ? 'course_manager' : 'organizer'}&plan=${product.plan}`,
                variant: index === 0 ? ("default" as const) : ("secondary" as const),
                trialDays: product.trial_days,
                showContactSales: product.show_contact_sales,
                categoryLabel: getCategoryLabel(product.plan),
            };
        }),
    ];

    return (
        <div className="flex flex-col">
            {/* Hero Section */}
            <section className="bg-gradient-to-b from-primary/5 to-background py-20">
                <div className="container mx-auto px-4">
                    <div className="text-center max-w-3xl mx-auto">
                        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl mb-4">
                            Plans for Every Stage
                        </h1>
                        <p className="text-xl text-muted-foreground mb-8">
                            Whether you're dealing with live events or self-paced courses,
                            we have a plan that fits your needs.
                        </p>
                        {hasAnnualPricing && (
                            <div className="flex justify-center gap-2">
                                <Button
                                    type="button"
                                    variant={billingInterval === 'month' ? 'default' : 'outline'}
                                    onClick={() => setBillingInterval('month')}
                                >
                                    Monthly
                                </Button>
                                <Button
                                    type="button"
                                    variant={billingInterval === 'year' ? 'default' : 'outline'}
                                    onClick={() => setBillingInterval('year')}
                                >
                                    Annual
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
            </section>

            {/* Pricing Cards */}
            <section className="py-16 bg-background">
                <div className="container mx-auto px-4">
                    <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
                        {allPlans.map((plan) => {
                            const Icon = plan.icon;
                            const planInterval = billingInterval === 'year' && plan.annualPrice != null ? 'year' : 'month';
                            const displayPrice = planInterval === 'year' ? plan.annualPrice : plan.monthlyPrice;
                            return (
                                <Card
                                    key={plan.plan}
                                    className="relative flex flex-col"
                                >
                                    <CardHeader>
                                        <div className="mb-4">
                                            <Badge variant="secondary" className="font-medium">
                                                {plan.categoryLabel}
                                            </Badge>
                                        </div>
                                        <div className="flex items-center gap-2 mb-2">
                                            <Icon className="h-6 w-6 text-primary" />
                                            <CardTitle>{plan.name}</CardTitle>
                                        </div>
                                        <CardDescription>{plan.description}</CardDescription>
                                        <div className="mt-4">
                                            {plan.showContactSales ? (
                                                <div className="text-2xl font-bold text-muted-foreground">
                                                    Custom Pricing
                                                </div>
                                            ) : plan.plan === 'attendee' || plan.monthlyPrice === 0 ? (
                                                <div className="text-2xl font-bold text-muted-foreground">
                                                    Free forever
                                                </div>
                                            ) : (
                                                <>
                                                    <div className="flex items-baseline gap-2">
                                                        <span className="text-4xl font-bold">
                                                            ${displayPrice}
                                                        </span>
                                                        <span className="text-muted-foreground">
                                                            {planInterval === 'year' ? '/year' : '/month'}
                                                        </span>
                                                    </div>
                                                    {billingInterval === 'year' && plan.annualPrice == null && (
                                                        <p className="text-sm text-muted-foreground mt-1">
                                                            Monthly billing only
                                                        </p>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    </CardHeader>
                                    <CardContent className="flex-1">
                                        <ul className="space-y-3">
                                            {plan.features.map((feature, i) => (
                                                <li key={i} className="flex items-start gap-2">
                                                    <Check className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                                                    <span className="text-sm">{feature}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </CardContent>
                                    <CardFooter>
                                        <Button
                                            asChild
                                            variant={plan.variant}
                                            className="w-full"
                                            size="lg"
                                        >
                                            <Link to={plan.ctaLink}>
                                                {plan.cta}
                                                <ArrowRight className="ml-2 h-4 w-4" />
                                            </Link>
                                        </Button>
                                    </CardFooter>
                                </Card>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* Organizations & Enterprise Banner */}
            <section className="pb-16 bg-background">
                <div className="container mx-auto px-4">
                    <div className="max-w-6xl mx-auto rounded-xl border bg-card p-8 shadow-sm flex flex-col md:flex-row items-center justify-between gap-8">
                        <div className="flex items-start gap-6">
                            <div className="p-3 bg-primary/10 rounded-lg shrink-0 hidden sm:block">
                                <Building2 className="h-8 w-8 text-primary" />
                            </div>
                            <div className="space-y-2">
                                <h3 className="text-2xl font-semibold tracking-tight">For Organizations</h3>
                                <p className="text-muted-foreground text-lg max-w-2xl">
                                    Need a custom fully branded and managed deployment? We offer dedicated 
                                    solutions tailored to your organization's specific requirements.
                                </p>
                            </div>
                        </div>
                        <Button asChild size="lg" className="shrink-0 min-w-[140px]">
                            <Link to="/contact">
                                Contact Sales
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                    </div>
                </div>
            </section>

            {/* FAQ Section */}
            <section className="py-16 bg-muted/30">
                <div className="container mx-auto px-4 max-w-3xl">
                    <h2 className="text-3xl font-bold text-center mb-12">
                        Frequently Asked Questions
                    </h2>
                    <Accordion type="single" collapsible className="w-full">
                        {faqs.map((faq, index) => (
                            <AccordionItem key={index} value={`item-${index}`}>
                                <AccordionTrigger className="text-left">
                                    {faq.question}
                                </AccordionTrigger>
                                <AccordionContent className="text-muted-foreground">
                                    {faq.answer}
                                </AccordionContent>
                            </AccordionItem>
                        ))}
                    </Accordion>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 bg-primary text-primary-foreground">
                <div className="container mx-auto px-4 text-center max-w-3xl">
                    <h2 className="text-3xl font-bold mb-4">
                        Ready to get started?
                    </h2>
                    <p className="text-xl mb-8 opacity-90">
                        Join thousands of professionals managing their CPD events
                    </p>
                    <div className="flex gap-4 justify-center">
                        <Button asChild size="lg" variant="secondary">
                            <Link to="/signup">
                                Start Free Trial
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                        <Button asChild size="lg" className="bg-white text-primary hover:bg-gray-100 border-2 border-white font-semibold">
                            <Link to="/contact">Contact Sales</Link>
                        </Button>
                    </div>
                </div>
            </section>
        </div>
    );
}
