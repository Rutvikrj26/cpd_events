import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LandingPage } from '@/pages/public/LandingPage';

export const AuthenticatedRoot: React.FC = () => {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
        return null; // Or a loading spinner if preferred
    }

    if (isAuthenticated) {
        // SMART REDIRECT LOGIC
        // Prioritize last active organization
        const lastOrgSlug = localStorage.getItem('current_org_slug');
        const target = lastOrgSlug ? `/org/${lastOrgSlug}` : '/dashboard';
        return <Navigate to={target} replace />;
    }

    // Not authenticated -> Show Landing Page
    return <LandingPage />;
};
