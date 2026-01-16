import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { completeZoomOAuth } from '@/api/integrations';
import { toast } from '@/components/ui/use-toast';

export const ZoomCallbackPage = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    // Prevent double-invocation in React 18 strict mode from causing duplicate OAuth calls
    const hasProcessedRef = useRef(false);

    useEffect(() => {
        // OAuth codes can only be used once - prevent duplicate processing
        if (hasProcessedRef.current) {
            return;
        }
        hasProcessedRef.current = true;

        const code = searchParams.get('code');
        const error = searchParams.get('error');

        // Check for onboarding redirect (set when connecting Zoom during onboarding)
        const onboardingRedirect = sessionStorage.getItem('onboarding_redirect');
        const defaultRedirect = '/organizer/dashboard';

        const getRedirectUrl = () => {
            if (onboardingRedirect) {
                // Clear the redirect after use
                sessionStorage.removeItem('onboarding_redirect');
                return onboardingRedirect;
            }
            return defaultRedirect;
        };

        if (error) {
            toast({
                title: "Connection Failed",
                description: `Zoom authorization failed: ${error}`,
                variant: "destructive",
            });
            navigate(getRedirectUrl());
            return;
        }

        if (!code) {
            toast({
                title: "Invalid Request",
                description: "No authorization code found.",
                variant: "destructive",
            });
            navigate(getRedirectUrl());
            return;
        }

        const connect = async () => {
            try {
                await completeZoomOAuth(code);
                toast({
                    title: "Connected",
                    description: "Zoom account connected successfully.",
                });
            } catch (err) {
                toast({
                    title: "Connection Failed",
                    description: "Failed to complete Zoom connection.",
                    variant: "destructive",
                });
            } finally {
                navigate(getRedirectUrl());
            }
        };

        connect();
    }, [searchParams, navigate]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-muted/30">
            <div className="text-center space-y-4">
                <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
                <h1 className="text-xl font-semibold text-foreground">Connecting to Zoom...</h1>
                <p className="text-muted-foreground">Please wait while we complete the secure connection.</p>
            </div>
        </div>
    );
};
