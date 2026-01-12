
import {
    Building2,
    Users,
    CreditCard,
    ShieldCheck,
    ArrowRight,
    Palette,
    LayoutDashboard,
    Wallet,
    Settings,
    CheckCircle2
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

// --- Visual Components ---

function HeroOrgMockup() {
    return (
        <div className="relative animate-fade-in-up">
            {/* Main Org Card */}
            <div className="bg-card rounded-2xl border border-border shadow-elevated overflow-hidden">
                {/* Header Bar */}
                <div className="bg-secondary/50 border-b border-border px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Building2 className="h-4 w-4 text-primary" />
                        </div>
                        <div>
                            <p className="font-semibold text-foreground text-sm">Acme Training Corp</p>
                            <p className="text-xs text-muted-foreground">Organization Admin</p>
                        </div>
                    </div>
                    <Button variant="outline" size="sm" className="h-7 text-xs">
                        <Settings className="h-3 w-3 mr-2" />
                        Settings
                    </Button>
                </div>

                {/* Dashboard Content */}
                <div className="p-6 space-y-6">
                    {/* Team Section */}
                    <div>
                        <div className="flex items-center justify-between mb-4">
                            <h4 className="text-sm font-semibold text-foreground">Team Members</h4>
                            <Badge variant="outline" className="text-xs">12 / 20 Seats</Badge>
                        </div>

                        <div className="space-y-3">
                            <div className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg border border-border/50">
                                <div className="flex items-center gap-3">
                                    <Avatar className="h-8 w-8">
                                        <AvatarImage src="/avatars/01.png" />
                                        <AvatarFallback>JD</AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <p className="text-sm font-medium text-foreground">Jane Doe</p>
                                        <p className="text-xs text-muted-foreground">jane@acme.com</p>
                                    </div>
                                </div>
                                <Badge variant="secondary" className="text-xs font-normal">Admin</Badge>
                            </div>

                            <div className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg border border-border/50">
                                <div className="flex items-center gap-3">
                                    <Avatar className="h-8 w-8">
                                        <AvatarFallback>RS</AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <p className="text-sm font-medium text-foreground">Robert Smith</p>
                                        <p className="text-xs text-muted-foreground">robert@acme.com</p>
                                    </div>
                                </div>
                                <Badge variant="outline" className="text-xs font-normal">Instructor</Badge>
                            </div>
                        </div>
                    </div>

                    {/* Billing / Payouts Row */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-primary/5 rounded-xl border border-primary/10">
                            <p className="text-xs text-muted-foreground mb-1">Total Revenue</p>
                            <p className="text-lg font-bold text-foreground">$124,500</p>
                        </div>
                        <div className="p-4 bg-secondary/50 rounded-xl border border-border/50">
                            <p className="text-xs text-muted-foreground mb-1">Active Courses</p>
                            <p className="text-lg font-bold text-foreground">14</p>
                        </div>
                    </div>

                </div>
            </div>

            <div className="absolute -right-4 top-24 bg-card p-3 rounded-xl shadow-elevated border border-border hidden md:flex items-center gap-3 animate-float">
                <div className="h-8 w-8 rounded-full bg-green-500/10 flex items-center justify-center text-green-500">
                    <Wallet className="h-4 w-4" />
                </div>
                <div>
                    <p className="text-xs font-medium text-foreground">Payout via Stripe</p>
                    <p className="text-[10px] text-muted-foreground">Sent just now</p>
                </div>
            </div>
        </div>
    );
}

// --- Main Page Component ---

export default function OrganizationsProductPage() {
    return (
        <div className="flex flex-col min-h-screen bg-background">
            {/* Hero Section */}
            <section className="relative pt-32 pb-20 overflow-hidden">
                <div className="container px-4 mx-auto relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="text-left animate-fade-in-up">
                            <Badge className="mb-4 bg-secondary text-foreground hover:bg-secondary/80 transition-colors border-0">
                                For Training Agencies & Teams
                            </Badge>
                            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6">
                                Scale Your Training <span className="gradient-text">Operations</span>
                            </h1>
                            <p className="text-xl text-muted-foreground mb-8 text-balance">
                                Manage your team, brand, and billing in one central hub.
                                Perfect for training organizations, associations, and enterprise L&D.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Link to="/register?type=organization">
                                    <Button size="lg" className="h-12 px-8 text-base shadow-lg shadow-primary/20 glow-primary w-full sm:w-auto">
                                        Create Organization
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Button>
                                </Link>
                                <Link to="/contact">
                                    <Button variant="outline" size="lg" className="h-12 px-8 text-base w-full sm:w-auto">
                                        Contact Sales
                                    </Button>
                                </Link>
                            </div>
                        </div>
                        <div className="relative mx-auto w-full max-w-[500px] lg:max-w-none">
                            <div className="absolute inset-0 bg-primary/10 blur-[100px] rounded-full opacity-20 animate-pulse-slow" />
                            <HeroOrgMockup />
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Grid */}
            <section className="py-20 bg-secondary/20">
                <div className="container px-4 mx-auto">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Enterprise-grade management tools</h2>
                        <p className="text-lg text-muted-foreground">Give your team the tools they need to collaborate without stepping on each other's toes.</p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={Users}
                            title="Team Management"
                            description="Invite admins, organizers, and instructors. Assign specific roles and permissions to control access."
                        />
                        <FeatureCard
                            icon={CreditCard}
                            title="Consolidated Billing"
                            description="One invoice for your entire team. Manage subscription seats centrally and scale up or down as needed."
                        />
                        <FeatureCard
                            icon={Wallet}
                            title="Stripe Connect"
                            description="Receive direct payouts to your organization's bank account. Split revenue automatically."
                        />
                        <FeatureCard
                            icon={Palette}
                            title="White-label Branding"
                            description="Make the platform your own. Customize logos, colors, and domains to match your brand identity."
                        />
                        <FeatureCard
                            icon={LayoutDashboard}
                            title="Unified Dashboard"
                            description="See all your organization's events and courses in one place. Track aggregate revenue and engagement."
                        />
                        <FeatureCard
                            icon={ShieldCheck}
                            title="Shared Resources"
                            description="Share certificate templates, speaker profiles, and assets across your entire organization."
                        />
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-24 bg-card border-y border-border">
                <div className="container px-4 mx-auto text-center">
                    <h2 className="text-3xl font-bold tracking-tight text-foreground mb-6">Ready to scale?</h2>
                    <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
                        Get your organization set up in minutes. No credit card required for the first 14 days.
                    </p>
                    <Link to="/register?type=organization">
                        <Button size="lg" className="h-14 px-10 text-lg shadow-xl shadow-primary/20 glow-primary">
                            Start Organization Trial
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
