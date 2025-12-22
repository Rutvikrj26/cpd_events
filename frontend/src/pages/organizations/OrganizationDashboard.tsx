/**
 * Organization Dashboard Page
 *
 * Main dashboard for an organization showing overview stats,
 * recent events, team members, and quick actions.
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
    Building2,
    Users,
    Calendar,
    BookOpen,
    Settings,
    Plus,
    ArrowRight,
    Crown,
    Shield,
    UserCog,
    User as UserIcon,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getOrganization, getOrganizationMembers } from '@/api/organizations';
import { Organization, OrganizationMember, OrganizationRole } from '@/api/organizations/types';
import { useOrganization } from '@/contexts/OrganizationContext';
import TeamManagementPage from './TeamManagementPage';
import OrgCoursesPage from './courses/OrgCoursesPage';
import OrganizationSettingsPage from './OrganizationSettingsPage';

const OrganizationDashboard: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { setCurrentOrg, hasRole } = useOrganization();

    const [org, setOrg] = useState<Organization | null>(null);
    const [members, setMembers] = useState<OrganizationMember[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadOrg = async () => {
            if (!slug) return;

            setIsLoading(true);
            try {
                // Find org by slug (need to list first)
                const { getOrganizations } = await import('@/api/organizations');
                const orgs = await getOrganizations();
                const found = orgs.find(o => o.slug === slug);

                if (!found) {
                    setError('Organization not found');
                    return;
                }

                const [fullOrg, membersList] = await Promise.all([
                    getOrganization(found.uuid),
                    getOrganizationMembers(found.uuid),
                ]);

                setOrg(fullOrg);
                setMembers(membersList);
                setCurrentOrg(fullOrg);

            } catch (err: any) {
                console.error('Failed to load organization:', err);
                setError(err.message || 'Failed to load organization');
            } finally {
                setIsLoading(false);
            }
        };

        loadOrg();
    }, [slug, setCurrentOrg]);

    const getRoleIcon = (role: OrganizationRole) => {
        switch (role) {
            case 'owner':
                return <Crown className="h-4 w-4 text-yellow-600" />;
            case 'admin':
                return <Shield className="h-4 w-4 text-blue-600" />;
            case 'manager':
                return <UserCog className="h-4 w-4 text-green-600" />;
            default:
                return <UserIcon className="h-4 w-4 text-gray-600" />;
        }
    };

    if (isLoading) {
        return (
            <div className="container mx-auto py-8 px-4">
                <div className="flex items-center gap-4 mb-8">
                    <Skeleton className="h-16 w-16 rounded-full" />
                    <div>
                        <Skeleton className="h-8 w-64 mb-2" />
                        <Skeleton className="h-4 w-32" />
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {[1, 2, 3].map(i => (
                        <Skeleton key={i} className="h-32" />
                    ))}
                </div>
            </div>
        );
    }

    if (error || !org) {
        return (
            <div className="container mx-auto py-16 px-4 text-center">
                <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h2 className="text-2xl font-bold mb-2">Organization Not Found</h2>
                <p className="text-muted-foreground mb-4">{error || 'Unable to load organization'}</p>
                <Button onClick={() => navigate('/organizations')}>
                    Back to Organizations
                </Button>
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8 px-4 max-w-6xl">
            {/* Header */}
            <div className="flex items-start justify-between mb-8">
                <div className="flex items-center gap-4">
                    <Avatar className="h-16 w-16">
                        {org.logo_url ? (
                            <AvatarImage src={org.logo_url} alt={org.name} />
                        ) : null}
                        <AvatarFallback className="bg-primary/10 text-primary text-2xl font-bold">
                            {org.name[0]}
                        </AvatarFallback>
                    </Avatar>
                    <div>
                        <div className="flex items-center gap-2">
                            <h1 className="text-3xl font-bold">{org.name}</h1>
                            {org.is_verified && (
                                <Badge variant="secondary" className="bg-blue-50 text-blue-700">
                                    Verified
                                </Badge>
                            )}
                        </div>
                        <p className="text-muted-foreground">
                            {org.description || 'No description provided'}
                        </p>
                    </div>
                </div>

                {hasRole('admin') && (
                    <Button variant="outline" onClick={() => navigate(`/org/${slug}/settings`)}>
                        <Settings className="h-4 w-4 mr-2" />
                        Settings
                    </Button>
                )}
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Team Members</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{org.members_count}</div>
                        <p className="text-xs text-muted-foreground">
                            {org.subscription?.active_organizer_seats || 0} organizers
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Events</CardTitle>
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{org.events_count}</div>
                        <p className="text-xs text-muted-foreground">
                            Total events created
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium">Courses</CardTitle>
                        <BookOpen className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{org.courses_count}</div>
                        <p className="text-xs text-muted-foreground">
                            Self-paced courses
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="team" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="members">Team Members</TabsTrigger>
                    <TabsTrigger value="courses">Courses</TabsTrigger>
                    <TabsTrigger value="settings">Settings</TabsTrigger>
                </TabsList>

                {/* Team Tab */}
                <TabsContent value="team">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle>Team Members</CardTitle>
                                <CardDescription>
                                    Manage your organization's team
                                </CardDescription>
                            </div>
                            {hasRole('admin') && (
                                <Button onClick={() => navigate(`/org/${slug}/team`)}>
                                    <Plus className="h-4 w-4 mr-2" />
                                    Invite Member
                                </Button>
                            )}
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {members.slice(0, 5).map((member) => (
                                    <div key={member.uuid} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                                        <div className="flex items-center gap-3">
                                            <Avatar className="h-10 w-10">
                                                <AvatarFallback>
                                                    {member.user_name?.[0] || member.user_email[0]}
                                                </AvatarFallback>
                                            </Avatar>
                                            <div>
                                                <p className="font-medium">{member.user_name || member.user_email}</p>
                                                <p className="text-sm text-muted-foreground">{member.title || member.user_email}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {getRoleIcon(member.role)}
                                            <Badge variant="outline" className="capitalize">
                                                {member.role}
                                            </Badge>
                                        </div>
                                    </div>
                                ))}

                                {members.length > 5 && (
                                    <Button variant="ghost" className="w-full" onClick={() => navigate(`/org/${slug}/team`)}>
                                        View all {members.length} members
                                        <ArrowRight className="h-4 w-4 ml-2" />
                                    </Button>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="members">
                    <TeamManagementPage />
                </TabsContent>

                <TabsContent value="courses">
                    <OrgCoursesPage />
                </TabsContent>

                <TabsContent value="settings">
                    <OrganizationSettingsPage />
                </TabsContent>

                {/* Subscription Tab */}
                <TabsContent value="subscription">
                    <Card>
                        <CardHeader>
                            <CardTitle>Subscription</CardTitle>
                            <CardDescription>
                                Your organization's billing and usage
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {org.subscription ? (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                                        <div>
                                            <p className="font-semibold text-lg capitalize">{org.subscription.plan} Plan</p>
                                            <p className="text-sm text-muted-foreground">
                                                Status: <span className="capitalize">{org.subscription.status}</span>
                                            </p>
                                        </div>
                                        {hasRole('owner') && (
                                            <Button variant="outline">
                                                Manage Billing
                                            </Button>
                                        )}
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-4 border rounded-lg">
                                            <p className="text-sm text-muted-foreground">Organizer Seats</p>
                                            <p className="text-2xl font-bold">
                                                {org.subscription.active_organizer_seats} / {org.subscription.total_seats}
                                            </p>
                                            <p className="text-sm text-muted-foreground">
                                                {org.subscription.available_seats} available
                                            </p>
                                        </div>
                                        <div className="p-4 border rounded-lg">
                                            <p className="text-sm text-muted-foreground">Events This Month</p>
                                            <p className="text-2xl font-bold">
                                                {org.subscription.events_created_this_period}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-muted-foreground">No subscription information available</p>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default OrganizationDashboard;
