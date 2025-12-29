import React from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm, FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription
} from "@/components/ui/form";
import { Loader2, Crown, Award } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

const formSchema = z.object({
  email: z.string().email({
    message: "Please enter a valid email address.",
  }),
  fullName: z.string().min(2, {
    message: "Name must be at least 2 characters.",
  }),
  password: z.string().min(8, {
    message: "Password must be at least 8 characters.",
  }),
  confirmPassword: z.string(),
  terms: z.boolean().refine(val => val === true, {
    message: "You must accept the terms and conditions.",
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

export function SignupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { register } = useAuth();
  const [isLoading, setIsLoading] = React.useState(false);

  // Get plan and role from URL
  const planFromUrl = searchParams.get('plan') || 'free';
  const roleFromUrl = searchParams.get('role');
  const isOrganizer = roleFromUrl === 'organizer';
  const isTrialPlan = ['pro', 'professional', 'starter'].includes(planFromUrl.toLowerCase());

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      fullName: "",
      password: "",
      confirmPassword: "",
      terms: false,
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsLoading(true);
    try {
      await register({
        email: values.email,
        password: values.password,
        password_confirm: values.confirmPassword,
        full_name: values.fullName,
        account_type: isOrganizer ? 'organizer' : 'attendee',
      });

      if (isOrganizer) {
        toast.success("Welcome! Your 30-day Professional trial has started.");
      } else {
        toast.success("Account created! Please check your email to verify.");
      }
      navigate("/login");
    } catch (error) {
      // Error toast is handled globally by API client
    } finally {
      setIsLoading(false);
    }
  }

  function onInvalid(errors: FieldErrors<z.infer<typeof formSchema>>) {
    if (errors.terms) {
      toast.error("You must accept the terms and conditions to continue.");
      return;
    }

    if (Object.keys(errors).length > 0) {
      toast.error("Please fix the errors in the form before continuing.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {isOrganizer ? "Create Organizer Account" : "Create Attendee Account"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:text-primary/80">
            Sign in
          </Link>
        </p>
      </div>

      {/* Trial Banner */}
      {isOrganizer && isTrialPlan && (
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-4 text-center">
          <div className="flex items-center justify-center gap-2 text-primary font-medium mb-1">
            <Crown className="h-4 w-4" />
            <span>30-Day Professional Trial</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Full access to all features. No credit card required.
          </p>
        </div>
      )}

      {/* Organizer Benefits - Moved above form for better context in Organizer mode */}
      {isOrganizer && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 space-y-3 animate-in fade-in slide-in-from-top-2">
          <div className="font-medium text-sm text-foreground flex items-center gap-2">
            <Award className="h-4 w-4 text-primary" />
            Organizer account includes:
          </div>
          <ul className="text-sm text-muted-foreground space-y-1.5 ml-6">
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Create unlimited events (with plan limits)
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Zoom integration for attendance tracking
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Issue professional certificates
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Accept payments for paid events
            </li>
          </ul>
        </div>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit, onInvalid)} className="space-y-6">
          <FormField
            control={form.control as any}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email address</FormLabel>
                <FormControl>
                  <Input placeholder="name@company.com" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control as any}
            name="fullName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Full Name</FormLabel>
                <FormControl>
                  <Input placeholder="John Doe" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control as any}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <Input type="password" placeholder="••••••••" {...field} />
                </FormControl>
                <FormDescription>
                  Must be at least 8 characters long.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control as any}
            name="confirmPassword"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Confirm Password</FormLabel>
                <FormControl>
                  <Input type="password" placeholder="••••••••" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control as any}
            name="terms"
            render={({ field }) => (
              <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
                <div className="space-y-1 leading-none">
                  <FormLabel className="font-normal text-foreground">
                    I agree to the{" "}
                    <Link to="/terms" className="text-primary hover:text-primary/80">
                      Terms of Service
                    </Link>{" "}
                    and{" "}
                    <Link to="/privacy" className="text-primary hover:text-primary/80">
                      Privacy Policy
                    </Link>
                  </FormLabel>
                  <FormMessage />
                </div>
              </FormItem>
            )}
          />

          <Button type="submit" className="w-full bg-primary hover:bg-primary/90" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isOrganizer ? 'Create Organizer Account' : 'Create Attendee Account'}
          </Button>
        </form>
      </Form>

      {/* Mode Switching Links */}
      <div className="text-center text-sm text-muted-foreground pt-2">
        {isOrganizer ? (
          <p>
            Looking for events?{" "}
            <Link to="/signup" className="text-primary hover:text-primary/80 font-medium">
              Create an Attendee Account
            </Link>
          </p>
        ) : (
          <p>
            Want to organize events?{" "}
            <Link to="/signup?role=organizer" className="text-primary hover:text-primary/80 font-medium">
              Create an Organizer Account
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
