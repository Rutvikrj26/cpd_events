import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Play, Shield, Users, Award, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EventCard } from "@/components/custom/EventCard";
import { mockEvents } from "@/lib/mock-data";

export function LandingPage() {
  const featuredEvents = mockEvents.slice(0, 3);

  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-white pt-16 pb-20 lg:pt-24 lg:pb-28">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
              Professional Development <span className="text-blue-600">Reimagined</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              The complete platform for hosting, attending, and tracking Continuing Professional Development (CPD) events. Seamless certificates, automated tracking, and engaging learning experiences.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link to="/signup">
                <Button size="lg" className="h-12 px-8 text-base bg-blue-600 hover:bg-blue-700">
                  Get Started for Free
                </Button>
              </Link>
              <Link to="/events/browse">
                <Button variant="outline" size="lg" className="h-12 px-8 text-base group">
                  Browse Events <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
        
        {/* Abstract Background Decoration */}
        <div className="absolute inset-0 -z-10 h-full w-full bg-white bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px] [mask-image:radial-gradient(ellipse_50%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30"></div>
      </section>

      {/* Stats Section */}
      <section className="bg-blue-600 py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4 text-center text-white">
            <div className="space-y-2">
              <div className="text-3xl font-bold">50k+</div>
              <div className="text-blue-100 text-sm font-medium">Active Learners</div>
            </div>
            <div className="space-y-2">
              <div className="text-3xl font-bold">10k+</div>
              <div className="text-blue-100 text-sm font-medium">Events Hosted</div>
            </div>
            <div className="space-y-2">
              <div className="text-3xl font-bold">1M+</div>
              <div className="text-blue-100 text-sm font-medium">Credits Issued</div>
            </div>
            <div className="space-y-2">
              <div className="text-3xl font-bold">99.9%</div>
              <div className="text-blue-100 text-sm font-medium">Uptime</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-gray-50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">Everything you need to grow</h2>
            <p className="mt-4 text-lg text-gray-600">
              Whether you're organizing professional education or advancing your career, we have the tools you need.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={Award}
              title="Automated Certificates"
              description="Instant certificate issuance upon completion. Verified, secure, and easy to share on LinkedIn."
            />
            <FeatureCard 
              icon={Users}
              title="Seamless Attendance"
              description="Automatic Zoom integration tracks attendance down to the minute. No more manual spreadsheets."
            />
            <FeatureCard 
              icon={Shield}
              title="Compliance Ready"
              description="Built to meet accreditation standards for CME, CLE, CPE, and other professional boards."
            />
          </div>
        </div>
      </section>

      {/* Featured Events Preview */}
      <section className="py-24 bg-white">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-end mb-10">
            <div>
               <h2 className="text-3xl font-bold tracking-tight text-gray-900">Upcoming Events</h2>
               <p className="mt-2 text-gray-600">Discover professional development opportunities.</p>
            </div>
            <Link to="/events/browse" className="hidden sm:block">
              <Button variant="ghost" className="text-blue-600 hover:text-blue-700 hover:bg-blue-50">
                View all events <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {featuredEvents.map(event => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>

          <div className="mt-8 text-center sm:hidden">
            <Link to="/events/browse">
              <Button variant="outline" className="w-full">View all events</Button>
            </Link>
          </div>
        </div>
      </section>
      
      {/* Call to Action */}
      <section className="py-20 bg-gray-900 text-white text-center">
         <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold tracking-tight mb-6">Ready to get started?</h2>
            <p className="text-gray-300 max-w-2xl mx-auto mb-10 text-lg">
              Join thousands of professionals and organizations using CPD Events to manage their continuous learning journey.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
               <Link to="/signup">
                <Button size="lg" className="bg-white text-gray-900 hover:bg-gray-100 min-w-[160px]">
                  Sign Up Free
                </Button>
               </Link>
               <Link to="/contact">
                <Button size="lg" variant="outline" className="border-gray-700 text-white hover:bg-gray-800 min-w-[160px]">
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
    <div className="bg-white p-8 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
      <div className="h-12 w-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-6">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-3">{title}</h3>
      <p className="text-gray-600 leading-relaxed">{description}</p>
    </div>
  );
}
