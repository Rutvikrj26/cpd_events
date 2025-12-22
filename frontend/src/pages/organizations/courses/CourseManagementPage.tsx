import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/custom/PageHeader';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CurriculumTab } from "./manage/CurriculumTab";
import { getCourseBySlug } from '@/api/courses';
import { Course } from '@/api/courses/types';

export function CourseManagementPage() {
    const { slug, courseSlug } = useParams<{ slug: string; courseSlug: string }>();
    const [course, setCourse] = useState<Course | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchCourse() {
            if (!courseSlug) return;
            try {
                const data = await getCourseBySlug(courseSlug);
                setCourse(data);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        }
        fetchCourse();
    }, [courseSlug]);

    if (loading) {
        return <div className="p-8">Loading course...</div>;
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
                    { label: "Organization", href: `/org/${slug}` },
                    { label: "Courses", href: `/org/${slug}/courses` },
                    { label: course.title },
                ]}
                actions={
                    <Link to={`/courses/${course.slug}`} target="_blank">
                        <Button variant="outline">View Public Page</Button>
                    </Link>
                }
            />

            <Tabs defaultValue="curriculum" className="w-full">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="curriculum">Curriculum</TabsTrigger>
                    <TabsTrigger value="enrollments">Enrollments</TabsTrigger>
                    <TabsTrigger value="settings">Settings</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="space-y-4">
                    <div className="p-4 border rounded-lg bg-gray-50 border-dashed text-center text-muted-foreground">
                        Overview metrics coming soon.
                    </div>
                </TabsContent>

                <TabsContent value="curriculum">
                    <CurriculumTab courseUuid={course.uuid} />
                </TabsContent>

                <TabsContent value="enrollments">
                    <div className="p-4 border rounded-lg bg-gray-50 border-dashed text-center text-muted-foreground">
                        Enrollment management coming soon.
                    </div>
                </TabsContent>

                <TabsContent value="settings">
                    <div className="p-4 border rounded-lg bg-gray-50 border-dashed text-center text-muted-foreground">
                        General settings coming soon.
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}

export default CourseManagementPage;
