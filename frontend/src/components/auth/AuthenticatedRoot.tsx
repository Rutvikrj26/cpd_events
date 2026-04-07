import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

export const AuthenticatedRoot: React.FC = () => {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
        return null;
    }

    if (isAuthenticated) {
        return <Navigate to="/dashboard" replace />;
    }

    // Not authenticated -> Redirect to login
    return <Navigate to="/login" replace />;
};
