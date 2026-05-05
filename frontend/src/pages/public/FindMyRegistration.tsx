/**
 * FindMyRegistration — Eventbrite-parity rescue page.
 *
 * Surface: `/find-my-registration`. The user types their email; we
 * re-issue a CLAIM link for any pending guest registration matching it.
 * The endpoint always returns 202 with the same body (anti-enumeration).
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Search } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { findMyRegistration } from '@/api/magic-link';

export function FindMyRegistration() {
    const [email, setEmail] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [sent, setSent] = useState(false);

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) return;
        setSubmitting(true);
        try {
            await findMyRegistration(email);
            setSent(true);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-muted/30 p-6">
            <Card className="w-full max-w-lg">
                <CardHeader className="space-y-3 text-center">
                    <div className="mx-auto">
                        <Search className="h-10 w-10 text-primary" />
                    </div>
                    <CardTitle className="text-xl">Find my registration</CardTitle>
                    <CardDescription className="text-sm">
                        Enter the email you used at registration and we'll send a fresh access link.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {sent ? (
                        <div className="rounded-md border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                            If we have a registration for that email, we've sent a fresh access link.
                            The link expires in 90 days.
                        </div>
                    ) : (
                        <form onSubmit={onSubmit} className="space-y-3">
                            <div className="space-y-1.5">
                                <Label htmlFor="fmr-email">Email</Label>
                                <Input
                                    id="fmr-email"
                                    type="email"
                                    inputMode="email"
                                    placeholder="name@company.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    disabled={submitting}
                                />
                            </div>
                            <Button type="submit" className="w-full" disabled={submitting}>
                                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                Send access link
                            </Button>
                        </form>
                    )}
                    <div className="text-center text-sm text-muted-foreground">
                        Already have an account?{' '}
                        <Link to="/login" className="underline underline-offset-2">
                            Sign in
                        </Link>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

export default FindMyRegistration;
