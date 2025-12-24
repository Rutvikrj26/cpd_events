import React from "react";
import { Link } from "react-router-dom";
import {
    ArrowRight,
    Award,
    Users,
    Shield,
    Zap,
    Target,
    Heart,
    Lightbulb
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function AboutPage() {
    return (
        <div className="flex flex-col">
            {/* Hero Section */}
            <section className="py-20 lg:py-28 bg-background relative overflow-hidden">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-primary/5 to-transparent rounded-full blur-3xl -z-10" />

                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-3xl mx-auto text-center">
                        <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium">
                            About Us
                        </Badge>
                        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground mb-6">
                            Simplifying Professional{" "}
                            <span className="gradient-text">Development</span>
                        </h1>
                        <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
                            We're on a mission to make CPD event management effortless for organizations worldwide.
                        </p>
                    </div>
                </div>
            </section>

            {/* Mission Section */}
            <section className="py-20 bg-secondary/30">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div>
                            <Badge variant="secondary" className="mb-4 px-4 py-1 text-sm font-medium">
                                Our Mission
                            </Badge>
                            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-6">
                                Making CPD Management Effortless
                            </h2>
                            <p className="text-lg text-muted-foreground mb-6">
                                Professional development is essential for career growth, but managing CPD events shouldn't be complicated. We built CPD Events to eliminate the administrative burden of tracking attendance and issuing certificates.
                            </p>
                            <p className="text-lg text-muted-foreground">
                                Our platform automates the tedious parts—attendance tracking, certificate generation, verification—so you can focus on what matters: delivering valuable educational experiences.
                            </p>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <StatCard number="1000+" label="Events Hosted" />
                            <StatCard number="10K+" label="Certificates Issued" />
                            <StatCard number="500+" label="Organizations" />
                            <StatCard number="99.9%" label="Uptime" />
                        </div>
                    </div>
                </div>
            </section>

            {/* Values Section */}
            <section className="py-20 bg-background">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
                            Our Values
                        </h2>
                        <p className="text-lg text-muted-foreground">
                            The principles that guide everything we build
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <ValueCard
                            icon={Zap}
                            title="Simplicity"
                            description="Complex workflows made simple. If it takes more than a few clicks, we're not done building."
                        />
                        <ValueCard
                            icon={Shield}
                            title="Reliability"
                            description="Your events are important. Our platform is built for 99.9% uptime and data security."
                        />
                        <ValueCard
                            icon={Lightbulb}
                            title="Innovation"
                            description="Constantly improving with new features and integrations based on user feedback."
                        />
                        <ValueCard
                            icon={Heart}
                            title="Support"
                            description="Real humans helping real users. We respond to every support request within 24 hours."
                        />
                    </div>
                </div>
            </section>

            {/* Why CPD Events */}
            <section className="py-20 bg-secondary/30">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-3xl mx-auto">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
                                Why We Built This
                            </h2>
                        </div>

                        <div className="space-y-6 text-lg text-muted-foreground">
                            <p>
                                We saw organizations spending countless hours on manual attendance tracking, creating certificates one by one, and managing spreadsheets of CPD records. It was clear there had to be a better way.
                            </p>
                            <p>
                                CPD Events was born from the frustration of organizing professional development events and dealing with the administrative overhead. We asked: what if attendance could be tracked automatically? What if certificates could be generated with one click? What if verification was instant?
                            </p>
                            <p>
                                Today, CPD Events handles all of this and more. We integrate directly with Zoom to track attendance in real-time, generate professional PDF certificates automatically, and provide a public verification portal for every certificate issued.
                            </p>
                            <p className="font-medium text-foreground">
                                Our goal is simple: let you focus on delivering great educational content while we handle the paperwork.
                            </p>
                        </div>
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
                    <div className="max-w-3xl mx-auto text-center">
                        <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">
                            Ready to Get Started?
                        </h2>
                        <p className="text-white/80 max-w-2xl mx-auto mb-10 text-lg">
                            Join organizations worldwide using CPD Events to streamline their professional development programs.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Link to="/signup">
                                <Button size="lg" className="bg-white text-primary hover:bg-white/90 min-w-[180px] h-14 text-lg font-semibold">
                                    Start for Free
                                    <ArrowRight className="ml-2 h-5 w-5" />
                                </Button>
                            </Link>
                            <Link to="/contact">
                                <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10 min-w-[180px] h-14 text-lg bg-transparent">
                                    Contact Us
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}

function StatCard({ number, label }: { number: string; label: string }) {
    return (
        <div className="bg-card rounded-2xl border border-border p-6 text-center">
            <p className="text-3xl font-bold text-primary mb-2">{number}</p>
            <p className="text-sm text-muted-foreground">{label}</p>
        </div>
    );
}

function ValueCard({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
    return (
        <div className="bg-card rounded-2xl border border-border p-6">
            <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4">
                <Icon className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
            <p className="text-muted-foreground">{description}</p>
        </div>
    );
}
