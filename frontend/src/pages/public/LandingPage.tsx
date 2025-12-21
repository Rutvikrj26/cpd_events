import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Play, Shield, Users, Award, Calendar, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { getPublicEvents } from "@/api/events";
import { Event } from "@/api/events/types";
import heroImage from "@/assets/images/hero-platform.png";

export function LandingPage() {
  const [featuredEvents, setFeaturedEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEvents() {
      try {
        const events = await getPublicEvents();
        setFeaturedEvents(events.slice(0, 3));
      } catch (error) {
        console.error("Failed to load events", error);
      } finally {
        setLoading(false);
      }
    }
    fetchEvents();
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 md:pt-20 lg:pt-32 pb-20 lg:pb-32 bg-background">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">

            {/* Text Content */}
            <div className="max-w-2xl text-center lg:text-left mx-auto lg:mx-0">
              <div className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-primary/10 text-primary mb-6">
                <span className="flex h-2 w-2 rounded-full bg-primary mr-2"></span>
                The #1 Platform for CPD
              </div>
              <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-6xl text-foreground mb-6">
                Professional growth, <br className="hidden lg:block" />
                <span className="text-primary bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
                  simplified & automated.
                </span>
              </h1>
              <p className="text-xl text-muted-foreground mb-8 leading-relaxed max-w-lg mx-auto lg:mx-0">
                Host events, track attendance, and issue certificates automatically. The complete ecosystem for continuous professional development.
              </p>

              <div className="flex flex-col sm:flex-row items-center gap-4 justify-center lg:justify-start">
                <Link to="/signup">
                  <Button size="lg" className="h-12 px-8 text-base shadow-lg shadow-blue-500/20">
                    Get Started Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
                <Link to="/events/browse">
                  <Button variant="outline" size="lg" className="h-12 px-8 text-base bg-background/50 backdrop-blur-sm">
                    Browse Events
                  </Button>
                </Link>
              </div>

              <div className="mt-10 flex items-center justify-center lg:justify-start gap-x-8 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  <span>Instant Certificates</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  <span>Zoom Integration</span>
                </div>
              </div>
            </div>

            {/* Visual Content */}
            <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
              <div className="relative rounded-2xl bg-gradient-to-b from-blue-50 to-white p-2 ring-1 ring-inset ring-slate-200/50 shadow-2xl overflow-hidden glass">

                <img
                  src={heroImage}
                  alt="CPD Platform Dashboard"
                  className="w-full rounded-xl shadow-inner bg-slate-50"
                />

                {/* Floating Badge 1 */}
                <div className="absolute -left-4 top-20 bg-white p-4 rounded-xl shadow-xl border border-slate-100 hidden md:block animate-in slide-in-from-left-4 duration-1000 delay-300 fill-mode-forwards">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                      <Award className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-900">Certificate Issued</p>
                      <p className="text-xs text-slate-500">Just now</p>
                    </div>
                  </div>
                </div>

                {/* Floating Badge 2 */}
                <div className="absolute -right-4 bottom-20 bg-white p-4 rounded-xl shadow-xl border border-slate-100 hidden md:block animate-in slide-in-from-right-4 duration-1000 delay-500 fill-mode-forwards">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                      <Users className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-900">120 Attendees</p>
                      <p className="text-xs text-slate-500">Live Session</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Background Decoration */}
              <div className="absolute -top-24 -right-24 -z-10 h-[400px] w-[400px] bg-gradient-to-br from-blue-400/20 to-purple-400/20 blur-3xl rounded-full opacity-50"></div>
              <div className="absolute -bottom-24 -left-24 -z-10 h-[400px] w-[400px] bg-gradient-to-tr from-cyan-400/20 to-blue-400/20 blur-3xl rounded-full opacity-50"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof / Trust */}
      <section className="border-y border-border/40 bg-slate-50/50 py-10">
        <div className="container mx-auto px-4 text-center">
          <p className="text-sm font-medium text-muted-foreground mb-6">TRUSTED BY FORWARD-THINKING ORGANIZATIONS</p>
          <div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-8 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
            {/* Placeholders for logos */}
            <div className="text-lg font-bold text-slate-900">ACME Corp</div>
            <div className="text-lg font-bold text-slate-900">GlobalHealth</div>
            <div className="text-lg font-bold text-slate-900">EduTech Inc</div>
            <div className="text-lg font-bold text-slate-900">FutureSkills</div>
            <div className="text-lg font-bold text-slate-900">LegalOne</div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-background relative">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">Everything needed to run professional events</h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Powerful tools for organizers, seamless experience for attendees.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FeatureCard
              icon={Award}
              title="Automated Certificates"
              description="Customize and issue verifiable certificates instantly upon event completion."
            />
            <FeatureCard
              icon={Users}
              title="Smart Attendance"
              description="Direct Zoom integration to track exactly when attendees join and leave."
            />
            <FeatureCard
              icon={Shield}
              title="Compliance Ready"
              description="Built to meet strict accreditation standards for CME, CLE, and CPE boards."
            />
          </div>
        </div>
      </section>

      {/* Featured Events Preview */}
      <section className="py-24 bg-slate-50/50 border-t border-border/40">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-end mb-10">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-foreground">Trending Events</h2>
              <p className="mt-2 text-muted-foreground">Join thousands of professionals learning today.</p>
            </div>
            <Link to="/events/browse" className="hidden sm:block">
              <Button variant="ghost" className="text-primary hover:text-primary/80">
                View all events <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>

          {loading ? (
            <div className="text-center py-20 text-muted-foreground">Loading events...</div>
          ) : featuredEvents.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {featuredEvents.map(event => (
                <EventCardFromApi key={event.uuid} event={event} />
              ))}
            </div>
          ) : (
            <div className="text-center py-20 border-2 border-dashed border-slate-200 rounded-2xl">
              <Calendar className="h-10 w-10 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900">No upcoming events</h3>
              <p className="text-slate-500 mt-1">Check back soon for new learning opportunities.</p>
            </div>
          )}

          <div className="mt-12 text-center sm:hidden">
            <Link to="/events/browse">
              <Button variant="outline" className="w-full">View all events</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-slate-900 text-white relative overflow-hidden">
        {/* Abstract shapes */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl"></div>

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">Ready to transform your professional development?</h2>
          <p className="text-slate-300 max-w-2xl mx-auto mb-10 text-lg">
            Join the platform that powers the next generation of professional learning. Free to get started.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/signup">
              <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 min-w-[160px] h-14 text-lg font-semibold border-0">
                Sign Up Free
              </Button>
            </Link>
            <Link to="/contact">
              <Button size="lg" variant="outline" className="border-slate-700 text-white hover:bg-slate-800 hover:text-white min-w-[160px] h-14 bg-transparent">
                Contact Sales
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, description }: { icon: any, title: string, description: string }) {
  return (
    <div className="group bg-card p-8 rounded-2xl border border-border shadow-sm hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
      <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-xl font-semibold text-foreground mb-3">{title}</h3>
      <p className="text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

// Adapter component to display API Event in card format
function EventCardFromApi({ event }: { event: Event }) {
  return (
    <Link to={`/events/${event.slug || event.uuid}`} className="group block h-full">
      <Card className="h-full overflow-hidden hover:shadow-xl transition-all duration-300 border-border/60 hover:border-primary/50 group-hover:-translate-y-1">
        <div className="h-48 bg-gradient-to-br from-slate-100 to-slate-200 relative flex items-center justify-center overflow-hidden">
          {/* Placeholder for real image */}
          <div className="absolute inset-0 bg-blue-600/5 group-hover:bg-blue-600/10 transition-colors"></div>
          <Calendar className="h-10 w-10 text-slate-300 group-hover:scale-110 transition-transform duration-500" />

          <div className="absolute top-4 right-4">
            <Badge variant={event.format === 'online' ? 'secondary' : 'default'} className="uppercase text-[10px] tracking-wider font-bold shadow-sm backdrop-blur-md bg-white/90 text-slate-900 hover:bg-white">
              {event.format}
            </Badge>
          </div>
          {event.registration_enabled && (
            <div className="absolute bottom-4 left-4">
              <Badge className="bg-green-500 hover:bg-green-600 text-white border-0 shadow-sm">
                Open
              </Badge>
            </div>
          )}
        </div>
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3 font-medium uppercase tracking-wider">
            <span className="text-primary">{event.event_type}</span>
            <span>•</span>
            <span>{new Date(event.starts_at).toLocaleDateString()}</span>
          </div>
          <h3 className="font-bold text-xl text-foreground group-hover:text-primary transition-colors line-clamp-2 mb-3 leading-tight">
            {event.title}
          </h3>
          <p className="text-sm text-muted-foreground line-clamp-2 mb-6">
            {event.short_description || event.description}
          </p>
          <div className="flex items-center justify-between mt-auto">
            <div className="flex items-center text-xs font-medium text-slate-500">
              <Users className="h-3.5 w-3.5 mr-1" />
              <span>{event.registration_count || 0} Registered</span>
            </div>
            <Button size="sm" variant="ghost" className="text-primary p-0 hover:bg-transparent hover:underline">
              Details <ExternalLink className="ml-1 h-3 w-3" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
