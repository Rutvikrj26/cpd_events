import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

/**
 * OAuth Callback Page
 * Handles the redirect from OAuth providers (Google, Zoom, etc.)
 * Extracts tokens from URL and logs the user in
 */
export function OAuthCallbackPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { setToken, setIsAuthenticated, fetchManifest } = useAuth();

    useEffect(() => {
        const handleCallback = async () => {
            const access = searchParams.get('access');
            const refresh = searchParams.get('refresh');
            const error = searchParams.get('error');

            if (error) {
                console.error('OAuth error:', error);
                navigate('/login?error=oauth_failed');
                return;
            }

            if (!access || !refresh) {
                console.error('Missing tokens in callback');
                navigate('/login?error=invalid_callback');
                return;
            }

            try {
                // Store tokens and set authenticated status
                setToken(access, refresh);
                setIsAuthenticated(true);

                // Fetch user manifest
                await fetchManifest();

                // Redirect to dashboard
                navigate('/dashboard');
            } catch (error) {
                console.error('Failed to complete OAuth login:', error);
                navigate('/login?error=login_failed');
            }
        };

        handleCallback();
    }, [searchParams, navigate, setToken, setIsAuthenticated, fetchManifest]);

    return (
        <div className="flex min-h-screen items-center justify-center">
            <div className="text-center space-y-4">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                <p className="text-muted-foreground">Completing sign in...</p>
            </div>
        </div>
    );
}
