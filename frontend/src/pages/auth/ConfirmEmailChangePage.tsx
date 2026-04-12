import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { confirmEmailChange } from "@/api/accounts";

type Status = "loading" | "success" | "error";

export function ConfirmEmailChangePage() {
    const [searchParams] = useSearchParams();
    const [status, setStatus] = useState<Status>("loading");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const token = searchParams.get("token");
        if (!token) {
            setStatus("error");
            setError("Missing confirmation token.");
            return;
        }

        let cancelled = false;
        (async () => {
            try {
                await confirmEmailChange(token);
                if (!cancelled) setStatus("success");
            } catch (err: any) {
                if (cancelled) return;
                const code = err?.response?.data?.error?.code;
                const message =
                    code === "TOKEN_EXPIRED"
                        ? "This confirmation link has expired. Request a new one from your settings."
                        : code === "EMAIL_TAKEN"
                        ? "That email is now in use by another account. Start a new request with a different address."
                        : code === "INVALID_TOKEN"
                        ? "This confirmation link is invalid."
                        : err?.response?.data?.error?.message || "Failed to confirm email change.";
                setError(message);
                setStatus("error");
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [searchParams]);

    return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="max-w-md w-full text-center space-y-6">
                {status === "loading" && (
                    <>
                        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                        <p className="text-muted-foreground">Confirming your new email...</p>
                    </>
                )}
                {status === "success" && (
                    <>
                        <CheckCircle2 className="h-12 w-12 mx-auto text-primary" />
                        <h1 className="text-2xl font-bold tracking-tight">Email updated</h1>
                        <p className="text-muted-foreground">
                            Your email address has been updated. For security, all sessions on other devices have been signed out. Please log in again with your new email.
                        </p>
                        <Button asChild className="w-full">
                            <Link to="/login">Go to login</Link>
                        </Button>
                    </>
                )}
                {status === "error" && (
                    <>
                        <AlertCircle className="h-12 w-12 mx-auto text-destructive" />
                        <h1 className="text-2xl font-bold tracking-tight">Can't confirm change</h1>
                        <p className="text-muted-foreground">{error}</p>
                        <Button asChild variant="outline" className="w-full">
                            <Link to="/settings">Back to settings</Link>
                        </Button>
                    </>
                )}
            </div>
        </div>
    );
}
