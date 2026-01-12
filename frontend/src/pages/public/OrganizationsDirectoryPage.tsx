import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getPublicOrganizations } from '@/api/organizations';
import { Organization } from '@/api/organizations/types';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Building2, Search, Users, BookOpen, Calendar } from 'lucide-react';

export const OrganizationsDirectoryPage: React.FC = () => {
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [filtered, setFiltered] = useState<Organization[]>([]);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                const data = await getPublicOrganizations();
                setOrganizations(data);
                setFiltered(data);
            } catch (error) {
                console.error('Failed to load organizations', error);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    useEffect(() => {
        if (!search.trim()) {
            setFiltered(organizations);
            return;
        }
        const query = search.toLowerCase();
        setFiltered(
            organizations.filter((org) => org.name.toLowerCase().includes(query) || org.description?.toLowerCase().includes(query))
        );
    }, [search, organizations]);

    if (loading) {
        return (
            <div className="container mx-auto py-12 px-4 max-w-7xl">
                <div className="mb-8">
                    <Skeleton className="h-10 w-64 mb-3" />
                    <Skeleton className="h-6 w-96" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[...Array(6)].map((_, idx) => (
                        <Card key={idx}>
                            <CardHeader>
                                <Skeleton className="h-16 w-16 rounded-full mb-4" />
                                <Skeleton className="h-6 w-3/4" />
                            </CardHeader>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
            <div className="container mx-auto py-12 px-4 max-w-7xl">
                <div className="text-center mb-10">
                    <div className="flex items-center justify-center gap-3 mb-3">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <Building2 className="h-6 w-6 text-primary" />
                        </div>
                        <h1 className="text-4xl font-bold">Organizations</h1>
                    </div>
                    <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                        Discover training providers, professional bodies, and teams hosting CPD events and courses.
                    </p>
                </div>

                <div className="max-w-2xl mx-auto mb-10">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                        <Input
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            placeholder="Search organizations by name or description"
                            className="pl-12 h-12"
                        />
                    </div>
                    <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                        <span>{filtered.length} organizations found</span>
                        {search && (
                            <Button variant="ghost" size="sm" onClick={() => setSearch('')}>
                                Clear search
                            </Button>
                        )}
                    </div>
                </div>

                {filtered.length === 0 ? (
                    <div className="text-center py-16">
                        <Building2 className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                        <h3 className="text-xl font-semibold mb-2">No organizations found</h3>
                        <p className="text-muted-foreground">Try a different search or check back later.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filtered.map((org) => (
                            <Link key={org.uuid} to={`/organizations/${org.slug}/public`} className="group">
                                <Card className="h-full hover:shadow-lg transition-shadow">
                                    <CardHeader className="flex flex-row items-center gap-4">
                                        <Avatar className="h-14 w-14">
                                            {org.logo_url ? (
                                                <AvatarImage src={org.logo_url} alt={org.name} />
                                            ) : null}
                                            <AvatarFallback className="bg-primary/10 text-primary text-xl font-semibold">
                                                {org.name?.[0]}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div className="flex-1">
                                            <CardTitle className="text-lg group-hover:text-primary transition-colors">
                                                {org.name}
                                            </CardTitle>
                                            {org.is_verified && (
                                                <Badge variant="secondary" className="mt-2">Verified</Badge>
                                            )}
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-3">
                                        <p className="text-sm text-muted-foreground line-clamp-3">
                                            {org.description || 'No description provided.'}
                                        </p>
                                        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                                            <div className="flex items-center gap-1">
                                                <Users className="h-4 w-4" />
                                                <span>{org.members_count} members</span>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                <Calendar className="h-4 w-4" />
                                                <span>{org.events_count} events</span>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                <BookOpen className="h-4 w-4" />
                                                <span>{org.courses_count} courses</span>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
