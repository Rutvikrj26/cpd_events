import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BookOpen, ClipboardCheck, Megaphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getOrganizations, getOrganization, getOrganizationMembers } from "@/api/organizations";
import { Organization, OrganizationMember } from "@/api/organizations/types";
import { Course, getCourse } from "@/api/courses";
import { useAuth } from "@/contexts/AuthContext";
import { useOrganization } from "@/contexts/OrganizationContext";

const InstructorDashboard: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const { user } = useAuth();
    const { setCurrentOrg } = useOrganization();

    const [org, setOrg] = useState<Organization | null>(null);
    const [membership, setMembership] = useState<OrganizationMember | null>(null);
    const [course, setCourse] = useState<Course | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadInstructorContext = async () => {
            if (!slug) return;
            setLoading(true);
            setError(null);

            try {
                const orgs = await getOrganizations();
                const found = orgs.find((item) => item.slug === slug);
                if (!found) {
                    setError("Organization not found");
                    return;
                }

                const [fullOrg, members] = await Promise.all([
                    getOrganization(found.uuid),
                    getOrganizationMembers(found.uuid),
                ]);

                setOrg(fullOrg);
                setCurrentOrg(fullOrg);

                const myMembership = members.find((member) => member.user_uuid === user?.uuid) || null;
                setMembership(myMembership);

                if (myMembership?.assigned_course_uuid) {
                    const assignedCourse = await getCourse(myMembership.assigned_course_uuid);
                    setCourse(assignedCourse);
                } else {
                    setCourse(null);
                }
            } catch (err: any) {
                console.error("Failed to load instructor dashboard", err);
                setError(err?.message || "Failed to load instructor dashboard");
            } finally {
                setLoading(false);
            }
        };

        loadInstructorContext();
    }, [slug, user?.uuid, setCurrentOrg]);

    if (loading) {
        return (
            <div className="container mx-auto py-8 px-4 space-y-6">
                <Skeleton className="h-8 w-64" />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[1, 2, 3].map((item) => (
                        <Skeleton key={item} className="h-24" />
                    ))}
                </div>
                <Skeleton className="h-48" />
            </div>
        );
    }

    if (error || !org) {
        return (
            <div className="container mx-auto py-12 px-4 text-center text-muted-foreground">
                {error || "Unable to load instructor dashboard."}
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8 px-4 space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Instructor Dashboard</h1>
                <p className="text-muted-foreground">
                    Manage your assigned course for {org.name}.
                </p>
            </div>

            {!membership?.assigned_course_uuid || !course ? (
                <Card className="border-dashed">
                    <CardContent className="py-12 text-center space-y-3">
                        <BookOpen className="h-12 w-12 mx-auto text-muted-foreground/40" />
                        <p className="text-muted-foreground">
                            You have not been assigned a course yet.
                        </p>
                        <p className="text-sm text-muted-foreground">
                            Ask an admin or course manager to assign a course to you.
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <Card>
                            <CardContent className="pt-4 text-center">
                                <p className="text-2xl font-bold">{course.enrollment_count}</p>
                                <p className="text-sm text-muted-foreground">Learners Enrolled</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent className="pt-4 text-center">
                                <p className="text-2xl font-bold">{course.completion_count}</p>
                                <p className="text-sm text-muted-foreground">Completions</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardContent className="pt-4 text-center">
                                <p className="text-2xl font-bold">{course.module_count}</p>
                                <p className="text-sm text-muted-foreground">Modules</p>
                            </CardContent>
                        </Card>
                    </div>

                    <Card>
                        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                                <CardTitle className="text-lg">{course.title}</CardTitle>
                                <CardDescription>{course.short_description || "Assigned course"}</CardDescription>
                            </div>
                            <Badge variant="secondary" className="capitalize">
                                {course.status}
                            </Badge>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex flex-wrap gap-3">
                                <Button asChild>
                                    <Link to={`/org/${org.slug}/courses/${course.slug}`}>Manage Course</Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link to={`/org/${org.slug}/courses/${course.slug}?tab=submissions`}>
                                        <ClipboardCheck className="mr-2 h-4 w-4" />
                                        Review Submissions
                                    </Link>
                                </Button>
                                <Button variant="outline" asChild>
                                    <Link to={`/org/${org.slug}/courses/${course.slug}?tab=announcements`}>
                                        <Megaphone className="mr-2 h-4 w-4" />
                                        Announcements
                                    </Link>
                                </Button>
                                <Button variant="ghost" asChild>
                                    <Link to={`/courses/${course.slug}`}>View Public Page</Link>
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
};

export default InstructorDashboard;
