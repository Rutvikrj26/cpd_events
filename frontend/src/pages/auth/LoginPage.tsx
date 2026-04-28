import React from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Checkbox } from "@/shared/ui/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from "@/shared/ui/form";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/features/auth";
import { toast } from "sonner";
import { signInWithFirebase } from "@/api/accounts";
import { getGoogleIdToken, isFirebaseConfigured } from "@/lib/firebase";
import { useDocumentTitle } from "@/shared/hooks/useDocumentTitle";

const formSchema = z.object({
  email: z.string().email({
    message: "Please enter a valid email address.",
  }),
  password: z.string().min(8, {
    message: "Password must be at least 8 characters.",
  }),
  remember: z.boolean().default(false),
});

export function LoginPage() {
  useDocumentTitle('Sign in');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, completeLogin, deployment, isAuthenticated } = useAuth();
  const [isLoading, setIsLoading] = React.useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = React.useState(false);
  const [showPassword, setShowPassword] = React.useState(false);
  const returnUrl = searchParams.get('returnUrl');
  const oauthError = searchParams.get('error');
  const firebaseReady = isFirebaseConfigured();
  const registrationMode = deployment?.registration_mode ?? 'open';
  const signupAllowed = registrationMode !== 'invite_only';

  React.useEffect(() => {
    if (oauthError === 'invite_only') {
      toast.error(
        'Registration is by invitation only. Contact your institution administrator for access.'
      );
    }
  }, [oauthError]);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema) as any,
    defaultValues: {
      email: "",
      password: "",
      remember: false,
    },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsLoading(true);
    // Clear any leftover toasts (e.g. a "Network error" from offline retries
    // or a previous failed login attempt) so the user starts each submit
    // with a clean slate.
    toast.dismiss();
    try {
      await login({ email: values.email, password: values.password });
      toast.dismiss();
      toast.success("Logged in successfully");

      // SMART REDIRECT LOGIC
      // 1. Return URL (explicit intent)
      if (returnUrl) {
        navigate(returnUrl);
        return;
      }

      // 2. Default fallback
      navigate("/dashboard");
    } catch (error) {
      toast.error("Invalid email or password", { id: "login-error" });
    } finally {
      setIsLoading(false);
    }
  }

  // Already-signed-in users hitting /login bounce straight to the dashboard
  // (or to the explicit returnUrl if one was passed). Placed after all hooks
  // so a post-login re-render can early-return without violating rules-of-hooks.
  if (isAuthenticated) {
    return <Navigate to={returnUrl || '/dashboard'} replace />;
  }

  async function onGoogle() {
    if (!firebaseReady) {
      toast.error("Google sign-in isn't configured for this environment.");
      return;
    }
    setIsGoogleLoading(true);
    try {
      const idToken = await getGoogleIdToken();
      const { access, refresh } = await signInWithFirebase(idToken);
      await completeLogin(access, refresh);
      toast.success("Signed in with Google");
      navigate(returnUrl ?? "/dashboard");
    } catch (err: any) {
      const msg =
        err?.response?.data?.error?.message ||
        err?.message ||
        "Google sign-in failed.";
      toast.error(msg);
    } finally {
      setIsGoogleLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Sign in to your account
        </h1>
        <p className="text-sm text-muted-foreground">
          {signupAllowed ? (
            <>
              New here?{" "}
              <Link to="/signup" className="font-medium text-primary hover:text-primary/80">
                Create an account
              </Link>
              .
            </>
          ) : (
            "Accounts on this platform are created by invitation only. Contact your administrator for access."
          )}
        </p>
      </div>

      {firebaseReady && (
        <>
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={onGoogle}
            disabled={isGoogleLoading || isLoading}
          >
            {isGoogleLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Continue with Google
          </Button>
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">or</span>
            </div>
          </div>
        </>
      )}

      <Form {...form}>
        <form noValidate onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-6">
          <FormField
            control={form.control as any}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email address</FormLabel>
                <FormControl>
                  <Input
                    type="email"
                    autoComplete="username"
                    inputMode="email"
                    placeholder="name@company.com"
                    {...field}
                  />
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
                <div className="flex items-center justify-between">
                  <FormLabel>Password</FormLabel>
                  <Link
                    to="/forgot-password"
                    className="text-sm font-medium text-primary hover:text-primary/80"
                  >
                    Forgot password?
                  </Link>
                </div>
                {/* FormControl uses Radix Slot — its id/aria props go to the
                    *immediate* child. Keep <Input> as that child so the label
                    association is correct, and overlay the show/hide toggle
                    via absolute positioning on a sibling. */}
                <div className="relative">
                  <FormControl>
                    <Input
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      placeholder="••••••••"
                      {...field}
                    />
                  </FormControl>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      onClick={() => setShowPassword((prev) => !prev)}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                      <span className="sr-only">
                        {showPassword ? "Hide password" : "Show password"}
                      </span>
                    </Button>
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control as any}
            name="remember"
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
                    Remember me
                  </FormLabel>
                </div>
              </FormItem>
            )}
          />

          <Button type="submit" className="w-full bg-primary hover:bg-primary/90" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Sign in
          </Button>
        </form>
      </Form>
    </div>
  );
}
