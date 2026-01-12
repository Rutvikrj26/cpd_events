import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Award, BookOpen, CheckCircle, Users, ArrowRight, Plus } from 'lucide-react';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DashboardStat } from '@/components/dashboard/DashboardStats';
import { PendingInvitationsBanner } from '@/components/PendingInvitationsBanner';
import { OnboardingChecklist } from '@/components/onboarding';
import { getOwnedCourses } from '@/api/courses';
import { Course } from '@/api/courses/types';

export function CourseManagerDashboard() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCourses() {
      try {
        const data = await getOwnedCourses();
        setCourses(data);
      } catch (error) {
        console.error('Failed to fetch course dashboard data', error);
      } finally {
        setLoading(false);
      }
    }
    fetchCourses();
  }, []);

  const stats = {
    totalCourses: courses.length,
    publishedCourses: courses.filter((course) => course.status === 'published').length,
    totalEnrollments: courses.reduce((acc, course) => acc + (course.enrollment_count || 0), 0),
    totalCompletions: courses.reduce((acc, course) => acc + (course.completion_count || 0), 0),
  };

  const recentCourses = [...courses]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-primary/10 text-primary hover:bg-primary/20 border-primary/20';
      case 'archived': return 'bg-muted text-muted-foreground hover:bg-muted/80 border-border';
      case 'draft':
      default:
        return 'bg-secondary text-secondary-foreground hover:bg-secondary/80 border-secondary-foreground/20';
    }
  };

  if (loading) {
    return <div className="p-8 flex items-center justify-center min-h-[50vh] text-muted-foreground animate-pulse">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader
        title="Course Manager Dashboard"
        description="Build courses, track enrollments, and measure learner completion."
        actions={(
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="outline" size="lg" className="shadow-sm">
              <Link to="/courses/manage">Manage Courses</Link>
            </Button>
            <Button asChild size="lg" className="shadow-sm">
              <Link to="/courses/manage/new">
                <Plus className="mr-2 h-4 w-4" />
                Create New Course
              </Link>
            </Button>
          </div>
        )}
      />

      <PendingInvitationsBanner />
      <OnboardingChecklist />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <DashboardStat
          title="Total Courses"
          value={stats.totalCourses}
          icon={BookOpen}
          description="All courses"
        />
        <DashboardStat
          title="Published"
          value={stats.publishedCourses}
          icon={CheckCircle}
          description="Live courses"
        />
        <DashboardStat
          title="Enrollments"
          value={stats.totalEnrollments}
          icon={Users}
          description="All time"
        />
        <DashboardStat
          title="Completions"
          value={stats.totalCompletions}
          icon={Award}
          description="Learners finished"
        />
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Recent Courses</h2>
          <Button variant="ghost" size="sm" asChild className="text-primary">
            <Link to="/courses/manage">
              View All <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        </div>

        <Card className="border-border/60 shadow-sm overflow-hidden">
          <CardContent className="p-0">
            {recentCourses.length === 0 ? (
              <div className="p-12 text-center bg-muted/50">
                <div className="w-12 h-12 bg-card border border-border rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm">
                  <BookOpen className="h-6 w-6 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-medium text-foreground">No courses yet</h3>
                <p className="text-muted-foreground mt-1 max-w-sm mx-auto mb-6">
                  Create your first course to start enrolling learners.
                </p>
                <Button asChild variant="outline">
                  <Link to="/courses/manage/new">Create Course</Link>
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-muted/80 border-b border-border text-muted-foreground font-medium">
                    <tr>
                      <th className="px-6 py-4">Course</th>
                      <th className="px-6 py-4">Status</th>
                      <th className="px-6 py-4 text-right">Enrollments</th>
                      <th className="px-6 py-4 text-right">Completions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {recentCourses.map((course) => (
                      <tr key={course.uuid} className="group hover:bg-muted/50 transition-colors">
                        <td className="px-6 py-4 font-medium text-foreground">
                          <Link
                            to={`/courses/manage/${course.slug}`}
                            className="hover:text-primary transition-colors block truncate max-w-[280px]"
                          >
                            {course.title}
                          </Link>
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant="secondary" className={`capitalize ${getStatusColor(course.status)}`}>
                            {course.status}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-right">{course.enrollment_count}</td>
                        <td className="px-6 py-4 text-right">{course.completion_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
