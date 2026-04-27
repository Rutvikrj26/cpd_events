import React, { useState, useEffect } from "react";
import { getInitials } from "@/lib/initials";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
   User,
   Briefcase,
   Lock,
   Bell,
   Camera,
   Trash2,
   Loader2,
   CheckCircle,
   AlertCircle,
   ExternalLink,
   Monitor,
   Shield,
   Download,
   AlertTriangle,
   Plug,
   Video as VideoIcon,
} from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Textarea } from "@/shared/ui/textarea";
import { Switch } from "@/shared/ui/switch";
import {
   Form,
   FormControl,
   FormDescription,
   FormField,
   FormItem,
   FormLabel,
   FormMessage
} from "@/shared/ui/form";
import {
   Card,
   CardContent,
   CardDescription,
   CardHeader,
   CardTitle
} from "@/shared/ui/card";
import {
   Dialog,
   DialogContent,
   DialogDescription,
   DialogFooter,
   DialogHeader,
   DialogTitle,
} from "@/shared/ui/dialog";
import { Label } from "@/shared/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/shared/ui/avatar";
import { Separator } from "@/shared/ui/separator";
import { Badge } from "@/shared/ui/badge";
import { Alert, AlertDescription } from "@/shared/ui/alert";
import { PageHeader } from "@/components/custom/PageHeader";
import { getCurrentUser, updateProfile, changePassword, getNotificationPreferences, updateNotificationPreferences, exportUserData, deleteAccount, requestEmailChange } from "@/api/accounts";
import { User as UserType, NotificationPreferences } from "@/api/accounts/types";
import { toast } from "sonner";
import { useAuth } from "@/features/auth";
import { getRoleFlags } from "@/lib/role-utils";
import { ActiveSessionsTab } from "@/components/settings/ActiveSessionsTab";
import { ConfirmDialog } from "@/shared/ui/confirm-dialog";

// Schema for General Profile
const profileSchema = z.object({
   full_name: z.string().min(2, "Name must be at least 2 characters"),
   professional_title: z.string().optional(),
   organization_name: z.string().optional(),
   timezone: z.string().optional(),
   gst_hst_number: z.string().optional(),
});

// Schema for Security (Password)
const securitySchema = z.object({
   current_password: z.string().min(1, "Current password is required"),
   new_password: z.string().min(8, "Password must be at least 8 characters"),
   new_password_confirm: z.string(),
}).refine((data) => data.new_password === data.new_password_confirm, {
   message: "Passwords do not match",
   path: ["new_password_confirm"],
});

interface PrefRowProps {
   label: string;
   description: string;
   checked: boolean;
   onChange: (value: boolean) => void;
   disabled?: boolean;
}

function PrefRow({ label, description, checked, onChange, disabled }: PrefRowProps) {
   return (
      <div className="flex items-center justify-between space-x-2">
         <div className="space-y-0.5">
            <label className="text-sm font-medium leading-none">{label}</label>
            <p className="text-sm text-muted-foreground">{description}</p>
         </div>
         <Switch checked={checked} onCheckedChange={onChange} disabled={disabled} />
      </div>
   );
}

