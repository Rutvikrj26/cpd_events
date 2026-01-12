import { useEffect } from 'react';
import { Outlet, useParams } from 'react-router-dom';
import { useOrganization } from '@/contexts/OrganizationContext';
import { Loader2 } from 'lucide-react';

export const OrganizationLayout = () => {
    const { slug } = useParams<{ slug: string }>();
    const { currentOrg, selectOrgBySlug, isLoading } = useOrganization();

    useEffect(() => {
        // Sync context with URL slug
        if (slug && (!currentOrg || currentOrg.slug !== slug)) {
            selectOrgBySlug(slug);
        }
    }, [slug, currentOrg, selectOrgBySlug]);

    // Show loader while syncing context
    // This prevents child routes from throwing "organization required" errors
    const isSyncing = slug && (!currentOrg || currentOrg.slug !== slug);

    if (isSyncing || isLoading) {
        return (
            <div className="flex items-center justify-center p-8 h-full">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return <Outlet />;
};
