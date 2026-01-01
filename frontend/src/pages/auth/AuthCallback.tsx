import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export function AuthCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    // We'll access the raw context dispatch/setter if exposed, 
    // or manually set localStorage and then reload/fetchUser.

    // Checking AuthContext, it exposes `login` but that takes email/password. 
    // It initializes state from localStorage on mount. 
    // So we can set localStorage directly and then trigger a window reload or 
    // if `useAuth` exposed a re-check function, we'd use that.
    // Since `useAuth` reads from localStorage on mount, a simple way is:
    // 1. Set localStorage
    // 2. Redirect to dashboard (which will re-mount or we might need to force a context refresh)

    // Actually, let's look at AuthContext again.
    // It has a `useEffect` that checks tokens on mount.
    // But it doesn't seem to have a "setToken" method exposed.
    // However, `login` sets tokens.

    // To keep it simple and robust:
    // We will manually set the keys in localStorage used by the client/context
    // Then we will redirect to dashboard. 
    // Since the Dashboard is likely protected, the AuthContext might need a kick.
    // A full page reload is a safe bet for ensuring all state is clean.

    useEffect(() => {
        const access = searchParams.get("access");
        const refresh = searchParams.get("refresh");

        if (access && refresh) {
            localStorage.setItem("token", access);
            localStorage.setItem("refreshToken", refresh);

            toast.success("Successfully logged in with Zoom");

            // Force a reload to ensure AuthContext picks up the new tokens
            // Alternatively, we could modify AuthContext to expose a setTokens method,
            // but that requires changing core logic.
            window.location.href = "/dashboard";
        } else {
            toast.error("Failed to login with Zoom");
            navigate("/login");
        }
    }, [searchParams, navigate]);

    return (
        <div className="flex h-screen w-full items-center justify-center bg-background">
            <div className="flex flex-col items-center space-y-4">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-muted-foreground">Authenticating with Zoom...</p>
            </div>
        </div>
    );
}
