/**
 * MagicLinkPage — public landing for `/magic-link/:uuid?t=<token>`.
 *
 * State machine:
 *   1. Verify the token → POST /public/magic-link/:uuid/verify/?t=
 *   2a. Invalid / expired / cancelled / accepted → terminal card.
 *   2b. CLAIM + user_exists=false → set-password form. Submit → accept,
 *       store JWTs, redirect.
 *   2c. CLAIM + user_exists=true → "An account already exists for this
 *       email — sign in to claim your registration." (We never silently
 *       bypass an existing password; mirrors the backend EMAIL_HAS_ACCOUNT
 *       guard at registration time.)
 *   2d. SIGN_IN → auto-accept, store JWTs, redirect.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2 } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { acceptMagicLink, verifyMagicLink } from '@/api/magic-link';
import type { MagicLinkVerifyResponse } from '@/api/magic-link/types';
import { useAuth } from '@/features/auth';

type ResolveState =
    | { status: 'loading' }
    | { status: 'ok'; link: MagicLinkVerifyResponse }
    | { status: 'expired' | 'cancelled' | 'accepted'; email?: string }
    | { status: 'invalid'; reason: string };

export function MagicLinkPage() {
    const { uuid } = useParams<{ uuid: string }>();
    const [searchParams] = useSearchParams();
    const token = searchParams.get('t') ?? '';
    const navigate = useNavigate();
    const { completeLogin, isLoading: authLoading } = useAuth();

    const [resolveState, setResolveState] = useState<ResolveState>({ status: 'loading' });
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [accepting, setAccepting] = useState(false);
    const [acceptError, setAcceptError] = useState<string | null>(null);
    const [signInTriggered, setSignInTriggered] = useState(false);

    const resolve = useCallback(async () => {
        if (!uuid || !token) {
            setResolveState({ status: 'invalid', reason: 'Missing or malformed link.' });
            return;
        }
        try {
            const link = await verifyMagicLink(uuid, token);
            setResolveState({ status: 'ok', link });
        } catch (err) {
            const status = (err as { response?: { status?: number; data?: { status?: string; email?: string } } })?.response?.status;
            const data = (err as { response?: { data?: { status?: string; email?: string } } })?.response?.data;
            if (status === 410 && data?.status) {
                if (data.status === 'expired') setResolveState({ status: 'expired', email: data.email });
                else if (data.status === 'cancelled') setResolveState({ status: 'cancelled', email: data.email });
                else setResolveState({ status: 'accepted', email: data.email });
            } else {
                setResolveState({ status: 'invalid', reason: 'This link is invalid or has expired.' });
            }
        }
    }, [uuid, token]);

    useEffect(() => {
        resolve();
    }, [resolve]);

    const acceptClaim = async () => {
        if (resolveState.status !== 'ok' || !uuid) return;
        if (password.length < 8) {
            setAcceptError('Password must be at least 8 characters.');
            return;
        }
        if (password !== confirm) {
            setAcceptError("Passwords don't match.");
            return;
        }
        setAccepting(true);
        setAcceptError(null);
        try {
            const result = await acceptMagicLink(uuid, token, { password });
            await completeLogin(result.access, result.refresh);
            navigate(result.redirect_url, { replace: true });
        } catch (err) {
            const detail =
                (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ||
                (err as Error)?.message ||
                'Failed to set password.';
            setAcceptError(detail);
        } finally {
            setAccepting(false);
        }
    };

    // SIGN_IN auto-accepts on page load — no form, no friction.
    const acceptSignIn = useCallback(async () => {
        if (!uuid) return;
        setAccepting(true);
        setAcceptError(null);
        try {
            const result = await acceptMagicLink(uuid, token, {});
            await completeLogin(result.access, result.refresh);
            navigate(result.redirect_url, { replace: true });
        } catch (err) {
            const detail =
                (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ||
                (err as Error)?.message ||
                'Failed to sign in.';
            setAcceptError(detail);
        } finally {
            setAccepting(false);
        }
    }, [uuid, token, completeLogin, navigate]);

    useEffect(() => {
        if (resolveState.status === 'ok' && resolveState.link.purpose === 'sign_in' && !signInTriggered) {
            setSignInTriggered(true);
            acceptSignIn();
        }
    }, [resolveState, signInTriggered, acceptSignIn]);

    /* -------- Render -------- */

    if (resolveState.status === 'loading' || authLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center p-6">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (resolveState.status === 'invalid') {
        return (
            <CenteredCard
                icon={<AlertCircle className="h-10 w-10 text-amber-500" />}
                title="Link not available"
                description={resolveState.reason}
            >
                <Button asChild variant="outline">
                    <Link to="/login">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Go to sign in
                    </Link>
                </Button>
            </CenteredCard>
        );
    }

    if (resolveState.status === 'expired') {
        return (
            <CenteredCard
                icon={<AlertCircle className="h-10 w-10 text-amber-500" />}
                title="This link has expired"
                description="Request a fresh link from the sign-in page."
            >
                <Button asChild>
                    <Link to="/login">Go to sign in</Link>
                </Button>
            </CenteredCard>
        );
    }
    if (resolveState.status === 'cancelled') {
        return (
            <CenteredCard
                icon={<AlertCircle className="h-10 w-10 text-amber-500" />}
                title="This link was cancelled"
                description="Contact support if you believe this is in error."
            />
        );
    }
    if (resolveState.status === 'accepted') {
        return (
            <CenteredCard
                icon={<CheckCircle2 className="h-10 w-10 text-primary" />}
                title="Link already used"
                description="This link has already been used. Sign in with your password."
            >
                <Button asChild>
                    <Link to="/login">Go to sign in</Link>
                </Button>
            </CenteredCard>
        );
    }

    const link = resolveState.link;
    const summary = link.registration_summary;

    if (link.purpose === 'sign_in') {
        return (
            <CenteredCard
                icon={<Loader2 className="h-10 w-10 animate-spin text-primary" />}
                title="Signing you in…"
                description="One moment."
            >
                {acceptError && <p className="text-sm text-destructive">{acceptError}</p>}
            </CenteredCard>
        );
    }

    // CLAIM branch.
    if (link.user_exists) {
        const next = encodeURIComponent('/');
        return (
            <CenteredCard
                icon={<AlertCircle className="h-10 w-10 text-amber-500" />}
                title="An account already exists for this email"
                description={`Sign in as ${link.email} to access your registration.`}
            >
                <Button asChild>
                    <Link to={`/login?email=${encodeURIComponent(link.email)}&next=${next}`}>
                        Sign in
                    </Link>
                </Button>
            </CenteredCard>
        );
    }

    return (
        <CenteredCard
            icon={<CheckCircle2 className="h-10 w-10 text-primary" />}
            title={summary ? `You're registered for ${summary.event_title}` : "Set a password to continue"}
            description={`Set a password for ${link.email} to access your registration.`}
        >
            {summary && (
                <div className="rounded-md border bg-muted/40 px-4 py-3 text-sm">
                    <p>
                        <span className="font-medium">Event:</span> {summary.event_title}
                    </p>
                    {summary.event_starts_at && (
                        <p className="text-muted-foreground">
                            {new Date(summary.event_starts_at).toLocaleString()}
                        </p>
                    )}
                    {Number(summary.total_amount) > 0 && (
                        <p className="text-muted-foreground">
                            {summary.currency} ${summary.total_amount} • paid
                        </p>
                    )}
                </div>
            )}

            <form
                className="space-y-3"
                onSubmit={(e) => {
                    e.preventDefault();
                    acceptClaim();
                }}
            >
                <div className="space-y-1.5">
                    <Label htmlFor="ml-password">New password</Label>
                    <Input
                        id="ml-password"
                        type="password"
                        autoComplete="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        minLength={8}
                        required
                        disabled={accepting}
                    />
                </div>
                <div className="space-y-1.5">
                    <Label htmlFor="ml-confirm">Confirm password</Label>
                    <Input
                        id="ml-confirm"
                        type="password"
                        autoComplete="new-password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        minLength={8}
                        required
                        disabled={accepting}
                    />
                </div>
                {acceptError && <p className="text-sm text-destructive">{acceptError}</p>}
                <Button type="submit" className="w-full" disabled={accepting}>
                    {accepting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {accepting ? 'Setting password…' : 'Set password and continue'}
                </Button>
            </form>
        </CenteredCard>
    );
}

/* -------- Helpers ----------------------------------------------------- */

function CenteredCard({
    icon,
    title,
    description,
    children,
}: {
    icon: React.ReactNode;
    title: string;
    description?: string;
    children?: React.ReactNode;
}) {
    return (
        <div className="flex min-h-screen items-center justify-center bg-muted/30 p-6">
            <Card className="w-full max-w-lg">
                <CardHeader className="space-y-3 text-center">
                    <div className="mx-auto">{icon}</div>
                    <CardTitle className="text-xl">{title}</CardTitle>
                    {description && (
                        <CardDescription className="text-sm">{description}</CardDescription>
                    )}
                </CardHeader>
                {children && <CardContent className="space-y-4">{children}</CardContent>}
            </Card>
        </div>
    );
}

export default MagicLinkPage;
