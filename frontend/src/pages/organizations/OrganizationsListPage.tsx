/**
 * Organization List Page
 *
 * Shows all organizations the user belongs to.
 */

import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Building2, Plus, Users, Calendar, ChevronRight, Sparkles } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { useOrganization } from '@/contexts/OrganizationContext';
import { OrganizationListItem } from '@/api/organizations/types';
import { getLinkableDataPreview } from '@/api/organizations';
import { useAuth } from '@/contexts/AuthContext';

const OrganizationsListPage: React.FC = () => {
    const navigate = useNavigate();
    const { user, hasFeature } = useAuth();
    const { organizations, isLoading, refreshOrganizations } = useOrganization();
    const [linkableData, setLinkableData] = useState<{ events_count: number; templates_count: number; has_linkable_data: boolean } | null>(null);

    useEffect(() => {
        refreshOrganizations();

        // Check if user has data that could be linked
        if (user?.account_type === 'organizer' || user?.account_type === 'admin') {
            getLinkableDataPreview()
                .then(setLinkableData)
                .catch(() => { });
        }
    }, []);

    const getRoleBadgeVariant = (role: string) => {
        switch (role) {
            case 'admin':
                return 'default';
            case 'organizer':
                return 'secondary';
            default:
                return 'outline';
        }
    };

    return (
        <div className="container mx-auto py-8 px-4 max-w-4xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Teams</h1>
                    <p className="text-muted-foreground mt-1">
                        Manage your collaborative teams and shared accounts
                    </p>
                </div>
                {hasFeature('can_create_organization') && (
                    <Link to="/contact?subject=New%20Organization%20Deployment">
                        <Button>
                            <Building2 className="h-4 w-4 mr-2" />
                            Request New Organization
                        </Button>
                    </Link>
                )}
            </div>

            {/* Upgrade CTA for individual organizers */}
            {hasFeature('can_create_organization') && (user?.account_type === 'organizer' || user?.account_type === 'admin') && linkableData?.has_linkable_data && organizations.length === 0 && (
                <Card className="mb-8 border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
                    <CardHeader>
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-primary" />
                            <CardTitle className="text-lg">Scale to a Branded Organization</CardTitle>
                        </div>
                        <CardDescription>
                            Get a dedicated standalone deployment with your own branding and domain.
                            Perfect for growing training agencies.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Link to="/contact?subject=Organization%20Upgrade">
                            <Button>
                                Contact Sales for Upgrade
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            )}

            {/* Loading State */}
            {isLoading && (
                <div className="grid gap-4">
                    {[1, 2, 3].map((i) => (
                        <Card key={i}>
                            <CardContent className="p-6">
                                <div className="flex items-center gap-4">
                                    <Skeleton className="h-12 w-12 rounded-full" />
                                    <div className="flex-1">
                                        <Skeleton className="h-5 w-48 mb-2" />
                                        <Skeleton className="h-4 w-24" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Empty State */}
            {!isLoading && organizations.length === 0 && !linkableData?.has_linkable_data && (
                <Card className="text-center py-12">
                    <CardContent>
                        <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-semibold mb-2">
                            {hasFeature('can_create_organization') ? 'No Active Teams' : 'No Teams Found'}
                        </h3>
                        <p className="text-muted-foreground mb-4">
                            {hasFeature('can_create_organization')
                                ? 'Need a dedicated branded deployment for your team? Contact us to set up your organization.'
                                : 'You are not a member of any teams yet.'}
                        </p>
                        {hasFeature('can_create_organization') && (
                            <Link to="/contact">
                                <Button>
                                    <Building2 className="h-4 w-4 mr-2" />
                                    Contact for Organization Account
                                </Button>
                            </Link>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Organization Cards */}
            {!isLoading && organizations.length > 0 && (
                <div className="grid gap-4">
                    {organizations.map((org) => (
                        <OrganizationCard
                            key={org.uuid}
                            organization={org}
                            getRoleBadgeVariant={getRoleBadgeVariant}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

interface OrganizationCardProps {
    organization: OrganizationListItem;
    getRoleBadgeVariant: (role: string) => 'default' | 'secondary' | 'outline' | 'destructive';
}

const OrganizationCard: React.FC<OrganizationCardProps> = ({ organization, getRoleBadgeVariant }) => {
    return (
        <Link to={`/org/${organization.slug}`}>
            <Card className="hover:shadow-md transition-all duration-300 cursor-pointer group">
                <CardContent className="p-6">
                    <div className="flex items-center gap-4">
                        {/* Logo */}
                        <Avatar className="h-12 w-12">
                            {organization.logo_url ? (
                                <AvatarImage src={organization.logo_url} alt={organization.name} />
                            ) : null}
                            <AvatarFallback className="bg-primary/10 text-primary text-lg font-semibold">
                                {organization.name[0]}
                            </AvatarFallback>
                        </Avatar>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <h3 className="font-semibold text-lg truncate">
                                    {organization.name}
                                </h3>
                                <Badge variant={getRoleBadgeVariant(organization.user_role || '')}>
                                    {organization.user_role}
                                </Badge>
                                {organization.is_verified && (
                                    <Badge variant="secondary" className="bg-blue-50 text-blue-700">
                                        Verified
                                    </Badge>
                                )}
                            </div>

                            {/* Stats */}
                            <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1">
                                    <Users className="h-4 w-4" />
                                    {organization.members_count} member{organization.members_count !== 1 ? 's' : ''}
                                </span>
                                <span className="flex items-center gap-1">
                                    <Calendar className="h-4 w-4" />
                                    {organization.events_count} event{organization.events_count !== 1 ? 's' : ''}
                                </span>
                            </div>
                        </div>

                        {/* Arrow */}
                        <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                </CardContent>
            </Card>
        </Link>
    );
};

export default OrganizationsListPage;
