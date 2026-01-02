import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ArrowRight, Building2, Users, User, Loader2 } from "lucide-react";
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

// Plan features mapped by plan type (fallback if backend doesn't provide features)
const PLAN_FEATURES = {
    attendee: [
        "Browse & register for events",
        "Track attendance history",
        "Download earned certificates",
        "Manage your profile",
        "Email notifications",
    ],
    professional: [
        "30 events per month",
        "500 certificates/month",
        "Zoom integration",
        "Custom certificate templates",
        "Priority email support",
    ],
    organization: [
        "Unlimited events",
        "Unlimited certificates",
        "Multi-user team access",
        "White-label options",
        "API access",
        "Priority support",
        "Team collaboration",
        "Shared templates",
        "Dedicated account manager",
    ],
};

const PLAN_ICONS = {
    attendee: User,
    professional: Users,
    organization: Building2,
};

export function PricingPage() {
    const [products, setProducts] = useState<PricingProduct[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

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
                : `The Attendee plan is completely free forever. All paid plans include a ${products[0]?.trial_days || 90}-day free trial with full access to all features - no credit card required to start!`,
        },
        {
            question: "What happens to my data if I downgrade?",
            answer: "Your data is always safe. If you downgrade, you'll retain access to all your existing events and certificates. You just won't be able to create new events beyond the plan limits.",
        },
        {
            question: "Do you offer discounts for nonprofits or educational institutions?",
            answer: "Yes! We offer special pricing for verified nonprofits and educational institutions. Contact our sales team to learn more about our discounted plans.",
        },
        {
            question: "Can I get a custom plan for my organization?",
            answer: "Absolutely. Our Organization plan is fully customizable. Contact our sales team to discuss your specific requirements and we'll create a tailored solution.",
        },
    ];

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

    // Build plans array: Attendee (hardcoded free) + fetched products
    const allPlans = [
        {
            name: "Attendee",
            plan: "attendee",
            icon: PLAN_ICONS.attendee,
            description: "For event participants who want to track their learning.",
            price: 0,
            annualPrice: null,
            period: "Free forever",
            features: PLAN_FEATURES.attendee,
            cta: "Get Started",
            ctaLink: "/signup",
            variant: "outline" as const,
            trialDays: 0,
            showContactSales: false,
        },
        ...products.map((product, index) => {
            // Use backend features if available, otherwise fall back to hardcoded
            const backendFeatures = product.features || [];
            const hardcodedFeatures = PLAN_FEATURES[product.plan as keyof typeof PLAN_FEATURES] || [];
            const features = backendFeatures.length > 0 ? backendFeatures : hardcodedFeatures;

            return {
                name: product.plan_display,
                plan: product.plan,
                icon: PLAN_ICONS[product.plan as keyof typeof PLAN_ICONS] || Users,
                description: product.description,
                price: product.show_contact_sales ? null : getMonthlyPrice(product),
                annualPrice: product.show_contact_sales ? null : getAnnualPrice(product),
                period: "/month",
                features: [
                    ...features,
                    ...(product.trial_days > 0 ? [`${product.trial_days}-day free trial`] : []),
                ],
                cta: product.show_contact_sales ? "Contact Sales" : "Start Free Trial",
                ctaLink: product.show_contact_sales ? "/contact" : `/signup?role=organizer&plan=${product.plan}`,
                variant: index === 0 ? ("default" as const) : ("secondary" as const),
                trialDays: product.trial_days,
                showContactSales: product.show_contact_sales,
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
                            Simple, Transparent Pricing
                        </h1>
                        <p className="text-xl text-muted-foreground mb-8">
                            Choose the perfect plan for your CPD events. All plans include a {allPlans[1]?.trialDays || 90}-day free trial.
                        </p>
                    </div>
                </div>
            </section>

            {/* Pricing Cards */}
            <section className="py-16 bg-background">
                <div className="container mx-auto px-4">
                    <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
                        {allPlans.map((plan) => {
                            const Icon = plan.icon;
                            return (
                                <Card
                                    key={plan.plan}
                                    className="relative flex flex-col"
                                >
                                    <CardHeader>
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
                                            ) : (
                                                <>
                                                    <div className="flex items-baseline gap-2">
                                                        <span className="text-4xl font-bold">
                                                            ${plan.price}
                                                        </span>
                                                        <span className="text-muted-foreground">
                                                            {plan.period}
                                                        </span>
                                                    </div>
                                                    {plan.annualPrice && (
                                                        <p className="text-sm text-muted-foreground mt-1">
                                                            ${plan.annualPrice}/mo billed annually
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
