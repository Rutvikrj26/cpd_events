import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
   User,
   Briefcase,
   Lock,
   Bell,
   Camera,
   CreditCard,
   Trash2,
   Loader2,
   CheckCircle,
   AlertCircle,
   Plus,
   Banknote,
   ExternalLink
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
   Form,
   FormControl,
   FormDescription,
   FormField,
   FormItem,
   FormLabel,
   FormMessage
} from "@/components/ui/form";
import {
   Card,
   CardContent,
   CardDescription,
   CardHeader,
   CardTitle
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PageHeader } from "@/components/custom/PageHeader";
import { getPaymentMethods, deletePaymentMethod, getSubscription, getBillingPortal } from "@/api/billing";
import { getCurrentUser, updateProfile, changePassword, getNotificationPreferences, updateNotificationPreferences } from "@/api/accounts";
import { PaymentMethod, Subscription } from "@/api/billing/types";
import { User as UserType, NotificationPreferences } from "@/api/accounts/types";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { getPayoutsStatus, initiatePayoutsConnect, PayoutsStatus } from "@/api/payouts";

// Schema for General Profile
const profileSchema = z.object({
   full_name: z.string().min(2, "Name must be at least 2 characters"),
   professional_title: z.string().optional(),
   organization_name: z.string().optional(),
   timezone: z.string().optional(),
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

export function ProfileSettings() {
   const [isSubmitting, setIsSubmitting] = useState(false);
   const [user, setUser] = useState<UserType | null>(null);
   const [loadingProfile, setLoadingProfile] = useState(true);

   // Payment method state
   const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
   const [subscription, setSubscription] = useState<Subscription | null>(null);
   const [loadingPayment, setLoadingPayment] = useState(true);
   const [deletingId, setDeletingId] = useState<string | null>(null);
   const [addingPayment, setAddingPayment] = useState(false);

   // Notification state
   const [notifications, setNotifications] = useState<NotificationPreferences | null>(null);
   const [loadingNotifications, setLoadingNotifications] = useState(true);
   const [savingNotifications, setSavingNotifications] = useState(false);

   // Payouts state
   const { user: authUser } = useAuth();
   const isOrganizer = authUser?.account_type === 'organizer';
   const [payoutsStatus, setPayoutsStatus] = useState<PayoutsStatus | null>(null);
   const [loadingPayouts, setLoadingPayouts] = useState(true);
   const [initiatingConnect, setInitiatingConnect] = useState(false);

   // Forms
   const profileForm = useForm({
      resolver: zodResolver(profileSchema),
      defaultValues: {
         full_name: "",
         professional_title: "",
         organization_name: "",
         timezone: "",
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
            });
         } catch (error) {
            console.error("Failed to load profile:", error);
         } finally {
            setLoadingProfile(false);
         }
      };
      loadProfile();
   }, []);

   // Load payment methods
   const loadPaymentData = async () => {
      setLoadingPayment(true);
      try {
         const promises: Promise<any>[] = [getPaymentMethods()];
         if (isOrganizer) {
            promises.push(getSubscription());
         }

         const [methods, sub] = await Promise.all(promises);
         setPaymentMethods(methods);
         if (isOrganizer) {
            setSubscription(sub);
         }
      } catch (error) {
         console.error("Failed to load payment data:", error);
      } finally {
         setLoadingPayment(false);
      }
   };

   useEffect(() => {
      loadPaymentData();
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

   // Load payouts status (organizers only)
   useEffect(() => {
      if (!isOrganizer) {
         setLoadingPayouts(false);
         return;
      }
      const loadPayouts = async () => {
         try {
            const status = await getPayoutsStatus();
            setPayoutsStatus(status);
         } catch (error) {
            console.error("Failed to load payouts status:", error);
         } finally {
            setLoadingPayouts(false);
         }
      };
      loadPayouts();
   }, [isOrganizer]);

   const handleDeletePaymentMethod = async (uuid: string) => {
      setDeletingId(uuid);
      try {
         await deletePaymentMethod(uuid);
         setPaymentMethods(prev => prev.filter(m => m.uuid !== uuid));
         toast.success("Payment method removed");
      } catch (error: any) {
         toast.error(error.message || "Failed to remove payment method");
      } finally {
         setDeletingId(null);
      }
   };

   const handleManagePayments = async () => {
      setAddingPayment(true);
      try {
         const { url } = await getBillingPortal(`${window.location.origin}/settings?tab=billing`);
         window.location.href = url;
      } catch (error: any) {
         toast.error(error.message || "Failed to open billing portal");
         setAddingPayment(false);
      }
   };

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

   const handleLinkPayouts = async () => {
      setInitiatingConnect(true);
      try {
         const { url } = await initiatePayoutsConnect();
         window.location.href = url;
      } catch (error: any) {
         toast.error(error.message || "Failed to initiate payouts setup.");
      } finally {
         setInitiatingConnect(false);
      }
   };

   const getInitials = (name: string) => {
      return name
         .split(" ")
         .map(n => n[0])
         .join("")
         .toUpperCase()
         .slice(0, 2);
   };

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
                        value="billing"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <CreditCard className="mr-2 h-4 w-4" /> Billing
                     </TabsTrigger>
                     <TabsTrigger
                        value="security"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <Lock className="mr-2 h-4 w-4" /> Security
                     </TabsTrigger>
                     <TabsTrigger
                        value="notifications"
                        className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                     >
                        <Bell className="mr-2 h-4 w-4" /> Notifications
                     </TabsTrigger>
                     {isOrganizer && (
                        <TabsTrigger
                           value="payouts"
                           className="justify-start w-full px-4 py-2 data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium"
                        >
                           <Banknote className="mr-2 h-4 w-4" /> Payouts
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
                              <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
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
                  </TabsContent>

                  {/* BILLING TAB */}
                  <TabsContent value="billing" className="mt-0 space-y-6">
                     <Card>
                        <CardHeader>
                           <CardTitle>Payment Methods</CardTitle>
                           <CardDescription>Manage your saved payment methods for billing.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                           {loadingPayment ? (
                              <div className="flex items-center justify-center py-8">
                                 <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                              </div>
                           ) : paymentMethods.length === 0 ? (
                              <div className="text-center py-8 space-y-4">
                                 <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center">
                                    <CreditCard className="h-6 w-6 text-muted-foreground" />
                                 </div>
                                 <div>
                                    <p className="font-medium">No payment methods</p>
                                    <p className="text-sm text-muted-foreground">
                                       Add a payment method to continue after your trial ends.
                                    </p>
                                 </div>
                                 <Button onClick={handleManagePayments} disabled={addingPayment}>
                                    {addingPayment ? (
                                       <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                       <Plus className="h-4 w-4 mr-2" />
                                    )}
                                    Add Payment Method
                                 </Button>
                              </div>
                           ) : (
                              <div className="space-y-3">
                                 {paymentMethods.map((method) => (
                                    <div
                                       key={method.uuid}
                                       className="flex items-center justify-between p-4 border rounded-lg bg-muted/30"
                                    >
                                       <div className="flex items-center gap-4">
                                          <div className="w-10 h-10 bg-background rounded-md flex items-center justify-center border">
                                             <CreditCard className="h-5 w-5 text-muted-foreground" />
                                          </div>
                                          <div>
                                             <div className="flex items-center gap-2">
                                                <span className="font-medium capitalize">{method.card_brand}</span>
                                                <span className="text-muted-foreground">•••• {method.card_last4}</span>
                                                {method.is_default && (
                                                   <Badge variant="secondary" className="text-xs">Default</Badge>
                                                )}
                                                {method.is_expired && (
                                                   <Badge variant="destructive" className="text-xs">Expired</Badge>
                                                )}
                                             </div>
                                             <p className="text-sm text-muted-foreground">
                                                Expires {method.card_exp_month}/{method.card_exp_year}
                                             </p>
                                          </div>
                                       </div>
                                       <Button
                                          variant="ghost"
                                          size="sm"
                                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                          onClick={() => handleDeletePaymentMethod(method.uuid)}
                                          disabled={deletingId === method.uuid}
                                       >
                                          {deletingId === method.uuid ? (
                                             <Loader2 className="h-4 w-4 animate-spin" />
                                          ) : (
                                             <Trash2 className="h-4 w-4" />
                                          )}
                                       </Button>
                                    </div>
                                 ))}
                                 <Button variant="outline" className="w-full" onClick={handleManagePayments} disabled={addingPayment}>
                                    {addingPayment ? (
                                       <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                       <Plus className="h-4 w-4 mr-2" />
                                    )}
                                    Add Another Payment Method
                                 </Button>
                              </div>
                           )}
                        </CardContent>
                     </Card>

                     {/* Subscription Status Card - Organizers Only */}
                     {isOrganizer && (
                        <Card>
                           <CardHeader>
                              <CardTitle>Subscription</CardTitle>
                              <CardDescription>Your current plan and billing status.</CardDescription>
                           </CardHeader>
                           <CardContent>
                              {subscription ? (
                                 <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                       <span className="text-muted-foreground">Current Plan</span>
                                       <span className="font-medium capitalize">{subscription.plan}</span>
                                    </div>
                                    <Separator />
                                    <div className="flex items-center justify-between">
                                       <span className="text-muted-foreground">Status</span>
                                       <Badge variant={subscription.is_active ? "default" : "secondary"}>
                                          {subscription.status_display}
                                       </Badge>
                                    </div>
                                    {subscription.is_trialing && subscription.days_until_trial_ends !== null && (
                                       <>
                                          <Separator />
                                          <div className="flex items-center justify-between">
                                             <span className="text-muted-foreground">Trial Ends</span>
                                             <span className="font-medium">
                                                {subscription.days_until_trial_ends} days remaining
                                             </span>
                                          </div>
                                       </>
                                    )}
                                    {subscription.has_payment_method && (
                                       <Alert className="bg-success/10 border-success/30">
                                          <CheckCircle className="h-4 w-4 text-success" />
                                          <AlertDescription className="text-success">
                                             Billing is set up. You'll be charged automatically when your trial ends.
                                          </AlertDescription>
                                       </Alert>
                                    )}
                                    {!subscription.has_payment_method && subscription.is_trialing && (
                                       <Alert className="bg-warning/10 border-warning/30">
                                          <AlertCircle className="h-4 w-4 text-warning" />
                                          <AlertDescription>
                                             Add a payment method to continue using premium features after your trial.
                                          </AlertDescription>
                                       </Alert>
                                    )}
                                 </div>
                              ) : (
                                 <div className="text-center py-4 text-muted-foreground">
                                    No subscription information available.
                                 </div>
                              )}
                           </CardContent>
                        </Card>
                     )}
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
                              <form onSubmit={securityForm.handleSubmit(onSecuritySubmit)} className="space-y-4">
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
                                 <div className="flex items-center justify-between space-x-2">
                                    <div className="space-y-0.5">
                                       <label className="text-sm font-medium leading-none">
                                          Event Reminders
                                       </label>
                                       <p className="text-sm text-muted-foreground">Get notified before events start.</p>
                                    </div>
                                    <Switch
                                       checked={notifications.notify_event_reminders}
                                       onCheckedChange={(checked) => handleNotificationChange('notify_event_reminders', checked)}
                                       disabled={savingNotifications}
                                    />
                                 </div>
                                 <Separator />
                                 <div className="flex items-center justify-between space-x-2">
                                    <div className="space-y-0.5">
                                       <label className="text-sm font-medium leading-none">
                                          Certificate Notifications
                                       </label>
                                       <p className="text-sm text-muted-foreground">Get notified when certificates are issued.</p>
                                    </div>
                                    <Switch
                                       checked={notifications.notify_certificate_issued}
                                       onCheckedChange={(checked) => handleNotificationChange('notify_certificate_issued', checked)}
                                       disabled={savingNotifications}
                                    />
                                 </div>
                                 <Separator />
                                 <div className="flex items-center justify-between space-x-2">
                                    <div className="space-y-0.5">
                                       <label className="text-sm font-medium leading-none">
                                          Marketing Updates
                                       </label>
                                       <p className="text-sm text-muted-foreground">Receive news about new features and promotions.</p>
                                    </div>
                                    <Switch
                                       checked={notifications.notify_marketing}
                                       onCheckedChange={(checked) => handleNotificationChange('notify_marketing', checked)}
                                       disabled={savingNotifications}
                                    />
                                 </div>
                              </>
                           ) : (
                              <p className="text-muted-foreground text-center py-4">
                                 Unable to load notification preferences.
                              </p>
                           )}
                        </CardContent>
                     </Card>
                  </TabsContent>

                  {/* PAYOUTS TAB */}
                  {isOrganizer && (
                     <TabsContent value="payouts" className="mt-0 space-y-6">
                        <Card>
                           <CardHeader>
                              <CardTitle>Receive Payouts</CardTitle>
                              <CardDescription>
                                 Link your bank account to receive revenue from paid events.
                              </CardDescription>
                           </CardHeader>
                           <CardContent className="space-y-4">
                              {loadingPayouts ? (
                                 <div className="flex items-center justify-center py-8">
                                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                 </div>
                              ) : payoutsStatus?.charges_enabled ? (
                                 <div className="space-y-4">
                                    <Alert className="bg-success/10 border-success/30">
                                       <CheckCircle className="h-4 w-4 text-success" />
                                       <AlertDescription className="text-success">
                                          Payouts are active! You can receive revenue from paid events.
                                       </AlertDescription>
                                    </Alert>
                                    <div className="p-4 border rounded-lg bg-muted/30">
                                       <div className="flex items-center justify-between">
                                          <div>
                                             <p className="font-medium">Stripe Connect</p>
                                             <p className="text-sm text-muted-foreground">Account ID: {payoutsStatus.stripe_id}</p>
                                          </div>
                                          <Badge variant="default">Active</Badge>
                                       </div>
                                    </div>
                                    <Button variant="outline" onClick={handleLinkPayouts} disabled={initiatingConnect}>
                                       {initiatingConnect && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                       <ExternalLink className="mr-2 h-4 w-4" />
                                       Update Payout Settings
                                    </Button>
                                 </div>
                              ) : payoutsStatus?.status === 'pending_verification' ? (
                                 <div className="space-y-4">
                                    <Alert className="bg-warning/10 border-warning/30">
                                       <AlertCircle className="h-4 w-4 text-warning" />
                                       <AlertDescription>
                                          Your account is pending verification by Stripe. This usually takes 1-2 business days.
                                       </AlertDescription>
                                    </Alert>
                                    <Button variant="outline" onClick={handleLinkPayouts} disabled={initiatingConnect}>
                                       {initiatingConnect && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                       <ExternalLink className="mr-2 h-4 w-4" />
                                       Check Status / Complete Setup
                                    </Button>
                                 </div>
                              ) : (
                                 <div className="text-center py-8 space-y-4">
                                    <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center">
                                       <Banknote className="h-6 w-6 text-muted-foreground" />
                                    </div>
                                    <div>
                                       <p className="font-medium">Link Your Bank Account</p>
                                       <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                                          To charge attendees for your events, you need to link a bank account via Stripe.
                                       </p>
                                    </div>
                                    <Button onClick={handleLinkPayouts} disabled={initiatingConnect}>
                                       {initiatingConnect && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                       <ExternalLink className="mr-2 h-4 w-4" />
                                       Link Bank Account
                                    </Button>
                                 </div>
                              )}
                           </CardContent>
                        </Card>
                     </TabsContent>
                  )}

               </div>
            </div>
         </Tabs>


      </div>
   );
}
