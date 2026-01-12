import React from 'react';
import { Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useOrganization } from '@/contexts/OrganizationContext';
import OrgEventsOverview from '../OrgEventsOverview';

const OrgEventsPage: React.FC = () => {
    const navigate = useNavigate();
    const { currentOrg, hasRole, isLoading } = useOrganization();

    if (isLoading || !currentOrg) {
        return (
            <div className="container mx-auto py-8 px-4 max-w-6xl">
                <Skeleton className="h-8 w-64 mb-4" />
                <Skeleton className="h-6 w-80 mb-8" />
                <Skeleton className="h-80 w-full" />
            </div>
        );
    }

    const isAdmin = hasRole('admin');
    const canCreateEvents = isAdmin || hasRole('organizer');

    return (
        <div className="container mx-auto py-8 px-4 max-w-6xl">
            {isAdmin ? (
                <OrgEventsOverview orgUuid={currentOrg.uuid} canCreateEvents={canCreateEvents} />
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle>Organization Events</CardTitle>
                        <CardDescription>
                            Organization-wide event oversight is available to admins.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="text-center py-8 text-muted-foreground">
                            <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                            <p>Head to your personal events list to manage your events.</p>
                            <Button variant="outline" className="mt-4" onClick={() => navigate('/events')}>
                                Go to My Events
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
};

export default OrgEventsPage;
