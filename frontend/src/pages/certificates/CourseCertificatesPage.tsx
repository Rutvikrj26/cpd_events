import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Award, BookOpen, Calendar, Loader2, Search, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { getOwnedCourses } from '@/api/courses';
import { Course } from '@/api/courses/types';
import client from '@/api/client';
import { toast } from 'sonner';

interface EnrollmentUser {
    email: string;
    first_name?: string;
    last_name?: string;
}

interface CourseEnrollment {
    uuid: string;
    user?: EnrollmentUser;
    status?: 'active' | 'completed' | 'dropped' | 'pending';
    enrolled_at?: string;
    completed_at?: string;
    certificate_issued?: boolean;
    certificate_issued_at?: string;
}

interface CourseCertificateRow {
    enrollmentUuid: string;
    courseUuid: string;
    courseSlug: string;
    courseTitle: string;
    learnerName: string;
    learnerEmail: string;
    issuedAt: string | null;
    status: string;
}

export const CourseCertificatesPage = () => {
    const [courses, setCourses] = useState<Course[]>([]);
    const [certificates, setCertificates] = useState<CourseCertificateRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [courseFilter, setCourseFilter] = useState('all');

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const ownedCourses = await getOwnedCourses();
                setCourses(ownedCourses);

                const rows = await Promise.all(
                    ownedCourses.map(async (course) => {
                        const response = await client.get(`/courses/${course.uuid}/enrollments/`);
                        const data = Array.isArray(response.data) ? response.data : response.data.results || [];

                        return (data as CourseEnrollment[])
                            .filter((enrollment) => enrollment.certificate_issued)
                            .map((enrollment) => {
                                const firstName = enrollment.user?.first_name || '';
                                const lastName = enrollment.user?.last_name || '';
                                const learnerName = `${firstName} ${lastName}`.trim() || 'Learner';
                                const issuedAt = enrollment.certificate_issued_at
                                    || enrollment.completed_at
                                    || enrollment.enrolled_at
                                    || null;

                                return {
                                    enrollmentUuid: enrollment.uuid,
                                    courseUuid: course.uuid,
                                    courseSlug: course.slug,
                                    courseTitle: course.title,
                                    learnerName,
                                    learnerEmail: enrollment.user?.email || 'Unknown',
                                    issuedAt,
                                    status: enrollment.status || 'completed',
                                };
                            });
                    })
                );

                setCertificates(rows.flat());
            } catch (error) {
                console.error('Failed to load course certificates', error);
                toast.error('Failed to load course certificates.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const filteredCertificates = useMemo(() => {
        const query = searchTerm.toLowerCase();
        return certificates.filter((cert) => {
            const matchesCourse = courseFilter === 'all' || cert.courseUuid === courseFilter;
            const matchesSearch = !query
                || cert.courseTitle.toLowerCase().includes(query)
                || cert.learnerName.toLowerCase().includes(query)
                || cert.learnerEmail.toLowerCase().includes(query);
            return matchesCourse && matchesSearch;
        });
    }, [certificates, courseFilter, searchTerm]);

    const courseOptions = courses.map((course) => ({
        value: course.uuid,
        label: course.title,
    }));

    const courseWithCertificates = new Set(certificates.map((cert) => cert.courseUuid)).size;
    const uniqueLearners = new Set(certificates.map((cert) => cert.learnerEmail)).size;

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center min-h-[50vh]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold text-foreground">Course Certificates</h1>
                <p className="text-muted-foreground">
                    Review certificates issued from your courses.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardContent className="pt-5">
                        <div className="flex items-center gap-3">
                            <Award className="h-5 w-5 text-primary" />
                            <div>
                                <p className="text-sm text-muted-foreground">Certificates Issued</p>
                                <p className="text-2xl font-bold">{certificates.length}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-5">
                        <div className="flex items-center gap-3">
                            <BookOpen className="h-5 w-5 text-primary" />
                            <div>
                                <p className="text-sm text-muted-foreground">Courses with Certificates</p>
                                <p className="text-2xl font-bold">{courseWithCertificates}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-5">
                        <div className="flex items-center gap-3">
                            <Users className="h-5 w-5 text-primary" />
                            <div>
                                <p className="text-sm text-muted-foreground">Certified Learners</p>
                                <p className="text-2xl font-bold">{uniqueLearners}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <CardTitle>Issued Certificates</CardTitle>
                        <CardDescription>Filter by course or search learners.</CardDescription>
                    </div>
                    <Button variant="outline" asChild>
                        <Link to="/courses/manage">
                            Manage Courses
                        </Link>
                    </Button>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="relative w-full sm:max-w-sm">
                            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search learners or courses..."
                                className="pl-9"
                                value={searchTerm}
                                onChange={(event) => setSearchTerm(event.target.value)}
                            />
                        </div>
                        <div className="w-full sm:w-72">
                            <Select value={courseFilter} onValueChange={setCourseFilter}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Filter by course" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Courses</SelectItem>
                                    {courseOptions.map((course) => (
                                        <SelectItem key={course.value} value={course.value}>
                                            {course.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="mt-6">
                        {filteredCertificates.length === 0 ? (
                            <div className="text-center py-16 text-muted-foreground">
                                <Award className="h-12 w-12 mx-auto mb-4 opacity-40" />
                                <p>No certificates issued yet.</p>
                                <p className="text-sm mt-2">
                                    Certificates appear here after learners complete your courses.
                                </p>
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Course</TableHead>
                                        <TableHead>Learner</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Issued</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredCertificates.map((cert) => (
                                        <TableRow key={cert.enrollmentUuid}>
                                            <TableCell>
                                                <div className="font-medium">{cert.courseTitle}</div>
                                            </TableCell>
                                            <TableCell>
                                                <div className="font-medium">{cert.learnerName}</div>
                                                <div className="text-xs text-muted-foreground">{cert.learnerEmail}</div>
                                            </TableCell>
                                            <TableCell>
                                                <Badge variant="outline" className="capitalize">
                                                    {cert.status}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex items-center gap-2 text-sm">
                                                    <Calendar className="h-3 w-3 text-muted-foreground" />
                                                    {cert.issuedAt
                                                        ? new Date(cert.issuedAt).toLocaleDateString()
                                                        : '—'}
                                                </div>
                                            </TableCell>
                                            <TableCell className="text-right">
                                                <Button variant="outline" size="sm" asChild>
                                                    <Link to={`/courses/manage/${cert.courseSlug}`}>
                                                        View Course
                                                    </Link>
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};
