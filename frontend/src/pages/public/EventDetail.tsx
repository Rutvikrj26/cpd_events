import React from "react";
import { useParams, Link } from "react-router-dom";
import { 
  Calendar, 
  Clock, 
  MapPin, 
  User, 
  Award, 
  Share2, 
  CheckCircle, 
  AlertCircle,
  Video
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { mockEvents } from "@/lib/mock-data";
import { StatusBadge } from "@/components/custom/StatusBadge";
import { PageHeader } from "@/components/custom/PageHeader";

export function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const event = mockEvents.find(e => e.id === id) || mockEvents[0]; // Fallback to first event for demo

  // Mock registration state
  const isRegistered = event.isRegistered;
  const isPast = new Date(event.startDate) < new Date();

  return (
    <div className="bg-gray-50 min-h-screen pb-12">
      {/* Hero Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          <div className="flex flex-col lg:flex-row gap-8 items-start">
            <div className="flex-1 space-y-4">
              <div className="flex flex-wrap gap-2 items-center">
                <StatusBadge status={event.status} />
                <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50">
                  {event.type}
                </Badge>
                <Badge variant="outline" className="border-gray-300">
                  {event.creditType} • {event.credits} Credits
                </Badge>
              </div>
              
              <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 tracking-tight">
                {event.title}
              </h1>
              
              <div className="flex flex-col sm:flex-row gap-4 sm:gap-8 text-gray-500 pt-2">
                <div className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium">
                    {new Date(event.startDate).toLocaleDateString(undefined, { 
                      weekday: 'long', 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric' 
                    })}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium">
                    {event.startTime} ({event.duration})
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium">
                    by <span className="text-gray-900">{event.organizer}</span>
                  </span>
                </div>
              </div>
            </div>
            
            <div className="flex gap-3">
              <Button variant="outline" size="icon">
                <Share2 className="h-4 w-4" />
              </Button>
              {isRegistered ? (
                 <Button disabled className="bg-green-600 text-white opacity-100">
                   <CheckCircle className="mr-2 h-4 w-4" /> Registered
                 </Button>
              ) : isPast ? (
                 <Button disabled>Event Ended</Button>
              ) : (
                <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
                  Register Now
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            <div className="aspect-video w-full overflow-hidden rounded-xl border border-gray-200 shadow-sm">
              <img 
                src={event.image} 
                alt={event.title} 
                className="h-full w-full object-cover"
              />
            </div>

            <Tabs defaultValue="about" className="w-full">
              <TabsList className="w-full justify-start border-b border-gray-200 bg-transparent p-0 h-auto rounded-none space-x-8">
                <TabsTrigger 
                  value="about" 
                  className="rounded-none border-b-2 border-transparent px-0 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none"
                >
                  About
                </TabsTrigger>
                <TabsTrigger 
                  value="schedule" 
                  className="rounded-none border-b-2 border-transparent px-0 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none"
                >
                  Schedule
                </TabsTrigger>
                <TabsTrigger 
                  value="speakers" 
                  className="rounded-none border-b-2 border-transparent px-0 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none"
                >
                  Speakers
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="about" className="pt-6 space-y-6">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">Event Description</h3>
                  <p className="text-gray-600 leading-relaxed whitespace-pre-line">
                    {event.description}
                  </p>
                  <p className="text-gray-600 leading-relaxed mt-4">
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
                  </p>
                </div>

                <Separator />

                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-4">What you'll learn</h3>
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {[1, 2, 3, 4].map((i) => (
                      <li key={i} className="flex items-start gap-2">
                        <CheckCircle className="h-5 w-5 text-green-500 shrink-0 mt-0.5" />
                        <span className="text-gray-600 text-sm">Understand key concepts and methodologies in the field.</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </TabsContent>

              <TabsContent value="schedule" className="pt-6">
                 <div className="space-y-6">
                    <div className="flex gap-4">
                       <div className="w-24 shrink-0 text-sm font-bold text-gray-900 pt-1">09:00 AM</div>
                       <div className="pb-6 border-l border-gray-200 pl-6 relative">
                          <div className="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full bg-blue-600" />
                          <h4 className="font-semibold text-gray-900">Introduction & Keynote</h4>
                          <p className="text-sm text-gray-500 mt-1">Dr. Sarah Johnson</p>
                       </div>
                    </div>
                    <div className="flex gap-4">
                       <div className="w-24 shrink-0 text-sm font-bold text-gray-900 pt-1">10:30 AM</div>
                       <div className="pb-6 border-l border-gray-200 pl-6 relative">
                          <div className="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full bg-gray-300" />
                          <h4 className="font-semibold text-gray-900">Deep Dive Session 1</h4>
                          <p className="text-sm text-gray-500 mt-1">Technical Review Panel</p>
                       </div>
                    </div>
                 </div>
              </TabsContent>
              
              <TabsContent value="speakers" className="pt-6">
                 <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg">
                       <Avatar className="h-12 w-12">
                          <AvatarImage src="https://github.com/shadcn.png" />
                          <AvatarFallback>SJ</AvatarFallback>
                       </Avatar>
                       <div>
                          <h4 className="font-semibold text-gray-900">Dr. Sarah Johnson</h4>
                          <p className="text-sm text-gray-500">Chief of Medicine</p>
                       </div>
                    </div>
                 </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <Card className="shadow-md border-gray-200">
              <CardHeader>
                <CardTitle>Registration</CardTitle>
                <CardDescription>Secure your spot today.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-gray-600">Price</span>
                  <span className="font-bold text-xl text-gray-900">
                    {event.price === "Free" ? "Free" : `$${event.price}`}
                  </span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-100">
                  <span className="text-gray-600">Capacity</span>
                  <span className="text-gray-900">{event.attendees} / {event.capacity} registered</span>
                </div>
                
                {isRegistered ? (
                  <div className="bg-green-50 p-4 rounded-lg border border-green-100 text-center space-y-2">
                    <div className="flex justify-center">
                       <CheckCircle className="h-8 w-8 text-green-600" />
                    </div>
                    <p className="font-medium text-green-800">You are registered!</p>
                    <p className="text-sm text-green-700">
                      Check your email for confirmation and join details.
                    </p>
                  </div>
                ) : (
                  <Button className="w-full bg-blue-600 hover:bg-blue-700 text-lg py-6">
                    Register Now
                  </Button>
                )}
                
                <p className="text-xs text-center text-gray-500">
                  Registration closes {new Date(event.startDate).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Organizer</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded bg-blue-100 flex items-center justify-center text-blue-700 font-bold">
                    {event.organizer.charAt(0)}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{event.organizer}</div>
                    <div className="text-xs text-gray-500">View Profile</div>
                  </div>
                </div>
                <Button variant="outline" className="w-full text-xs h-8">Contact Organizer</Button>
              </CardContent>
            </Card>

             <Card>
              <CardHeader>
                <CardTitle className="text-base">Location</CardTitle>
              </CardHeader>
              <CardContent>
                 <div className="flex items-start gap-2 text-sm text-gray-600">
                    <Video className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>
                       <p className="font-medium text-gray-900">Online Event</p>
                       <p className="mt-1">Link provided upon registration</p>
                    </div>
                 </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
