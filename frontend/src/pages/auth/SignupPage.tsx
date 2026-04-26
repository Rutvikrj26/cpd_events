import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { useAuth } from "@/contexts/AuthContext";
import { signup, signInWithFirebase } from "@/api/accounts";
import { getGoogleIdToken, isFirebaseConfigured } from "@/lib/firebase";

const schema = z
    .object({
        full_name: z.string().min(2, { message: "Please enter your full name." }),
        email: z.string().email({ message: "Please enter a valid email address." }),
        password: z.string().min(8, { message: "Password must be at least 8 characters." }),
        password_confirm: z.string(),
    })
    .refine((d) => d.password === d.password_confirm, {
        message: "Passwords don't match.",
        path: ["password_confirm"],
    });

type FormValues = z.infer<typeof schema>;

export function SignupPage() {
    useDocumentTitle('Create account');
    const navigate = useNavigate();
    const { deployment, completeLogin } = useAuth();
    const [isSubmitting, setIsSubmitting] = React.useState(false);
    const [isGoogleLoading, setIsGoogleLoading] = React.useState(false);
    const [showPassword, setShowPassword] = React.useState(false);

    const firebaseReady = isFirebaseConfigured();
    const registrationMode = deployment?.registration_mode ?? "open";

    const form = useForm<FormValues>({
        resolver: zodResolver(schema) as any,
        defaultValues: {
            full_name: "",
            email: "",
            password: "",
            password_confirm: "",
        },
    });

    // If the deployment is invite-only, don't let the page render signup.
    if (registrationMode === "invite_only") {
        return (
            <div className="space-y-4 text-center">
                <h1 className="text-2xl font-bold tracking-tight text-foreground">
                    Sign-up is disabled
                </h1>
                <p className="text-sm text-muted-foreground">
                    Accounts on this platform are created by invitation only. Contact your administrator for access.
                </p>
                <Link to="/login" className="text-sm font-medium text-primary hover:text-primary/80">
                    Back to sign in
                </Link>
            </div>
        );
    }

    async function onSubmit(values: FormValues) {
        setIsSubmitting(true);
        try {
            await signup(values);
            toast.success("Account created. Check your email to verify.");
            navigate(`/auth/check-email?email=${encodeURIComponent(values.email)}`);
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            const msg = err?.response?.data?.error?.message || "Sign-up failed. Please try again.";
            if (code === "EMAIL_IN_USE") {
                toast.error(msg);
            } else if (code === "REGISTRATION_DISABLED") {
                toast.error(msg);
            } else {
                toast.error(msg);
            }
        } finally {
            setIsSubmitting(false);
        }
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
            navigate("/dashboard");
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
                <h1 className="text-2xl font-bold tracking-tight text-foreground">Create your account</h1>
                <p className="text-sm text-muted-foreground">
                    Get started in under a minute.{" "}
                    <Link to="/login" className="font-medium text-primary hover:text-primary/80">
                        Already have an account?
                    </Link>
                </p>
            </div>

            {firebaseReady && (
                <>
                    <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        onClick={onGoogle}
                        disabled={isGoogleLoading || isSubmitting}
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
                <form onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-4">
                    <FormField
                        control={form.control as any}
                        name="full_name"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Full name</FormLabel>
                                <FormControl>
                                    <Input autoComplete="name" placeholder="Dr. Jane Doe" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control as any}
                        name="email"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Email address</FormLabel>
                                <FormControl>
                                    <Input
                                        type="email"
                                        autoComplete="email"
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
                                <FormLabel>Password</FormLabel>
                                <FormControl>
                                    <div className="relative">
                                        <Input
                                            type={showPassword ? "text" : "password"}
                                            autoComplete="new-password"
                                            placeholder="At least 8 characters"
                                            {...field}
                                        />
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                            onClick={() => setShowPassword((p) => !p)}
                                        >
                                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                            <span className="sr-only">
                                                {showPassword ? "Hide password" : "Show password"}
                                            </span>
                                        </Button>
                                    </div>
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <FormField
                        control={form.control as any}
                        name="password_confirm"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Confirm password</FormLabel>
                                <FormControl>
                                    <Input
                                        type={showPassword ? "text" : "password"}
                                        autoComplete="new-password"
                                        placeholder="Repeat password"
                                        {...field}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />

                    <Button
                        type="submit"
                        className="w-full bg-primary hover:bg-primary/90"
                        disabled={isSubmitting || isGoogleLoading}
                    >
                        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Create account
                    </Button>
                </form>
            </Form>

            <p className="text-center text-xs text-muted-foreground">
                By signing up you agree to our{" "}
                <Link to="/terms" className="underline hover:text-foreground">
                    terms
                </Link>{" "}
                and{" "}
                <Link to="/privacy" className="underline hover:text-foreground">
                    privacy policy
                </Link>
                .
            </p>
        </div>
    );
}
