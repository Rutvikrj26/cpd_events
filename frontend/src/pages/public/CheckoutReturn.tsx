import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Card, CardContent } from "@/shared/ui/card";

/**
 * Cosmetic landing pages after Stripe-hosted Checkout.
 *
 * The actual fulfilment is driven by the ``checkout.session.completed``
 * webhook. These pages just acknowledge the outcome and point the learner at
 * their dashboard; they do not write any state.
 */

const KIND_COPY: Record<string, {
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

export function CheckoutSuccess() {
    const [params] = useSearchParams();
    const sessionId = params.get("session_id");
    const kind = params.get("kind") ?? "event";
    const copy = KIND_COPY[kind] ?? KIND_COPY.event;
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <Card className="max-w-md w-full mx-4">
                <CardContent className="pt-6 text-center">
                    <div className="h-16 w-16 bg-success-subtle rounded-full flex items-center justify-center mx-auto mb-4">
                        <CheckCircle className="h-8 w-8 text-success" />
                    </div>
                    <h2 className="text-2xl font-bold text-foreground mb-2">Payment received</h2>
                    <p className="text-muted-foreground mb-6">{copy.subtitle}</p>
                    {sessionId && (
                        <p className="text-xs text-muted-foreground mb-6 font-mono break-all">{sessionId}</p>
                    )}
                    <div className="space-y-3">
                        <Link to={copy.primary.to}>
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
