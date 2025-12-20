import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { completeZoomOAuth } from '@/api/integrations';
import { toast } from '@/components/ui/use-toast';

export const ZoomCallbackPage = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    useEffect(() => {
        const code = searchParams.get('code');
        const error = searchParams.get('error');

        if (error) {
            toast({
                title: "Connection Failed",
                description: `Zoom authorization failed: ${error}`,
                variant: "destructive",
            });
            navigate('/organizer/dashboard');
            return;
        }

        if (!code) {
            toast({
                title: "Invalid Request",
                description: "No authorization code found.",
                variant: "destructive",
            });
            navigate('/organizer/dashboard');
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
                navigate('/organizer/dashboard');
            }
        };

        connect();
    }, [searchParams, navigate]);

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50">
            <div className="text-center space-y-4">
                <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
                <h1 className="text-xl font-semibold text-slate-900">Connecting to Zoom...</h1>
                <p className="text-slate-500">Please wait while we complete the secure connection.</p>
            </div>
        </div>
    );
};
