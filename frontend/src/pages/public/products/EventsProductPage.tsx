
import {
    Calendar,
    Users,
    Video,
    Award,
    Play,
    CheckCircle2,
    Mail,
    ArrowRight,
    Shield,
    Zap,
    BarChart3,
    Globe,
    Ticket
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// --- Visual Components ---

function HeroDashboardMockup() {
    return (
        <div className="relative animate-fade-in-up">
            {/* Main Dashboard Card */}
            <div className="bg-card rounded-2xl border border-border shadow-elevated overflow-hidden">
                {/* Header Bar */}
                <div className="bg-primary/5 border-b border-border px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                            <Calendar className="h-4 w-4 text-primary-foreground" />
                        </div>
                        <div>
                            <p className="font-semibold text-foreground text-sm">Event Dashboard</p>
                            <p className="text-xs text-muted-foreground">Accredit Platform</p>
                        </div>
                    </div>
                    <Badge variant="secondary" className="text-xs">Live</Badge>
                </div>

                {/* Dashboard Content */}
                <div className="p-6 space-y-4">
                    <div className="grid grid-cols-3 gap-3">
                        <div className="bg-secondary/50 rounded-xl p-4 text-center">
                            <div className="flex items-center justify-center mb-2">
                                <Users className="h-5 w-5 text-primary" />
                            </div>
                            <p className="text-lg font-bold text-foreground">124</p>
                            <p className="text-xs text-muted-foreground">Registered</p>
                        </div>
                        <div className="bg-secondary/50 rounded-xl p-4 text-center">
                            <div className="flex items-center justify-center mb-2">
                                <Video className="h-5 w-5 text-accent" />
                            </div>
                            <p className="text-lg font-bold text-foreground">85</p>
                            <p className="text-xs text-muted-foreground">Attended</p>
                        </div>
                        <div className="bg-secondary/50 rounded-xl p-4 text-center">
                            <div className="flex items-center justify-center mb-2">
                                <Award className="h-5 w-5 text-primary" />
                            </div>
                            <p className="text-lg font-bold text-foreground">72</p>
                            <p className="text-xs text-muted-foreground">Certified</p>
                        </div>
                    </div>

                    <div className="bg-secondary/30 rounded-xl p-4">
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                    <Play className="h-5 w-5 text-primary" />
                                </div>
                                <div>
                                    <p className="font-medium text-foreground text-sm">Annual CPD Workshop</p>
                                    <p className="text-xs text-muted-foreground">2 CPD Credits • Online (Zoom)</p>
                                </div>
                            </div>
                            <Badge className="bg-primary/10 text-primary border-0 text-xs">In Progress</Badge>
                        </div>
                        <div className="w-full bg-secondary rounded-full h-2">
                            <div className="bg-primary h-2 rounded-full" style={{ width: '65%' }}></div>
                        </div>
                    </div>

                    <Button className="w-full" size="sm">
                        <Award className="h-4 w-4 mr-2" />
                        Issue Certificates
                    </Button>
                </div>
            </div>

            <div className="absolute -left-4 top-16 bg-card p-3 rounded-xl shadow-elevated border border-border hidden md:flex items-center gap-3 animate-float">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                    <CheckCircle2 className="h-4 w-4" />
                </div>
                <div>
                    <p className="text-xs font-medium text-foreground">Attendance Verified</p>
                    <p className="text-[10px] text-muted-foreground">Auto-tracked via Zoom</p>
                </div>
            </div>
        </div>
    );
}

// --- Main Page Component ---

export default function EventsProductPage() {
    return (
        <div className="flex flex-col min-h-screen bg-background">
            {/* Hero Section */}
            <section className="relative pt-32 pb-20 overflow-hidden">
                <div className="container px-4 mx-auto relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="text-left animate-fade-in-up">
                            <Badge className="mb-4 bg-primary/10 text-primary hover:bg-primary/20 transition-colors border-0">
                                For Event Organizers
                            </Badge>
                            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6">
                                Host Professional <span className="gradient-text">CPD Events</span>
                            </h1>
                            <p className="text-xl text-muted-foreground mb-8 text-balance">
                                The all-in-one platform for webinars, workshops, and conferences.
                                Automate certificates, sync with Zoom, and manage registrations effortlessly.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Link to="/register">
                                    <Button size="lg" className="h-12 px-8 text-base shadow-lg shadow-primary/20 glow-primary w-full sm:w-auto">
                                        Start Hosting
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Button>
                                </Link>
                                <Link to="/contact">
                                    <Button variant="outline" size="lg" className="h-12 px-8 text-base w-full sm:w-auto">
                                        Request Demo
                                    </Button>
                                </Link>
                            </div>
                        </div>
                        <div className="relative mx-auto w-full max-w-[500px] lg:max-w-none">
                            <div className="absolute inset-0 bg-primary/20 blur-[100px] rounded-full opacity-20 animate-pulse-slow" />
                            <HeroDashboardMockup />
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Grid */}
            <section className="py-20 bg-secondary/20">
                <div className="container px-4 mx-auto">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Everything you need to run successful events</h2>
                        <p className="text-lg text-muted-foreground">From registration to certification, we handle the boring parts so you can focus on the content.</p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={Video}
                            title="Seamless Zoom Integration"
                            description="Connect your Zoom account to auto-generate secure meeting links. We track attendance down to the minute."
                        />
                        <FeatureCard
                            icon={Award}
                            title="Automated Certificates"
                            description="Issue verified CPD certificates automatically when attendees meet your attendance and feedback criteria."
                        />
                        <FeatureCard
                            icon={Ticket}
                            title="Smart Registration"
                            description="Sell tickets (Stripe integrated), manage waitlists, and collect custom attendee details with ease."
                        />
                        <FeatureCard
                            icon={Globe}
                            title="Hybrid & In-Person"
                            description="Support for physical locations and hybrid events. Manage both online and on-site attendees in one list."
                        />
                        <FeatureCard
                            icon={BarChart3}
                            title="Real-time Analytics"
                            description="Track registrations, revenue, and attendance rates in real-time with beautiful dashboards."
                        />
                        <FeatureCard
                            icon={Zap}
                            title="Multi-Session Support"
                            description="Perfect for multi-day conferences. Track attendance across multiple sessions for full credit."
                        />
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-24 bg-card border-y border-border">
                <div className="container px-4 mx-auto text-center">
                    <h2 className="text-3xl font-bold tracking-tight text-foreground mb-6">Ready to host your next event?</h2>
                    <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
                        Join thousands of organizers who trust Accredit for their professional development events.
                    </p>
                    <Link to="/register">
                        <Button size="lg" className="h-14 px-10 text-lg shadow-xl shadow-primary/20 glow-primary">
                            Get Started for Free
                        </Button>
                    </Link>
                </div>
            </section>
        </div>
    );
}

function FeatureCard({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
    return (
        <div className="group bg-card p-8 rounded-2xl border border-border shadow-soft hover:shadow-elevated transition-all duration-300 hover:-translate-y-1">
            <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors duration-300">
                <Icon className="h-6 w-6" />
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-3">{title}</h3>
            <p className="text-muted-foreground leading-relaxed">{description}</p>
        </div>
    );
}
