import React, { useState, useEffect, useCallback } from "react";
import { Link, useLocation } from "react-router-dom";
import { Mail, ArrowRight, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { resendVerificationEmail } from "@/api/accounts";

const COOLDOWN_SECONDS = 60;

export function CheckEmailPage() {
    const location = useLocation();
    // Try to get email from state if it was passed during navigation
    const email = location.state?.email || "your email address";

    const [resendState, setResendState] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [resendError, setResendError] = useState<string>("");
    const [cooldown, setCooldown] = useState(0);

    useEffect(() => {
        if (cooldown <= 0) return;
        const timer = setInterval(() => {
            setCooldown((prev) => {
                if (prev <= 1) {
                    clearInterval(timer);
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(timer);
    }, [cooldown]);

    const handleResend = useCallback(async () => {
        if (cooldown > 0 || resendState === 'loading') return;
        if (!email || email === "your email address") {
            setResendError("Email address is not available. Please sign up again.");
            setResendState('error');
            return;
        }

        setResendState('loading');
        setResendError("");

        try {
            await resendVerificationEmail(email);
            setResendState('success');
            setCooldown(COOLDOWN_SECONDS);
        } catch (err: any) {
            const message = err?.response?.data?.error?.message
                || err?.response?.data?.detail
                || err?.response?.data?.message
                || "Failed to resend verification email. Please try again later.";
            setResendError(message);
            setResendState('error');
            // Still set a shorter cooldown on error to prevent spamming
            setCooldown(15);
        }
    }, [email, cooldown, resendState]);

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <div className="flex justify-center mb-4">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <Mail className="h-6 w-6 text-primary" />
                        </div>
                    </div>
                    <CardTitle className="text-2xl font-bold">Check your email</CardTitle>
                    <CardDescription className="text-base mt-2">
                        We've sent a verification link to <span className="font-medium text-foreground">{email}</span>.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground text-center">
                        Click the link in the email to verify your account and continue to onboarding.
                        If you don't see it, check your spam folder.
                    </p>

                    {/* Resend feedback */}
                    {resendState === 'success' && (
                        <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400 rounded-md p-3">
                            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                            <span>Verification email sent! Please check your inbox.</span>
                        </div>
                    )}
                    {resendState === 'error' && resendError && (
                        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-md p-3">
                            <AlertCircle className="h-4 w-4 flex-shrink-0" />
                            <span>{resendError}</span>
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex flex-col space-y-2">
                    <Button
                        variant="outline"
                        className="w-full"
                        onClick={handleResend}
                        disabled={cooldown > 0 || resendState === 'loading'}
                    >
                        {resendState === 'loading' ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Sending...
                            </>
                        ) : cooldown > 0 ? (
                            `Resend verification email (${cooldown}s)`
                        ) : (
                            "Resend verification email"
                        )}
                    </Button>
                    <Button variant="ghost" className="w-full" asChild>
                        <Link to="/login">
                            Return to Login
                        </Link>
                    </Button>
                </CardFooter>
            </Card>
        </div>
    );
}
