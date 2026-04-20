import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { getMyProgramEnrollments, ProgramEnrollment, ProgramEnrollmentCourse } from '@/api/programs';

function CourseRow({ course }: { course: ProgramEnrollmentCourse }) {
    const done = course.enrollment_status === 'completed';
    return (
        <div className="flex items-center gap-3 py-2 border-b last:border-b-0">
            <div className="shrink-0">
                {done ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                    <Circle className="h-4 w-4 text-muted-foreground" />
                )}
            </div>
            <div className="min-w-[2rem] text-xs font-mono text-muted-foreground">{course.order + 1}.</div>
            <Link to={`/courses/${course.slug}`} className="flex-1 text-sm hover:underline">
                {course.title}
                {!course.is_required && <span className="text-xs text-muted-foreground ml-2">(optional)</span>}
            </Link>
            <div className="w-32 shrink-0">
                <Progress value={course.progress_percent} className="h-1.5" />
            </div>
            <div className="text-xs text-muted-foreground w-10 text-right">{Math.round(course.progress_percent)}%</div>
        </div>
    );
}

export function MyProgramsPage() {
    const [loading, setLoading] = useState(true);
    const [enrollments, setEnrollments] = useState<ProgramEnrollment[]>([]);

    useEffect(() => {
        (async () => {
            try {
                const data = await getMyProgramEnrollments();
                setEnrollments(data);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (enrollments.length === 0) {
        return (
            <div className="max-w-4xl mx-auto py-10 px-4">
                <Card>
                    <CardContent className="py-12 text-center space-y-3">
                        <BookOpen className="h-10 w-10 mx-auto text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">You are not enrolled in any programs yet.</p>
                        <Link to="/programs" className="text-sm text-primary underline">
                            Browse programs
                        </Link>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
            <div>
                <h1 className="text-2xl font-bold">My Programs</h1>
                <p className="text-sm text-muted-foreground">Track your progress through each program's courses in order.</p>
            </div>

            {enrollments.map((e) => {
                const courses = [...(e.courses ?? [])].sort((a, b) => a.order - b.order);
                const completed = courses.filter((c) => c.enrollment_status === 'completed').length;
                const total = courses.length;
                return (
                    <Card key={e.uuid}>
                        <CardHeader className="flex flex-row items-start justify-between">
                            <div>
                                <CardTitle className="text-lg">
                                    <Link to={`/programs/${e.program.slug}`} className="hover:underline">
                                        {e.program.title}
                                    </Link>
                                </CardTitle>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {completed}/{total} courses completed
                                </p>
                            </div>
                            <Badge variant={e.status === 'completed' ? 'default' : 'secondary'}>{e.status}</Badge>
                        </CardHeader>
                        <CardContent>
                            {courses.length === 0 ? (
                                <p className="text-xs text-muted-foreground">No courses in this program yet.</p>
                            ) : (
                                <div>
                                    {courses.map((c) => (
                                        <CourseRow key={c.uuid} course={c} />
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                );
            })}
        </div>
    );
}
