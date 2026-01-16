/**
 * Organization Dashboard Page
 *
 * Main dashboard for an organization showing overview stats,
 * recent events, team members, and quick actions.
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Building2,
    Users,
    Calendar,
    BookOpen,
    Settings,
    Plus,
    Shield,
    User as UserIcon,
    CreditCard,
    Award,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getOrganization, getOrganizationMembers, createOrganizationPortalSession } from '@/api/organizations';
import { Organization, OrganizationMember, OrganizationRole } from '@/api/organizations/types';
import { useOrganization } from '@/contexts/OrganizationContext';
import TeamManagementPage from './TeamManagementPage';
import OrgCoursesOverview from './courses/OrgCoursesOverview';
import OrgEventsOverview from './OrgEventsOverview';
import OrganizationSettingsPage from './OrganizationSettingsPage';

const OrganizationDashboard: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { setCurrentOrg, hasRole } = useOrganization();

    const [org, setOrg] = useState<Organization | null>(null);
    const [members, setMembers] = useState<OrganizationMember[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isManagingBilling, setIsManagingBilling] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleManageBilling = async () => {
        if (!org) return;
        setIsManagingBilling(true);
        try {
            const { url } = await createOrganizationPortalSession(org.uuid);
            window.location.href = url;
        } catch (err) {
            console.error('Failed to open billing portal', err);
        } finally {
            setIsManagingBilling(false);
        }
    };

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

    useEffect(() => {
        if (org?.user_role === 'instructor' && slug) {
            navigate(`/org/${slug}/instructor`, { replace: true });
        }
    }, [org?.user_role, slug, navigate]);

    // Redirect admin to onboarding if not completed
    useEffect(() => {
        if (org && !org.onboarding_completed && org.user_role === 'admin' && slug) {
            navigate(`/org/${slug}/onboarding`, { replace: true });
        }
    }, [org, slug, navigate]);

    const getRoleIcon = (role: OrganizationRole) => {
        switch (role) {
            case 'admin':
                return <Shield className="h-4 w-4 text-blue-600" />;
            case 'organizer':
                return <Calendar className="h-4 w-4 text-indigo-600" />;
            case 'course_manager':
                return <BookOpen className="h-4 w-4 text-emerald-600" />;
            case 'instructor':
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

    const isAdmin = hasRole('admin');
    const canViewEvents = isAdmin || hasRole('organizer');
    const canViewCourses = isAdmin || hasRole('course_manager');
    const canViewTeam = isAdmin || hasRole('course_manager');
    const canCreateEvents = canViewEvents;
    const canCreateCourses = canViewCourses;

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

                {isAdmin && (
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => navigate(`/org/${slug}/billing`)}>
                            <CreditCard className="h-4 w-4 mr-2" />
                            Billing
                        </Button>
                        <Button variant="outline" onClick={() => navigate(`/org/${slug}/settings`)}>
                            <Settings className="h-4 w-4 mr-2" />
                            Settings
                        </Button>
                    </div>
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

                {canViewEvents && (
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
                )}

                {canViewCourses && (
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
                )}
            </div>

            {/* Tabs */}
            <Tabs defaultValue="overview" className="space-y-6">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    {canViewEvents && <TabsTrigger value="events">Events</TabsTrigger>}
                    {canViewCourses && <TabsTrigger value="courses">Courses</TabsTrigger>}
                    {canViewTeam && <TabsTrigger value="members">Team</TabsTrigger>}
                    <TabsTrigger value="certificates">Certificates</TabsTrigger>
                    {isAdmin && (
                        <TabsTrigger value="settings">Settings</TabsTrigger>
                    )}
                </TabsList>

                {/* Overview Tab */}
                <TabsContent value="overview">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Recent Activity Card */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Quick Actions</CardTitle>
                                <CardDescription>Common tasks for your organization</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {canViewEvents && (
                                    <Button className="w-full justify-start" variant="outline" onClick={() => navigate('/events/create')}>
                                        <Calendar className="h-4 w-4 mr-2" />
                                        Create New Event
                                    </Button>
                                )}
                                {canViewCourses && (
                                    <Button className="w-full justify-start" variant="outline" onClick={() => navigate(`/org/${slug}/courses/new`)}>
                                        <BookOpen className="h-4 w-4 mr-2" />
                                        Create New Course
                                    </Button>
                                )}
                                {canViewTeam && (
                                    <Button className="w-full justify-start" variant="outline" onClick={() => navigate(`/org/${slug}/team`)}>
                                        <Users className="h-4 w-4 mr-2" />
                                        Invite Team Member
                                    </Button>
                                )}
                            </CardContent>
                        </Card>

                        {/* Team Preview Card */}
                        {canViewTeam && (
                            <Card>
                                <CardHeader className="flex flex-row items-center justify-between">
                                    <div>
                                        <CardTitle>Team</CardTitle>
                                        <CardDescription>{members.length} member(s)</CardDescription>
                                    </div>
                                    {isAdmin && (
                                        <Button size="sm" variant="outline" onClick={() => navigate(`/org/${slug}/team`)}>
                                            <Plus className="h-4 w-4 mr-2" />
                                            Invite
                                        </Button>
                                    )}
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        {members.slice(0, 4).map((member) => (
                                            <div key={member.uuid} className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <Avatar className="h-8 w-8">
                                                        <AvatarFallback>
                                                            {member.user_name?.[0] || member.user_email[0]}
                                                        </AvatarFallback>
                                                    </Avatar>
                                                    <div>
                                                        <p className="text-sm font-medium">{member.user_name || member.user_email}</p>
                                                        <p className="text-xs text-muted-foreground capitalize">{member.role}</p>
                                                    </div>
                                                </div>
                                                {getRoleIcon(member.role)}
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </TabsContent>

                {/* Events Tab */}
                {canViewEvents && (
                    <TabsContent value="events">
                        {isAdmin ? (
                            <OrgEventsOverview orgUuid={org.uuid} canCreateEvents={canCreateEvents} />
                        ) : (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Events</CardTitle>
                                    <CardDescription>
                                        Organization-wide event oversight is available to admins.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-center py-8 text-muted-foreground">
                                        <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                        <p>Only organization admins can view all events across organizers.</p>
                                        <Button variant="outline" className="mt-4" onClick={() => navigate('/events')}>
                                            Go to My Events
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>
                )}

                {/* Courses Tab */}
                {canViewCourses && (
                    <TabsContent value="courses">
                        {isAdmin ? (
                            <OrgCoursesOverview
                                orgUuid={org.uuid}
                                orgSlug={org.slug}
                                canCreateCourses={canCreateCourses}
                            />
                        ) : (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Courses</CardTitle>
                                    <CardDescription>
                                        Organization-wide course oversight is available to admins.
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-center py-8 text-muted-foreground">
                                        <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                        <p>Course managers can manage courses in the full courses view.</p>
                                        <Button variant="outline" className="mt-4" onClick={() => navigate(`/org/${slug}/courses`)}>
                                            Go to Courses
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>
                )}

                {/* Team Tab */}
                {canViewTeam && (
                    <TabsContent value="members">
                        <TeamManagementPage />
                    </TabsContent>
                )}

                {/* Certificates Tab */}
                <TabsContent value="certificates">
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle>Certificate Templates</CardTitle>
                                <CardDescription>
                                    Manage certificate templates for your events and courses
                                </CardDescription>
                            </div>
                            <Button onClick={() => navigate('/certificate-templates/new')}>
                                <Plus className="h-4 w-4 mr-2" />
                                New Template
                            </Button>
                        </CardHeader>
                        <CardContent>
                            <div className="text-center py-8 text-muted-foreground">
                                <Award className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                <p>Create certificate templates for your organization.</p>
                                <p className="text-sm mt-2">Templates can be shared across all organization members.</p>
                                <Button variant="link" onClick={() => navigate('/certificate-templates')}>
                                    Manage Templates
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Settings Tab */}
                {isAdmin && (
                    <TabsContent value="settings">
                        <OrganizationSettingsPage />
                    </TabsContent>
                )}

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
                                        {isAdmin && (
                                            <Button variant="outline" onClick={handleManageBilling} disabled={isManagingBilling}>
                                                {isManagingBilling ? 'Opening...' : 'Manage Billing'}
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
