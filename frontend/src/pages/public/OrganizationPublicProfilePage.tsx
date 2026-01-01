import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPublicOrganizationProfile } from '@/api/organizations';
import { getPublicCourses } from '@/api/courses';
import { Organization } from '@/api/organizations/types';
import { Course } from '@/api/courses/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
    Building2,
    Globe,
    Mail,
    Phone,
    Users,
    BookOpen,
    Calendar,
    CheckCircle,
    ExternalLink,
    Award,
    Clock,
    ArrowRight,
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export const OrganizationPublicProfilePage: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const [organization, setOrganization] = useState<Organization | null>(null);
    const [courses, setCourses] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            if (!slug) return;

            try {
                const [orgData, coursesData] = await Promise.all([
                    getPublicOrganizationProfile(slug),
                    getPublicCourses({ org: slug }),
                ]);

                setOrganization(orgData);

                // Filter for published and public courses
                const publicCourses = coursesData.filter(
                    course => course.status === 'published' && course.is_public
                );
                setCourses(publicCourses);
            } catch (err: any) {
                console.error('Failed to load organization:', err);
                setError(err.message || 'Failed to load organization');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [slug]);

    if (loading) {
        return (
            <div className="container mx-auto py-12 px-4 max-w-7xl">
                <div className="mb-8">
                    <div className="flex items-center gap-6 mb-6">
                        <Skeleton className="h-24 w-24 rounded-full" />
                        <div className="flex-1">
                            <Skeleton className="h-10 w-64 mb-3" />
                            <Skeleton className="h-6 w-96" />
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !organization) {
        return (
            <div className="container mx-auto py-12 px-4 max-w-7xl">
                <Card className="border-destructive/20">
                    <CardContent className="pt-6">
                        <div className="text-center py-8">
                            <Building2 className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                            <h2 className="text-2xl font-bold mb-2">Organization Not Found</h2>
                            <p className="text-muted-foreground mb-6">
                                {error || "The organization you're looking for doesn't exist or is no longer active."}
                            </p>
                            <Button asChild>
                                <Link to="/">Go Home</Link>
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
            <div className="container mx-auto py-12 px-4 max-w-7xl">
                {/* Header Section */}
                <div className="mb-12">
                    <div className="flex flex-col md:flex-row items-start gap-6 mb-6">
                        {/* Organization Logo */}
                        <Avatar className="h-24 w-24">
                            {organization.logo_url ? (
                                <AvatarImage src={organization.logo_url} alt={organization.name} />
                            ) : null}
                            <AvatarFallback className="bg-primary/10 text-primary text-3xl font-bold">
                                {organization.name[0]}
                            </AvatarFallback>
                        </Avatar>

                        {/* Organization Info */}
                        <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                                <h1 className="text-4xl font-bold">{organization.name}</h1>
                                {organization.is_verified && (
                                    <Badge className="bg-blue-50 text-blue-700 border-blue-200">
                                        <CheckCircle className="h-3 w-3 mr-1" />
                                        Verified
                                    </Badge>
                                )}
                            </div>

                            {organization.description && (
                                <p className="text-lg text-muted-foreground mb-4">{organization.description}</p>
                            )}

                            {/* Contact Info */}
                            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                                {organization.website && (
                                    <a
                                        href={organization.website}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-1 hover:text-primary transition-colors"
                                    >
                                        <Globe className="h-4 w-4" />
                                        <span>Website</span>
                                        <ExternalLink className="h-3 w-3" />
                                    </a>
                                )}
                                {organization.contact_email && (
                                    <a
                                        href={`mailto:${organization.contact_email}`}
                                        className="flex items-center gap-1 hover:text-primary transition-colors"
                                    >
                                        <Mail className="h-4 w-4" />
                                        <span>{organization.contact_email}</span>
                                    </a>
                                )}
                                {organization.contact_phone && (
                                    <a
                                        href={`tel:${organization.contact_phone}`}
                                        className="flex items-center gap-1 hover:text-primary transition-colors"
                                    >
                                        <Phone className="h-4 w-4" />
                                        <span>{organization.contact_phone}</span>
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <Card>
                            <CardContent className="pt-6">
                                <div className="flex items-center gap-3">
                                    <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                                        <Users className="h-6 w-6 text-primary" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Team Members</p>
                                        <p className="text-2xl font-bold">{organization.members_count}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardContent className="pt-6">
                                <div className="flex items-center gap-3">
                                    <div className="h-12 w-12 rounded-full bg-success/10 flex items-center justify-center">
                                        <BookOpen className="h-6 w-6 text-success" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Courses</p>
                                        <p className="text-2xl font-bold">{organization.courses_count}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardContent className="pt-6">
                                <div className="flex items-center gap-3">
                                    <div className="h-12 w-12 rounded-full bg-blue-50 flex items-center justify-center">
                                        <Calendar className="h-6 w-6 text-blue-600" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Events</p>
                                        <p className="text-2xl font-bold">{organization.events_count}</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* Content Tabs */}
                <Tabs defaultValue="courses" className="space-y-6">
                    <TabsList>
                        <TabsTrigger value="courses">
                            Courses ({courses.length})
                        </TabsTrigger>
                        <TabsTrigger value="about">About</TabsTrigger>
                    </TabsList>

                    {/* Courses Tab */}
                    <TabsContent value="courses">
                        {courses.length === 0 ? (
                            <Card>
                                <CardContent className="pt-12 pb-12">
                                    <div className="text-center">
                                        <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                                        <h3 className="text-xl font-semibold mb-2">No Courses Available</h3>
                                        <p className="text-muted-foreground">
                                            This organization hasn't published any public courses yet.
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {courses.map((course) => (
                                    <Card
                                        key={course.uuid}
                                        className="group hover:shadow-lg transition-shadow duration-200 flex flex-col"
                                    >
                                        <CardHeader className="pb-4">
                                            {/* Course Image */}
                                            <div className="relative aspect-video bg-muted rounded-lg mb-4 overflow-hidden">
                                                {course.featured_image_url ? (
                                                    <img
                                                        src={course.featured_image_url}
                                                        alt={course.title}
                                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                                                    />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/10 to-primary/5">
                                                        <BookOpen className="h-16 w-16 text-primary/30" />
                                                    </div>
                                                )}
                                                {!course.is_free && (
                                                    <div className="absolute top-3 right-3">
                                                        <Badge className="bg-white/90 text-foreground border">
                                                            ${(course.price_cents / 100).toFixed(0)}
                                                        </Badge>
                                                    </div>
                                                )}
                                                {course.is_free && (
                                                    <div className="absolute top-3 right-3">
                                                        <Badge className="bg-success/90 text-white">Free</Badge>
                                                    </div>
                                                )}
                                            </div>

                                            <CardTitle className="text-xl group-hover:text-primary transition-colors line-clamp-2">
                                                {course.title}
                                            </CardTitle>
                                        </CardHeader>

                                        <CardContent className="flex-grow pb-4">
                                            <CardDescription className="line-clamp-3 mb-4">
                                                {course.short_description || course.description}
                                            </CardDescription>

                                            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                                                {course.estimated_hours && (
                                                    <div className="flex items-center gap-1">
                                                        <Clock className="h-4 w-4" />
                                                        <span>{course.estimated_hours}h</span>
                                                    </div>
                                                )}
                                                {course.cpd_credits && (
                                                    <div className="flex items-center gap-1">
                                                        <Award className="h-4 w-4" />
                                                        <span>{course.cpd_credits} CPD</span>
                                                    </div>
                                                )}
                                            </div>
                                        </CardContent>

                                        <div className="px-6 pb-6">
                                            <Button className="w-full group/btn" asChild>
                                                <Link to={`/courses/${course.uuid}`}>
                                                    View Course
                                                    <ArrowRight className="ml-2 h-4 w-4 group-hover/btn:translate-x-1 transition-transform" />
                                                </Link>
                                            </Button>
                                        </div>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </TabsContent>

                    {/* About Tab */}
                    <TabsContent value="about">
                        <Card>
                            <CardHeader>
                                <CardTitle>About {organization.name}</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {organization.description ? (
                                    <div>
                                        <h3 className="font-semibold mb-2">Overview</h3>
                                        <p className="text-muted-foreground">{organization.description}</p>
                                    </div>
                                ) : (
                                    <p className="text-muted-foreground">
                                        This organization hasn't added a description yet.
                                    </p>
                                )}

                                {/* Contact Information */}
                                <div>
                                    <h3 className="font-semibold mb-3">Contact Information</h3>
                                    <div className="space-y-2">
                                        {organization.website && (
                                            <div className="flex items-center gap-2">
                                                <Globe className="h-4 w-4 text-muted-foreground" />
                                                <a
                                                    href={organization.website}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-primary hover:underline"
                                                >
                                                    {organization.website}
                                                </a>
                                            </div>
                                        )}
                                        {organization.contact_email && (
                                            <div className="flex items-center gap-2">
                                                <Mail className="h-4 w-4 text-muted-foreground" />
                                                <a
                                                    href={`mailto:${organization.contact_email}`}
                                                    className="text-primary hover:underline"
                                                >
                                                    {organization.contact_email}
                                                </a>
                                            </div>
                                        )}
                                        {organization.contact_phone && (
                                            <div className="flex items-center gap-2">
                                                <Phone className="h-4 w-4 text-muted-foreground" />
                                                <a
                                                    href={`tel:${organization.contact_phone}`}
                                                    className="text-primary hover:underline"
                                                >
                                                    {organization.contact_phone}
                                                </a>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>
        </div>
    );
};
