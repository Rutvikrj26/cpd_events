import React, { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, CheckCircle, XCircle, Eye, EyeOff, Lock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/AuthContext";
import { verifyEmail, confirmPasswordReset } from "@/api/accounts";
import { toast } from "sonner";

type PageStatus = 'loading' | 'needs_password' | 'setting_password' | 'success' | 'error';

export function VerifyEmailPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { setToken, setIsAuthenticated, setUser, fetchManifest } = useAuth();
    const [status, setStatus] = useState<PageStatus>('loading');
    const [errorMessage, setErrorMessage] = useState<string>('');

    // Password form state
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [passwordError, setPasswordError] = useState('');

    const token = searchParams.get('token');
    const passwordToken = searchParams.get('password_token');
    const verificationAttempted = useRef(false);

    // Store verified user data for after password setup
    const [verifiedAuth, setVerifiedAuth] = useState<{
        access: string;
        refresh: string;
        user: any;
    } | null>(null);

    useEffect(() => {
        const verify = async () => {
            if (!token) {
                setStatus('error');
                setErrorMessage('No verification token provided.');
                return;
            }

            if (verificationAttempted.current) return;
            verificationAttempted.current = true;

            try {
                const response = await verifyEmail(token);

                // Store tokens and user data
                if (response.access && response.refresh && response.user) {
                    setVerifiedAuth({
                        access: response.access,
                        refresh: response.refresh,
                        user: response.user,
                    });

                    // If password_token is present, user needs to set password
                    if (passwordToken) {
                        setStatus('needs_password');
                        toast.success('Email verified! Please set your password.');
                        return;
                    }

                    // Normal flow: complete login
                    setToken(response.access, response.refresh);
                    setIsAuthenticated(true);
                    setUser(response.user);
                    await fetchManifest();
                    setStatus('success');
                    toast.success('Email verified successfully!');

                    // Redirect after 2 seconds
                    setTimeout(() => {
                        navigate('/onboarding');
                    }, 2000);
                } else {
                    throw new Error("Invalid response from server");
                }
            } catch (error: any) {
                setStatus('error');
                const message = error.response?.data?.error?.message || 'Failed to verify email. The token may be invalid or expired.';
                setErrorMessage(message);
                toast.error(message);
            }
        };

        verify();
    }, [token]);

    const handlePasswordSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setPasswordError('');

        // Validation
        if (password.length < 8) {
            setPasswordError('Password must be at least 8 characters.');
            return;
        }
        if (password !== confirmPassword) {
            setPasswordError('Passwords do not match.');
            return;
        }
        if (!passwordToken) {
            setPasswordError('Missing password token.');
            return;
        }

        setStatus('setting_password');

        try {
            // Call password reset endpoint
            await confirmPasswordReset({ token: passwordToken, new_password: password, new_password_confirm: confirmPassword });

            // Now complete login with stored auth
            if (verifiedAuth) {
                setToken(verifiedAuth.access, verifiedAuth.refresh);
                setIsAuthenticated(true);
                setUser(verifiedAuth.user);
                await fetchManifest();
            }

            setStatus('success');
            toast.success('Password set successfully!');

            // Check if user has an organization to redirect to
            setTimeout(() => {
                // Redirect based on account type
                navigate('/onboarding');
            }, 2000);

        } catch (error: any) {
            setStatus('needs_password');
            const message = error.response?.data?.error?.message || 'Failed to set password.';
            setPasswordError(message);
            toast.error(message);
        }
    };

    if (status === 'loading') {
        return (
            <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
                <Card className="w-full max-w-md">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                        <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
                        <p className="text-muted-foreground">Verifying your email...</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (status === 'needs_password' || status === 'setting_password') {
        return (
            <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
                <Card className="w-full max-w-md">
                    <CardContent className="py-8">
                        <div className="flex flex-col items-center text-center mb-6">
                            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                                <Lock className="h-8 w-8 text-primary" />
                            </div>
                            <h2 className="text-2xl font-bold mb-2">Set Your Password</h2>
                            <p className="text-muted-foreground">
                                Your email has been verified. Please set a password to complete your account setup.
                            </p>
                        </div>

                        <form onSubmit={handlePasswordSubmit} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="password">Password</Label>
                                <div className="relative">
                                    <Input
                                        id="password"
                                        type={showPassword ? "text" : "password"}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Enter password"
                                        required
                                        minLength={8}
                                        disabled={status === 'setting_password'}
                                    />
                                    <button
                                        type="button"
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                        onClick={() => setShowPassword(!showPassword)}
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                                <p className="text-sm text-muted-foreground">Must be at least 8 characters.</p>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="confirmPassword">Confirm Password</Label>
                                <Input
                                    id="confirmPassword"
                                    type={showPassword ? "text" : "password"}
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    placeholder="Confirm password"
                                    required
                                    disabled={status === 'setting_password'}
                                />
                            </div>

                            {passwordError && (
                                <p className="text-sm text-destructive">{passwordError}</p>
                            )}

                            <Button
                                type="submit"
                                className="w-full"
                                disabled={status === 'setting_password'}
                            >
                                {status === 'setting_password' ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Setting Password...
                                    </>
                                ) : (
                                    'Set Password & Continue'
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (status === 'success') {
        return (
            <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
                <Card className="w-full max-w-md border-green-200 bg-green-50/50">
                    <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                        <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center mb-4">
                            <CheckCircle className="h-8 w-8 text-green-600" />
                        </div>
                        <h2 className="text-2xl font-bold mb-2">You're All Set!</h2>
                        <p className="text-muted-foreground mb-4">
                            Your email has been verified and you're now logged in.
                        </p>
                        <p className="text-sm text-muted-foreground">
                            Redirecting to your dashboard...
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Error state
    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
            <Card className="w-full max-w-md border-destructive/20">
                <CardContent className="py-12">
                    <div className="flex flex-col items-center text-center mb-6">
                        <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
                            <XCircle className="h-8 w-8 text-destructive" />
                        </div>
                        <h2 className="text-2xl font-bold mb-2">Verification Failed</h2>
                        <p className="text-muted-foreground">{errorMessage}</p>
                    </div>
                    <div className="flex justify-center gap-4">
                        <Button variant="outline" onClick={() => navigate('/login')}>
                            Go to Login
                        </Button>
                        <Button onClick={() => navigate('/onboarding')}>
                            Go to Dashboard
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