export function ProfileSettings() {
   const [isSubmitting, setIsSubmitting] = useState(false);
   const [user, setUser] = useState<UserType | null>(null);
   const [loadingProfile, setLoadingProfile] = useState(true);

   // Notification state
   const [notifications, setNotifications] = useState<NotificationPreferences | null>(null);
   const [loadingNotifications, setLoadingNotifications] = useState(true);
   const [savingNotifications, setSavingNotifications] = useState(false);

   // Privacy state
   const [showDeleteDialog, setShowDeleteDialog] = useState(false);
   const [deletingAccount, setDeletingAccount] = useState(false);
   const [exportingData, setExportingData] = useState(false);

   // Email change
   const [emailChangeOpen, setEmailChangeOpen] = useState(false);
   const [emailChangeLoading, setEmailChangeLoading] = useState(false);
   const [emailChangePassword, setEmailChangePassword] = useState("");
   const [emailChangeNewEmail, setEmailChangeNewEmail] = useState("");
   const [emailChangeError, setEmailChangeError] = useState<string | null>(null);

   const handleRequestEmailChange = async (e: React.FormEvent) => {
      e.preventDefault();
      setEmailChangeError(null);
      setEmailChangeLoading(true);
      try {
         const res = await requestEmailChange({
            current_password: emailChangePassword,
            new_email: emailChangeNewEmail,
         });
         toast.success(`Confirmation link sent to ${res.pending_email}`);
         setEmailChangeOpen(false);
         setEmailChangePassword("");
         setEmailChangeNewEmail("");
         const fresh = await getCurrentUser();
         setUser(fresh);
      } catch (err: any) {
         const detail =
            err?.response?.data?.error?.details?.current_password?.[0] ||
            err?.response?.data?.error?.details?.new_email?.[0] ||
            err?.response?.data?.error?.message ||
            "Failed to request email change";
         setEmailChangeError(detail);
      } finally {
         setEmailChangeLoading(false);
      }
   };

   const { user: authUser, logout, manifest, hasFeature } = useAuth();

   const [videoStatus, setVideoStatus] = useState<{ configured: boolean; provider: string } | null>(null);
   const [loadingVideoStatus, setLoadingVideoStatus] = useState(false);

   useEffect(() => {
      if (!hasFeature('manage_video')) return;
      let cancelled = false;
      setLoadingVideoStatus(true);
      import('@/api/video').then(({ getVideoStatus }) =>
         getVideoStatus()
            .then((s) => { if (!cancelled) setVideoStatus(s); })
            .catch(() => { if (!cancelled) setVideoStatus({ configured: false, provider: '' }); })
            .finally(() => { if (!cancelled) setLoadingVideoStatus(false); })
      );
      return () => { cancelled = true; };
   }, [hasFeature]);
   const { isOrganizer, isInstructor } = getRoleFlags(authUser);
   // Kept for the data-export tab visibility check; payouts UI was removed
   // when the platform moved to single-tenant (no Stripe Connect).
   const isContentCreator = isOrganizer || isInstructor;

   // Forms
   const profileForm = useForm({
      resolver: zodResolver(profileSchema),
      defaultValues: {
         full_name: "",
         professional_title: "",
         organization_name: "",
         timezone: "",
         gst_hst_number: "",
      },
   });

   const securityForm = useForm({
      resolver: zodResolver(securitySchema),
      defaultValues: {
         current_password: "",
         new_password: "",
         new_password_confirm: "",
      },
   });

   // Load user profile
   useEffect(() => {
      const loadProfile = async () => {
         try {
            const userData = await getCurrentUser();
            setUser(userData);
            profileForm.reset({
               full_name: userData.full_name || "",
               professional_title: (userData as any).professional_title || "",
               organization_name: userData.organization_name || "",
               timezone: (userData as any).timezone || "",
               gst_hst_number: userData.gst_hst_number || "",
            });
         } catch (error) {
            console.error("Failed to load profile:", error);
         } finally {
            setLoadingProfile(false);
         }
      };
      loadProfile();
   }, []);

   // Load notification preferences
   useEffect(() => {
      const loadNotifications = async () => {
         try {
            const prefs = await getNotificationPreferences();
            setNotifications(prefs);
         } catch (error) {
            console.error("Failed to load notifications:", error);
         } finally {
            setLoadingNotifications(false);
         }
      };
      loadNotifications();
   }, []);

   const onProfileSubmit = async (data: z.infer<typeof profileSchema>) => {
      setIsSubmitting(true);
      try {
         const updated = await updateProfile(data);
         setUser(prev => prev ? { ...prev, ...updated } : updated);
         toast.success("Profile updated successfully");
      } catch (error: any) {
         toast.error(error.message || "Failed to update profile");
      } finally {
         setIsSubmitting(false);
      }
   };

   const onSecuritySubmit = async (data: z.infer<typeof securitySchema>) => {
      setIsSubmitting(true);
      try {
         await changePassword(data);
         securityForm.reset();
         toast.success("Password changed successfully");
      } catch (error: any) {
         toast.error(error.message || "Failed to change password");
      } finally {
         setIsSubmitting(false);
      }
   };

   const handleNotificationChange = async (key: keyof NotificationPreferences, value: boolean) => {
      if (!notifications) return;

      const updated = { ...notifications, [key]: value };
      setNotifications(updated);
      setSavingNotifications(true);

      try {
         await updateNotificationPreferences(updated);
         toast.success("Preferences saved");
      } catch (error: any) {
         // Revert on error
         setNotifications(notifications);
         toast.error(error.message || "Failed to save preferences");
      } finally {
         setSavingNotifications(false);
      }
   };

   const handleExportData = async () => {
      setExportingData(true);
      try {
         const blob = await exportUserData();
         const url = window.URL.createObjectURL(blob);
         const a = document.createElement("a");
         a.href = url;
         a.download = "my-data-export.json";
         document.body.appendChild(a);
         a.click();
         document.body.removeChild(a);
         window.URL.revokeObjectURL(url);
         toast.success("Data export downloaded");
      } catch (error: any) {
         toast.error(error.message || "Failed to export data");
      } finally {
         setExportingData(false);
      }
   };

   const handleDeleteAccount = async () => {
      setDeletingAccount(true);
      try {
         await deleteAccount();
         toast.success("Account deleted");
         await logout();
      } catch (error: any) {
         toast.error(error.message || "Failed to delete account");
      } finally {
         setDeletingAccount(false);
         setShowDeleteDialog(false);
      }
   };

   // getInitials lives in @/lib/initials and strips honorifics ("Dr. M Torres" → "MT").

   if (loadingProfile) {
      return (
         <div className="flex items-center justify-center min-h-[400px]">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
         </div>
      );
   }

   return (
      <div className="max-w-4xl mx-auto space-y-8 pb-12">
         <PageHeader
            title="Account Settings"
            description="Manage your profile, preferences, and security settings."
         />

         <Tabs defaultValue="general" className="w-full">
            <div className="flex flex-col md:flex-row gap-8">
               {/* Sidebar Navigation for Tabs */}
               <aside className="w-full md:w-64 shrink-0">
                  <TabsList className="flex flex-col h-auto w-full bg-transparent p-0 space-y-1">
                     <TabsTrigger
                        value="general"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <User className="mr-2 h-4 w-4" /> General
                     </TabsTrigger>
                     <TabsTrigger
                        value="security"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <Lock className="mr-2 h-4 w-4" /> Security
                     </TabsTrigger>
                     <TabsTrigger
                        value="sessions"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <Monitor className="mr-2 h-4 w-4" /> Sessions
                     </TabsTrigger>
                     <TabsTrigger
                        value="notifications"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <Bell className="mr-2 h-4 w-4" /> Notifications
                     </TabsTrigger>
                     <TabsTrigger
                        value="privacy"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <Shield className="mr-2 h-4 w-4" /> Privacy
                     </TabsTrigger>
                     {hasFeature('manage_video') && (
                        <TabsTrigger
                           value="integrations"
                           className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                        >
                           <Plug className="mr-2 h-4 w-4" /> Integrations
                        </TabsTrigger>
                     )}
                  </TabsList>
               </aside>

               {/* Tab Content Area */}
               <div className="flex-1 space-y-6">

                  {/* GENERAL TAB */}
                  <TabsContent value="general" className="mt-0 space-y-6">
                     <Card>
                        <CardHeader>
                           <CardTitle>Profile Information</CardTitle>
                           <CardDescription>Update your public profile details.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                           <div className="flex items-center gap-6">
                              <Avatar className="h-20 w-20">
                                 <AvatarImage src={user?.profile_image} />
                                 <AvatarFallback>{getInitials(user?.full_name || "U")}</AvatarFallback>
                              </Avatar>
                              <div>
                                 <p className="font-medium">{user?.full_name}</p>
                                 <p className="text-sm text-muted-foreground">{user?.email}</p>
                              </div>
                           </div>

                           <Separator />

                           <Form {...profileForm}>
                              <form noValidate onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
                                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <FormField
                                       control={profileForm.control}
                                       name="full_name"
                                       render={({ field }) => (
                                          <FormItem>
                                             <FormLabel>Full Name</FormLabel>
                                             <FormControl><Input {...field} /></FormControl>
                                             <FormMessage />
                                          </FormItem>
                                       )}
                                    />
                                    <FormField
                                       control={profileForm.control}
                                       name="professional_title"
                                       render={({ field }) => (
                                          <FormItem>
                                             <FormLabel>Professional Title</FormLabel>
                                             <FormControl><Input placeholder="e.g. Senior Cardiologist" {...field} /></FormControl>
                                             <FormMessage />
                                          </FormItem>
                                       )}
                                    />
                                 </div>
                                 <FormField
                                    control={profileForm.control}
                                    name="organization_name"
                                    render={({ field }) => (
                                       <FormItem>
                                          <FormLabel>Organization</FormLabel>
                                          <FormControl><Input placeholder="Your company or institution" {...field} /></FormControl>
                                          <FormMessage />
                                       </FormItem>
                                    )}
                                 />
                                 {isContentCreator && (
                                    <FormField
                                       control={profileForm.control}
                                       name="gst_hst_number"
                                       render={({ field }) => (
                                          <FormItem>
                                             <FormLabel>GST/HST Number</FormLabel>
                                             <FormControl><Input placeholder="Optional (for your records)" {...field} /></FormControl>
                                             <FormMessage />
                                          </FormItem>
                                       )}
                                    />
                                 )}
                                 <div className="flex justify-end">
                                    <Button type="submit" disabled={isSubmitting}>
                                       {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                       Save Changes
                                    </Button>
                                 </div>
                              </form>
                           </Form>
                        </CardContent>
                     </Card>

                     {/* Email Address */}
                     <Card>
                        <CardHeader>
                           <CardTitle>Email Address</CardTitle>
                           <CardDescription>
                              Your login email. Changing it requires confirmation from the new address.
                           </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                           {user?.pending_email && (
                              <Alert>
                                 <AlertCircle className="h-4 w-4" />
                                 <AlertDescription>
                                    A change to <strong>{user.pending_email}</strong> is pending.
                                    Check that inbox for a confirmation link. Once confirmed, you'll need to log in again.
                                 </AlertDescription>
                              </Alert>
                           )}
                           <div className="flex items-center justify-between gap-4">
                              <div>
                                 <div className="font-medium">{user?.email}</div>
                                 <div className="text-sm text-muted-foreground">
                                    {user?.email_verified ? "Verified" : "Not verified"}
                                 </div>
                              </div>
                              <Button variant="outline" onClick={() => setEmailChangeOpen(true)}>
                                 Change email
                              </Button>
                           </div>
                        </CardContent>
                     </Card>
                  </TabsContent>

                  {/* SECURITY TAB */}
                  <TabsContent value="security" className="mt-0">
                     <Card>
                        <CardHeader>
                           <CardTitle>Change Password</CardTitle>
                           <CardDescription>Update your password to keep your account secure.</CardDescription>
                        </CardHeader>
                        <CardContent>
                           <Form {...securityForm}>
                              <form noValidate onSubmit={securityForm.handleSubmit(onSecuritySubmit)} className="space-y-4">
                                 <FormField
                                    control={securityForm.control}
                                    name="current_password"
                                    render={({ field }) => (
                                       <FormItem>
                                          <FormLabel>Current Password</FormLabel>
                                          <FormControl><Input type="password" {...field} /></FormControl>
                                          <FormMessage />
                                       </FormItem>
                                    )}
                                 />
                                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <FormField
                                       control={securityForm.control}
                                       name="new_password"
                                       render={({ field }) => (
                                          <FormItem>
                                             <FormLabel>New Password</FormLabel>
                                             <FormControl><Input type="password" {...field} /></FormControl>
                                             <FormMessage />
                                          </FormItem>
                                       )}
                                    />
                                    <FormField
                                       control={securityForm.control}
                                       name="new_password_confirm"
                                       render={({ field }) => (
                                          <FormItem>
                                             <FormLabel>Confirm Password</FormLabel>
                                             <FormControl><Input type="password" {...field} /></FormControl>
                                             <FormMessage />
                                          </FormItem>
                                       )}
                                    />
                                 </div>
                                 <div className="flex justify-end">
                                    <Button type="submit" disabled={isSubmitting}>
                                       {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                       Update Password
                                    </Button>
                                 </div>
                              </form>
                           </Form>
                        </CardContent>
                     </Card>
                  </TabsContent>

                  {/* NOTIFICATIONS TAB */}
                  <TabsContent value="notifications" className="mt-0">
                     <Card>
                        <CardHeader>
                           <CardTitle>Notification Preferences</CardTitle>
                           <CardDescription>Choose how you receive updates.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                           {loadingNotifications ? (
                              <div className="flex items-center justify-center py-8">
                                 <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                              </div>
                           ) : notifications ? (
                              <>
                                 <div>
                                    <h4 className="text-sm font-semibold mb-3">Events</h4>
                                    <div className="space-y-4">
                                       <PrefRow
                                          label="Event reminders"
                                          description="Reminders before events you've registered for start (24h, 1h, now)."
                                          checked={notifications.notify_event_reminders}
                                          onChange={(v) => handleNotificationChange('notify_event_reminders', v)}
                                          disabled={savingNotifications}
                                       />
                                       <PrefRow
                                          label="Event updates"
                                          description="Notifications when an event is rescheduled, cancelled, or you're promoted from the waitlist."
                                          checked={notifications.notify_event_updates}
                                          onChange={(v) => handleNotificationChange('notify_event_updates', v)}
                                          disabled={savingNotifications}
                                       />
                                       <PrefRow
                                          label="Recordings available"
                                          description="Notifications when a recording is published for an event you attended."
                                          checked={notifications.notify_recordings}
                                          onChange={(v) => handleNotificationChange('notify_recordings', v)}
                                          disabled={savingNotifications}
                                       />
                                    </div>
                                 </div>
                                 <Separator />
                                 <div>
                                    <h4 className="text-sm font-semibold mb-3">Achievements</h4>
                                    <div className="space-y-4">
                                       <PrefRow
                                          label="Certificate issued"
                                          description="Notifications when a certificate is issued to you."
                                          checked={notifications.notify_certificate_issued}
                                          onChange={(v) => handleNotificationChange('notify_certificate_issued', v)}
                                          disabled={savingNotifications}
                                       />
                                       <PrefRow
                                          label="Badge issued"
                                          description="Notifications when you earn a digital badge."
                                          checked={notifications.notify_badges}
                                          onChange={(v) => handleNotificationChange('notify_badges', v)}
                                          disabled={savingNotifications}
                                       />
                                    </div>
                                 </div>
                                 <Separator />
                                 <div>
                                    <h4 className="text-sm font-semibold mb-3">Courses</h4>
                                    <div className="space-y-4">
                                       <PrefRow
                                          label="Course progress"
                                          description="Enrollment confirmations, module unlocks, and completion summaries."
                                          checked={notifications.notify_course_progress}
                                          onChange={(v) => handleNotificationChange('notify_course_progress', v)}
                                          disabled={savingNotifications}
                                       />
                                    </div>
                                 </div>
                                 <p className="text-xs text-muted-foreground pt-2">
                                    Transactional emails (registration confirmations, password resets, payment receipts) ignore these settings and always send.
                                 </p>
                              </>
                           ) : (
                              <p className="text-muted-foreground text-center py-4">
                                 Unable to load notification preferences.
                              </p>
                           )}
                        </CardContent>
                     </Card>
                  </TabsContent>

                  {/* SESSIONS TAB */}
                  <TabsContent value="sessions" className="mt-0">
                     <ActiveSessionsTab />
                  </TabsContent>

                  {/* PRIVACY TAB */}
                  <TabsContent value="privacy" className="mt-0 space-y-6">
                     <Card>
                        <CardHeader>
                           <CardTitle>Export My Data</CardTitle>
                           <CardDescription>
                              Download a copy of all your personal data stored in our system.
                           </CardDescription>
                        </CardHeader>
                        <CardContent>
                           <Button onClick={handleExportData} disabled={exportingData}>
                              {exportingData ? (
                                 <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              ) : (
                                 <Download className="mr-2 h-4 w-4" />
                              )}
                              Export My Data
                           </Button>
                        </CardContent>
                     </Card>

                     <Card className="border-destructive/50">
                        <CardHeader>
                           <CardTitle className="text-destructive">Delete Account</CardTitle>
                           <CardDescription>
                              Permanently delete your account and all associated data. This action cannot be undone.
                           </CardDescription>
                        </CardHeader>
                        <CardContent>
                           <Button
                              variant="destructive"
                              onClick={() => setShowDeleteDialog(true)}
                           >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete My Account
                           </Button>
                        </CardContent>
                     </Card>

                     <ConfirmDialog
                        open={showDeleteDialog}
                        onOpenChange={setShowDeleteDialog}
                        title="Delete Account Permanently"
                        description={
                           <div className="space-y-3">
                              <div className="flex items-start gap-2 text-destructive">
                                 <AlertTriangle className="h-5 w-5 mt-0.5 shrink-0" />
                                 <span className="font-medium">This action is permanent and cannot be undone.</span>
                              </div>
                              <p>Deleting your account will:</p>
                              <ul className="list-disc ml-5 space-y-1 text-sm">
                                 <li>Remove all your personal information</li>
                                 <li>Delete your event history and certificates</li>
                                 <li>Cancel any active subscriptions</li>
                                 <li>Revoke access to all sessions</li>
                              </ul>
                              <p className="text-sm">We recommend exporting your data before proceeding.</p>
                           </div>
                        }
                        confirmLabel="Delete My Account"
                        variant="destructive"
                        isLoading={deletingAccount}
                        onConfirm={handleDeleteAccount}
                     />
                  </TabsContent>

                  {/* INTEGRATIONS TAB */}
                  {hasFeature('manage_video') && (
                     <TabsContent value="integrations" className="mt-0 space-y-6">
                        <Card>
                           <CardHeader>
                              <CardTitle>Video conferencing</CardTitle>
                              <CardDescription>
                                 Provider used to host live event and course-session video rooms.
                              </CardDescription>
                           </CardHeader>
                           <CardContent>
                              {loadingVideoStatus ? (
                                 <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Checking…
                                 </div>
                              ) : (
                                 <div className="flex items-center justify-between gap-4 p-4 border rounded-lg bg-muted/30">
                                    <div className="flex items-center gap-3">
                                       <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                                          <VideoIcon className="h-4 w-4" />
                                       </div>
                                       <div>
                                          <p className="font-medium capitalize">{videoStatus?.provider || 'LiveKit'}</p>
                                          <p className="text-xs text-muted-foreground">
                                             {videoStatus?.configured
                                                ? 'Rooms are provisioned automatically when you enable video on an event or live course session.'
                                                : 'Not configured yet — contact your admin to connect a provider.'}
                                          </p>
                                       </div>
                                    </div>
                                    {videoStatus?.configured ? (
                                       <Badge variant="default" className="bg-success/15 text-success border-success/30">
                                          <CheckCircle className="h-3 w-3 mr-1" /> Connected
                                       </Badge>
                                    ) : (
                                       <Badge variant="outline" className="text-muted-foreground">
                                          Not connected
                                       </Badge>
                                    )}
                                 </div>
                              )}
                           </CardContent>
                        </Card>
                     </TabsContent>
                  )}

                  {/* Payouts tab removed in single-tenant migration — money flows
                      to the institution's single Stripe account; no per-organizer
                      Stripe Connect onboarding is needed. */}

               </div>
            </div>
         </Tabs>

         <Dialog open={emailChangeOpen} onOpenChange={(v) => {
            setEmailChangeOpen(v);
            if (!v) {
               setEmailChangePassword("");
               setEmailChangeNewEmail("");
               setEmailChangeError(null);
            }
         }}>
            <DialogContent>
               <DialogHeader>
                  <DialogTitle>Change email address</DialogTitle>
                  <DialogDescription>
                     We'll send a confirmation link to the new address. The change only takes effect after you click that link.
                  </DialogDescription>
               </DialogHeader>
               <form noValidate onSubmit={handleRequestEmailChange} className="space-y-4">
                  {emailChangeError && (
                     <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                        {emailChangeError}
                     </div>
                  )}
                  <div className="space-y-2">
                     <Label htmlFor="ec-password">Current password</Label>
                     <Input
                        id="ec-password"
                        type="password"
                        value={emailChangePassword}
                        onChange={(e) => setEmailChangePassword(e.target.value)}
                        required
                        autoComplete="current-password"
                     />
                  </div>
                  <div className="space-y-2">
                     <Label htmlFor="ec-email">New email</Label>
                     <Input
                        id="ec-email"
                        type="email"
                        value={emailChangeNewEmail}
                        onChange={(e) => setEmailChangeNewEmail(e.target.value)}
                        required
                     />
                  </div>
                  <DialogFooter>
                     <Button type="submit" disabled={emailChangeLoading}>
                        {emailChangeLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Send confirmation link
                     </Button>
                  </DialogFooter>
               </form>
            </DialogContent>
         </Dialog>
      </div>
   );
}
