import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
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
   Filter,
   Video,
   Copy,
   ExternalLink,
   RefreshCw,
   Trash2
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
import { toast } from "sonner";
import { getEvent, publishEvent, unpublishEvent, getEventRegistrations, checkInAttendee, deleteEvent } from "@/api/events";
import { issueCertificates } from "@/api/certificates";
import {
   AlertDialog,
   AlertDialogAction,
   AlertDialogCancel,
   AlertDialogContent,
   AlertDialogDescription,
   AlertDialogFooter,
   AlertDialogHeader,
   AlertDialogTitle,
   AlertDialogTrigger,
} from "@/components/ui/alert-dialog";



import { EditAttendanceDialog } from "@/components/events/EditAttendanceDialog";

export function EventManagement() {
   const { uuid } = useParams<{ uuid: string }>();
   const navigate = useNavigate();
   const [event, setEvent] = useState<any | null>(null);
   const [loading, setLoading] = useState(true);
   const [deleting, setDeleting] = useState(false);

   // Dialog State
   const [editAttendanceOpen, setEditAttendanceOpen] = useState(false);
   const [selectedAttendee, setSelectedAttendee] = useState<any>(null);

   useEffect(() => {
      async function fetchEvent() {
         if (!uuid) return;
         try {
            const data = await getEvent(uuid);
            setEvent(data);
         } catch (e) {
            console.error("Failed to fetch event", e);
            toast.error("Failed to load event details");
         } finally {
            setLoading(false);
         }
      }
      fetchEvent();
   }, [uuid]);

   const [attendees, setAttendees] = useState<any[]>([]);
   const [searchTerm, setSearchTerm] = useState("");
   const [publishing, setPublishing] = useState(false);

   const fetchRegistrations = async () => {
      if (!uuid) return;
      try {
         const regs = await getEventRegistrations(uuid);
         setAttendees(regs);
      } catch (e) {
         console.error("Failed to fetch registrations", e);
      }
   };

   // Fetch registrations for the event
   useEffect(() => {
      fetchRegistrations();
   }, [uuid]);

   const hasStarted = event ? new Date(event.starts_at) < new Date() : false;

   if (loading || !event) {
      return <div className="p-8">Loading event details...</div>;
   }

   // Handler for Check-in
   // Handler for Check-in
   // Handler for Check-in
   const handleCheckIn = async (attendeeUuid: string) => {
      // Find the attendee first to get current state
      const attendee = attendees.find(a => a.uuid === attendeeUuid);
      if (!attendee) return;

      const newAttended = !attendee.attended;

      // Optimistic Update
      setAttendees(prev => prev.map(a => {
         if (a.uuid === attendeeUuid) {
            return {
               ...a,
               attended: newAttended,
               checkIn: newAttended ? new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null
            };
         }
         return a;
      }));

      try {
         if (uuid) {
            const updatedReg = await checkInAttendee(uuid, attendeeUuid, newAttended);

            // Update with server response (logic: server returns updated object)
            // checkInAttendee returns the response data which in partial_update returns the serializer data
            setAttendees(prev => prev.map(a => {
               if (a.uuid === attendeeUuid) {
                  return {
                     ...a,
                     attended: updatedReg.attended,
                     check_in_time: updatedReg.check_in_time
                  };
               }
               return a;
            }));

            toast.success(newAttended ? "Attendee checked in" : "Check-in canceled");
         }
      } catch (error) {
         console.error("Check-in failed", error);
         toast.error("Failed to update check-in status");
         // Revert State
         setAttendees(prev => prev.map(a => {
            if (a.uuid === attendeeUuid) {
               // Revert to original state
               return {
                  ...a,
                  attended: !newAttended,
                  check_in_time: attendee.check_in_time
               };
            }
            return a;
         }));
      }
   };

   const handleIssueCertificate = async (registrationUuid: string) => {
      if (!uuid) return;
      try {
         await issueCertificates(uuid, { registration_uuids: [registrationUuid] });
         toast.success("Certificate issued successfully");
         fetchRegistrations();
      } catch (error: any) {
         toast.error(error?.response?.data?.detail || "Failed to issue certificate");
      }
   };

   const handleIssueAllCertificates = async () => {
      if (!uuid) return;
      try {
         const result = await issueCertificates(uuid, {});
         toast.success(`Issued ${result.issued} certificates (${result.skipped} skipped)`);
         fetchRegistrations();
      } catch (error: any) {
         toast.error(error?.response?.data?.detail || "Failed to issue certificates");
      }
   };


   const handlePublish = async () => {
      if (!uuid) return;
      setPublishing(true);
      try {
         await publishEvent(uuid);
         setEvent((prev: any) => prev ? { ...prev, status: 'published' } : prev);
         toast.success("Event published successfully! It's now visible to the public.");
      } catch (error: any) {
         toast.error(error?.response?.data?.message || "Failed to publish event");
      } finally {
         setPublishing(false);
      }
   };

   const handleUnpublish = async () => {
      if (!uuid) return;
      if (hasStarted) {
         toast.error("Cannot convert to draft after event has started");
         return;
      }

      setPublishing(true);
      try {
         await unpublishEvent(uuid);
         setEvent((prev: any) => prev ? { ...prev, status: 'draft' } : prev);
         toast.success("Event reverted to draft.");
      } catch (error: any) {
         toast.error(error?.response?.data?.message || "Failed to revert to draft");
      } finally {
         setPublishing(false);
      }
   };

   const handleDelete = async () => {
      if (!uuid) return;
      setDeleting(true);
      try {
         await deleteEvent(uuid);
         toast.success(`"${event.title}" has been deleted.`);
         navigate('/events');
      } catch (error: any) {
         toast.error(error?.response?.data?.message || "Failed to delete event");
         setDeleting(false);
      }
   };

   const filteredAttendees = attendees.filter(a =>
      (a.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (a.email || '').toLowerCase().includes(searchTerm.toLowerCase())
   );

   const stats = {
      registered: attendees.filter(a => a.status !== "cancelled").length,
      checkedIn: attendees.filter(a => a.attended).length,
      cancelled: attendees.filter(a => a.status === "cancelled").length,
      issued: attendees.filter(a => a.certificate_uuid).length,
   };

   return (
      <div className="space-y-8">
         <PageHeader
            title={event.title}
            description={`Manage registrations and attendance for your ${event.format || 'event'}.`}
            actions={
               <div className="flex gap-2">
                  {event.status === 'draft' && !hasStarted && (
                     <Button
                        onClick={handlePublish}
                        disabled={publishing}
                        className="bg-green-600 hover:bg-green-700"
                     >
                        {publishing ? 'Publishing...' : 'Publish Event'}
                     </Button>
                  )}
                  {event.status === 'published' && !hasStarted && (
                     <Button
                        onClick={handleUnpublish}
                        disabled={publishing}
                        variant="outline"
                        className="text-orange-600 border-orange-200 hover:bg-orange-50"
                     >
                        {publishing ? 'Updating...' : 'Convert to Draft'}
                     </Button>
                  )}
                  {hasStarted ? (
                     <Button variant="outline" disabled title="Event has started">Edit Event</Button>
                  ) : (
                     <Link to={`/events/${event.uuid}/edit`}>
                        <Button variant="outline">Edit Event</Button>
                     </Link>
                  )}
                  <Link to={`/events/${event.slug}`}>
                     <Button className="bg-blue-600 hover:bg-blue-700">View Public Page</Button>
                  </Link>
                  <AlertDialog>
                     <AlertDialogTrigger asChild>
                        <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700">
                           <Trash2 className="h-4 w-4 mr-2" />
                           Delete
                        </Button>
                     </AlertDialogTrigger>
                     <AlertDialogContent>
                        <AlertDialogHeader>
                           <AlertDialogTitle>Delete Event</AlertDialogTitle>
                           <AlertDialogDescription>
                              Are you sure you want to delete "{event.title}"? This action cannot be undone.
                           </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                           <AlertDialogCancel>Cancel</AlertDialogCancel>
                           <AlertDialogAction
                              onClick={handleDelete}
                              disabled={deleting}
                              className="bg-red-600 hover:bg-red-700"
                           >
                              {deleting ? 'Deleting...' : 'Delete Event'}
                           </AlertDialogAction>
                        </AlertDialogFooter>
                     </AlertDialogContent>
                  </AlertDialog>
               </div>
            }
         >
            <div className="flex flex-wrap items-center gap-4 mt-4 text-sm text-muted-foreground">
               <StatusBadge status={event.status} />
               <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {new Date(event.starts_at).toLocaleDateString()}
               </div>
               <div>•</div>
               <div>{event.capacity || 'Unlimited'} Capacity</div>
            </div>
         </PageHeader>

         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
               <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Registrations</CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">{stats.registered}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                     {(stats.registered / event.capacity * 100).toFixed(0)}% of capacity
                  </p>
               </CardContent>
            </Card>
            <Card>
               <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Checked In</CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">{stats.checkedIn}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                     {stats.registered > 0 ? (stats.checkedIn / stats.registered * 100).toFixed(0) : 0}% attendance rate
                  </p>
               </CardContent>
            </Card>
            <Card>
               <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Certificates Issued</CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">{stats.issued}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                     {stats.checkedIn > 0 ? (stats.issued / stats.checkedIn * 100).toFixed(0) : 0}% of attendees
                  </p>
               </CardContent>
            </Card>
         </div>

         {/* Zoom Meeting Details Card */}
         {event.zoom_settings?.enabled && (
            <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-900">
               <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                     <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/50">
                           <Video className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                           <CardTitle className="text-base">Zoom Meeting</CardTitle>
                           <CardDescription className="text-xs">
                              {event.zoom_meeting_id ? 'Meeting created and ready' : 'Meeting pending creation'}
                           </CardDescription>
                        </div>
                     </div>
                     {!event.zoom_meeting_id && (
                        <Button variant="outline" size="sm" className="gap-2">
                           <RefreshCw className="h-4 w-4" />
                           Retry Creation
                        </Button>
                     )}
                  </div>
               </CardHeader>
               {event.zoom_meeting_id && (
                  <CardContent className="pt-0">
                     <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Meeting ID */}
                        <div className="space-y-1">
                           <label className="text-xs font-medium text-muted-foreground">Meeting ID</label>
                           <div className="flex items-center gap-2">
                              <code className="flex-1 px-3 py-2 text-sm bg-background border rounded-md font-mono">
                                 {event.zoom_meeting_id}
                              </code>
                              <Button
                                 variant="ghost"
                                 size="icon"
                                 className="h-9 w-9"
                                 onClick={() => {
                                    navigator.clipboard.writeText(event.zoom_meeting_id);
                                    toast.success('Meeting ID copied');
                                 }}
                              >
                                 <Copy className="h-4 w-4" />
                              </Button>
                           </div>
                        </div>

                        {/* Password */}
                        <div className="space-y-1">
                           <label className="text-xs font-medium text-muted-foreground">Password</label>
                           <div className="flex items-center gap-2">
                              <code className="flex-1 px-3 py-2 text-sm bg-background border rounded-md font-mono">
                                 {event.zoom_passcode || '—'}
                              </code>
                              {event.zoom_passcode && (
                                 <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-9 w-9"
                                    onClick={() => {
                                       navigator.clipboard.writeText(event.zoom_passcode);
                                       toast.success('Password copied');
                                    }}
                                 >
                                    <Copy className="h-4 w-4" />
                                 </Button>
                              )}
                           </div>
                        </div>

                        {/* Join URL */}
                        <div className="space-y-1 md:col-span-2">
                           <label className="text-xs font-medium text-muted-foreground">Attendee Join URL</label>
                           <div className="flex items-center gap-2">
                              <code className="flex-1 px-3 py-2 text-sm bg-background border rounded-md font-mono truncate">
                                 {event.zoom_join_url}
                              </code>
                              <Button
                                 variant="ghost"
                                 size="icon"
                                 className="h-9 w-9"
                                 onClick={() => {
                                    navigator.clipboard.writeText(event.zoom_join_url);
                                    toast.success('Join URL copied');
                                 }}
                              >
                                 <Copy className="h-4 w-4" />
                              </Button>
                              <Button
                                 variant="ghost"
                                 size="icon"
                                 className="h-9 w-9"
                                 onClick={() => window.open(event.zoom_join_url, '_blank')}
                              >
                                 <ExternalLink className="h-4 w-4" />
                              </Button>
                           </div>
                        </div>
                     </div>
                  </CardContent>
               )}
            </Card>
         )}

         <Tabs defaultValue="registrations" className="w-full">
            <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none mb-6">
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
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
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
                     <table className="min-w-full divide-y divide-border">
                        <thead className="bg-muted/50">
                           <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Attendee</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Ticket Type</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                              <th className="px-6 py-3 relative"><span className="sr-only">Actions</span></th>
                           </tr>
                        </thead>
                        <tbody className="bg-card divide-y divide-border">
                           {filteredAttendees.map((attendee) => (
                              <tr key={attendee.uuid} className="hover:bg-muted/50">
                                 <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center">
                                       <Avatar className="h-8 w-8 mr-3">
                                          <AvatarImage src={`https://ui-avatars.com/api/?name=${encodeURIComponent(attendee.full_name || '')}`} />
                                          <AvatarFallback>{(attendee.full_name || 'U').charAt(0)}</AvatarFallback>
                                       </Avatar>
                                       <div>
                                          <div className="text-sm font-medium text-foreground">{attendee.full_name}</div>
                                          <div className="text-xs text-muted-foreground">{attendee.email}</div>
                                       </div>
                                    </div>
                                 </td>
                                 <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground capitalize">
                                    {attendee.status}
                                 </td>
                                 <td className="px-6 py-4 whitespace-nowrap">
                                    <Badge
                                       variant="outline"
                                       className={
                                          attendee.status === "Cancelled"
                                             ? "text-red-600 border-red-200 bg-red-500/10"
                                             : "text-green-600 border-green-200 bg-green-500/10"
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
                                          <DropdownMenuItem onClick={() => {
                                             setSelectedAttendee(attendee);
                                             setEditAttendanceOpen(true);
                                          }}>
                                             Edit Attendance
                                          </DropdownMenuItem>
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

            {/* Attendance Dialog */}
            <EditAttendanceDialog
               isOpen={editAttendanceOpen}
               onOpenChange={setEditAttendanceOpen}
               attendee={selectedAttendee}
               eventUuid={uuid || ''}
               onSuccess={fetchRegistrations}
            />

            {/* ATTENDANCE TAB */}
            <TabsContent value="attendance" className="mt-0">
               <Card>
                  <div className="p-4 border-b border-border bg-muted/30 flex items-center justify-between">
                     <div className="text-sm text-muted-foreground">
                        {event.format === 'online'
                           ? 'Attendance is tracked automatically via Zoom participation.'
                           : event.format === 'hybrid'
                              ? 'Track in-person check-ins and online participation.'
                              : 'Mark attendance manually or use the QR scanner app.'}
                     </div>
                  </div>
                  <div className="overflow-x-auto">
                     <table className="min-w-full divide-y divide-border">
                        <thead className="bg-muted/50">
                           <tr>
                              {/* Present checkbox - show for in-person and hybrid */}
                              {event.format !== 'online' && (
                                 <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider w-10">
                                    Present
                                 </th>
                              )}
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Attendee</th>
                              {/* Check-in Time - show for in-person and hybrid */}
                              {event.format !== 'online' && (
                                 <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Check-in Time</th>
                              )}
                              {/* Attendance Minutes - show for online and hybrid */}
                              {event.format !== 'in-person' && (
                                 <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Attendance Minutes</th>
                              )}
                              <th className="px-6 py-3 relative"><span className="sr-only">Actions</span></th>
                           </tr>
                        </thead>
                        <tbody className="bg-card divide-y divide-border">
                           {filteredAttendees.filter(a => a.status !== "Cancelled").map((attendee) => (
                              <tr key={attendee.uuid} className="hover:bg-muted/50">
                                 {/* Present checkbox - show for in-person and hybrid */}
                                 {event.format !== 'online' && (
                                    <td className="px-6 py-4 whitespace-nowrap">
                                       <Checkbox
                                          checked={attendee.attended}
                                          onCheckedChange={() => handleCheckIn(attendee.uuid)}
                                       />
                                    </td>
                                 )}
                                 <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center">
                                       <div>
                                          <div className="text-sm font-medium text-foreground">{attendee.full_name}</div>
                                          <div className="text-xs text-muted-foreground">{attendee.email}</div>
                                       </div>
                                    </div>
                                 </td>
                                 {/* Check-in Time - show for in-person and hybrid */}
                                 {event.format !== 'online' && (
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                       {attendee.check_in_time ? new Date(attendee.check_in_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "-"}
                                    </td>
                                 )}
                                 {/* Attendance Minutes - show for online and hybrid */}
                                 {event.format !== 'in-person' && (
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                       {attendee.total_attendance_minutes != null ? `${attendee.total_attendance_minutes} min` : "-"}
                                    </td>
                                 )}
                                 <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <DropdownMenu>
                                       <DropdownMenuTrigger asChild>
                                          <Button variant="ghost" className="h-8 w-8 p-0">
                                             <MoreVertical className="h-4 w-4" />
                                          </Button>
                                       </DropdownMenuTrigger>
                                       <DropdownMenuContent align="end">
                                          <DropdownMenuItem onClick={() => {
                                             setSelectedAttendee(attendee);
                                             setEditAttendanceOpen(true);
                                          }}>
                                             Edit Attendance
                                          </DropdownMenuItem>
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

            {/* CERTIFICATES TAB */}
            <TabsContent value="certificates" className="mt-0">
               <div className="mb-4 flex justify-between items-center bg-blue-500/10 border border-blue-500/20 p-4 rounded-lg">
                  <div className="flex gap-3">
                     <div className="bg-blue-500/20 p-2 rounded-full h-10 w-10 flex items-center justify-center text-blue-600">
                        <Award className="h-5 w-5" />
                     </div>
                     <div>
                        <h3 className="text-sm font-bold text-blue-600 dark:text-blue-400">Ready to issue?</h3>
                        <p className="text-sm text-blue-600/80 dark:text-blue-400/80">
                           You have {stats.checkedIn} verified attendees eligible for certificates.
                        </p>
                     </div>
                  </div>
                  <Button onClick={handleIssueAllCertificates} className="bg-blue-600 hover:bg-blue-700 text-white">
                     Issue All Certificates
                  </Button>
               </div>

               <Card>
                  <div className="overflow-x-auto">
                     <table className="min-w-full divide-y divide-border">
                        <thead className="bg-muted/50">
                           <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Attendee</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Eligibility</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Certificate Status</th>
                              <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Action</th>
                           </tr>
                        </thead>
                        <tbody className="bg-card divide-y divide-border">
                           {filteredAttendees.filter(a => a.status !== "cancelled").map((attendee) => (
                              <tr key={attendee.uuid} className="hover:bg-muted/50">
                                 <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-sm font-medium text-foreground">{attendee.full_name}</div>
                                 </td>
                                 <td className="px-6 py-4 whitespace-nowrap">
                                    {attendee.attendance_eligible ? (
                                       <Badge variant="outline" className="text-green-600 bg-green-500/10 border-green-200">Eligible</Badge>
                                    ) : (
                                       <Badge variant="outline" className="text-muted-foreground bg-muted border-border">Not Eligible</Badge>
                                    )}
                                 </td>
                                 <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                    {attendee.certificate_uuid ? 'Issued' : 'Not Issued'}
                                 </td>
                                 <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <Button
                                       size="sm"
                                       variant="outline"
                                       disabled={!attendee.attendance_eligible || !!attendee.certificate_uuid}
                                       onClick={() => handleIssueCertificate(attendee.uuid)}
                                    >
                                       {attendee.certificate_uuid ? 'Issued' : 'Issue'}
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
