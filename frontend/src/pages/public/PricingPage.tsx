import { useEffect, useState } from "react";
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
import type { InstitutionPlan } from "@/api/billing/types";

function iconForPlan(name: string) {
    const n = name.toLowerCase();
    if (n.includes("organization") || n.includes("enterprise") || n.includes("team")) return Building2;
    if (n.includes("course") || n.includes("lms")) return BookOpen;
    if (n.includes("organizer") || n.includes("event")) return Users;
    return User;
}

export function PricingPage() {
    const [plans, setPlans] = useState<InstitutionPlan[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [billingInterval, setBillingInterval] = useState<"month" | "year">("month");

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                setLoading(true);
                const data = await getPublicPricing();
                if (!cancelled) {
                    setPlans(data);
                    setError(null);
                }
            } catch (err) {
                console.error("Failed to fetch pricing:", err);
                if (!cancelled) setError("Failed to load pricing. Please try again later.");
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    const hasAnnualPricing = plans.some(p => p.billing_interval === "year");
    const plansForInterval = plans.filter(p => p.billing_interval === billingInterval);

    const faqs = [
        {
            question: "Can I switch plans anytime?",
            answer: "Yes — contact your administrator to upgrade or downgrade your plan.",
        },
        {
            question: "What payment methods do you accept?",
            answer:
                "We accept all major credit cards (Visa, Mastercard, American Express) through Stripe. We never store your card details.",
        },
        {
            question: "Can I get a custom plan for my organization?",
            answer:
                "Absolutely. Our Organization plans are fully customizable. Contact sales to discuss your specific requirements.",
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
                <Button onClick={() => window.location.reload()}>Try Again</Button>
            </div>
        );
    }

    return (
        <div className="flex flex-col">
            <section className="bg-gradient-to-b from-primary/5 to-background py-20">
                <div className="container mx-auto px-4">
                    <div className="text-center max-w-3xl mx-auto">
                        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl mb-4">Plans for Every Stage</h1>
                        <p className="text-xl text-muted-foreground mb-8">
                            Whether you're hosting live events, running self-paced courses, or managing a large
                            organization, we have a plan that fits.
                        </p>
                        {hasAnnualPricing && (
                            <div className="flex justify-center gap-2">
                                <Button
                                    type="button"
                                    variant={billingInterval === "month" ? "default" : "outline"}
                                    onClick={() => setBillingInterval("month")}
                                >
                                    Monthly
                                </Button>
                                <Button
                                    type="button"
                                    variant={billingInterval === "year" ? "default" : "outline"}
                                    onClick={() => setBillingInterval("year")}
                                >
                                    Annual
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
            </section>

            <section className="py-16 bg-background">
                <div className="container mx-auto px-4">
                    {plansForInterval.length === 0 ? (
                        <p className="text-center text-muted-foreground">
                            No plans are currently available. Contact your administrator for access.
                        </p>
                    ) : (
                        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
                            {plansForInterval.map((plan, idx) => {
                                const Icon = iconForPlan(plan.name);
                                return (
                                    <Card key={plan.uuid} className="relative flex flex-col">
                                        <CardHeader>
                                            {plan.is_featured && (
                                                <div className="mb-4">
                                                    <Badge variant="secondary" className="font-medium">
                                                        Most popular
                                                    </Badge>
                                                </div>
                                            )}
                                            <div className="flex items-center gap-2 mb-2">
                                                <Icon className="h-6 w-6 text-primary" />
                                                <CardTitle>{plan.name}</CardTitle>
                                            </div>
                                            <CardDescription>{plan.description}</CardDescription>
                                            <div className="mt-4">
                                                <div className="flex items-baseline gap-2">
                                                    <span className="text-4xl font-bold">{plan.price_display}</span>
                                                    <span className="text-muted-foreground">
                                                        /{plan.billing_interval}
                                                    </span>
                                                </div>
                                            </div>
                                        </CardHeader>
                                        <CardContent className="flex-1">
                                            <ul className="space-y-3">
                                                {plan.features_list.map((feature, i) => (
                                                    <li key={i} className="flex items-start gap-2">
                                                        <Check className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                                                        <span className="text-sm">{feature}</span>
                                                    </li>
                                                ))}
                                                {plan.max_enrollments !== null && (
                                                    <li className="flex items-start gap-2">
                                                        <Check className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                                                        <span className="text-sm">
                                                            Up to {plan.max_enrollments} enrollments
                                                        </span>
                                                    </li>
                                                )}
                                                {plan.includes_all_courses && (
                                                    <li className="flex items-start gap-2">
                                                        <Check className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                                                        <span className="text-sm">Access to all courses</span>
                                                    </li>
                                                )}
                                            </ul>
                                        </CardContent>
                                        <CardFooter>
                                            <Button
                                                asChild
                                                variant={idx === 0 ? "default" : "secondary"}
                                                className="w-full"
                                                size="lg"
                                            >
                                                <Link to="/contact">
                                                    Contact Sales
                                                    <ArrowRight className="ml-2 h-4 w-4" />
                                                </Link>
                                            </Button>
                                        </CardFooter>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </div>
            </section>

            <section className="py-16 bg-muted/30">
                <div className="container mx-auto px-4 max-w-3xl">
                    <h2 className="text-3xl font-bold text-center mb-12">Frequently Asked Questions</h2>
                    <Accordion type="single" collapsible className="w-full">
                        {faqs.map((faq, index) => (
                            <AccordionItem key={index} value={`item-${index}`}>
                                <AccordionTrigger className="text-left">{faq.question}</AccordionTrigger>
                                <AccordionContent className="text-muted-foreground">{faq.answer}</AccordionContent>
                            </AccordionItem>
                        ))}
                    </Accordion>
                </div>
            </section>

            <section className="py-20 bg-primary text-primary-foreground">
                <div className="container mx-auto px-4 text-center max-w-3xl">
                    <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
                    <p className="text-xl mb-8 opacity-90">
                        Join professionals managing their continuing education with Accredit.
                    </p>
                    <div className="flex gap-4 justify-center">
                        <Button asChild size="lg" variant="secondary">
                            <Link to="/login">
                                Access Portal
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Link>
                        </Button>
                        <Button
                            asChild
                            size="lg"
                            className="bg-white text-primary hover:bg-gray-100 border-2 border-white font-semibold"
                        >
                            <Link to="/contact">Contact Sales</Link>
                        </Button>
                    </div>
                </div>
            </section>
        </div>
    );
}
