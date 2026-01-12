import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useToast } from '@/components/ui/use-toast';
import { getCourseBySlug, enrollInCourse, getPublicCourses, courseCheckout, getEnrollments } from '@/api/courses';
import { Course } from '@/api/courses/types';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Loader2, CheckCircle, Clock, BookOpen, Award, Users, Building2, ArrowRight } from 'lucide-react';

export const PublicCourseDetailPage = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();
    const { isAuthenticated, user } = useAuth();

    const [course, setCourse] = useState<Course | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isEnrolling, setIsEnrolling] = useState(false);
    const [relatedCourses, setRelatedCourses] = useState<Course[]>([]);
    const [isEnrolled, setIsEnrolled] = useState(false);

    useEffect(() => {
        const fetchCourse = async () => {
            if (!slug) return;
            try {
                const data = await getCourseBySlug(slug);
                if (!data) {
                    navigate('/404'); // Or handle not found
                } else {
                    setCourse(data);
                }
            } catch (error) {
                console.error('Failed to fetch course details:', error);
                toast({
                    variant: 'destructive',
                    title: 'Error',
                    description: 'Failed to load course details.',
                });
            } finally {
                setIsLoading(false);
            }
        };

        fetchCourse();
    }, [slug, navigate, toast]);

    // Fetch related courses from same organization
    useEffect(() => {
        const fetchRelatedCourses = async () => {
            if (!course?.organization_slug) return;

            try {
                const allCourses = await getPublicCourses({ org: course.organization_slug });
                // Filter published and public courses, exclude current course
                const orgCourses = allCourses
                    .filter(c =>
                        c.status === 'published' &&
                        c.is_public &&
                        c.uuid !== course.uuid
                    )
                    .slice(0, 3); // Show up to 3 related courses
                setRelatedCourses(orgCourses);
            } catch (error) {
                console.error('Failed to fetch related courses:', error);
            }
        };

        fetchRelatedCourses();
    }, [course]);

    useEffect(() => {
        const fetchEnrollmentStatus = async () => {
            if (!course || !isAuthenticated) return;
            try {
                const enrollments = await getEnrollments();
                const enrolled = enrollments.some(enrollment => enrollment.course?.uuid === course.uuid);
                setIsEnrolled(enrolled);
            } catch (error) {
                console.error('Failed to fetch enrollments:', error);
            }
        };

        fetchEnrollmentStatus();
    }, [course, isAuthenticated]);

    const handleEnroll = async () => {
        if (!isAuthenticated) {
            // Redirect to login with return URL
            navigate(`/login?returnUrl=/courses/${slug}`);
            return;
        }

        if (!course) return;

        if (isEnrolled) {
            navigate(`/learn/${course.uuid}`);
            return;
        }

        setIsEnrolling(true);
        try {
            // Check if this is a paid course
            if (!course.is_free && course.price_cents > 0) {
                // Paid course: initiate Stripe Checkout
                const currentUrl = window.location.origin;
                const result = await courseCheckout(
                    course.uuid,
                    `${currentUrl}/my-courses?enrolled=${course.uuid}`, // Success URL
                    `${currentUrl}/courses/${slug}` // Cancel URL (return to course page)
                );

                if (result.success && result.url) {
                    // Redirect to Stripe Checkout
                    window.location.href = result.url;
                } else {
                    throw new Error(result.error || 'Failed to create checkout session');
                }
            } else {
                // Free course: direct enrollment
                await enrollInCourse(course.uuid);
                toast({
                    title: 'Enrolled successfully!',
                    description: 'You have been enrolled in this course.',
                });
                navigate('/my-courses');
            }
        } catch (error: any) {
            console.error('Enrollment failed:', error);
            toast({
                variant: 'destructive',
                title: 'Enrollment failed',
                description: error.response?.data?.error?.message || error.message || 'Could not enroll in course.',
            });
        } finally {
            setIsEnrolling(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!course) {
        return (
            <div className="container mx-auto py-12 text-center">
                <h2 className="text-2xl font-bold">Course not found</h2>
                <Button variant="link" onClick={() => navigate('/courses')}>Browse other learning</Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background pb-12">
            {/* Hero Section */}
            <div className="bg-muted/30 border-b">
                <div className="container mx-auto py-12 px-4 md:py-16">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
                        <div className="lg:col-span-2 space-y-4">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                                <Link to="/courses" className="hover:underline">Browse</Link>
                                <span>/</span>
                                <Link to={`/organizations/${course.organization_slug}/public`} className="hover:underline text-foreground font-medium">
                                    {course.organization_name}
                                </Link>
                                <span>/</span>
                                <span>{course.title}</span>
                            </div>

                            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl mb-2">
                                {course.title}
                            </h1>
                            <p className="text-xl text-muted-foreground leading-relaxed">
                                {course.short_description}
                            </p>

                            <div className="flex flex-wrap gap-4 mt-6">
                                <Badge variant={Number(course.cpd_credits) > 0 ? "default" : "secondary"} className="text-sm py-1 px-3">
                                    <Award className="mr-1 h-4 w-4" />
                                    {course.cpd_credits} CPD Credits
                                </Badge>
                                <Badge variant="outline" className="text-sm py-1 px-3">
                                    <Clock className="mr-1 h-4 w-4" />
                                    {course.estimated_hours} Hours
                                </Badge>
                                <Badge variant="outline" className="text-sm py-1 px-3">
                                    <BookOpen className="mr-1 h-4 w-4" />
                                    {course.module_count} Modules
                                </Badge>
                            </div>
                        </div>

                        {/* Enrollment Card */}
                        <Card className="lg:col-span-1 shadow-lg border-primary/10">
                            <CardHeader>
                                <CardTitle className="flex justify-between items-center">
                                    <span>{course.is_free ? 'Free' : `$${(course.price_cents / 100).toFixed(2)}`}</span>
                                </CardTitle>
                                <CardDescription>
                                    Includes lifetime access and certificate of completion.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <Button
                                    size="lg"
                                    className="w-full text-lg"
                                    onClick={handleEnroll}
                                    disabled={isEnrolling || (!course.enrollment_open && !isEnrolled)}
                                >
                                    {isEnrolling ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                                    {!course.enrollment_open
                                        ? 'Enrollment Closed'
                                        : isEnrolled
                                            ? 'Continue Course'
                                            : 'Enroll Now'}
                                </Button>
                                <div className="text-sm text-muted-foreground text-center">
                                    30-day money-back guarantee
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>

            <div className="container mx-auto py-12 px-4 grid grid-cols-1 lg:grid-cols-3 gap-12">

                {/* Main Content */}
                <div className="lg:col-span-2 space-y-10">

                    {/* About Course */}
                    <section>
                        <h2 className="text-2xl font-bold mb-4">About This Course</h2>
                        <div className="prose max-w-none text-muted-foreground">
                            {course.description ? (
                                <div dangerouslySetInnerHTML={{ __html: course.description.replace(/\n/g, '<br/>') }} />
                            ) : (
                                <p>No detailed description available.</p>
                            )}
                        </div>
                    </section>

                    <Separator />

                    {/* Curriculum */}
                    <section>
                        <h2 className="text-2xl font-bold mb-6">Course Curriculum</h2>
                        {course.modules && course.modules.length > 0 ? (
                            <Accordion type="single" collapsible className="w-full">
                                {course.modules.sort((a, b) => a.order - b.order).map((courseModule) => (
                                    <AccordionItem key={courseModule.uuid} value={courseModule.uuid}>
                                        <AccordionTrigger className="hover:no-underline">
                                            <div className="flex items-center gap-3 text-left">
                                                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                                                    {courseModule.order + 1}
                                                </div>
                                                <div>
                                                    <span className="font-semibold block">{courseModule.module?.title}</span>
                                                    <span className="text-sm text-muted-foreground font-normal">
                                                        {courseModule.module?.content_count || 0} lessons • {courseModule.module?.assignment_count || 0} assignments
                                                    </span>
                                                </div>
                                            </div>
                                        </AccordionTrigger>
                                        <AccordionContent className="pl-14 pr-4">
                                            <p className="text-muted-foreground mb-4">{courseModule.module?.description}</p>
                                            {/* We could list contents here if available in nested data */}
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        ) : (
                            <div className="text-muted-foreground italic">No modules published yet.</div>
                        )}
                    </section>
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* Organization Card */}
                    {course.organization_name && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base">Offered By</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="flex items-center gap-3">
                                    <Avatar className="h-10 w-10">
                                        {course.organization_logo_url ? (
                                            <AvatarImage src={course.organization_logo_url} alt={course.organization_name} />
                                        ) : null}
                                        <AvatarFallback className="bg-primary/10 text-primary font-bold">
                                            {course.organization_name?.[0]}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="flex-1">
                                        <div className="font-medium text-foreground">{course.organization_name}</div>
                                        <div className="text-xs text-muted-foreground">Organization</div>
                                    </div>
                                </div>
                                {course.organization_slug && (
                                    <Link to={`/organizations/${course.organization_slug}/public`}>
                                        <Button variant="outline" className="w-full text-xs h-8">
                                            <Building2 className="h-3 w-3 mr-1" />
                                            View Profile
                                        </Button>
                                    </Link>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    <Card>
                        <CardHeader>
                            <CardTitle>What you'll get</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex gap-3">
                                <Award className="h-5 w-5 text-primary shrink-0" />
                                <div className="text-sm">
                                    <span className="font-medium block">Certificate of Completion</span>
                                    <span className="text-muted-foreground">Official documentation of your achievement</span>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <Clock className="h-5 w-5 text-primary shrink-0" />
                                <div className="text-sm">
                                    <span className="font-medium block">Self-Paced Learning</span>
                                    <span className="text-muted-foreground">Learn at your own schedule</span>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <Users className="h-5 w-5 text-primary shrink-0" />
                                <div className="text-sm">
                                    <span className="font-medium block">Expert Support</span>
                                    <span className="text-muted-foreground">Access to instructor feedback</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* More from Organization */}
            {course.organization_name && relatedCourses.length > 0 && (
                <div className="container mx-auto px-4 py-12 border-t">
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h2 className="text-2xl font-bold text-foreground">
                                More from {course.organization_name}
                            </h2>
                            <p className="text-muted-foreground mt-1">
                                Explore other courses from this organization
                            </p>
                        </div>
                        {course.organization_slug && (
                            <Link to={`/organizations/${course.organization_slug}/public`}>
                                <Button variant="outline">
                                    View All
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                            </Link>
                        )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {relatedCourses.map((relatedCourse) => (
                            <Card
                                key={relatedCourse.uuid}
                                className="group hover:shadow-lg transition-shadow duration-200 flex flex-col"
                            >
                                <CardContent className="p-0 flex-grow flex flex-col">
                                    {/* Course Image */}
                                    <div className="relative aspect-video bg-muted rounded-t-lg overflow-hidden">
                                        {relatedCourse.featured_image_url ? (
                                            <img
                                                src={relatedCourse.featured_image_url}
                                                alt={relatedCourse.title}
                                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/10 to-primary/5">
                                                <BookOpen className="h-16 w-16 text-primary/30" />
                                            </div>
                                        )}
                                        {!relatedCourse.is_free && (
                                            <div className="absolute top-3 right-3">
                                                <Badge className="bg-white/90 text-foreground border">
                                                    ${(relatedCourse.price_cents / 100).toFixed(0)}
                                                </Badge>
                                            </div>
                                        )}
                                        {relatedCourse.is_free && (
                                            <div className="absolute top-3 right-3">
                                                <Badge className="bg-success/90 text-white">Free</Badge>
                                            </div>
                                        )}
                                    </div>

                                    <div className="p-4 space-y-3 flex-grow flex flex-col">
                                        <h3 className="font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                                            {relatedCourse.title}
                                        </h3>
                                        <p className="text-sm text-muted-foreground line-clamp-2 flex-grow">
                                            {relatedCourse.short_description || relatedCourse.description}
                                        </p>
                                        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground pt-2">
                                            {relatedCourse.estimated_hours && (
                                                <div className="flex items-center gap-1">
                                                    <Clock className="h-4 w-4" />
                                                    <span>{relatedCourse.estimated_hours}h</span>
                                                </div>
                                            )}
                                            {relatedCourse.cpd_credits && (
                                                <div className="flex items-center gap-1">
                                                    <Award className="h-4 w-4" />
                                                    <span>{relatedCourse.cpd_credits} CPD</span>
                                                </div>
                                            )}
                                        </div>
                                        <Link to={`/courses/${relatedCourse.uuid}`} className="mt-auto">
                                            <Button variant="outline" size="sm" className="w-full">
                                                View Course
                                                <ArrowRight className="ml-2 h-3 w-3" />
                                            </Button>
                                        </Link>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
