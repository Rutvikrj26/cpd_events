import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getEnrollments } from '@/api/courses';
import { CourseEnrollment } from '@/api/courses/types'; // Need to define this type or use any for now
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Loader2, BookOpen, Award, ArrowRight, PlayCircle } from 'lucide-react';
import { format } from 'date-fns';

export const MyCoursesPage = () => {
    const navigate = useNavigate();
    const [enrollments, setEnrollments] = useState<any[]>([]); // Using any for now as CourseEnrollment type needs to be exported
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchEnrollments = async () => {
            try {
                const data = await getEnrollments();
                setEnrollments(data);
            } catch (error) {
                console.error('Failed to fetch enrollments:', error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchEnrollments();
    }, []);

    if (isLoading) {
        return (
            <div className="flex h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">My Courses</h1>
                    <p className="text-muted-foreground mt-1">
                        Continue learning where you left off.
                    </p>
                </div>
                <Button onClick={() => navigate('/courses')}>Browse Catalog</Button>
            </div>

            {enrollments.length === 0 ? (
                <div className="text-center py-12 border rounded-lg bg-muted/20">
                    <BookOpen className="mx-auto h-12 w-12 text-muted-foreground/50 mb-4" />
                    <h3 className="text-lg font-medium mb-2">No courses yet</h3>
                    <p className="text-muted-foreground mb-6">You haven't enrolled in any courses yet.</p>
                    <Button onClick={() => navigate('/courses')}>Browse Courses</Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {enrollments.map((enrollment) => (
                        <Card key={enrollment.uuid} className="flex flex-col h-full hover:shadow-md transition-shadow">
                            <CardHeader className="pb-4">
                                <div className="flex justify-between items-start mb-2">
                                    <Badge variant={enrollment.status === 'completed' ? 'default' : 'secondary'}>
                                        {enrollment.status === 'completed' ? 'Completed' : 'In Progress'}
                                    </Badge>
                                    {enrollment.certificate_issued && (
                                        <div title="Certificate Earned">
                                            <Award className="h-5 w-5 text-amber-500" />
                                        </div>
                                    )}
                                </div>
                                <CardTitle className="line-clamp-2 leading-tight">
                                    {enrollment.course?.title}
                                </CardTitle>
                                <CardDescription className="line-clamp-1">
                                    {enrollment.course?.organization_name}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="pb-4 flex-grow">
                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-muted-foreground">Progress</span>
                                            <span className="font-medium">{enrollment.progress_percent}%</span>
                                        </div>
                                        <Progress value={enrollment.progress_percent} className="h-2" />
                                    </div>
                                    <div className="text-xs text-muted-foreground flex justify-between">
                                        <span>Started: {enrollment.started_at ? format(new Date(enrollment.started_at), 'MMM d, yyyy') : 'Not started'}</span>
                                        {enrollment.completed_at && (
                                            <span>Finished: {format(new Date(enrollment.completed_at), 'MMM d, yyyy')}</span>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                            <CardFooter className="pt-0 flex gap-2">
                                <Button className="flex-1" asChild>
                                    <Link to={`/learn/${enrollment.course?.uuid}`}>
                                        {enrollment.status === 'completed' ? 'Review' : 'Continue'}
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Link>
                                </Button>
                                {enrollment.certificate_issued && (
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        onClick={() => window.open(`/certificates`, '_blank')}
                                        title="View Certificate"
                                    >
                                        <Award className="h-4 w-4" />
                                    </Button>
                                )}
                            </CardFooter>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
};
