import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks';
import { Loader2 } from 'lucide-react';
import type { ReactNode } from 'react';
import type { Manifest } from '@/api/auth/manifest';

interface ProtectedRouteProps {
    requiredRoute?: string;
    requiredFeature?: keyof Manifest['features'];
    redirectTo?: string;
    children?: ReactNode;
}

export default function ProtectedRoute({
    requiredRoute,
    requiredFeature,
    redirectTo = '/dashboard',
    children,
}: ProtectedRouteProps) {
    const { isAuthenticated, isLoading, manifest, user, hasRoute, hasFeature } = useAuth();
    const location = useLocation();

    if (isLoading || (isAuthenticated && !manifest && (requiredRoute || requiredFeature))) {
        return (
            <div className="flex h-screen w-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    // Force users with incomplete onboarding through the wizard, except when
    // they are already on an onboarding route (we'd otherwise redirect-loop).
    const onboardingPaths = ['/onboarding'];
    const onOnboardingRoute = onboardingPaths.some(p => location.pathname.startsWith(p));
    if (user && user.onboarding_completed === false && !onOnboardingRoute) {
        return <Navigate to="/onboarding" replace />;
    }

    if (requiredRoute && !hasRoute(requiredRoute)) {
        return <Navigate to={redirectTo} replace />;
    }

    if (requiredFeature && !hasFeature(requiredFeature)) {
        return <Navigate to={redirectTo} replace />;
    }

    if (children) {
        return <>{children}</>;
    }

    return <Outlet />;
}
