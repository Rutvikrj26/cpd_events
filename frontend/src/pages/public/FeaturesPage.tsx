import React from "react";
import { Link } from "react-router-dom";
import {
    ArrowRight,
    CheckCircle2,
    Video,
    Award,
    Calendar,
    Users,
    BarChart3,
    Shield,
    Clock,
    Globe,
    Building2,
    Settings,
    FileCheck,
    Zap,
    ChevronRight,
    BookOpen
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function FeaturesPage() {
    return (
        <div className="flex flex-col">
            {/* Hero Section */}
            <section className="py-20 lg:py-28 bg-background relative overflow-hidden">
                {/* Background decoration */}
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-primary/5 to-transparent rounded-full blur-3xl -z-10" />
                <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-to-tr from-accent/5 to-transparent rounded-full blur-3xl -z-10" />

                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="max-w-3xl mx-auto text-center">
                        <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium">
                            Platform Features
                        </Badge>
                        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground mb-6">
                            Everything You Need to{" "}
                            <span className="gradient-text">Manage Professional Development</span>
                        </h1>
                        <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
                            A comprehensive platform for hosting professional development events, tracking attendance automatically, and issuing verifiable certificates.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Link to="/signup">
                                <Button size="lg" className="h-12 px-8 glow-primary">
                                    Get Started Free
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                            </Link>
                            <Link to="/contact">
                                <Button size="lg" variant="outline" className="h-12 px-8">
                                    Request Demo
                                </Button>
                            </Link>
                        </div>

                        {/* Feature Navigation Cards */}
                        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-5xl mx-auto">
                            <a href="#event-management" className="bg-card hover:bg-accent/5 border border-border hover:border-primary/50 rounded-xl p-4 text-center transition-all duration-300 hover:-translate-y-1 group">
                                <div className="h-10 w-10 mx-auto bg-primary/10 rounded-lg flex items-center justify-center text-primary mb-3 group-hover:bg-primary group-hover:text-white transition-colors">
                                    <Calendar className="h-5 w-5" />
                                </div>
                                <h3 className="font-semibold text-sm">Event Management</h3>
                            </a>
                            <a href="#course-management" className="bg-card hover:bg-accent/5 border border-border hover:border-primary/50 rounded-xl p-4 text-center transition-all duration-300 hover:-translate-y-1 group">
                                <div className="h-10 w-10 mx-auto bg-accent/10 rounded-lg flex items-center justify-center text-accent mb-3 group-hover:bg-accent group-hover:text-white transition-colors">
                                    <BookOpen className="h-5 w-5" />
                                </div>
                                <h3 className="font-semibold text-sm">Course Management</h3>
                            </a>
                            <a href="#certificates" className="bg-card hover:bg-accent/5 border border-border hover:border-primary/50 rounded-xl p-4 text-center transition-all duration-300 hover:-translate-y-1 group">
                                <div className="h-10 w-10 mx-auto bg-primary/10 rounded-lg flex items-center justify-center text-primary mb-3 group-hover:bg-primary group-hover:text-white transition-colors">
                                    <Award className="h-5 w-5" />
                                </div>
                                <h3 className="font-semibold text-sm">Certificates</h3>
                            </a>
                            <a href="#organizations" className="bg-card hover:bg-accent/5 border border-border hover:border-primary/50 rounded-xl p-4 text-center transition-all duration-300 hover:-translate-y-1 group">
                                <div className="h-10 w-10 mx-auto bg-primary/10 rounded-lg flex items-center justify-center text-primary mb-3 group-hover:bg-primary group-hover:text-white transition-colors">
                                    <Building2 className="h-5 w-5" />
                                </div>
                                <h3 className="font-semibold text-sm">Organizations</h3>
                            </a>
                        </div>
                    </div>
                </div>
            </section>

            {/* Feature Highlight 1: Event Management */}
            <FeatureSection
                id="event-management"
                badge="Event Management"
                title="Create and Manage Professional Events"
                description="Build events of any format with our intuitive event creation wizard. Configure CPD credits, registration settings, and certificate requirements all in one place."
                features={[
                    "Multi-format support: Online, In-Person, and Hybrid events",
                    "Multi-session programs with individual tracking",
                    "Registration management with waitlist support",
                    "CPD credit configuration per event or session",
                    "Custom fields for registration forms"
                ]}
                visual={<EventManagementVisual />}
                reversed={false}
                ctaLink="/signup?role=organizer"
                ctaText="Start Creating Events"
            />

            {/* Feature Highlight 2: Course Management */}
            <FeatureSection
                id="course-management"
                badge="Course Management"
                title="Build and Sell Self-Paced Courses"
                description="Create engaging on-demand courses with our flexible LMS. Organize content into modules, add quizzes to test knowledge, and track learner progress automatically."
                features={[
                    "Modular course builder with drag-and-drop ordering",
                    "Support for video, PDF, and text content",
                    "Built-in quizzes with passing score requirements",
                    "Paid course enrollment via Stripe",
                    "Automatic progress tracking and completion logic"
                ]}
                visual={<CourseManagementVisual />}
                reversed={true}
                ctaLink="/signup?role=course_manager"
                ctaText="Start Building Courses"
            />

            {/* Feature Highlight 3: Certificates */}
            <FeatureSection
                id="certificates"
                badge="Certificates"
                title="Professional Certificates, Automatically Issued"
                description="Generate beautiful PDF certificates for attendees who meet attendance requirements or learners who complete a course."
                features={[
                    "Customizable PDF certificate templates",
                    "Automatic issuance rules (Attendance or Course Completion)",
                    "Unique verification codes for each certificate",
                    "Public verification page for employers",
                    "Bulk issuance for large cohorts"
                ]}
                visual={<CertificatesVisual />}
                reversed={false}
                ctaLink="/features/certificates"
                ctaText="Learn More About Certificates"
            />

            {/* Feature Highlight 4: Team Management */}
            <FeatureSection
                id="organizations"
                badge="Organizations"
                title="Manage Everything as a Team"
                description="Create organizations and invite team members with specific roles. Collaborate on events and courses and share resources across your organization."
                features={[
                    "Team roles: Admin, Organizer, Course Manager, Instructor",
                    "Shared events and courses library",
                    "Centralized certificate templates",
                    "Organization-wide analytics and reporting",
                    "Consolidated billing for the entire team"
                ]}
                visual={<TeamManagementVisual />}
                reversed={true}
                ctaLink="/signup"
                ctaText="Create Your Organization"
            />

            {/* All Features Grid */}
            <section className="py-24 bg-background">
                <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
                            And Much More
                        </h2>
                        <p className="text-lg text-muted-foreground">
                            Explore all the features that make Accredit the complete platform for professional development
                        </p>
                    </div>

                    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        <FeatureCard icon={Calendar} title="Event Scheduling" description="Flexible scheduling with timezone support" />
                        <FeatureCard icon={Users} title="Registration" description="Manage registrations with capacity limits" />
                        <FeatureCard icon={Clock} title="Session Tracking" description="Track attendance per session for multi-day events" />
                        <FeatureCard icon={BarChart3} title="Analytics" description="Event performance and attendance insights" />
                        <FeatureCard icon={Shield} title="Verification" description="Public certificate verification portal" />
                        <FeatureCard icon={Globe} title="Hybrid Events" description="Support for mixed virtual and in-person" />
                        <FeatureCard icon={Settings} title="Customization" description="Brand your events and certificates" />
                        <FeatureCard icon={FileCheck} title="CPD Compliance" description="Track CPD credits and requirements" />
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-24 bg-gradient-to-br from-primary to-accent text-white relative overflow-hidden">
                <div className="absolute inset-0 opacity-10">
                    <div className="absolute top-0 right-0 w-96 h-96 bg-white/20 rounded-full blur-3xl" />
                    <div className="absolute bottom-0 left-0 w-96 h-96 bg-white/10 rounded-full blur-3xl" />
                </div>

                <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="max-w-3xl mx-auto text-center">
                        <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">
                            Ready to Streamline Your Professional Development?
                        </h2>
                        <p className="text-white/80 max-w-2xl mx-auto mb-10 text-lg">
                            Start hosting professional development events and issuing verifiable certificates today.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Link to="/signup">
                                <Button size="lg" className="bg-white text-primary hover:bg-white/90 min-w-[180px] h-14 text-lg font-semibold">
                                    Get Started Free
                                    <ArrowRight className="ml-2 h-5 w-5" />
                                </Button>
                            </Link>
                            <Link to="/pricing">
                                <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10 min-w-[180px] h-14 text-lg bg-transparent">
                                    View Pricing
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}

// Feature Section Component
function FeatureSection({
    id,
    badge,
    title,
    description,
    features,
    visual,
    reversed,
    ctaLink,
    ctaText
}: {
    id?: string;
    badge: string;
    title: string;
    description: string;
    features: string[];
    visual: React.ReactNode;
    reversed: boolean;
    ctaLink: string;
    ctaText: string;
}) {
    return (
        <section id={id} className={`py-24 ${reversed ? 'bg-secondary/30' : 'bg-background'} scroll-mt-20`}>
            <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                <div className={`grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center ${reversed ? 'lg:flex-row-reverse' : ''}`}>
                    <div className={reversed ? 'lg:order-2' : ''}>
                        <Badge variant="secondary" className="mb-4 px-4 py-1 text-sm font-medium">
                            {badge}
                        </Badge>
                        <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-6">
                            {title}
                        </h2>
                        <p className="text-lg text-muted-foreground mb-8">
                            {description}
                        </p>
                        <ul className="space-y-3 mb-8">
                            {features.map((feature, index) => (
                                <li key={index} className="flex items-start gap-3">
                                    <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
                                    <span className="text-foreground">{feature}</span>
                                </li>
                            ))}
                        </ul>
                        <Link to={ctaLink}>
                            <Button className="glow-primary">
                                {ctaText}
                                <ChevronRight className="ml-2 h-4 w-4" />
                            </Button>
                        </Link>
                    </div>
                    <div className={reversed ? 'lg:order-1' : ''}>
                        {visual}
                    </div>
                </div>
            </div>
        </section>
    );
}

// Feature Card Component
function FeatureCard({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
    return (
        <div className="p-6 rounded-2xl border border-border bg-card hover:shadow-soft transition-all duration-300">
            <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4">
                <Icon className="h-5 w-5" />
            </div>
            <h3 className="font-semibold text-foreground mb-2">{title}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
        </div>
    );
}

// Visual Components
function EventManagementVisual() {
    return (
        <div className="bg-card rounded-2xl border border-border shadow-elevated p-6">
            <div className="flex items-center justify-between mb-6">
                <h3 className="font-semibold text-foreground">Create Event</h3>
                <Badge className="bg-primary/10 text-primary border-0">Step 1 of 4</Badge>
            </div>

            <div className="space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Event Title</label>
                    <div className="h-10 bg-secondary/50 rounded-lg px-3 flex items-center text-sm text-muted-foreground">
                        Annual CPD Workshop 2024
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">Format</label>
                        <div className="h-10 bg-primary/10 border border-primary/20 rounded-lg px-3 flex items-center text-sm text-primary font-medium">
                            <Video className="h-4 w-4 mr-2" /> Online
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">CPD Credits</label>
                        <div className="h-10 bg-secondary/50 rounded-lg px-3 flex items-center text-sm text-muted-foreground">
                            4 Credits
                        </div>
                    </div>
                </div>

                <div className="pt-4 flex gap-3">
                    <Button variant="outline" size="sm" className="flex-1">Back</Button>
                    <Button size="sm" className="flex-1">Continue</Button>
                </div>
            </div>
        </div>
    );
}

function ZoomIntegrationVisual() {
    return (
        <div className="bg-card rounded-2xl border border-border shadow-elevated p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Video className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-foreground">Zoom Connected</h3>
                        <p className="text-xs text-muted-foreground">Tracking attendance</p>
                    </div>
                </div>
                <Badge className="bg-success/10 text-success border-0">Live</Badge>
            </div>

            <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-medium text-primary">JD</div>
                        <div>
                            <p className="text-sm font-medium text-foreground">John Doe</p>
                            <p className="text-xs text-muted-foreground">Joined 45 min ago</p>
                        </div>
                    </div>
                    <Badge variant="outline" className="text-xs">92%</Badge>
                </div>

                <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-accent/20 flex items-center justify-center text-xs font-medium text-accent">SM</div>
                        <div>
                            <p className="text-sm font-medium text-foreground">Sarah Miller</p>
                            <p className="text-xs text-muted-foreground">Joined 40 min ago</p>
                        </div>
                    </div>
                    <Badge variant="outline" className="text-xs">85%</Badge>
                </div>

                <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-xs font-medium text-primary">MJ</div>
                        <div>
                            <p className="text-sm font-medium text-foreground">Mike Johnson</p>
                            <p className="text-xs text-muted-foreground">Joined 38 min ago</p>
                        </div>
                    </div>
                    <Badge variant="outline" className="text-xs">78%</Badge>
                </div>
            </div>
        </div>
    );
}

function CertificatesVisual() {
    return (
        <div className="relative">
            <div className="bg-card rounded-2xl border border-border shadow-elevated p-6">
                <div className="aspect-[4/3] bg-gradient-to-br from-primary/5 to-accent/5 rounded-xl flex flex-col items-center justify-center p-8 border border-border">
                    <Award className="h-12 w-12 text-primary mb-4" />
                    <h3 className="text-lg font-bold text-foreground text-center mb-2">Certificate of Completion</h3>
                    <p className="text-sm text-muted-foreground text-center mb-4">This certifies that</p>
                    <p className="text-xl font-semibold text-foreground mb-2">John Doe</p>
                    <p className="text-sm text-muted-foreground text-center mb-4">
                        has successfully completed the requirements for
                    </p>
                    <p className="text-base font-medium text-foreground text-center">Annual CPD Workshop 2024</p>
                    <div className="mt-6 flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">4 CPD Credits</Badge>
                        <Badge variant="outline" className="text-xs">Code: ABC123</Badge>
                    </div>
                </div>
            </div>

            {/* Floating verification badge */}
            <div className="absolute -right-4 -bottom-4 bg-card p-3 rounded-xl shadow-elevated border border-border flex items-center gap-2">
                <Shield className="h-5 w-5 text-success" />
                <span className="text-sm font-medium text-foreground">Verified</span>
            </div>
        </div>
    );
}

function TeamManagementVisual() {
    return (
        <div className="bg-card rounded-2xl border border-border shadow-elevated p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Building2 className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-foreground">Acme Training Co.</h3>
                        <p className="text-xs text-muted-foreground">5 team members</p>
                    </div>
                </div>
                <Badge className="bg-primary/10 text-primary border-0">Pro Plan</Badge>
            </div>

            <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-xs font-medium text-white">AD</div>
                        <div>
                            <p className="text-sm font-medium text-foreground">Alex Davis</p>
                            <p className="text-xs text-muted-foreground">alex@acme.com</p>
                        </div>
                    </div>
                    <Badge variant="secondary" className="text-xs">Admin</Badge>
                </div>

                <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-accent/80 flex items-center justify-center text-xs font-medium text-white">JW</div>
                        <div>
                            <p className="text-sm font-medium text-foreground">Jane Wilson</p>
                            <p className="text-xs text-muted-foreground">jane@acme.com</p>
                        </div>
                    </div>
                    <Badge variant="secondary" className="text-xs">Admin</Badge>
                </div>

                <div className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground">+3</div>
                        <div>
                            <p className="text-sm font-medium text-foreground">3 more members</p>
                            <p className="text-xs text-muted-foreground">View all →</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function CourseManagementVisual() {
    return (
        <div className="bg-card rounded-2xl border border-border shadow-elevated p-6">
            <div className="flex items-center justify-between mb-6">
                <h3 className="font-semibold text-foreground">Course Content</h3>
                <Badge className="bg-accent/10 text-accent border-0">Module 2</Badge>
            </div>

            <div className="space-y-4">
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-foreground">1. Introduction to Ethics</span>
                        <CheckCircle2 className="h-4 w-4 text-success" />
                    </div>
                </div>

                <div className="space-y-2 p-3 bg-secondary/30 rounded-lg border border-primary/20">
                    <div className="flex items-center justify-between text-sm mb-2">
                        <span className="font-medium text-foreground">2. Core Principles</span>
                        <Badge variant="outline" className="text-xs">In Progress</Badge>
                    </div>
                    <div className="space-y-2 pl-4 border-l-2 border-border">
                        <div className="flex items-center gap-2 text-sm text-foreground">
                            <Video className="h-3 w-3 text-primary" />
                            <span>Video Lecture (15:00)</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <FileCheck className="h-3 w-3" />
                            <span>Reading Material</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <CheckCircle2 className="h-3 w-3" />
                            <span>Knowledge Check</span>
                        </div>
                    </div>
                </div>

                <div className="space-y-2 opacity-60">
                    <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-foreground">3. Case Studies</span>
                        <Badge variant="outline" className="text-xs">Locked</Badge>
                    </div>
                </div>

                <div className="pt-2">
                    <Button className="w-full bg-accent hover:bg-accent/90" size="sm">
                        Continue Learning
                    </Button>
                </div>
            </div>
        </div>
    );
}
