/**
 * RegistrationPending — info page after an anonymous registration.
 *
 * Lands here in two flows:
 *   1. Anonymous free registration: navigate('replace') from EventRegistration.
 *   2. Anonymous paid registration: Stripe redirects to /checkout/success,
 *      which (when reg.user is null) bounces here. The CheckoutReturn page
 *      keeps that wiring; we just render the same "Check your email" UI.
 *
 * Pulls minimal context from URL params: the registrant's email (so we
 * can show "We sent a link to <email>") and the event slug (so we can
 * link them back to the event page). Nothing sensitive.
 */

import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Mail } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';

export function RegistrationPending() {
    const { slug } = useParams<{ slug: string }>();
    const [params] = useSearchParams();
    const email = params.get('email') || '';

    return (
        <div className="flex min-h-screen items-center justify-center bg-muted/30 p-6">
            <Card className="w-full max-w-lg">
                <CardHeader className="space-y-3 text-center">
                    <div className="mx-auto">
                        <Mail className="h-10 w-10 text-primary" />
                    </div>
                    <CardTitle className="text-xl">Check your email</CardTitle>
                    <CardDescription className="text-sm">
                        {email
                            ? <>We've sent an access link to <span className="font-medium">{email}</span>.</>
                            : <>We've sent an access link to your email.</>}
                        {' '}Click it to set a password and view your registration.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                        The link expires in 90 days. Didn't get the email?
                        Check your spam folder, or{' '}
                        <Link to="/find-my-registration" className="underline underline-offset-2">
                            request a fresh link
                        </Link>
                        . Already have an account?{' '}
                        <Link to="/login" className="underline underline-offset-2">
                            Sign in
                        </Link>
                        .
                    </p>
                    {slug && (
                        <Button asChild variant="outline" className="w-full">
                            <Link to={`/events/${slug}`}>Back to event page</Link>
                        </Button>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default RegistrationPending;
