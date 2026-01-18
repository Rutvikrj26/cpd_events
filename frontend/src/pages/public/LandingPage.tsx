
import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Calendar,
  BookOpen,
  Building2,
  Shield,
  Zap,
  Clock,
  MousePointerClick,
  Wallet,
  Award,
  GraduationCap,
  Presentation,
  Search,
  Users,
  DollarSign,
  Video,
  Banknote,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-24 pb-20 lg:pt-32 lg:pb-32 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium border-primary/20 mx-auto">
            <span className="flex h-2 w-2 rounded-full bg-primary mr-2"></span>
            The Accredit Platform
          </Badge>

          <h1 className="text-4xl md:text-5xl lg:text-7xl font-extrabold tracking-tight text-foreground mb-6 leading-tight max-w-4xl mx-auto">
            Professional Development, <br />
            <span className="gradient-text">Unified.</span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground mb-12 leading-relaxed max-w-2xl mx-auto">
            Find world-class training or deliver your own—all on one platform.
          </p>

          {/* Split Persona Cards */}
          <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
            {/* For Learners Card */}
            <div className="bg-card border-2 border-border rounded-2xl p-8 text-left hover:border-primary/50 transition-all duration-300 shadow-sm hover:shadow-elevated">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <GraduationCap className="h-5 w-5 text-primary" />
                </div>
                <h2 className="text-2xl font-bold text-foreground">For Learners</h2>
              </div>
              <p className="text-muted-foreground mb-6">
                Discover events and courses from trusted providers
              </p>
              <ul className="space-y-3 mb-8">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground">Browse live events and self-paced courses</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground">Track your CPD credits in one place</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground">Earn verified, shareable certificates</span>
                </li>
              </ul>
              <Link to="/events/browse">
                <Button variant="outline" size="lg" className="w-full h-12 text-base">
                  Browse Training
                  <Search className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <div className="mt-4 text-center">
                <Badge variant="secondary" className="text-xs font-normal">Free forever</Badge>
              </div>
            </div>

            {/* For Providers Card */}
            <div className="bg-card border-2 border-primary/20 rounded-2xl p-8 text-left hover:border-primary transition-all duration-300 shadow-sm hover:shadow-elevated">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Presentation className="h-5 w-5 text-primary" />
                </div>
                <h2 className="text-2xl font-bold text-foreground">For Providers</h2>
              </div>
              <p className="text-muted-foreground mb-6">
                Deliver professional development at scale
              </p>
              <ul className="space-y-3 mb-8">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground">Host webinars, workshops, and conferences</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground">Build self-paced courses and quizzes</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <span className="text-sm text-foreground">Issue automated CPD certificates</span>
                </li>
              </ul>
              <Link to="/pricing">
                <Button size="lg" className="w-full h-12 text-base shadow-xl shadow-primary/20 glow-primary">
                  Start Creating
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <div className="mt-4 text-center">
                <Badge variant="secondary" className="text-xs font-normal">Free trial included</Badge>
              </div>
            </div>
          </div>
        </div>

        {/* Background Gradients */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 -z-10 h-[600px] w-[600px] bg-primary/5 blur-[120px] rounded-full"></div>
      </section>

      {/* Why Learners Choose Accredit */}
      <section className="py-24 bg-secondary/30 border-y border-border/50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center max-w-6xl mx-auto">
            {/* Left: Text Content */}
            <div className="space-y-6">
              <div>
                <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Why learners choose Accredit</h2>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Your professional development journey, simplified and secure.
                </p>
              </div>

              <p className="text-muted-foreground leading-relaxed">
                Browse thousands of CPD events and courses, filter by topic or date, and register in seconds with no complicated forms. All your certificates and credits are tracked automatically in one secure dashboard, giving you instantly shareable credentials that employers and regulators can verify online. Never lose track of your professional development again.
              </p>

              <div className="pt-4">
                <Link to="/events/browse">
                  <Button size="lg" variant="outline" className="h-12 px-8">
                    Browse Training
                    <Search className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>

            {/* Right: Icon Grid */}
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3">
                  <Search className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">Easy Discovery</p>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-green-500/10 text-green-500 flex items-center justify-center mb-3">
                  <MousePointerClick className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">Quick Registration</p>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center mb-3">
                  <Wallet className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">CPD Wallet</p>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center mb-3">
                  <Award className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">Verified Credentials</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Why Providers Choose Accredit */}
      <section className="py-24 bg-background">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-12 items-center max-w-6xl mx-auto">
            {/* Left: Icon Grid */}
            <div className="grid grid-cols-2 gap-6 order-2 lg:order-1">
              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-3">
                  <Shield className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">Enterprise Reliability</p>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center mb-3">
                  <Zap className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">Automated Workflows</p>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-secondary text-foreground flex items-center justify-center mb-3">
                  <Clock className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">Global Standards</p>
              </div>

              <div className="bg-card rounded-2xl p-6 border border-border shadow-sm flex flex-col items-center justify-center text-center min-h-[160px]">
                <div className="h-12 w-12 rounded-xl bg-green-500/10 text-green-500 flex items-center justify-center mb-3">
                  <Banknote className="h-6 w-6" />
                </div>
                <p className="font-semibold text-foreground text-sm">Direct Payments</p>
              </div>
            </div>

            {/* Right: Text Content */}
            <div className="space-y-6 order-1 lg:order-2">
              <div>
                <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Why providers choose Accredit</h2>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Built for reliability, compliance, and efficiency.
                </p>
              </div>

              <p className="text-muted-foreground leading-relaxed">
                Our platform scales automatically to handle events of any size with zero downtime. Save hours every week with automated attendance tracking, certificate generation, and reminder emails. Issue verifiable credentials that meet international CPD/CME requirements and get paid directly via Stripe Connect to your bank account.
              </p>

              <div className="pt-4">
                <Link to="/pricing">
                  <Button size="lg" className="h-12 px-8 shadow-xl shadow-primary/20 glow-primary">
                    View Pricing
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-card border-t border-border">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-6">
            Ready to get started?
          </h2>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join the professionals already using Accredit
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/events/browse">
              <Button size="lg" variant="outline" className="h-14 px-10 text-lg w-full sm:w-auto">
                Browse Training
                <Search className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link to="/pricing">
              <Button size="lg" className="h-14 px-10 text-lg shadow-xl shadow-primary/20 glow-primary w-full sm:w-auto">
                Start Creating
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span>Free for learners</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span>Free trial for providers</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
