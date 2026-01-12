import { Navigate, Outlet } from 'react-router-dom';
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
    const { isAuthenticated, isLoading, manifest, hasRoute, hasFeature } = useAuth();

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
