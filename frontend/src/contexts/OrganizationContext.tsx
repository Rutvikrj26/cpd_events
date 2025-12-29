/**
 * Organization Context Provider
 *
 * Manages organization state across the app:
 * - Current active organization (if user is in org context)
 * - User's organizations list
 * - Role-based access helpers
 */

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useAuth } from './AuthContext';
import {
    getOrganizations,
    getOrganization,
    OrganizationListItem,
    Organization,
    OrganizationRole,
} from '@/api/organizations';

interface OrganizationContextType {
    // State
    organizations: OrganizationListItem[];
    currentOrg: Organization | null;
    isLoading: boolean;
    error: string | null;

    // Actions
    setCurrentOrg: (org: Organization | null) => void;
    selectOrgBySlug: (slug: string) => Promise<void>;
    refreshOrganizations: () => Promise<void>;
    clearCurrentOrg: () => void;

    // Permission helpers
    hasRole: (minRole: OrganizationRole) => boolean;
    canManageMembers: () => boolean;
    canCreateContent: () => boolean;
    isOwner: () => boolean;
    isAdmin: () => boolean;
    isManager: () => boolean;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined);

// Role hierarchy for permission checks
const ROLE_HIERARCHY: Record<OrganizationRole, number> = {
    owner: 4,
    admin: 3,
    manager: 2,
    member: 1,
};

const LOCAL_STORAGE_KEY = 'current_org_slug';

export const OrganizationProvider = ({ children }: { children: ReactNode }) => {
    const { user, isAuthenticated } = useAuth();

    const [organizations, setOrganizations] = useState<OrganizationListItem[]>([]);
    const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch user's organizations on auth change
    const refreshOrganizations = useCallback(async () => {
        if (!isAuthenticated || !user) {
            setOrganizations([]);
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const orgs = await getOrganizations();
            setOrganizations(orgs);
        } catch (err: any) {
            console.error('Failed to fetch organizations:', err);
            setError(err.message || 'Failed to load organizations');
        } finally {
            setIsLoading(false);
        }
    }, [isAuthenticated, user]);

    // Load organizations when authenticated
    useEffect(() => {
        if (isAuthenticated && user) {
            refreshOrganizations();
        }
    }, [isAuthenticated, user, refreshOrganizations]);

    // Persist current org to localStorage
    useEffect(() => {
        if (currentOrg) {
            localStorage.setItem(LOCAL_STORAGE_KEY, currentOrg.slug);
        } else {
            localStorage.removeItem(LOCAL_STORAGE_KEY);
        }
    }, [currentOrg]);

    // Select org by slug (e.g., from URL)
    const selectOrgBySlug = useCallback(async (slug: string) => {
        // First check if in quick list
        const quickMatch = organizations.find(o => o.slug === slug);

        if (quickMatch) {
            // Fetch full details
            try {
                const fullOrg = await getOrganization(quickMatch.uuid);
                setCurrentOrg(fullOrg);
            } catch (err: any) {
                console.error('Failed to load organization:', err);
                setError(err.message || 'Failed to load organization');
            }
        } else {
            setError('Organization not found');
        }
    }, [organizations]);

    // Restore org from localStorage on mount
    useEffect(() => {
        if (organizations.length > 0) {
            const savedSlug = localStorage.getItem(LOCAL_STORAGE_KEY);
            if (savedSlug && !currentOrg) {
                // Try to restore the saved organization
                selectOrgBySlug(savedSlug).catch(() => {
                    // If failed, clear the stale localStorage value
                    localStorage.removeItem(LOCAL_STORAGE_KEY);
                });
            }
        }
    }, [organizations, currentOrg, selectOrgBySlug]);



    // Clear current org (back to personal account)
    const clearCurrentOrg = useCallback(() => {
        setCurrentOrg(null);
    }, []);

    // Permission helpers
    const getUserRole = (): OrganizationRole | null => {
        return currentOrg?.user_role || null;
    };

    const hasRole = (minRole: OrganizationRole): boolean => {
        const userRole = getUserRole();
        if (!userRole) return false;
        return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[minRole];
    };

    const canManageMembers = (): boolean => hasRole('admin');
    const canCreateContent = (): boolean => hasRole('manager');
    const isOwner = (): boolean => hasRole('owner');
    const isAdmin = (): boolean => hasRole('admin');
    const isManager = (): boolean => hasRole('manager');

    return (
        <OrganizationContext.Provider
            value={{
                organizations,
                currentOrg,
                isLoading,
                error,
                setCurrentOrg,
                selectOrgBySlug,
                refreshOrganizations,
                clearCurrentOrg,
                hasRole,
                canManageMembers,
                canCreateContent,
                isOwner,
                isAdmin,
                isManager,
            }}
        >
            {children}
        </OrganizationContext.Provider>
    );
};

export const useOrganization = () => {
    const context = useContext(OrganizationContext);
    if (context === undefined) {
        throw new Error('useOrganization must be used within an OrganizationProvider');
    }
    return context;
};

/**
 * Hook to require organization context.
 * Throws if no organization is selected.
 */
export const useRequiredOrganization = () => {
    const ctx = useOrganization();
    if (!ctx.currentOrg) {
        throw new Error('This page requires an organization to be selected');
    }
    return {
        ...ctx,
        currentOrg: ctx.currentOrg,
    };
};
