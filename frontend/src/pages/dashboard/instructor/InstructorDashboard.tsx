import { Link } from 'react-router-dom';
import { Award, BookOpen, CheckCircle, Plus, Users } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { EmptyState } from '@/shared/ui/empty-state';
import { useAuth } from '@/features/auth';
import {
    HeroBand,
    MiniStat,
    SectionHeader,
    DashboardSkeleton,
    useInstructorDashboard,
} from '@/features/dashboard';
import { getRoleFlags } from '@/lib/role-utils';

const STATUS_VARIANT: Record<string, 'success' | 'progress' | 'locked' | 'secondary'> = {
    published: 'success',
    archived: 'locked',
    draft: 'secondary',
};

export function InstructorDashboard() {
    const { user } = useAuth();
    const { isAdmin } = getRoleFlags(user);
    const dashboard = useInstructorDashboard();

    if (dashboard.isLoading) {
        return <DashboardSkeleton />;
    }

    const { stats, recentCourses } = dashboard;

    return (
        <div className="space-y-block animate-in fade-in slide-in-from-bottom-4 duration-500">
            <HeroBand
                eyebrow="Instructor portal"
                title="Manage your courses"
                description="Grade submissions, track enrollments, and ship new content to your learners."
                actions={[
                    {
                        label: <><Plus className="mr-2 h-4 w-4" /> Create course</>,
                        to: '/courses/manage/new',
                        primary: true,
                    },
                    { label: 'Manage all', to: '/courses/manage' },
                ]}
            />

            <div className="grid grid-cols-2 gap-tight lg:grid-cols-4">
                <MiniStat label="Total courses" value={stats.totalCourses} icon={BookOpen} tone="primary" />
                <MiniStat label="Published" value={stats.publishedCourses} icon={CheckCircle} tone="success" />
                <MiniStat label="Enrollments" value={stats.totalEnrollments} icon={Users} tone="muted" />
                <MiniStat label="Completions" value={stats.totalCompletions} icon={Award} tone="warning" />
            </div>

            <div className="space-y-card">
                <SectionHeader
                    title="Recent courses"
                    link={recentCourses.length > 0 ? { to: '/courses/manage', label: 'View all' } : undefined}
                />

                {recentCourses.length === 0 ? (
                    <EmptyState
                        tone="dashed"
                        icon={BookOpen}
                        title="No courses yet"
                        description={
                            isAdmin
                                ? 'Create your first course to start enrolling learners.'
                                : 'You have not been assigned to any courses yet. Contact your administrator.'
                        }
                        action={
                            isAdmin ? (
                                <Button asChild>
                                    <Link to="/courses/manage/new">Create course</Link>
                                </Button>
                            ) : undefined
                        }
                    />
                ) : (
                    <Card elevation="rest" className="overflow-hidden">
                        <CardContent className="p-0">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-body">
                                    <thead className="border-b border-border bg-muted/40 text-caption font-medium uppercase tracking-wide text-muted-foreground">
                                        <tr>
                                            <th className="px-card py-3">Course</th>
                                            <th className="px-card py-3">Status</th>
                                            <th className="px-card py-3 text-right">Enrollments</th>
                                            <th className="px-card py-3 text-right">Completions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border">
                                        {recentCourses.map((course) => (
                                            <tr key={course.uuid} className="group transition-colors hover:bg-muted/40">
                                                <td className="px-card py-3 font-medium text-foreground">
                                                    <Link
                                                        to={`/courses/manage/${course.slug}`}
                                                        className="block max-w-[280px] truncate transition-colors hover:text-primary"
                                                    >
                                                        {course.title}
                                                    </Link>
                                                </td>
                                                <td className="px-card py-3">
                                                    <Badge
                                                        variant={STATUS_VARIANT[course.status] || 'secondary'}
                                                        className="capitalize"
                                                    >
                                                        {course.status}
                                                    </Badge>
                                                </td>
                                                <td className="px-card py-3 text-right tabular-nums">
                                                    {course.enrollment_count}
                                                </td>
                                                <td className="px-card py-3 text-right tabular-nums">
                                                    {course.completion_count}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}
