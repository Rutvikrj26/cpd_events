
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
            One platform to host live events, build self-paced courses, and manage your organization's entire training delivery.
          </p>

          <div className="flex flex-wrap justify-center gap-6">
            <Link to="/products/events">
              <Button variant="outline" size="lg" className="h-14 px-8 text-lg hover:border-primary/50 hover:bg-primary/5">
                <Calendar className="mr-2 h-5 w-5 text-primary" />
                Explore Events
              </Button>
            </Link>
            <Link to="/products/lms">
              <Button variant="outline" size="lg" className="h-14 px-8 text-lg hover:border-accent/50 hover:bg-accent/5">
                <BookOpen className="mr-2 h-5 w-5 text-accent" />
                Explore LMS
              </Button>
            </Link>
            <Link to="/products/organizations">
              <Button variant="outline" size="lg" className="h-14 px-8 text-lg hover:border-foreground/50 hover:bg-foreground/5">
                <Building2 className="mr-2 h-5 w-5 text-foreground" />
                Explore Orgs
              </Button>
            </Link>
          </div>
        </div>

        {/* Background Gradients */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 -z-10 h-[600px] w-[600px] bg-primary/5 blur-[120px] rounded-full"></div>
      </section>

      {/* Product Selection Section */}
      <section className="py-24 bg-secondary/30 border-y border-border/50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-foreground">Choose your path</h2>
            <p className="text-muted-foreground mt-4 text-lg">Select the product that fits your needs</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Events Card */}
            <Link to="/products/events" className="group">
              <div className="bg-card h-full rounded-2xl border border-border p-8 shadow-sm hover:shadow-elevated hover:border-primary/50 transition-all duration-300 relative overflow-hidden">
                <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-6">
                  <Calendar className="h-6 w-6" />
                </div>
                <h3 className="text-2xl font-bold text-foreground mb-4">Event Management</h3>
                <p className="text-muted-foreground mb-8 min-h-[80px]">
                  Host webinars, workshops, and conferences with automated CPD certificates and Zoom integration.
                </p>
                <div className="flex items-center text-primary font-medium group-hover:translate-x-1 transition-transform">
                  Learn more <ArrowRight className="ml-2 h-4 w-4" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>

            {/* LMS Card */}
            <Link to="/products/lms" className="group">
              <div className="bg-card h-full rounded-2xl border border-border p-8 shadow-sm hover:shadow-elevated hover:border-accent/50 transition-all duration-300 relative overflow-hidden">
                <div className="h-12 w-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center mb-6">
                  <BookOpen className="h-6 w-6" />
                </div>
                <h3 className="text-2xl font-bold text-foreground mb-4">LMS & Courses</h3>
                <p className="text-muted-foreground mb-8 min-h-[80px]">
                  Build self-paced courses, quizzes, and digital products. Track progress and issue certificates.
                </p>
                <div className="flex items-center text-accent font-medium group-hover:translate-x-1 transition-transform">
                  Learn more <ArrowRight className="ml-2 h-4 w-4" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>

            {/* Org Card */}
            <Link to="/products/organizations" className="group">
              <div className="bg-card h-full rounded-2xl border border-border p-8 shadow-sm hover:shadow-elevated hover:border-foreground/20 transition-all duration-300 relative overflow-hidden">
                <div className="h-12 w-12 rounded-xl bg-secondary text-foreground flex items-center justify-center mb-6">
                  <Building2 className="h-6 w-6" />
                </div>
                <h3 className="text-2xl font-bold text-foreground mb-4">Organizations</h3>
                <p className="text-muted-foreground mb-8 min-h-[80px]">
                  Manage your team, sync contacts, monetize content, and consolidate billing in one dashboard.
                </p>
                <div className="flex items-center text-foreground font-medium group-hover:translate-x-1 transition-transform">
                  Learn more <ArrowRight className="ml-2 h-4 w-4" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-secondary to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Why Choose Section */}
      <section className="py-24 bg-background">
        <div className="container mx-auto px-4">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-foreground mb-4">Why professionals choose Accredit</h2>
            <p className="text-lg text-muted-foreground">Built for reliability, compliance, and speed.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 text-center px-4">
            <div className="space-y-4">
              <div className="mx-auto h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <Shield className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">Fail-safe Reliability</h3>
              <p className="text-muted-foreground">99.9% uptime guarantee. Our platform scales automatically to handle events of any size.</p>
            </div>

            <div className="space-y-4">
              <div className="mx-auto h-12 w-12 rounded-xl bg-accent/10 text-accent flex items-center justify-center">
                <Zap className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">Automated Efficiency</h3>
              <p className="text-muted-foreground">Save 10+ hours per week. We handle the busywork of attendance tracking and certification.</p>
            </div>

            <div className="space-y-4">
              <div className="mx-auto h-12 w-12 rounded-xl bg-secondary text-foreground flex items-center justify-center">
                <Clock className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-semibold text-foreground">Global Compliance</h3>
              <p className="text-muted-foreground">Verifiable digital credentials that meet international CPD/CME standards.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-card border-t border-border">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground mb-6">
            Start your free trial today
          </h2>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join thousands of professionals issuing verified certificates.
          </p>
          <Link to="/signup">
            <Button size="lg" className="h-14 px-10 text-lg shadow-xl shadow-primary/20 glow-primary">
              Get Started Free
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
          <div className="mt-6 flex items-center justify-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span>free trial</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span>Cancel anytime</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
