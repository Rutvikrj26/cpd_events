/**
 * AcceptInvitePage — public landing page for `/invite/:uuid?t=<token>`.
 *
 * State machine:
 *   1. resolve token → GET /public/invitations/:uuid/?t=
 *   2a. expired / cancelled / 404 → terminal explainer card
 *   2b. ok + unauthenticated → "Sign in / Sign up to accept" CTAs (carrying ?next= back here)
 *   2c. ok + authenticated AND email matches → "Accept" button → POST → redirect to target
 *   2d. ok + authenticated AND email differs → "switch account" hint (with sign-out + sign-in shortcut)
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2 } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { acceptInvitation, getPublicInvitation } from '@/api/invitations';
import type { PublicInvitation } from '@/api/invitations/types';
import { useAuth } from '@/features/auth';
import { useLogout } from '@/features/auth/hooks/useLogout';

type ResolveState =
    | { status: 'loading' }
    | { status: 'ok'; invitation: PublicInvitation }
    | { status: 'expired'; invitation: PublicInvitation }
    | { status: 'cancelled'; invitation: PublicInvitation }
    | { status: 'invalid'; reason: string };

export function AcceptInvitePage() {
    const { uuid } = useParams<{ uuid: string }>();
    const [searchParams] = useSearchParams();
    const token = searchParams.get('t') ?? '';
    const navigate = useNavigate();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const logout = useLogout();

    const [resolveState, setResolveState] = useState<ResolveState>({ status: 'loading' });
    const [accepting, setAccepting] = useState(false);
    const [acceptError, setAcceptError] = useState<string | null>(null);

    const nextUrl = useMemo(() => {
        // Round-trip back through the same accept page after sign-in / sign-up.
        const base = `/invite/${uuid}`;
        const qs = token ? `?t=${encodeURIComponent(token)}` : '';
        return encodeURIComponent(`${base}${qs}`);
    }, [uuid, token]);

    const resolve = useCallback(async () => {
        if (!uuid || !token) {
            setResolveState({ status: 'invalid', reason: 'Missing invitation token.' });
            return;
        }
        try {
            const inv = await getPublicInvitation(uuid, token);
            if (inv.expired || inv.status === 'expired') {
                setResolveState({ status: 'expired', invitation: inv });
            } else if (inv.status === 'cancelled') {
                setResolveState({ status: 'cancelled', invitation: inv });
            } else {
                setResolveState({ status: 'ok', invitation: inv });
            }
        } catch (err) {
            const status = (err as { response?: { status?: number; data?: PublicInvitation & { expired?: boolean; cancelled?: boolean } } })?.response?.status;
            const data = (err as { response?: { data?: PublicInvitation & { expired?: boolean; cancelled?: boolean } } })?.response?.data;
            if (status === 410 && data) {
                if (data.expired) {
                    setResolveState({ status: 'expired', invitation: data });
                } else if (data.cancelled) {
                    setResolveState({ status: 'cancelled', invitation: data });
                } else {
                    setResolveState({ status: 'invalid', reason: 'This invitation is no longer valid.' });
                }
            } else {
                setResolveState({
                    status: 'invalid',
                    reason: 'This invitation link is invalid or has expired.',
                });
            }
        }
    }, [uuid, token]);

    useEffect(() => {
        resolve();
    }, [resolve]);

    const accept = async () => {
        if (resolveState.status !== 'ok' || !uuid) return;
        setAccepting(true);
        setAcceptError(null);
        try {
            const result = await acceptInvitation(uuid, token);
            navigate(result.redirect_url, { replace: true });
        } catch (err) {
            const detail =
                (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message ||
                (err as Error)?.message ||
                'Failed to accept invitation.';
            setAcceptError(detail);
        } finally {
            setAccepting(false);
        }
    };

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
                title="Invitation not available"
                description={resolveState.reason}
            >
                <Button asChild variant="outline">
                    <Link to="/">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Go home
                    </Link>
                </Button>
            </CenteredCard>
        );
    }

    const inv = resolveState.invitation;
    const targetVerb = inv.target_type === 'event' ? 'register for' : 'enroll in';

    if (resolveState.status === 'expired') {
        return (
            <CenteredCard
                icon={<AlertCircle className="h-10 w-10 text-amber-500" />}
                title="This invitation has expired"
                description={`The link to ${targetVerb} ${inv.target_title} is no longer active. Reach out to ${inv.invited_by_name || 'the organizer'} for a fresh invite.`}
            />
        );
    }
    if (resolveState.status === 'cancelled') {
        return (
            <CenteredCard
                icon={<AlertCircle className="h-10 w-10 text-amber-500" />}
                title="This invitation was cancelled"
                description={`The invite to ${targetVerb} ${inv.target_title} has been withdrawn.`}
            />
        );
    }

    // OK state — branch on auth.
    if (!isAuthenticated || !user) {
        return (
            <CenteredCard
                icon={<CheckCircle2 className="h-10 w-10 text-primary" />}
                title={`You're invited to ${targetVerb} ${inv.target_title}`}
                description={`${inv.invited_by_name || 'An organizer'} has invited ${inv.email}.`}
            >
                {inv.personal_message && (
                    <PersonalMessageBlock message={inv.personal_message} from={inv.invited_by_name} />
                )}
                <p className="text-sm text-muted-foreground">
                    Sign in or create an account to accept. We'll bring you right back here.
                </p>
                <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
                    <Button asChild className="flex-1">
                        <Link to={`/login?next=${nextUrl}&email=${encodeURIComponent(inv.email)}`}>
                            Sign in
                        </Link>
                    </Button>
                    <Button asChild variant="outline" className="flex-1">
                        <Link to={`/signup?next=${nextUrl}&email=${encodeURIComponent(inv.email)}`}>
                            Create account
                        </Link>
                    </Button>
                </div>
            </CenteredCard>
        );
    }

    if (user.email.toLowerCase() !== inv.email.toLowerCase()) {
        return (
            <CenteredCard
                icon={<AlertCircle className="h-10 w-10 text-amber-500" />}
                title="This invitation is for a different account"
                description={`The invite was sent to ${inv.email}, but you're signed in as ${user.email}. Sign out and sign back in to accept.`}
            >
                <Button
                    onClick={() => {
                        // useLogout does its own hard-nav to /login; we
                        // pre-stash the next-url so the post-login redirect
                        // brings them back to this accept page.
                        sessionStorage.setItem('post-login-next', `/invite/${uuid}?t=${token}`);
                        logout();
                    }}
                >
                    Sign out and switch accounts
                </Button>
            </CenteredCard>
        );
    }

    return (
        <CenteredCard
            icon={<CheckCircle2 className="h-10 w-10 text-primary" />}
            title={`You're invited to ${targetVerb} ${inv.target_title}`}
            description={`${inv.invited_by_name || 'An organizer'} invited you. Click accept to ${
                inv.target_type === 'event' ? 'register' : 'start the course'
            }.`}
        >
            {inv.personal_message && (
                <PersonalMessageBlock message={inv.personal_message} from={inv.invited_by_name} />
            )}
            {inv.comp && inv.target_is_paid && (
                <p className="rounded-md border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-primary">
                    ✓ This is a complimentary seat — no payment required.
                </p>
            )}
            {!inv.comp && inv.target_is_paid && (
                <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    This {inv.target_type} requires payment. Accepting takes you to checkout.
                </p>
            )}
            {acceptError && (
                <p className="text-sm text-destructive">{acceptError}</p>
            )}
            <Button onClick={accept} disabled={accepting} className="w-full">
                {accepting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {accepting ? 'Accepting…' : 'Accept invitation'}
            </Button>
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

function PersonalMessageBlock({ message, from }: { message: string; from?: string }) {
    return (
        <blockquote className="rounded-md border-l-4 border-primary/40 bg-muted/40 px-4 py-3">
            <p className="whitespace-pre-line text-sm text-foreground">{message}</p>
            {from && <p className="mt-2 text-xs text-muted-foreground">— {from}</p>}
        </blockquote>
    );
}
