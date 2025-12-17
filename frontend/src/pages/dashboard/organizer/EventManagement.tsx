import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { 
  Users, 
  CheckCircle, 
  Clock, 
  Search, 
  Download, 
  Mail, 
  MoreVertical,
  QrCode,
  Award,
  Filter
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from "@/components/ui/dropdown-menu";
import { Checkbox } from "@/components/ui/checkbox";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { PageHeader } from "@/components/custom/PageHeader";
import { StatusBadge } from "@/components/custom/StatusBadge";
import { mockEvents } from "@/lib/mock-data";
import { toast } from "sonner";

// Mock data for attendees
const mockAttendees = [
  { id: "1", name: "Alice Freeman", email: "alice@example.com", status: "Registered", checkIn: null, ticket: "General" },
  { id: "2", name: "Bob Smith", email: "bob@example.com", status: "Checked In", checkIn: "08:45 AM", ticket: "VIP" },
  { id: "3", name: "Charlie Davis", email: "charlie@example.com", status: "Registered", checkIn: null, ticket: "General" },
  { id: "4", name: "Diana Prince", email: "diana@example.com", status: "Cancelled", checkIn: null, ticket: "General" },
  { id: "5", name: "Evan Wright", email: "evan@example.com", status: "Checked In", checkIn: "09:00 AM", ticket: "General" },
];

export function EventManagement() {
  const { id } = useParams<{ id: string }>();
  const event = mockEvents.find(e => e.id === id) || mockEvents[0];
  const [attendees, setAttendees] = useState(mockAttendees);
  const [searchTerm, setSearchTerm] = useState("");

  // Handler for Check-in
  const handleCheckIn = (attendeeId: string) => {
    setAttendees(prev => prev.map(a => {
      if (a.id === attendeeId) {
        const isCheckedIn = a.status === "Checked In";
        return {
          ...a,
          status: isCheckedIn ? "Registered" : "Checked In",
          checkIn: isCheckedIn ? null : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
      }
      return a;
    }));
    toast.success("Attendance updated");
  };

  const handleIssueCertificate = (attendeeId: string) => {
    toast.success("Certificate issued successfully");
  };

  const handleIssueAllCertificates = () => {
    toast.success("Processing certificates for all attended users...");
  };

  const filteredAttendees = attendees.filter(a => 
    a.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    a.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const stats = {
    registered: attendees.filter(a => a.status !== "Cancelled").length,
    checkedIn: attendees.filter(a => a.status === "Checked In").length,
    cancelled: attendees.filter(a => a.status === "Cancelled").length,
  };

  return (
    <div className="space-y-8">
      <PageHeader 
        title={event.title}
        description={`Manage registrations and attendance for your ${event.type}.`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline">Edit Event</Button>
            <Button className="bg-blue-600 hover:bg-blue-700">View Public Page</Button>
          </div>
        }
      >
        <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-gray-500">
           <StatusBadge status={event.status} />
           <div className="flex items-center gap-1">
             <Clock className="h-4 w-4" />
             {new Date(event.startDate).toLocaleDateString()} at {event.startTime}
           </div>
           <div>•</div>
           <div>{event.attendees} / {event.capacity} Capacity</div>
        </div>
      </PageHeader>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
           <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">Total Registrations</CardTitle>
           </CardHeader>
           <CardContent>
              <div className="text-2xl font-bold">{stats.registered}</div>
              <p className="text-xs text-gray-500 mt-1">
                 {(stats.registered / event.capacity * 100).toFixed(0)}% of capacity
              </p>
           </CardContent>
        </Card>
        <Card>
           <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">Checked In</CardTitle>
           </CardHeader>
           <CardContent>
              <div className="text-2xl font-bold">{stats.checkedIn}</div>
              <p className="text-xs text-gray-500 mt-1">
                 {stats.registered > 0 ? (stats.checkedIn / stats.registered * 100).toFixed(0) : 0}% attendance rate
              </p>
           </CardContent>
        </Card>
        <Card>
           <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">Certificates Issued</CardTitle>
           </CardHeader>
           <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-gray-500 mt-1">
                 Pending event completion
              </p>
           </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="registrations" className="w-full">
        <TabsList className="w-full justify-start border-b border-gray-200 bg-transparent p-0 h-auto rounded-none mb-6">
           <TabsTrigger value="registrations" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none">
             Registrations
           </TabsTrigger>
           <TabsTrigger value="attendance" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none">
             Attendance
           </TabsTrigger>
           <TabsTrigger value="certificates" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 data-[state=active]:bg-transparent shadow-none">
             Certificates
           </TabsTrigger>
        </TabsList>

        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-4">
           <div className="relative w-full sm:w-80">
             <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
             <Input 
               placeholder="Search attendees..." 
               className="pl-9"
               value={searchTerm}
               onChange={(e) => setSearchTerm(e.target.value)}
             />
           </div>
           <div className="flex gap-2 w-full sm:w-auto">
              <Button variant="outline" size="sm" className="w-full sm:w-auto">
                 <Filter className="mr-2 h-4 w-4" /> Filter
              </Button>
              <Button variant="outline" size="sm" className="w-full sm:w-auto">
                 <Download className="mr-2 h-4 w-4" /> Export CSV
              </Button>
           </div>
        </div>

        {/* REGISTRATIONS TAB */}
        <TabsContent value="registrations" className="mt-0">
          <Card>
            <div className="overflow-x-auto">
               <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                     <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Attendee</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticket Type</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 relative"><span className="sr-only">Actions</span></th>
                     </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                     {filteredAttendees.map((attendee) => (
                        <tr key={attendee.id} className="hover:bg-gray-50">
                           <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                 <Avatar className="h-8 w-8 mr-3">
                                    <AvatarImage src={`https://ui-avatars.com/api/?name=${attendee.name}`} />
                                    <AvatarFallback>{attendee.name.charAt(0)}</AvatarFallback>
                                 </Avatar>
                                 <div>
                                    <div className="text-sm font-medium text-gray-900">{attendee.name}</div>
                                    <div className="text-xs text-gray-500">{attendee.email}</div>
                                 </div>
                              </div>
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {attendee.ticket}
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap">
                              <Badge 
                                variant="outline" 
                                className={
                                   attendee.status === "Cancelled" 
                                   ? "text-red-600 border-red-200 bg-red-50" 
                                   : "text-green-600 border-green-200 bg-green-50"
                                }
                              >
                                 {attendee.status}
                              </Badge>
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <DropdownMenu>
                                 <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" className="h-8 w-8 p-0">
                                       <MoreVertical className="h-4 w-4" />
                                    </Button>
                                 </DropdownMenuTrigger>
                                 <DropdownMenuContent align="end">
                                    <DropdownMenuItem>View Profile</DropdownMenuItem>
                                    <DropdownMenuItem>Send Email</DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem className="text-red-600">Cancel Registration</DropdownMenuItem>
                                 </DropdownMenuContent>
                              </DropdownMenu>
                           </td>
                        </tr>
                     ))}
                  </tbody>
               </table>
            </div>
          </Card>
        </TabsContent>

        {/* ATTENDANCE TAB */}
        <TabsContent value="attendance" className="mt-0">
          <Card>
             <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                <div className="text-sm text-gray-500">
                   Mark attendance manually or use the QR scanner app.
                </div>
                <Button size="sm" variant="outline" className="gap-2">
                   <QrCode className="h-4 w-4" /> Launch Scanner
                </Button>
             </div>
            <div className="overflow-x-auto">
               <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                     <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-10">
                           Present
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Attendee</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Check-in Time</th>
                     </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                     {filteredAttendees.filter(a => a.status !== "Cancelled").map((attendee) => (
                        <tr key={attendee.id} className="hover:bg-gray-50">
                           <td className="px-6 py-4 whitespace-nowrap">
                              <Checkbox 
                                 checked={attendee.status === "Checked In"} 
                                 onCheckedChange={() => handleCheckIn(attendee.id)}
                              />
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                 <div>
                                    <div className="text-sm font-medium text-gray-900">{attendee.name}</div>
                                    <div className="text-xs text-gray-500">{attendee.email}</div>
                                 </div>
                              </div>
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {attendee.checkIn || "-"}
                           </td>
                        </tr>
                     ))}
                  </tbody>
               </table>
            </div>
          </Card>
        </TabsContent>

        {/* CERTIFICATES TAB */}
        <TabsContent value="certificates" className="mt-0">
           <div className="mb-4 flex justify-between items-center bg-blue-50 border border-blue-100 p-4 rounded-lg">
              <div className="flex gap-3">
                 <div className="bg-blue-100 p-2 rounded-full h-10 w-10 flex items-center justify-center text-blue-600">
                    <Award className="h-5 w-5" />
                 </div>
                 <div>
                    <h3 className="text-sm font-bold text-blue-900">Ready to issue?</h3>
                    <p className="text-sm text-blue-700">
                       You have {stats.checkedIn} verified attendees eligible for certificates.
                    </p>
                 </div>
              </div>
              <Button onClick={handleIssueAllCertificates} className="bg-blue-600 hover:bg-blue-700">
                 Issue All Certificates
              </Button>
           </div>

           <Card>
            <div className="overflow-x-auto">
               <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                     <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Attendee</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Eligibility</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Certificate Status</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                     </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                     {filteredAttendees.filter(a => a.status !== "Cancelled").map((attendee) => (
                        <tr key={attendee.id} className="hover:bg-gray-50">
                           <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-gray-900">{attendee.name}</div>
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap">
                              {attendee.status === "Checked In" ? (
                                 <Badge variant="outline" className="text-green-600 bg-green-50 border-green-200">Eligible</Badge>
                              ) : (
                                 <Badge variant="outline" className="text-gray-500 bg-gray-50 border-gray-200">Not Attended</Badge>
                              )}
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              Not Issued
                           </td>
                           <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <Button 
                                 size="sm" 
                                 variant="outline" 
                                 disabled={attendee.status !== "Checked In"}
                                 onClick={() => handleIssueCertificate(attendee.id)}
                              >
                                 Issue
                              </Button>
                           </td>
                        </tr>
                     ))}
                  </tbody>
               </table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
