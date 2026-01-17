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
import { initiateGoogleSignIn } from "@/api/auth/googleAuth";
import { getPublicPricing } from "@/api/billing";

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
  const [isGoogleLoading, setIsGoogleLoading] = React.useState(false);
  const [trialDays, setTrialDays] = React.useState<number | null>(null);

  // Get plan, role, and returnUrl from URL
  const planFromUrl = searchParams.get('plan') || 'free';
  const roleFromUrl = searchParams.get('role');
  const returnUrl = searchParams.get('returnUrl');
  const isOrganizer = roleFromUrl === 'organizer';
  const isCourseManager = roleFromUrl === 'course_manager';
  const isTrialPlan = ['organizer', 'lms', 'organization'].includes(planFromUrl.toLowerCase());

  // Fetch trial days from backend pricing API
  React.useEffect(() => {
    async function fetchTrialDays() {
      try {
        const products = await getPublicPricing();
        // Find the matching product based on the plan
        const planKey = isCourseManager ? 'lms' : isOrganizer ? 'organizer' : planFromUrl.toLowerCase();
        const product = products.find(p => p.plan === planKey);
        if (product?.trial_days) {
          setTrialDays(product.trial_days);
        }
      } catch (error) {
        // Fallback handled by trialDays being null
        console.error('Failed to fetch pricing:', error);
      }
    }
    if (isTrialPlan) {
      fetchTrialDays();
    }
  }, [isTrialPlan, isOrganizer, isCourseManager, planFromUrl]);

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
      const accountType = isOrganizer ? 'organizer' : isCourseManager ? 'course_manager' : 'attendee';
      await register({
        email: values.email,
        password: values.password,
        password_confirm: values.confirmPassword,
        full_name: values.fullName,
        account_type: accountType,
      });

      // Check if we are authenticated (have tokens)
      // If NOT authenticated, it means we need email verification (local flow)
      // We can check this by seeing if the register function stored tokens (which updates auth state)
      // But since state updates might be async, we key off the fact that register didn't throw.
      // A better check is to see if we have a returnUrl usage or just force check-email for local.

      // Actually, my AuthContext change means we WON'T have tokens for local signup.
      // So we should navigate to check-email.

      // However, we need to distinguish slightly or just assume local always needs it now?
      // Yes, local always needs it now. Google sign-in is handled separately.

      navigate("/auth/check-email", { state: { email: values.email } });

    } catch (error) {
      // Error toast is handled globally by API client
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGoogleSignIn() {
    setIsGoogleLoading(true);
    try {
      await initiateGoogleSignIn();
    } catch (error) {
      toast.error("Failed to initiate Google sign-in");
      setIsGoogleLoading(false);
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
          {isOrganizer ? "Create Organizer Account" : isCourseManager ? "Create Course Manager Account" : "Create Attendee Account"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:text-primary/80">
            Sign in
          </Link>
        </p>
      </div>

      {/* Trial Banner */}
      {(isOrganizer || isCourseManager) && isTrialPlan && (
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-4 text-center">
          <div className="flex items-center justify-center gap-2 text-primary font-medium mb-1">
            <Crown className="h-4 w-4" />
            <span>{trialDays ? `${trialDays}-Day Trial` : 'Free Trial'}</span>
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

      {isCourseManager && (
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 space-y-3 animate-in fade-in slide-in-from-top-2">
          <div className="font-medium text-sm text-foreground flex items-center gap-2">
            <Award className="h-4 w-4 text-primary" />
            LMS account includes:
          </div>
          <ul className="text-sm text-muted-foreground space-y-1.5 ml-6">
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Build self-paced courses and modules
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Track learner progress and completion
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Issue course completion certificates
            </li>
            <li className="flex items-center gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-primary" />
              Accept payments for paid courses
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
            {isOrganizer ? 'Create Organizer Account' : isCourseManager ? 'Create Course Manager Account' : 'Create Attendee Account'}
          </Button>
        </form>
      </Form>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
        </div>
      </div>

      {/* Google Sign-In */}
      <Button
        variant="outline"
        className="w-full"
        onClick={handleGoogleSignIn}
        disabled={isGoogleLoading || isLoading}
      >
        {isGoogleLoading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
            <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
          </svg>
        )}
        Sign up with Google
      </Button>

      {/* Mode Switching Links */}
      <div className="text-center text-sm text-muted-foreground pt-4 space-y-2 border-t border-border mt-2">
        <p className="text-xs text-muted-foreground mb-3">Looking for a different account type?</p>
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-1">
          {!isOrganizer && !isCourseManager && (
            <>
              <Link to="/signup?role=organizer&plan=organizer" className="text-primary hover:text-primary/80 font-medium">
                Host Events
              </Link>
              <span className="text-border">•</span>
              <Link to="/signup?role=course_manager&plan=lms" className="text-accent hover:text-accent/80 font-medium">
                Create Courses
              </Link>
            </>
          )}
          {isOrganizer && (
            <>
              <Link to="/signup" className="text-primary hover:text-primary/80 font-medium">
                Attend Events
              </Link>
              <span className="text-border">•</span>
              <Link to="/signup?role=course_manager&plan=lms" className="text-accent hover:text-accent/80 font-medium">
                Create Courses
              </Link>
            </>
          )}
          {isCourseManager && (
            <>
              <Link to="/signup" className="text-primary hover:text-primary/80 font-medium">
                Attend Events
              </Link>
              <span className="text-border">•</span>
              <Link to="/signup?role=organizer&plan=organizer" className="text-primary hover:text-primary/80 font-medium">
                Host Events
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
