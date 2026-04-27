import { Link } from 'react-router-dom';
import { BookOpen, CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Progress } from '@/shared/ui/progress';
import { EmptyState } from '@/shared/ui/empty-state';
import { useMyProgramEnrollments } from '@/features/programs';
import type { ProgramEnrollmentCourse } from '@/api/programs';

export function MyProgramsPage() {
    const { data: enrollments = [], isLoading } = useMyProgramEnrollments();

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-section">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (enrollments.length === 0) {
        return (
            <div className="mx-auto max-w-4xl px-4 py-section">
                <EmptyState
                    tone="dashed"
                    icon={BookOpen}
                    title="You're not enrolled in any programs yet"
                    description="Browse the program catalog to find your next learning track."
                    action={
                        <Link to="/programs" className="text-body text-primary underline">
                            Browse programs
                        </Link>
                    }
                />
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-4xl space-y-card px-4 py-block">
            <header>
                <h1 className="text-h1 text-foreground">My programs</h1>
                <p className="text-body text-muted-foreground">
                    Track your progress through each program's courses in order.
                </p>
            </header>

            {enrollments.map((e) => {
                const courses = [...(e.courses ?? [])].sort((a, b) => a.order - b.order);
                const completed = courses.filter(
                    (c) => c.enrollment_status === 'completed'
                ).length;
                const total = courses.length;
                return (
                    <Card key={e.uuid} elevation="rest">
                        <CardHeader className="flex flex-row items-start justify-between">
                            <div>
                                <CardTitle>
                                    <Link
                                        to={`/programs/${e.program.slug}`}
                                        className="hover:underline"
                                    >
                                        {e.program.title}
                                    </Link>
                                </CardTitle>
                                <p className="mt-1 text-caption text-muted-foreground">
                                    {completed}/{total} courses completed
                                </p>
                            </div>
                            <ProgramEnrollmentBadge viewState={(e as any).view_state} />
                        </CardHeader>
                        <CardContent>
                            {courses.length === 0 ? (
                                <p className="text-caption text-muted-foreground">
                                    No courses in this program yet.
                                </p>
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

function CourseRow({ course }: { course: ProgramEnrollmentCourse }) {
    const done = course.enrollment_status === 'completed';
    return (
        <div className="flex items-center gap-3 border-b py-2 last:border-b-0">
            <div className="shrink-0">
                {done ? (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                ) : (
                    <Circle className="h-4 w-4 text-muted-foreground" />
                )}
            </div>
            <div className="min-w-[2rem] font-mono text-caption text-muted-foreground">
                {course.order + 1}.
            </div>
            <Link
                to={`/courses/${course.slug}`}
                className="flex-1 text-body hover:underline"
            >
                {course.title}
                {!course.is_required && (
                    <span className="ml-2 text-caption text-muted-foreground">(optional)</span>
                )}
            </Link>
            <div className="w-32 shrink-0">
                <Progress value={course.progress_percent} className="h-1.5" />
            </div>
            <div className="w-10 text-right text-caption text-muted-foreground">
                {Math.round(course.progress_percent)}%
            </div>
        </div>
    );
}

// Discriminated badge per backend-derived view_state. Five kinds; the
// derivation lives in `learning.view_states.derive_program_enrollment_view_state`.
function ProgramEnrollmentBadge({ viewState }: { viewState?: { kind?: string } | null }) {
    const kind = viewState?.kind;
    const config: Record<string, { label: string; variant: 'success' | 'secondary' | 'outline' | 'progress-subtle' | 'success-subtle' | 'locked-subtle' }> = {
        awaiting_approval: { label: 'Awaiting approval', variant: 'locked-subtle' },
        ready_to_start: { label: 'Ready to start', variant: 'success-subtle' },
        in_progress: { label: 'In progress', variant: 'progress-subtle' },
        completed: { label: 'Completed', variant: 'success' },
        revoked: { label: 'Dropped', variant: 'outline' },
    };
    const c = (kind && config[kind]) || { label: 'Enrolled', variant: 'secondary' as const };
    return <Badge variant={c.variant}>{c.label}</Badge>;
}
