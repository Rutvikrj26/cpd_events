import React, { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getPublicCourses, Course, PublicCourseListParams } from '@/api/courses';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Search, BookOpen, Clock, Award, Users, ArrowRight } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Pagination } from '@/components/ui/pagination';

export const CourseCatalogPage: React.FC = () => {
    const [courses, setCourses] = useState<Course[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const navigate = useNavigate();

    // Pagination state
    const [page, setPage] = useState(1);
    const [pageSize] = useState(12);
    const [totalPages, setTotalPages] = useState(1);
    const [totalCount, setTotalCount] = useState(0);

    const fetchCourses = useCallback(async () => {
        setLoading(true);
        try {
            const params: PublicCourseListParams = {
                page,
                page_size: pageSize,
                search: searchQuery || undefined,
            };
            const response = await getPublicCourses(params);
            // Filter only published and public courses (client-side for now)
            const publicCourses = response.results.filter(
                course => course.status === 'published' && course.is_public
            );
            setCourses(publicCourses);
            setTotalPages(response.total_pages);
            setTotalCount(response.count);
        } catch (error) {
            console.error('Failed to load courses:', error);
        } finally {
            setLoading(false);
        }
    }, [page, pageSize, searchQuery]);

    useEffect(() => {
        fetchCourses();
    }, [fetchCourses]);

    // Reset to page 1 when search changes
    useEffect(() => {
        setPage(1);
    }, [searchQuery]);

    const handleEnroll = (courseUuid: string) => {
        navigate(`/courses/${courseUuid}`);
    };

    if (loading && page === 1) {
        return (
            <div className="container mx-auto py-8 px-4 max-w-7xl">
                <div className="mb-8">
                    <Skeleton className="h-12 w-64 mb-4" />
                    <Skeleton className="h-6 w-96" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[...Array(6)].map((_, i) => (
                        <Card key={i}>
                            <CardHeader>
                                <Skeleton className="h-40 w-full mb-4" />
                                <Skeleton className="h-6 w-3/4 mb-2" />
                                <Skeleton className="h-4 w-full" />
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
                {/* Header */}
                <div className="text-center mb-12">
                    <div className="flex items-center justify-center gap-3 mb-4">
                        <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <BookOpen className="h-6 w-6 text-primary" />
                        </div>
                        <h1 className="text-4xl font-bold">Course Catalog</h1>
                    </div>
                    <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                        Discover self-paced professional development courses from leading organizations
                    </p>
                </div>

                {/* Search Bar */}
                <div className="max-w-2xl mx-auto mb-12">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                        <Input
                            type="text"
                            placeholder="Search courses by title, description, or organization..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-12 h-14 text-base"
                        />
                    </div>
                    <div className="flex items-center gap-4 mt-4 text-sm text-muted-foreground">
                        <span>{totalCount} courses found</span>
                        {searchQuery && (
                            <Button variant="ghost" size="sm" onClick={() => setSearchQuery('')}>
                                Clear search
                            </Button>
                        )}
                    </div>
                </div>

                {/* Course Grid */}
                {courses.length === 0 ? (
                    <div className="text-center py-16">
                        <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                        <h3 className="text-xl font-semibold mb-2">No courses found</h3>
                        <p className="text-muted-foreground mb-6">
                            {searchQuery
                                ? 'Try adjusting your search terms'
                                : 'Check back soon for new courses'}
                        </p>
                        {searchQuery && (
                            <Button variant="outline" onClick={() => setSearchQuery('')}>
                                Clear search
                            </Button>
                        )}
                    </div>
                ) : (
                    <>
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

                                        {/* Course Title */}
                                        <CardTitle className="text-xl group-hover:text-primary transition-colors line-clamp-2">
                                            {course.title}
                                        </CardTitle>

                                        {/* Organization */}
                                        {course.organization_name && (
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground mt-2">
                                                <Avatar className="h-6 w-6">
                                                    {course.organization_logo_url ? (
                                                        <AvatarImage src={course.organization_logo_url} alt={course.organization_name} />
                                                    ) : null}
                                                    <AvatarFallback className="text-xs">
                                                        {course.organization_name[0]}
                                                    </AvatarFallback>
                                                </Avatar>
                                                <span>{course.organization_name}</span>
                                            </div>
                                        )}
                                    </CardHeader>

                                    <CardContent className="flex-grow pb-4">
                                        {/* Description */}
                                        <CardDescription className="line-clamp-3 mb-4">
                                            {course.short_description || course.description}
                                        </CardDescription>

                                        {/* Course Stats */}
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
                                            {course.enrollment_count > 0 && (
                                                <div className="flex items-center gap-1">
                                                    <Users className="h-4 w-4" />
                                                    <span>{course.enrollment_count} enrolled</span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Modules Count */}
                                        {course.module_count > 0 && (
                                            <div className="mt-3 text-sm text-muted-foreground">
                                                {course.module_count} module{course.module_count !== 1 ? 's' : ''}
                                            </div>
                                        )}
                                    </CardContent>

                                    <CardFooter className="pt-4 border-t">
                                        <Button
                                            className="w-full group/btn"
                                            onClick={() => handleEnroll(course.uuid)}
                                        >
                                            View Course
                                            <ArrowRight className="ml-2 h-4 w-4 group-hover/btn:translate-x-1 transition-transform" />
                                        </Button>
                                    </CardFooter>
                                </Card>
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <Pagination
                                page={page}
                                totalPages={totalPages}
                                totalCount={totalCount}
                                pageSize={pageSize}
                                onPageChange={setPage}
                                className="mt-8"
                            />
                        )}
                    </>
                )}

                {/* Call to Action */}
                {courses.length > 0 && (
                    <div className="mt-16 text-center bg-gradient-to-r from-primary/10 to-primary/5 rounded-lg p-8">
                        <h2 className="text-2xl font-bold mb-2">Looking to create your own courses?</h2>
                        <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
                            Join organizations creating professional development content for their communities
                        </p>
                        <div className="flex gap-4 justify-center">
                            <Button variant="outline" asChild>
                                <Link to="/organizations/new">Create Organization</Link>
                            </Button>
                            <Button asChild>
                                <Link to="/pricing">View Plans</Link>
                            </Button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
