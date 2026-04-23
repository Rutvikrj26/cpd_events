import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Cosmetic landing pages after Stripe-hosted Checkout.
 *
 * The actual fulfilment is driven by the ``checkout.session.completed``
 * webhook. These pages just acknowledge the outcome and point the learner at
 * their dashboard; they do not write any state.
 */

export function CheckoutSuccess() {
    const [params] = useSearchParams();
    const sessionId = params.get("session_id");
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <Card className="max-w-md w-full mx-4">
                <CardContent className="pt-6 text-center">
                    <div className="h-16 w-16 bg-success-subtle rounded-full flex items-center justify-center mx-auto mb-4">
                        <CheckCircle className="h-8 w-8 text-success" />
                    </div>
                    <h2 className="text-2xl font-bold text-foreground mb-2">Payment received</h2>
                    <p className="text-muted-foreground mb-6">
                        Your registration will appear in your dashboard within a few moments.
                    </p>
                    {sessionId && (
                        <p className="text-xs text-muted-foreground mb-6 font-mono break-all">{sessionId}</p>
                    )}
                    <div className="space-y-3">
                        <Link to="/registrations">
                            <Button className="w-full">Go to my dashboard</Button>
                        </Link>
                        <Link to="/discover/events">
                            <Button variant="outline" className="w-full">
                                Browse more events
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
