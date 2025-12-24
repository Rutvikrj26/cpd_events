import React from "react";
import { Link } from "react-router-dom";
import { Check, ArrowRight, Zap, Building2, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function PricingPage() {
    const [isAnnual, setIsAnnual] = React.useState(true);

    const plans = [
        {
            name: "Starter",
            icon: Zap,
            description: "For individual organizers getting started.",
            price: isAnnual ? 0 : 0,
            period: "Free forever",
            features: [
                "Up to 3 events per month",
                "Basic Zoom integration",
                "Standard certificates",
                "Email support",
                "50 attendees per event",
            ],
            cta: "Get Started",
            ctaLink: "/signup",
            variant: "outline" as const,
        },
        {
            name: "Professional",
            icon: Users,
            description: "For growing organizations with regular events.",
            popular: true,
            price: isAnnual ? 29 : 39,
            period: isAnnual ? "/month, billed annually" : "/month",
            features: [
                "Unlimited events",
                "Advanced Zoom integration",
                "Custom certificate templates",
                "Priority support",
                "500 attendees per event",
                "Multi-session events",
                "Attendance analytics",
            ],
            cta: "Start Free Trial",
            ctaLink: "/signup?plan=pro",
            variant: "default" as const,
        },
        {
            name: "Enterprise",
            icon: Building2,
            description: "For large organizations and teams.",
            price: "Custom",
            period: "Contact for pricing",
            features: [
                "Everything in Professional",
                "Unlimited attendees",
                "Team management",
                "Custom branding",
                "API access",
                "SSO integration",
                "Dedicated account manager",
                "Custom contracts",
            ],
            cta: "Contact Sales",
            ctaLink: "/contact",
            variant: "secondary" as const,
        },
    ];

    return (
        <div className="flex flex-col">
            {/* Hero Section */}
            <section className="py-16 lg:py-24 bg-background relative overflow-hidden">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-primary/5 to-transparent rounded-full blur-3xl -z-10" />
                <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-to-tr from-accent/5 to-transparent rounded-full blur-3xl -z-10" />

                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-3xl mx-auto text-center">
                        <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium">
                            Simple Pricing
                        </Badge>
                        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground mb-6">
                            Plans for Every{" "}
                            <span className="gradient-text">Organization</span>
                        </h1>
                        <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-10">
                            Start free and scale as you grow. No hidden fees, no surprises.
                        </p>

                        {/* Billing Toggle */}
                        <div className="flex items-center justify-center gap-3 bg-secondary/50 w-fit mx-auto p-1.5 rounded-full border border-border">
                            <button
                                onClick={() => setIsAnnual(false)}
                                className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${!isAnnual
                                    ? "bg-primary text-primary-foreground shadow-md"
                                    : "text-muted-foreground hover:text-foreground"
                                    }`}
                            >
                                Monthly
                            </button>
                            <button
                                onClick={() => setIsAnnual(true)}
                                className={`px-5 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${isAnnual
                                    ? "bg-primary text-primary-foreground shadow-md"
                                    : "text-muted-foreground hover:text-foreground"
                                    }`}
                            >
                                Yearly
                                <Badge variant="secondary" className="bg-success/10 text-success border-0 text-xs">
                                    Save 25%
                                </Badge>
                            </button>
                        </div>
                    </div>
                </div>
            </section>

            {/* Pricing Cards */}
            <section className="py-16 bg-secondary/30">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
                        {plans.map((plan) => (
                            <Card
                                key={plan.name}
                                className={`flex flex-col relative transition-all duration-300 hover:-translate-y-1 hover:shadow-elevated ${plan.popular
                                    ? "border-primary shadow-lg ring-1 ring-primary/20"
                                    : "border-border"
                                    }`}
                            >
                                {plan.popular && (
                                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                                        <Badge className="bg-primary text-primary-foreground shadow-md px-4">
                                            Most Popular
                                        </Badge>
                                    </div>
                                )}
                                <CardHeader className="pt-8">
                                    <div className="flex items-center gap-3 mb-2">
                                        <div className={`h-10 w-10 rounded-xl flex items-center justify-center ${plan.popular ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary'}`}>
                                            <plan.icon className="h-5 w-5" />
                                        </div>
                                        <CardTitle className="text-xl">{plan.name}</CardTitle>
                                    </div>
                                    <CardDescription className="text-sm">{plan.description}</CardDescription>
                                </CardHeader>
                                <CardContent className="flex-1">
                                    <div className="mb-6">
                                        {typeof plan.price === "number" ? (
                                            <div className="flex items-baseline">
                                                <span className="text-4xl font-bold text-foreground">${plan.price}</span>
                                                <span className="text-muted-foreground ml-2 text-sm">{plan.period}</span>
                                            </div>
                                        ) : (
                                            <div>
                                                <span className="text-4xl font-bold text-foreground">{plan.price}</span>
                                                <p className="text-muted-foreground text-sm mt-1">{plan.period}</p>
                                            </div>
                                        )}
                                    </div>
                                    <ul className="space-y-3">
                                        {plan.features.map((feature) => (
                                            <li key={feature} className="flex items-start text-sm text-foreground">
                                                <Check className="h-4 w-4 text-success mr-3 mt-0.5 shrink-0" />
                                                {feature}
                                            </li>
                                        ))}
                                    </ul>
                                </CardContent>
                                <CardFooter className="pt-4">
                                    <Link to={plan.ctaLink} className="w-full">
                                        <Button
                                            variant={plan.variant}
                                            className={`w-full ${plan.popular ? 'glow-primary' : ''}`}
                                            size="lg"
                                        >
                                            {plan.cta}
                                            <ArrowRight className="ml-2 h-4 w-4" />
                                        </Button>
                                    </Link>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                </div>
            </section>

            {/* Feature Comparison (Simple) */}
            <section className="py-16 bg-background">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-3xl mx-auto text-center mb-12">
                        <h2 className="text-2xl font-bold text-foreground mb-4">
                            All Plans Include
                        </h2>
                        <p className="text-muted-foreground">
                            Essential features available on every plan
                        </p>
                    </div>

                    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-4xl mx-auto">
                        <IncludedFeature title="Zoom Integration" description="Connect your Zoom account" />
                        <IncludedFeature title="Auto Attendance" description="Track attendance automatically" />
                        <IncludedFeature title="PDF Certificates" description="Generate professional certificates" />
                        <IncludedFeature title="Verification" description="Public certificate verification" />
                    </div>
                </div>
            </section>

            {/* FAQ Section */}
            <section className="py-16 bg-secondary/30">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-3xl">
                    <div className="text-center mb-12">
                        <h2 className="text-2xl font-bold text-foreground mb-4">Pricing FAQ</h2>
                        <p className="text-muted-foreground">Common questions about our pricing</p>
                    </div>

                    <div className="bg-card rounded-2xl border border-border p-6">
                        <Accordion type="single" collapsible className="space-y-2">
                            <AccordionItem value="item-1" className="border-b border-border/50 last:border-0">
                                <AccordionTrigger className="text-left font-medium text-foreground hover:no-underline py-4">
                                    Can I switch plans later?
                                </AccordionTrigger>
                                <AccordionContent className="text-muted-foreground pb-4">
                                    Yes, you can upgrade or downgrade your plan at any time. Upgrades take effect immediately with prorated billing. Downgrades take effect at the start of your next billing cycle.
                                </AccordionContent>
                            </AccordionItem>
                            <AccordionItem value="item-2" className="border-b border-border/50 last:border-0">
                                <AccordionTrigger className="text-left font-medium text-foreground hover:no-underline py-4">
                                    What payment methods do you accept?
                                </AccordionTrigger>
                                <AccordionContent className="text-muted-foreground pb-4">
                                    We accept all major credit cards (Visa, Mastercard, American Express) through our secure payment processor. For Enterprise plans, we can arrange invoice billing.
                                </AccordionContent>
                            </AccordionItem>
                            <AccordionItem value="item-3" className="border-b border-border/50 last:border-0">
                                <AccordionTrigger className="text-left font-medium text-foreground hover:no-underline py-4">
                                    Is there a free trial?
                                </AccordionTrigger>
                                <AccordionContent className="text-muted-foreground pb-4">
                                    Yes! The Professional plan includes a 14-day free trial with full access to all features. No credit card required to start.
                                </AccordionContent>
                            </AccordionItem>
                            <AccordionItem value="item-4" className="border-b border-border/50 last:border-0">
                                <AccordionTrigger className="text-left font-medium text-foreground hover:no-underline py-4">
                                    Do you offer refunds?
                                </AccordionTrigger>
                                <AccordionContent className="text-muted-foreground pb-4">
                                    We offer a 30-day money-back guarantee for all paid plans. If you're not satisfied, contact us for a full refund.
                                </AccordionContent>
                            </AccordionItem>
                        </Accordion>
                    </div>

                    <div className="mt-8 text-center">
                        <p className="text-muted-foreground mb-4">Still have questions?</p>
                        <Link to="/contact">
                            <Button variant="outline">
                                Contact Support
                                <ArrowRight className="ml-2 h-4 w-4" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-20 bg-gradient-to-br from-primary to-accent text-white relative overflow-hidden">
                <div className="absolute inset-0 opacity-10">
                    <div className="absolute top-0 right-0 w-96 h-96 bg-white/20 rounded-full blur-3xl" />
                    <div className="absolute bottom-0 left-0 w-96 h-96 bg-white/10 rounded-full blur-3xl" />
                </div>

                <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="max-w-2xl mx-auto text-center">
                        <h2 className="text-3xl font-bold tracking-tight mb-6">
                            Ready to Get Started?
                        </h2>
                        <p className="text-white/80 mb-8">
                            Join organizations worldwide using CPD Events to streamline their professional development programs.
                        </p>
                        <Link to="/signup">
                            <Button size="lg" className="bg-white text-primary hover:bg-white/90 h-14 px-8 text-lg font-semibold">
                                Start Free Today
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>
        </div>
    );
}

function IncludedFeature({ title, description }: { title: string; description: string }) {
    return (
        <div className="text-center p-4">
            <div className="h-10 w-10 rounded-xl bg-success/10 text-success flex items-center justify-center mx-auto mb-3">
                <Check className="h-5 w-5" />
            </div>
            <h3 className="font-medium text-foreground mb-1">{title}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
        </div>
    );
}
