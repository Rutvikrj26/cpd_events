import React from "react";
import { Check, HelpCircle, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import pricingHeroImage from "@/assets/images/pricing-hero.png";

export function PricingPage() {
    const [isAnnual, setIsAnnual] = React.useState(true);

    const plans = [
        {
            name: "Basic",
            description: "Essential tools for occasional learners.",
            price: isAnnual ? 0 : 0,
            features: [
                "Access to free webinars",
                "Track CPD credits manually",
                "Basic profile",
                "Email support",
            ],
            cta: "Get Started",
            variant: "outline" as const,
        },
        {
            name: "Pro",
            description: "Perfect for dedicated professionals.",
            popular: true,
            price: isAnnual ? 99 : 12,
            features: [
                "Everything in Basic",
                "Unlimited webinar access",
                "Automatic CPD tracking",
                "Certificate wallet",
                "Priority support",
                "Exclusive workshops discount",
            ],
            cta: "Start Free Trial",
            variant: "default" as const,
        },
        {
            name: "Enterprise",
            description: "For hospitals and large teams.",
            price: "Custom",
            features: [
                "Everything in Pro",
                "Team management dashboard",
                "Bulk event registration",
                "Custom reporting",
                "Dedicated account manager",
                "SSO Integration",
            ],
            cta: "Contact Sales",
            variant: "secondary" as const,
        },
    ];

    return (
        <div className="flex flex-col min-h-screen">
            {/* Hero Section */}
            <section className="relative py-20 overflow-hidden bg-slate-900">
                <div className="absolute inset-0">
                    <img
                        src={pricingHeroImage}
                        alt="Abstract pricing background"
                        className="w-full h-full object-cover opacity-30"
                    />
                    <div className="absolute inset-0 bg-gradient-to-b from-slate-900/50 to-slate-900"></div>
                </div>

                <div className="container relative mx-auto px-4 text-center">
                    <Badge className="mb-4 bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 border-blue-500/50 transition-colors">
                        Simple Pricing
                    </Badge>
                    <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-6">
                        Invest in your professional growth
                    </h1>
                    <p className="text-xl text-slate-300 max-w-2xl mx-auto mb-10">
                        Choose the plan that fits your career goals. Cancel anytime.
                    </p>

                    <div className="flex items-center justify-center gap-4 bg-slate-800/50 w-fit mx-auto p-1 rounded-full border border-slate-700 backdrop-blur-sm">
                        <button
                            onClick={() => setIsAnnual(false)}
                            className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${!isAnnual ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 hover:text-white"
                                }`}
                        >
                            Monthly
                        </button>
                        <button
                            onClick={() => setIsAnnual(true)}
                            className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${isAnnual ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 hover:text-white"
                                }`}
                        >
                            Yearly <span className="ml-1 text-blue-200 text-xs">(Save 20%)</span>
                        </button>
                    </div>
                </div>
            </section>

            {/* Pricing Cards */}
            <section className="py-20 -mt-10 container mx-auto px-4 z-10 relative">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {plans.map((plan) => (
                        <Card
                            key={plan.name}
                            className={`flex flex-col relative transition-all duration-300 hover:-translate-y-2 hover:shadow-xl ${plan.popular
                                    ? "border-blue-500 shadow-blue-500/20 scale-105 z-10"
                                    : "border-border/50"
                                }`}
                        >
                            {plan.popular && (
                                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide shadow-md">
                                    Most Popular
                                </div>
                            )}
                            <CardHeader>
                                <CardTitle className="text-2xl">{plan.name}</CardTitle>
                                <CardDescription>{plan.description}</CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                <div className="mb-6">
                                    {typeof plan.price === "number" ? (
                                        <div className="flex items-baseline">
                                            <span className="text-4xl font-bold text-slate-900">${plan.price}</span>
                                            <span className="text-slate-500 ml-2">/{isAnnual ? "year" : "month"}</span>
                                        </div>
                                    ) : (
                                        <div className="text-4xl font-bold text-slate-900">{plan.price}</div>
                                    )}
                                </div>
                                <ul className="space-y-3">
                                    {plan.features.map((feature) => (
                                        <li key={feature} className="flex items-start text-sm text-slate-600">
                                            <Check className="h-4 w-4 text-blue-500 mr-2 mt-0.5 shrink-0" />
                                            {feature}
                                        </li>
                                    ))}
                                </ul>
                            </CardContent>
                            <CardFooter>
                                <Button variant={plan.variant} className="w-full" size="lg">
                                    {plan.cta}
                                </Button>
                            </CardFooter>
                        </Card>
                    ))}
                </div>
            </section>

            {/* FAQ Section */}
            <section className="py-20 bg-slate-50">
                <div className="container mx-auto px-4 max-w-3xl">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-bold text-slate-900">Frequently Asked Questions</h2>
                        <p className="text-slate-600 mt-2">Everything you need to know about our pricing.</p>
                    </div>

                    <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="item-1">
                            <AccordionTrigger>Can I switch plans later?</AccordionTrigger>
                            <AccordionContent>
                                Yes, you can upgrade or downgrade your plan at any time. Changes will take effect at the start of the next billing cycle.
                            </AccordionContent>
                        </AccordionItem>
                        <AccordionItem value="item-2">
                            <AccordionTrigger>What payment methods do you accept?</AccordionTrigger>
                            <AccordionContent>
                                We accept all major credit cards (Visa, Mastercard, Amex), PayPal, and wire transfers for Enterprise plans.
                            </AccordionContent>
                        </AccordionItem>
                        <AccordionItem value="item-3">
                            <AccordionTrigger>Do you offer refunds?</AccordionTrigger>
                            <AccordionContent>
                                We offer a 14-day money-back guarantee for all paid plans if you are not satisfied with our service.
                            </AccordionContent>
                        </AccordionItem>
                        <AccordionItem value="item-4">
                            <AccordionTrigger>Are the certificates accredited?</AccordionTrigger>
                            <AccordionContent>
                                Yes, all CPD certificates issued through our platform are valid and recognized by major professional bodies.
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>

                    <div className="mt-12 text-center">
                        <p className="text-slate-600 mb-4">Still have questions?</p>
                        <Button variant="outline" asChild>
                            <a href="/contact">Contact Support <ArrowRight className="ml-2 h-4 w-4" /></a>
                        </Button>
                    </div>
                </div>
            </section>
        </div>
    );
}
