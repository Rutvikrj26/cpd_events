import React, { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/custom/PageHeader';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CurriculumTab } from "./manage/CurriculumTab";
import { OverviewTab } from "./manage/OverviewTab";
import { EnrollmentsTab } from "./manage/EnrollmentsTab";
import { AnnouncementsTab } from "./manage/AnnouncementsTab";
import { SubmissionsTab } from "./manage/SubmissionsTab";
import { SessionsTab } from "./manage/SessionsTab";
import { SettingsTab } from "./manage/SettingsTab";
import { CertificatesTab } from "./manage/CertificatesTab";
import { getCourseBySlug } from '@/api/courses';
import { Course } from '@/api/courses/types';
import { Loader2 } from 'lucide-react';
export function CourseManagementPage() {
    const { slug, courseSlug } = useParams<{ slug?: string; courseSlug?: string }>();
    const [searchParams, setSearchParams] = useSearchParams();
    const [course, setCourse] = useState<Course | null>(null);
    const [loading, setLoading] = useState(true);
    // Course staff see limited tabs (no overview/settings)
    const isStaffOnly = course?.user_role === 'course_manager' || course?.user_role === 'instructor';

    // Sessions tab shows for live and hybrid; curriculum is hidden for live (no modules)
    const showSessions = course?.format === 'hybrid' || course?.format === 'live';
    const showCurriculum = course?.format !== 'live';

    const requestedTab = searchParams.get('tab') || (isStaffOnly ? (showCurriculum ? 'curriculum' : 'sessions') : 'overview');
    const availableTabs = [
        ...(isStaffOnly ? [] : ['overview']),
        'enrollments',
        ...(showCurriculum ? ['curriculum'] : []),
        'announcements',
        'submissions',
        ...(showSessions ? ['sessions'] : []),
        'certificates',
        ...(isStaffOnly ? [] : ['settings']),
    ];
    const defaultTab = availableTabs.includes(requestedTab) ? requestedTab : availableTabs[0];

    useEffect(() => {
        async function fetchCourse() {
            if (!courseSlug) return;
            try {
                const data = await getCourseBySlug(courseSlug, { owned: true });
                setCourse(data);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        }
        fetchCourse();
    }, [courseSlug, slug]);

    const handleCourseUpdated = (updatedCourse: Course) => {
        setCourse(updatedCourse);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!course) {
        return <div className="p-8">Course not found.</div>;
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title={course.title}
                description={`Manage course content and settings.`}
                breadcrumbs={[
                    { label: "My Courses", href: `/courses/manage` },
                    { label: course.title },
                ]}
                actions={
                    <Link to={`/courses/${course.slug}`} target="_blank">
                        <Button variant="outline">View Public Page</Button>
                    </Link>
                }
            />

            <Tabs
                value={defaultTab}
                onValueChange={(value) => {
                    const next = new URLSearchParams(searchParams);
                    next.set('tab', value);
                    setSearchParams(next, { replace: true });
                }}
                className="w-full"
            >
                <TabsList>
                    {!isStaffOnly && <TabsTrigger value="overview">Overview</TabsTrigger>}
                    {showSessions && <TabsTrigger value="sessions">Sessions</TabsTrigger>}
                    {showCurriculum && <TabsTrigger value="curriculum">Curriculum</TabsTrigger>}
                    <TabsTrigger value="enrollments">Enrollments</TabsTrigger>
                    <TabsTrigger value="announcements">Announcements</TabsTrigger>
                    <TabsTrigger value="submissions">Submissions</TabsTrigger>
                    <TabsTrigger value="certificates">Certificates</TabsTrigger>
                    {!isStaffOnly && <TabsTrigger value="settings">Settings</TabsTrigger>}
                </TabsList>

                {!isStaffOnly && (
                    <TabsContent value="overview" className="space-y-4 mt-6">
                        <OverviewTab course={course} />
                    </TabsContent>
                )}

                {showSessions && (
                    <TabsContent value="sessions" className="mt-6">
                        <SessionsTab courseUuid={course.uuid} />
                    </TabsContent>
                )}

                {showCurriculum && (
                    <TabsContent value="curriculum" className="mt-6">
                        <CurriculumTab courseUuid={course.uuid} />
                    </TabsContent>
                )}

                <TabsContent value="enrollments" className="mt-6">
                    <EnrollmentsTab courseUuid={course.uuid} />
                </TabsContent>

                <TabsContent value="announcements" className="mt-6">
                    <AnnouncementsTab courseUuid={course.uuid} />
                </TabsContent>

                <TabsContent value="submissions" className="mt-6">
                    <SubmissionsTab courseUuid={course.uuid} />
                </TabsContent>

                <TabsContent value="certificates" className="mt-6">
                    <CertificatesTab courseUuid={course.uuid} />
                </TabsContent>

                {!isStaffOnly && (
                    <TabsContent value="settings" className="mt-6">
                        <SettingsTab
                            course={course}
                            onCourseUpdated={handleCourseUpdated}
                            organizationSlug={slug}
                        />
                    </TabsContent>
                )}
            </Tabs>
        </div>
    );
}

export default CourseManagementPage;
