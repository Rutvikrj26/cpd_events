import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
   Clock,
   Search,
   Download,
   MoreVertical,
   Award,
   Filter,
   Trash2,
   MessageSquare,
   Star,
   AlertCircle
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
import { getEvent, updateEvent, publishEvent, unpublishEvent, getEventRegistrations, checkInAttendee, deleteEvent, cancelEventRegistration, refundEventRegistration } from "@/api/events";
import { issueCertificates, revokeCertificate } from "@/api/certificates";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
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
import { AttendanceReconciliation } from "@/components/events/AttendanceReconciliation";
import { CustomFieldResponsesDialog } from "@/components/events/CustomFieldResponsesDialog";
import { FeedbackCard, FeedbackSummary } from "@/components/feedback";
import { getEventFeedback, calculateFeedbackSummary } from "@/api/feedback";
import { EventFeedback } from "@/api/feedback/types";

export function EventManagement() {
   const { uuid } = useParams<{ uuid: string }>();
   const navigate = useNavigate();
   const [event, setEvent] = useState<any | null>(null);
   const [loading, setLoading] = useState(true);
   const [deleting, setDeleting] = useState(false);

   const [editAttendanceOpen, setEditAttendanceOpen] = useState(false);

   const [selectedAttendee, setSelectedAttendee] = useState<any>(null);
   const [actionDialogOpen, setActionDialogOpen] = useState(false);
   const [actionType, setActionType] = useState<'cancel' | 'refund' | null>(null);
   const [actionReason, setActionReason] = useState('');
   const [actionLoading, setActionLoading] = useState(false);
   const [actionAttendee, setActionAttendee] = useState<any>(null);

   // Custom field responses dialog state
   const [customFieldDialogOpen, setCustomFieldDialogOpen] = useState(false);
   const [customFieldAttendee, setCustomFieldAttendee] = useState<any>(null);

   // Certificate revocation state
   const [revokeTarget, setRevokeTarget] = useState<any>(null);
   const [revokeReason, setRevokeReason] = useState('');
   const [revokeLoading, setRevokeLoading] = useState(false);

   const fetchEvent = useCallback(async () => {
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
   }, [uuid]);

   useEffect(() => {
      fetchEvent();
   }, [fetchEvent]);

   const [attendees, setAttendees] = useState<any[]>([]);
   const [searchTerm, setSearchTerm] = useState("");
   const [publishing, setPublishing] = useState(false);

   // Feedback state
   const [feedback, setFeedback] = useState<EventFeedback[]>([]);
   const [feedbackLoading, setFeedbackLoading] = useState(false);

   const fetchRegistrations = useCallback(async () => {
      if (!uuid) return;
      try {
         const regs = await getEventRegistrations(uuid);
         setAttendees(regs);
      } catch (e) {
         console.error("Failed to fetch registrations", e);
      }
   }, [uuid]);

   // Fetch registrations for the event
   useEffect(() => {
      fetchRegistrations();
   }, [fetchRegistrations]);

   // Fetch feedback for the event
   const fetchFeedback = useCallback(async () => {
      if (!uuid) return;
      setFeedbackLoading(true);
      try {
         const data = await getEventFeedback(uuid);
         setFeedback(data);
      } catch (e) {
         console.error("Failed to fetch feedback", e);
      } finally {
         setFeedbackLoading(false);
      }
   }, [uuid]);

   useEffect(() => {
      fetchFeedback();
   }, [fetchFeedback]);

   const hasStarted = event ? new Date(event.starts_at) < new Date() : false;

   const getRegistrationBadge = (attendee: any) => {
      const paymentStatus = (attendee.payment_status || '').toLowerCase();
      const registrationStatus = (attendee.status || '').toLowerCase();

      if (paymentStatus === 'refunded') {
         return { label: 'Refunded', className: 'text-primary border-primary bg-primary/10' };
      }
      if (paymentStatus === 'failed') {
         return { label: 'Payment Failed', className: 'text-destructive border-destructive bg-destructive/10' };
      }
      if (paymentStatus === 'pending') {
         return { label: 'Payment Pending', className: 'text-warning border-warning bg-warning-subtle' };
      }
      if (paymentStatus === 'paid') {
         return { label: 'Paid', className: 'text-success border-success bg-success-subtle' };
      }
      if (registrationStatus === 'cancelled') {
         return { label: 'Cancelled', className: 'text-destructive border-destructive bg-destructive/10' };
      }
      if (registrationStatus === 'waitlisted') {
         return { label: 'Waitlisted', className: 'text-warning border-warning bg-warning-subtle' };
      }
      if (registrationStatus === 'pending') {
         return { label: 'Pending', className: 'text-warning border-warning bg-warning-subtle' };
      }
      return { label: 'Confirmed', className: 'text-success border-success bg-success-subtle' };
   };

   const openActionDialog = (attendee: any, type: 'cancel' | 'refund') => {
      setActionAttendee(attendee);
      setActionType(type);
      setActionReason('');
      setActionDialogOpen(true);
   };

   const closeActionDialog = () => {
      setActionDialogOpen(false);
      setActionType(null);
      setActionReason('');
      setActionAttendee(null);
   };

   const handleActionConfirm = async () => {
      if (!uuid || !actionAttendee || !actionType) return;
      setActionLoading(true);
      try {
         const reason = actionReason.trim() || undefined;
         if (actionType === 'refund') {
            await refundEventRegistration(uuid, actionAttendee.uuid, reason);
            toast.success('Registration refunded');
         } else {
            await cancelEventRegistration(uuid, actionAttendee.uuid, reason);
            toast.success('Registration cancelled');
         }
         await fetchRegistrations();
         closeActionDialog();
      } catch (error: any) {
         const message = error?.response?.data?.error?.message || error?.response?.data?.detail || 'Action failed';
         toast.error(message);
      } finally {
         setActionLoading(false);
      }
   };

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

   const handleRevokeCertificate = async () => {
      if (!uuid || !revokeTarget?.certificate_uuid) return;
      setRevokeLoading(true);
      try {
         await revokeCertificate(uuid, revokeTarget.certificate_uuid, revokeReason);
         toast.success("Certificate revoked");
         setRevokeTarget(null);
         setRevokeReason('');
         fetchRegistrations();
      } catch (error: any) {
         toast.error(error?.response?.data?.detail || "Failed to revoke certificate");
      } finally {
         setRevokeLoading(false);
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

   const handleExportCsv = () => {
      if (attendees.length === 0) {
         toast.error("No attendees to export");
         return;
      }
      const headers = ['Full Name', 'Email', 'Status', 'Payment Status', 'Attended', 'Registered At'];
      const rows = attendees.map(a => [
         `"${(a.full_name || '').replace(/"/g, '""')}"`,
         `"${(a.email || '').replace(/"/g, '""')}"`,
         a.status || '',
         a.payment_status || '',
         a.attended ? 'Yes' : 'No',
         a.created_at ? new Date(a.created_at).toISOString() : '',
      ].join(','));
      const csvContent = [headers.join(','), ...rows].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${event?.title || 'event'}-attendees.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success("CSV exported");
   };

   const filteredAttendees = attendees.filter(a =>
      (a.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (a.email || '').toLowerCase().includes(searchTerm.toLowerCase())
   );

   const feedbackSummary = calculateFeedbackSummary(feedback);

   const stats = {
      registered: attendees.filter(a => a.status !== "cancelled").length,
      checkedIn: attendees.filter(a => a.attended).length,
      cancelled: attendees.filter(a => a.status === "cancelled").length,
      issued: attendees.filter(a => a.certificate_uuid).length,
      feedbackCount: feedback.length,
      avgRating: feedbackSummary.average_rating,
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
                        className="bg-success hover:bg-success/90 text-white"
                     >
                        {publishing ? 'Publishing...' : 'Publish Event'}
                     </Button>
                  )}
                  {event.status === 'published' && !hasStarted && (
                     <Button
                        onClick={handleUnpublish}
                        disabled={publishing}
                        variant="outline"
                        className="text-warning border-warning hover:bg-warning-subtle"
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
                     <Button>View Public Page</Button>
                  </Link>
                  <AlertDialog>
                     <AlertDialogTrigger asChild>
                        <Button variant="outline" className="text-destructive border-destructive hover:bg-destructive/10 hover:text-destructive">
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
                              className="bg-destructive hover:bg-destructive/90"
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

         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
               <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Registrations</CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="text-2xl font-bold">{stats.registered}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                     {event.capacity ? `${(stats.registered / event.capacity * 100).toFixed(0)}% of capacity` : 'Unlimited capacity'}
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
            <Card>
               <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Feedback</CardTitle>
               </CardHeader>
               <CardContent>
                  <div className="flex items-center gap-2">
                     <div className="text-2xl font-bold">{stats.avgRating > 0 ? stats.avgRating : '-'}</div>
                     {stats.avgRating > 0 && <Star className="h-5 w-5 fill-yellow-400 text-yellow-400" />}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                     {stats.feedbackCount} response{stats.feedbackCount !== 1 ? 's' : ''}
                  </p>
               </CardContent>
            </Card>
         </div>

         <Tabs defaultValue="registrations" className="w-full">
            <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none mb-6">
               <TabsTrigger value="registrations" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none">
                  Registrations
               </TabsTrigger>
               <TabsTrigger value="attendance" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none">
                  Attendance
               </TabsTrigger>
               {event.certificates_enabled && (
                  <TabsTrigger value="certificates" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none">
                     Certificates
                  </TabsTrigger>
               )}
               {event.badges_enabled && (
                  <TabsTrigger value="badges" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none">
                     Badges
                  </TabsTrigger>
               )}
               <TabsTrigger value="feedback" className="rounded-none border-b-2 border-transparent px-6 py-3 data-[state=active]:border-primary data-[state=active]:text-primary data-[state=active]:bg-transparent shadow-none">
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Feedback
                  {stats.feedbackCount > 0 && (
                     <Badge variant="secondary" className="ml-2 h-5 px-1.5">{stats.feedbackCount}</Badge>
                  )}
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
                  <Button variant="outline" size="sm" className="w-full sm:w-auto" onClick={handleExportCsv}>
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
                           {filteredAttendees.map((attendee) => {
                              const badge = getRegistrationBadge(attendee);
                              const paymentStatus = (attendee.payment_status || '').toLowerCase();
                              const registrationStatus = (attendee.status || '').toLowerCase();
                              const isRefunded = paymentStatus === 'refunded';
                              const isCancelled = registrationStatus === 'cancelled';
                              const canRefund = paymentStatus === 'paid';
                              const canCancel = !canRefund && !isRefunded && !isCancelled;

                              return (
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
                                       <Badge variant="outline" className={badge.className}>
                                          {badge.label}
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

                                             <DropdownMenuItem>Send Email</DropdownMenuItem>
                                             <DropdownMenuItem onClick={() => {
                                                setSelectedAttendee(attendee);
                                                setEditAttendanceOpen(true);
                                             }}>
                                                Edit Attendance
                                             </DropdownMenuItem>
                                             {event.custom_fields && event.custom_fields.length > 0 && (
                                                <DropdownMenuItem onClick={() => {
                                                   setCustomFieldAttendee(attendee);
                                                   setCustomFieldDialogOpen(true);
                                                }}>
                                                   View Responses
                                                </DropdownMenuItem>
                                             )}
                                             <DropdownMenuSeparator />
                                             {canRefund ? (
                                                <DropdownMenuItem
                                                   onClick={() => openActionDialog(attendee, 'refund')}
                                                   className="text-warning"
                                                >
                                                   Refund Registration
                                                </DropdownMenuItem>
                                             ) : (
                                                <DropdownMenuItem
                                                   onClick={() => openActionDialog(attendee, 'cancel')}
                                                   disabled={!canCancel}
                                                   className="text-destructive"
                                                >
                                                   {isRefunded ? 'Already Refunded' : isCancelled ? 'Already Cancelled' : 'Cancel Registration'}
                                                </DropdownMenuItem>
                                             )}
                                          </DropdownMenuContent>
                                       </DropdownMenu>
                                    </td>
                                 </tr>
                              );
                           })}
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

            {/* Custom Field Responses Dialog */}
            <CustomFieldResponsesDialog
               open={customFieldDialogOpen}
               onOpenChange={setCustomFieldDialogOpen}
               attendeeName={customFieldAttendee?.full_name || ''}
               eventUuid={uuid || ''}
               registrationUuid={customFieldAttendee?.uuid || ''}
            />

            <AlertDialog
               open={actionDialogOpen}
               onOpenChange={(open) => {
                  if (!open) {
                     closeActionDialog();
                     return;
                  }
                  setActionDialogOpen(true);
               }}
            >
               <AlertDialogContent>
                  <AlertDialogHeader>
                     <AlertDialogTitle>
                        {actionType === 'refund' ? 'Refund Registration' : 'Cancel Registration'}
                     </AlertDialogTitle>
                     <AlertDialogDescription>
                        {actionType === 'refund'
                           ? 'This will refund the attendee and cancel their registration.'
                           : 'This will cancel the registration without issuing a refund.'}
                     </AlertDialogDescription>
                  </AlertDialogHeader>
                  <div className="space-y-2">
                     <label className="text-sm font-medium text-foreground">Reason (optional)</label>
                     <Input
                        placeholder="Add a reason for the attendee"
                        value={actionReason}
                        onChange={(e) => setActionReason(e.target.value)}
                     />
                  </div>
                  <AlertDialogFooter>
                     <AlertDialogCancel disabled={actionLoading}>Back</AlertDialogCancel>
                     <AlertDialogAction
                        onClick={(event) => {
                           event.preventDefault();
                           handleActionConfirm();
                        }}
                        disabled={actionLoading}
                        className={actionType === 'refund'
                           ? 'bg-warning hover:bg-warning/90 text-white'
                           : 'bg-destructive hover:bg-destructive/90'
                        }
                     >
                        {actionLoading
                           ? 'Processing...'
                           : actionType === 'refund'
                              ? 'Refund Registration'
                              : 'Cancel Registration'}
                     </AlertDialogAction>
                  </AlertDialogFooter>
               </AlertDialogContent>
            </AlertDialog>

            {/* ATTENDANCE TAB */}
            <TabsContent value="attendance" className="mt-0 space-y-4">
               {/* Attendance Reconciliation - for online/hybrid events */}
               {(event.format === 'online' || event.format === 'hybrid') && (
                  <AttendanceReconciliation eventUuid={event.uuid} onReconciled={() => fetchEvent()} />
               )}

               <Card>
                  <div className="p-4 border-b border-border bg-muted/30 flex items-center justify-between">
                     <div className="text-sm text-muted-foreground">
                        {event.format === 'online'
                           ? 'Attendance is tracked automatically via online participation.'
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
                           {filteredAttendees.filter(a => a.status !== "cancelled").map((attendee) => (
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
            {event.certificates_enabled && (
               <TabsContent value="certificates" className="mt-0">
                  <div className="mb-4 flex justify-between items-center bg-info-subtle border border-info p-4 rounded-lg">
                     <div className="flex gap-3">
                        <div className="bg-info/20 p-2 rounded-full h-10 w-10 flex items-center justify-center text-info">
                           <Award className="h-5 w-5" />
                        </div>
                        <div>
                           <h3 className="text-sm font-bold text-info">Ready to issue?</h3>
                           <p className="text-sm text-muted-foreground">
                              You have {stats.checkedIn} verified attendees eligible for certificates.
                           </p>
                        </div>
                     </div>
                     <Button onClick={handleIssueAllCertificates}>
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
                                          <Badge variant="outline" className="text-success bg-success-subtle border-success">Eligible</Badge>
                                       ) : (
                                          <Badge variant="outline" className="text-muted-foreground bg-muted border-border">Not Eligible</Badge>
                                       )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                       {attendee.certificate_uuid ? 'Issued' : 'Not Issued'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                                       {attendee.certificate_uuid ? (
                                          <Button
                                             size="sm"
                                             variant="outline"
                                             className="text-destructive border-destructive hover:bg-destructive/10"
                                             onClick={() => setRevokeTarget(attendee)}
                                          >
                                             Revoke
                                          </Button>
                                       ) : (
                                          <Button
                                             size="sm"
                                             variant="outline"
                                             disabled={!attendee.attendance_eligible}
                                             onClick={() => handleIssueCertificate(attendee.uuid)}
                                          >
                                             Issue
                                          </Button>
                                       )}
                                    </td>
                                 </tr>
                              ))}
                           </tbody>
                        </table>
                     </div>
                  </Card>
               </TabsContent>
            )}

            {/* BADGES TAB */}
            {event.badges_enabled && (
               <TabsContent value="badges" className="mt-0">
                  <div className="mb-4 p-4 rounded-lg bg-muted/50 border">
                     <div className="flex gap-3 items-center">
                        <Award className="h-5 w-5 text-muted-foreground" />
                        <div>
                           <h3 className="text-sm font-medium">Auto-Issue Badges</h3>
                           <p className="text-sm text-muted-foreground">
                              {event.auto_issue_badges
                                 ? "Badges are automatically issued to eligible attendees when the event completes."
                                 : "Auto-issue is disabled. Badges will not be automatically issued."}
                           </p>
                        </div>
                     </div>
                  </div>
                  <Card>
                     <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-border">
                           <thead className="bg-muted/50">
                              <tr>
                                 <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Attendee</th>
                                 <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Eligibility</th>
                                 <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Badge Status</th>
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
                                          <Badge variant="outline" className="text-success bg-success-subtle border-success">Eligible</Badge>
                                       ) : (
                                          <Badge variant="outline" className="text-muted-foreground bg-muted border-border">Not Eligible</Badge>
                                       )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                       {attendee.badge_uuid ? (
                                          <Badge variant="default">Issued</Badge>
                                       ) : (
                                          <span>Not Issued</span>
                                       )}
                                    </td>
                                 </tr>
                              ))}
                           </tbody>
                        </table>
                     </div>
                  </Card>
               </TabsContent>
            )}

            {/* FEEDBACK TAB */}
            <TabsContent value="feedback" className="mt-0">
               <div className="space-y-6">
                  {/* Summary Card */}
                  <FeedbackSummary summary={feedbackSummary} />

                  {/* Individual Feedback Cards */}
                  {feedback.length > 0 && (
                     <div className="space-y-4">
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                           <MessageSquare className="h-5 w-5" />
                           All Responses
                        </h3>
                        <div className="grid gap-4">
                           {feedback.map((fb) => (
                              <FeedbackCard key={fb.uuid} feedback={fb} />
                           ))}
                        </div>
                     </div>
                  )}

                  {feedbackLoading && (
                     <div className="text-center py-8 text-muted-foreground">
                        Loading feedback...
                     </div>
                  )}
               </div>
            </TabsContent>
         </Tabs>

         {/* Custom Field Responses Dialog */}
         <CustomFieldResponsesDialog
            open={customFieldDialogOpen}
            onOpenChange={setCustomFieldDialogOpen}
            attendeeName={customFieldAttendee?.full_name || ""}
            eventUuid={uuid}
            registrationUuid={customFieldAttendee?.uuid}
         />

         {/* Certificate Revocation Dialog */}
         <ConfirmDialog
            open={!!revokeTarget}
            onOpenChange={(open) => {
               if (!open) {
                  setRevokeTarget(null);
                  setRevokeReason('');
               }
            }}
            title="Revoke Certificate"
            description={
               <div className="space-y-3">
                  <p>Are you sure you want to revoke the certificate for <strong>{revokeTarget?.full_name}</strong>? This action can be undone by reissuing.</p>
                  <div className="space-y-2">
                     <label className="text-sm font-medium">Reason for revocation</label>
                     <Input
                        value={revokeReason}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRevokeReason(e.target.value)}
                        placeholder="e.g. Attendance records corrected"
                     />
                  </div>
               </div>
            }
            confirmLabel="Revoke Certificate"
            variant="destructive"
            isLoading={revokeLoading}
            onConfirm={handleRevokeCertificate}
         />
      </div>
   );
}
