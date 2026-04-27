import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle, Loader2, XCircle } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Card, CardContent } from "@/shared/ui/card";
import { verifySession, type PurchaseKind, type VerifySessionResponse } from "@/api/billing";

/**
 * Landing pages after Stripe-hosted Checkout.
 *
 * Success page polls the verify-session endpoint — webhooks usually fulfil
 * in under two seconds, but reconciliation may need longer. We show a
 * spinner while waiting and a "still processing" message after the budget
 * is exhausted (the user can refresh; their dashboard will show the
 * enrollment when fulfilment completes).
 *
 * The kind in the URL is treated as a hint only; the verify-session
 * response is authoritative once it arrives.
 */

const KIND_COPY: Record<PurchaseKind, {
    subtitle: string;
    primary: { label: string; to: string };
    secondary: { label: string; to: string };
}> = {
    event: {
        subtitle: "Your event registration will appear in My Learning within a few moments.",
        primary: { label: "Go to My Learning", to: "/registrations" },
        secondary: { label: "Browse more events", to: "/discover/events" },
    },
    course: {
        subtitle: "You're enrolled. The course will appear on your dashboard within a few moments.",
        primary: { label: "Go to dashboard", to: "/dashboard" },
        secondary: { label: "Browse more courses", to: "/discover/courses" },
    },
    program: {
        subtitle:
            "You're enrolled in every course in this program. They'll appear under My Programs within a few moments.",
        primary: { label: "Go to My Programs", to: "/my-programs" },
        secondary: { label: "Browse more programs", to: "/programs" },
    },
};

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 6;

export function CheckoutSuccess() {
    const [params] = useSearchParams();
    const sessionId = params.get("session_id");
    const fallbackKind = (params.get("kind") as PurchaseKind | null) ?? "event";

    const [verification, setVerification] = useState<VerifySessionResponse | null>(null);
    const [pollCount, setPollCount] = useState(0);
    const [exhausted, setExhausted] = useState(false);

    useEffect(() => {
        if (!sessionId) {
            // Direct navigation with no session_id — show the cosmetic success
            // page so the legacy "share success URL" path still works.
            setExhausted(true);
            return;
        }
        let cancelled = false;
        let timer: ReturnType<typeof setTimeout> | null = null;

        const tick = async (attempt: number) => {
            try {
                const res = await verifySession(sessionId);
                if (cancelled) return;
                setVerification(res);
                if (res.fulfilled) return;
                if (attempt + 1 >= MAX_POLLS) {
                    setExhausted(true);
                    return;
                }
                timer = setTimeout(() => {
                    setPollCount(attempt + 1);
                    tick(attempt + 1);
                }, POLL_INTERVAL_MS);
            } catch {
                // Network/other error — fall back to the cosmetic page rather
                // than blocking the user behind a perpetual spinner.
                setExhausted(true);
            }
        };
        tick(pollCount);
        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
        // pollCount is intentionally NOT in deps — we drive it from the timer
        // chain inside ``tick`` to avoid effect re-entry.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId]);

    const kind: PurchaseKind = (verification?.kind ?? fallbackKind) as PurchaseKind;
    const copy = KIND_COPY[kind] ?? KIND_COPY.event;
    const isFulfilled = Boolean(verification?.fulfilled);
    const isWaiting = !exhausted && !isFulfilled;

    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <Card className="max-w-md w-full mx-4">
                <CardContent className="pt-6 text-center">
                    <div
                        className={`h-16 w-16 ${isWaiting ? "bg-muted" : "bg-success-subtle"} rounded-full flex items-center justify-center mx-auto mb-4`}
                    >
                        {isWaiting ? (
                            <Loader2 className="h-8 w-8 text-muted-foreground animate-spin" />
                        ) : (
                            <CheckCircle className="h-8 w-8 text-success" />
                        )}
                    </div>
                    <h2 className="text-2xl font-bold text-foreground mb-2">
                        {isWaiting ? "Confirming your payment..." : "Payment received"}
                    </h2>
                    <p className="text-muted-foreground mb-6">
                        {isWaiting
                            ? "Stripe has accepted your card. We're recording your enrollment now."
                            : exhausted && !isFulfilled
                              ? "Your payment is being processed. Refresh in a minute, or check your dashboard — the enrollment will appear there once recorded."
                              : copy.subtitle}
                    </p>
                    {sessionId && (
                        <p className="text-xs text-muted-foreground mb-6 font-mono break-all">{sessionId}</p>
                    )}
                    <div className="space-y-3">
                        <Link to={verification?.redirect_url ?? copy.primary.to}>
                            <Button className="w-full">{copy.primary.label}</Button>
                        </Link>
                        <Link to={copy.secondary.to}>
                            <Button variant="outline" className="w-full">
                                {copy.secondary.label}
                            </Button>
                        </Link>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

export function CheckoutCancel() {
    const [params] = useSearchParams();
    const kind = params.get("kind") || "checkout";
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <Card className="max-w-md w-full mx-4">
                <CardContent className="pt-6 text-center">
                    <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                        <XCircle className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h2 className="text-2xl font-bold text-foreground mb-2">Checkout cancelled</h2>
                    <p className="text-muted-foreground mb-6">
                        You can resume {kind} anytime — no charge was made.
                    </p>
                    <div className="space-y-3">
                        <Link to="/discover/events">
                            <Button className="w-full">Back to browsing</Button>
                        </Link>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
