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
import { SettingsTab } from "./manage/SettingsTab";
import { getCourseBySlug } from '@/api/courses';
import { Course } from '@/api/courses/types';
import { Loader2 } from 'lucide-react';
import { useOrganization } from '@/contexts/OrganizationContext';

export function CourseManagementPage() {
    const { slug, courseSlug } = useParams<{ slug?: string; courseSlug?: string }>();
    const [searchParams] = useSearchParams();
    const { currentOrg } = useOrganization();
    const [course, setCourse] = useState<Course | null>(null);
    const [loading, setLoading] = useState(true);
    const isInstructor = Boolean(slug && currentOrg?.user_role === 'instructor');
    const requestedTab = searchParams.get('tab') || 'overview';
    const availableTabs = [
        'overview',
        'enrollments',
        'announcements',
        'submissions',
        ...(isInstructor ? [] : ['curriculum', 'settings']),
    ];
    const defaultTab = availableTabs.includes(requestedTab) ? requestedTab : 'overview';

    useEffect(() => {
        async function fetchCourse() {
            if (!courseSlug) return;
            try {
                const data = await getCourseBySlug(courseSlug, slug ? { org: slug } : { owned: true });
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
                    ...(slug
                        ? [
                            { label: "Organization", href: `/org/${slug}` },
                            { label: "Courses", href: `/org/${slug}/courses` },
                        ]
                        : [
                            { label: "My Courses", href: `/courses/manage` },
                        ]),
                    { label: course.title },
                ]}
                actions={
                    <Link to={`/courses/${course.slug}`} target="_blank">
                        <Button variant="outline">View Public Page</Button>
                    </Link>
                }
            />

            <Tabs defaultValue={defaultTab} className="w-full">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="enrollments">Enrollments</TabsTrigger>
                    <TabsTrigger value="announcements">Announcements</TabsTrigger>
                    <TabsTrigger value="submissions">Submissions</TabsTrigger>
                    {!isInstructor && <TabsTrigger value="curriculum">Curriculum</TabsTrigger>}
                    {!isInstructor && <TabsTrigger value="settings">Settings</TabsTrigger>}
                </TabsList>

                <TabsContent value="overview" className="space-y-4 mt-6">
                    <OverviewTab course={course} />
                </TabsContent>

                <TabsContent value="enrollments" className="mt-6">
                    <EnrollmentsTab courseUuid={course.uuid} />
                </TabsContent>

                <TabsContent value="announcements" className="mt-6">
                    <AnnouncementsTab courseUuid={course.uuid} />
                </TabsContent>

                <TabsContent value="submissions" className="mt-6">
                    <SubmissionsTab courseUuid={course.uuid} />
                </TabsContent>

                {!isInstructor && (
                    <TabsContent value="curriculum" className="mt-6">
                        <CurriculumTab courseUuid={course.uuid} />
                    </TabsContent>
                )}

                {!isInstructor && (
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
