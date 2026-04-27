import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/features/auth';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import client from '@/api/client';

export const AcceptInvitationPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { setToken, setIsAuthenticated, setUser, fetchManifest } = useAuth();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [passwordConfirm, setPasswordConfirm] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    if (!token) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle>Invalid Link</CardTitle>
                        <CardDescription>This invitation link is invalid or missing.</CardDescription>
                    </CardHeader>
                </Card>
            </div>
        );
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (password !== passwordConfirm) {
            setError("Passwords don't match.");
            return;
        }

        if (password.length < 8) {
            setError("Password must be at least 8 characters.");
            return;
        }

        setIsLoading(true);
        try {
            const response = await client.post('/auth/accept-invitation/', {
                token,
                password,
                password_confirm: passwordConfirm,
            });

            const { access, refresh, user } = response.data;

            // Auto-login
            setToken(access, refresh);
            setIsAuthenticated(true);
            setUser(user);
            await fetchManifest();

            navigate('/dashboard', { replace: true });
        } catch (err: any) {
            const msg = err.response?.data?.error?.message
                || err.response?.data?.detail
                || 'Failed to accept invitation. Please try again.';
            setError(msg);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl">Set Up Your Account</CardTitle>
                    <CardDescription>
                        Choose a password to complete your account setup.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form noValidate onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                                {error}
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                minLength={8}
                                placeholder="Choose a strong password"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="password_confirm">Confirm Password</Label>
                            <Input
                                id="password_confirm"
                                type="password"
                                value={passwordConfirm}
                                onChange={(e) => setPasswordConfirm(e.target.value)}
                                required
                                minLength={8}
                                placeholder="Confirm your password"
                            />
                        </div>

                        <Button type="submit" className="w-full" disabled={isLoading}>
                            {isLoading ? 'Setting up...' : 'Create Account'}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
};
