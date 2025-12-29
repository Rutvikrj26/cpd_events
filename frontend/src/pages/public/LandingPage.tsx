import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Users,
  Award,
  Calendar,
  Video,
  FileCheck,
  Clock,
  Globe,
  ChevronRight,
  Shield,
  Building2,
  BookOpen,
  Play,
  BarChart3,
  Mail
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 md:pt-24 lg:pt-32 pb-20 lg:pb-32 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">

            {/* Text Content */}
            <div className="max-w-2xl text-center lg:text-left mx-auto lg:mx-0">
              <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium border-primary/20">
                <span className="flex h-2 w-2 rounded-full bg-primary mr-2"></span>
                Accredit Platform
              </Badge>

              <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground mb-6 leading-tight">
                Host Events.{" "}
                <span className="gradient-text">
                  Issue Certificates.
                </span>{" "}
                Automatically.
              </h1>

              <p className="text-lg md:text-xl text-muted-foreground mb-8 leading-relaxed max-w-lg mx-auto lg:mx-0">
                The complete platform for professional development. Create events, track attendance via Zoom, and automatically issue CPD certificates to qualified attendees.
              </p>

              <div className="flex flex-col sm:flex-row items-center gap-4 justify-center lg:justify-start">
                <Link to="/signup?role=organizer">
                  <Button size="lg" className="h-12 px-8 text-base shadow-lg hover:shadow-xl transition-all duration-300 glow-primary">
                    Start for Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {/* Trust Indicators */}
              <div className="mt-10 flex flex-wrap items-center justify-center lg:justify-start gap-6 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  <span>Free to start</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  <span>No credit card required</span>
                </div>
              </div>
            </div>

            {/* Hero Visual - Platform Mockup */}
            <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
              <HeroDashboardMockup />

              {/* Background Decoration */}
              <div className="absolute -top-24 -right-24 -z-10 h-[400px] w-[400px] bg-gradient-to-br from-primary/10 to-accent/10 blur-3xl rounded-full opacity-60"></div>
              <div className="absolute -bottom-24 -left-24 -z-10 h-[400px] w-[400px] bg-gradient-to-tr from-accent/10 to-primary/10 blur-3xl rounded-full opacity-60"></div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 bg-secondary/30 border-y border-border/50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
              How It Works
            </h2>
            <p className="text-lg text-muted-foreground">
              Three simple steps to automate your CPD event workflow
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <StepCard
              number="1"
              icon={Calendar}
              title="Create Your Event"
              description="Set up your CPD event with all the details: format (online, in-person, hybrid), CPD credits, registration settings, and certificate requirements."
            />
            <StepCard
              number="2"
              icon={Video}
              title="Connect & Host"
              description="Connect your Zoom account to automatically create meetings and track attendance in real-time. Or use manual check-in for in-person events."
            />
            <StepCard
              number="3"
              icon={Award}
              title="Issue Certificates"
              description="Certificates are automatically issued to attendees who meet your attendance requirements. Each certificate includes a unique verification code."
            />
          </div>
        </div>
      </section>

      {/* Core Features Section */}
      <section className="py-24 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="secondary" className="mb-4 px-4 py-1 text-sm font-medium">Platform Features</Badge>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
              Everything You Need for CPD Management
            </h2>
            <p className="text-lg text-muted-foreground">
              A comprehensive toolkit built for professional development organizations
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={Video}
              title="Zoom Integration"
              description="Connect your Zoom account to automatically create meetings and track participant join/leave times in real-time via webhooks."
            />
            <FeatureCard
              icon={FileCheck}
              title="Automated Certificates"
              description="Generate professional PDF certificates automatically when attendees meet your attendance threshold. Customize templates for your brand."
            />
            <FeatureCard
              icon={Clock}
              title="Attendance Tracking"
              description="Automatic tracking for virtual events via Zoom. Manual check-in available for in-person events. Override capability for organizers."
            />
            <FeatureCard
              icon={Shield}
              title="Certificate Verification"
              description="Every certificate includes a unique code for public verification. Recipients can share verified credentials with employers."
            />
            <FeatureCard
              icon={Globe}
              title="Multi-Format Events"
              description="Support for online, in-person, and hybrid events. Multi-session events with individual session tracking and completion criteria."
            />
            <FeatureCard
              icon={Building2}
              title="Team Management"
              description="Create organizations with team roles (Owner, Admin, Manager, Member). Manage events and certificates as a team."
            />
          </div>
        </div>
      </section>

      {/* Event Formats Section */}
      <section className="py-24 bg-secondary/30">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <Badge variant="secondary" className="mb-4 px-4 py-1 text-sm font-medium">Flexible Events</Badge>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-6">
                Host Any Type of CPD Event
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                From quick webinars to multi-day conferences, our platform adapts to your professional development needs.
              </p>

              <div className="space-y-4">
                <FeatureListItem
                  title="Webinars & Workshops"
                  description="Single-session events with Zoom integration for automatic attendance"
                />
                <FeatureListItem
                  title="Multi-Session Programs"
                  description="Training programs with multiple sessions. Track completion across all sessions."
                />
                <FeatureListItem
                  title="Hybrid Events"
                  description="Combine virtual and in-person attendance with flexible tracking options."
                />
                <FeatureListItem
                  title="Conference Sessions"
                  description="Multiple tracks with individual session CPD credits and certificates."
                />
              </div>

              <div className="mt-8">
                <Link to="/signup?role=organizer">
                  <Button className="glow-primary">
                    Create Your First Event
                    <ChevronRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>

            <div className="relative">
              <EventTypesVisual />
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-24 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="secondary" className="mb-4 px-4 py-1 text-sm font-medium">Use Cases</Badge>
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-4">
              Built for Professional Organizations
            </h2>
            <p className="text-lg text-muted-foreground">
              Organizations across industries use our platform to manage their CPD programs
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <UseCaseCard
              icon={BookOpen}
              title="Professional Associations"
              description="Issue CPD certificates to members attending your educational events and conferences."
            />
            <UseCaseCard
              icon={Building2}
              title="Training Providers"
              description="Manage courses and workshops with automatic attendance tracking and certification."
            />
            <UseCaseCard
              icon={Users}
              title="Corporate L&D Teams"
              description="Track employee professional development and issue internal certificates."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-primary via-primary to-accent text-white relative overflow-hidden">
        {/* Pattern overlay */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white/20 rounded-full blur-3xl"></div>
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-white/10 rounded-full blur-3xl"></div>
        </div>

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">
              Ready to Streamline Your Professional Development?
            </h2>
            <p className="text-white/80 max-w-2xl mx-auto mb-10 text-lg">
              Start hosting professional development events and issuing verifiable certificates today. Free to get started.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/signup?role=organizer">
                <Button size="lg" className="bg-white text-primary hover:bg-white/90 min-w-[180px] h-14 text-lg font-semibold shadow-lg">
                  Get Started Free
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

// Hero Dashboard Mockup Component
function HeroDashboardMockup() {
  return (
    <div className="relative">
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
          {/* Stats Row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-secondary/50 rounded-xl p-4 text-center">
              <div className="flex items-center justify-center mb-2">
                <Users className="h-5 w-5 text-primary" />
              </div>
              <p className="text-lg font-bold text-foreground">24</p>
              <p className="text-xs text-muted-foreground">Registered</p>
            </div>
            <div className="bg-secondary/50 rounded-xl p-4 text-center">
              <div className="flex items-center justify-center mb-2">
                <Video className="h-5 w-5 text-accent" />
              </div>
              <p className="text-lg font-bold text-foreground">18</p>
              <p className="text-xs text-muted-foreground">Attended</p>
            </div>
            <div className="bg-secondary/50 rounded-xl p-4 text-center">
              <div className="flex items-center justify-center mb-2">
                <Award className="h-5 w-5 text-primary" />
              </div>
              <p className="text-lg font-bold text-foreground">15</p>
              <p className="text-xs text-muted-foreground">Certified</p>
            </div>
          </div>

          {/* Event Item */}
          <div className="bg-secondary/30 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Play className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-foreground text-sm">Annual CPD Workshop</p>
                  <p className="text-xs text-muted-foreground">2 CPD Credits • Online</p>
                </div>
              </div>
              <Badge className="bg-primary/10 text-primary border-0 text-xs">Published</Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>Dec 28, 2024 • 2:00 PM</span>
            </div>
          </div>

          {/* Action Button */}
          <Button className="w-full" size="sm">
            <Award className="h-4 w-4 mr-2" />
            Issue Certificates
          </Button>
        </div>
      </div>

      {/* Floating Elements */}
      <div className="absolute -left-4 top-16 bg-card p-3 rounded-xl shadow-elevated border border-border hidden md:flex items-center gap-3 animate-float">
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <CheckCircle2 className="h-4 w-4" />
        </div>
        <div>
          <p className="text-xs font-medium text-foreground">Attendance Verified</p>
          <p className="text-[10px] text-muted-foreground">85% attendance</p>
        </div>
      </div>

      <div className="absolute -right-4 bottom-24 bg-card p-3 rounded-xl shadow-elevated border border-border hidden md:flex items-center gap-3 animate-float" style={{ animationDelay: '1.5s' }}>
        <div className="h-8 w-8 rounded-full bg-accent/20 flex items-center justify-center text-accent">
          <Mail className="h-4 w-4" />
        </div>
        <div>
          <p className="text-xs font-medium text-foreground">Certificate Sent</p>
          <p className="text-[10px] text-muted-foreground">john@example.com</p>
        </div>
      </div>
    </div>
  );
}

// Helper Components

function StepCard({ number, icon: Icon, title, description }: { number: string; icon: any; title: string; description: string }) {
  return (
    <div className="relative group">
      <div className="bg-card p-8 rounded-2xl border border-border shadow-soft hover:shadow-elevated transition-all duration-300 h-full">
        <div className="flex items-center gap-4 mb-6">
          <div className="h-12 w-12 rounded-xl bg-primary flex items-center justify-center text-primary-foreground font-bold text-xl">
            {number}
          </div>
          <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
            <Icon className="h-6 w-6" />
          </div>
        </div>
        <h3 className="text-xl font-semibold text-foreground mb-3">{title}</h3>
        <p className="text-muted-foreground leading-relaxed">{description}</p>
      </div>
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

function FeatureListItem({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex items-start gap-4 p-4 rounded-xl bg-card border border-border hover:border-primary/30 transition-colors">
      <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center text-primary flex-shrink-0 mt-0.5">
        <CheckCircle2 className="h-4 w-4" />
      </div>
      <div>
        <h4 className="font-semibold text-foreground">{title}</h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function UseCaseCard({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
  return (
    <div className="bg-card p-8 rounded-2xl border border-border shadow-soft hover:shadow-elevated transition-all duration-300">
      <div className="h-14 w-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-6">
        <Icon className="h-7 w-7" />
      </div>
      <h3 className="text-xl font-semibold text-foreground mb-3">{title}</h3>
      <p className="text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

function EventTypesVisual() {
  const eventTypes = [
    { type: "Webinar", format: "Online", icon: Video, credits: "2 CPD" },
    { type: "Workshop", format: "Hybrid", icon: Users, credits: "4 CPD" },
    { type: "Conference", format: "In-Person", icon: Building2, credits: "8 CPD" },
  ];

  return (
    <div className="bg-card rounded-2xl p-6 border border-border shadow-elevated">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-foreground">Event Types</h3>
        <Badge variant="secondary" className="text-xs">Supported Formats</Badge>
      </div>

      <div className="space-y-4">
        {eventTypes.map((event, index) => (
          <div key={index} className="flex items-center justify-between p-4 bg-secondary/50 rounded-xl">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <event.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">{event.type}</p>
                <p className="text-sm text-muted-foreground">{event.format}</p>
              </div>
            </div>
            <Badge variant="outline" className="text-xs">{event.credits}</Badge>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-6 border-t border-border">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Multi-session support</span>
          <CheckCircle2 className="h-5 w-5 text-primary" />
        </div>
      </div>
    </div>
  );
}
