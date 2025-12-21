import React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { 
  User, 
  Briefcase, 
  Lock, 
  Bell, 
  Save, 
  Camera
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
import { PageHeader } from "@/components/custom/PageHeader";
import { toast } from "sonner";

// Schema for General Profile
const profileSchema = z.object({
  fullName: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email(),
  bio: z.string().optional(),
  phone: z.string().optional(),
});

// Schema for Professional Info
const professionalSchema = z.object({
  jobTitle: z.string().min(2, "Job title is required"),
  organization: z.string().min(2, "Organization is required"),
  licenseNumber: z.string().optional(),
  specialization: z.string().optional(),
});

// Schema for Security (Password)
const securitySchema = z.object({
  currentPassword: z.string().min(1, "Current password is required"),
  newPassword: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

export function ProfileSettings() {
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Forms
  const profileForm = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      fullName: "Jane Doe",
      email: "jane@example.com",
      bio: "Cardiologist with 10 years of experience in clinical practice and research.",
      phone: "+1 (555) 000-0000",
    },
  });

  const professionalForm = useForm({
    resolver: zodResolver(professionalSchema),
    defaultValues: {
      jobTitle: "Senior Cardiologist",
      organization: "General Hospital",
      licenseNumber: "MD-12345-NY",
      specialization: "Cardiology",
    },
  });

  const securityForm = useForm({
    resolver: zodResolver(securitySchema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  });

  const onProfileSubmit = (data: any) => {
    setIsSubmitting(true);
    setTimeout(() => {
      console.log("Profile Data:", data);
      setIsSubmitting(false);
      toast.success("Profile updated successfully");
    }, 1000);
  };

  const onProfessionalSubmit = (data: any) => {
    setIsSubmitting(true);
    setTimeout(() => {
      console.log("Professional Data:", data);
      setIsSubmitting(false);
      toast.success("Professional details updated");
    }, 1000);
  };

  const onSecuritySubmit = (data: any) => {
    setIsSubmitting(true);
    setTimeout(() => {
      console.log("Security Data:", data);
      setIsSubmitting(false);
      securityForm.reset();
      toast.success("Password changed successfully");
    }, 1000);
  };

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
                   className="justify-start w-full px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 font-medium"
                >
                   <User className="mr-2 h-4 w-4" /> General
                </TabsTrigger>
                <TabsTrigger 
                   value="professional" 
                   className="justify-start w-full px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 font-medium"
                >
                   <Briefcase className="mr-2 h-4 w-4" /> Professional
                </TabsTrigger>
                <TabsTrigger 
                   value="security" 
                   className="justify-start w-full px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 font-medium"
                >
                   <Lock className="mr-2 h-4 w-4" /> Security
                </TabsTrigger>
                <TabsTrigger 
                   value="notifications" 
                   className="justify-start w-full px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-700 font-medium"
                >
                   <Bell className="mr-2 h-4 w-4" /> Notifications
                </TabsTrigger>
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
                         <AvatarImage src="https://github.com/shadcn.png" />
                         <AvatarFallback>JD</AvatarFallback>
                      </Avatar>
                      <Button variant="outline" size="sm">
                         <Camera className="mr-2 h-4 w-4" /> Change Photo
                      </Button>
                   </div>
                   
                   <Separator />

                   <Form {...profileForm}>
                      <form onSubmit={profileForm.handleSubmit(onProfileSubmit)} className="space-y-4">
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <FormField
                               control={profileForm.control}
                               name="fullName"
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
                               name="email"
                               render={({ field }) => (
                                  <FormItem>
                                     <FormLabel>Email</FormLabel>
                                     <FormControl><Input {...field} /></FormControl>
                                     <FormMessage />
                                  </FormItem>
                               )}
                            />
                         </div>
                         <FormField
                            control={profileForm.control}
                            name="phone"
                            render={({ field }) => (
                               <FormItem>
                                  <FormLabel>Phone Number</FormLabel>
                                  <FormControl><Input {...field} /></FormControl>
                                  <FormMessage />
                               </FormItem>
                            )}
                         />
                         <FormField
                            control={profileForm.control}
                            name="bio"
                            render={({ field }) => (
                               <FormItem>
                                  <FormLabel>Bio</FormLabel>
                                  <FormControl><Textarea className="min-h-[100px]" {...field} /></FormControl>
                                  <FormDescription>Brief description for your profile.</FormDescription>
                                  <FormMessage />
                               </FormItem>
                            )}
                         />
                         <div className="flex justify-end">
                            <Button type="submit" disabled={isSubmitting}>
                               {isSubmitting && <span className="mr-2 animate-spin">⏳</span>}
                               Save Changes
                            </Button>
                         </div>
                      </form>
                   </Form>
                </CardContent>
              </Card>
            </TabsContent>

            {/* PROFESSIONAL TAB */}
            <TabsContent value="professional" className="mt-0">
               <Card>
                <CardHeader>
                  <CardTitle>Professional Details</CardTitle>
                  <CardDescription>These details appear on your certificates.</CardDescription>
                </CardHeader>
                <CardContent>
                   <Form {...professionalForm}>
                      <form onSubmit={professionalForm.handleSubmit(onProfessionalSubmit)} className="space-y-4">
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <FormField
                               control={professionalForm.control}
                               name="jobTitle"
                               render={({ field }) => (
                                  <FormItem>
                                     <FormLabel>Job Title</FormLabel>
                                     <FormControl><Input {...field} /></FormControl>
                                     <FormMessage />
                                  </FormItem>
                               )}
                            />
                            <FormField
                               control={professionalForm.control}
                               name="organization"
                               render={({ field }) => (
                                  <FormItem>
                                     <FormLabel>Organization / Hospital</FormLabel>
                                     <FormControl><Input {...field} /></FormControl>
                                     <FormMessage />
                                  </FormItem>
                               )}
                            />
                         </div>
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <FormField
                               control={professionalForm.control}
                               name="licenseNumber"
                               render={({ field }) => (
                                  <FormItem>
                                     <FormLabel>License Number</FormLabel>
                                     <FormControl><Input {...field} /></FormControl>
                                     <FormDescription>Required for CME credits.</FormDescription>
                                     <FormMessage />
                                  </FormItem>
                               )}
                            />
                            <FormField
                               control={professionalForm.control}
                               name="specialization"
                               render={({ field }) => (
                                  <FormItem>
                                     <FormLabel>Specialization</FormLabel>
                                     <FormControl><Input {...field} /></FormControl>
                                     <FormMessage />
                                  </FormItem>
                               )}
                            />
                         </div>
                         <div className="flex justify-end">
                            <Button type="submit" disabled={isSubmitting}>
                               {isSubmitting && <span className="mr-2 animate-spin">⏳</span>}
                               Save Professional Info
                            </Button>
                         </div>
                      </form>
                   </Form>
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
                      <form onSubmit={securityForm.handleSubmit(onSecuritySubmit)} className="space-y-4">
                         <FormField
                            control={securityForm.control}
                            name="currentPassword"
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
                               name="newPassword"
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
                               name="confirmPassword"
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
                               {isSubmitting && <span className="mr-2 animate-spin">⏳</span>}
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
                   <div className="flex items-center justify-between space-x-2">
                      <div className="space-y-0.5">
                         <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                            Email Notifications
                         </label>
                         <p className="text-sm text-muted-foreground">Receive emails about your account activity.</p>
                      </div>
                      <Switch defaultChecked />
                   </div>
                   <Separator />
                   <div className="flex items-center justify-between space-x-2">
                      <div className="space-y-0.5">
                         <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                            Event Reminders
                         </label>
                         <p className="text-sm text-muted-foreground">Get notified 24 hours before events start.</p>
                      </div>
                      <Switch defaultChecked />
                   </div>
                   <Separator />
                   <div className="flex items-center justify-between space-x-2">
                      <div className="space-y-0.5">
                         <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                            Marketing Updates
                         </label>
                         <p className="text-sm text-muted-foreground">Receive news about new features and promotions.</p>
                      </div>
                      <Switch />
                   </div>
                   <div className="flex justify-end pt-4">
                      <Button onClick={() => toast.success("Preferences saved")}>Save Preferences</Button>
                   </div>
                </CardContent>
              </Card>
            </TabsContent>

          </div>
        </div>
      </Tabs>
    </div>
  );
}
