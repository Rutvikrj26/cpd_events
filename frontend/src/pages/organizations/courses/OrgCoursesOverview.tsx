import React, { useEffect, useState } from 'react';
import { BookOpen, FileText, Loader2, MoreVertical, Search, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { getOrganizationCoursesOverview } from '@/api/organizations';
import { Course } from '@/api/courses';
import { format } from 'date-fns';

interface OrgCoursesOverviewProps {
    orgUuid: string;
    orgSlug: string;
    canCreateCourses?: boolean;
}

const OrgCoursesOverview: React.FC<OrgCoursesOverviewProps> = ({
    orgUuid,
    orgSlug,
    canCreateCourses = false,
}) => {
    const navigate = useNavigate();
    const [courses, setCourses] = useState<Course[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeTab, setActiveTab] = useState('all');

    useEffect(() => {
        const loadCourses = async () => {
            if (!orgUuid) return;
            setIsLoading(true);
            try {
                const data = await getOrganizationCoursesOverview(orgUuid);
                setCourses(data);
            } catch (error) {
                console.error('Failed to load organization courses', error);
                toast.error('Failed to load organization courses');
            } finally {
                setIsLoading(false);
            }
        };

        loadCourses();
    }, [orgUuid]);

    const filteredCourses = courses.filter(course => {
        const matchesSearch = course.title.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesTab = activeTab === 'all' || course.status === activeTab;
        return matchesSearch && matchesTab;
    });

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'published':
                return 'bg-green-100 text-green-800';
            case 'draft':
                return 'bg-yellow-100 text-yellow-800';
            case 'archived':
                return 'bg-gray-100 text-gray-800';
            default:
                return 'bg-slate-100 text-slate-800';
        }
    };

    return (
        <Card>
            <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <CardTitle>Organization Courses</CardTitle>
                    <CardDescription>All courses across course managers in this organization.</CardDescription>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                    <Button variant="outline" onClick={() => navigate(`/org/${orgSlug}/courses`)}>
                        Manage Courses
                    </Button>
                    {canCreateCourses && (
                        <Button onClick={() => navigate(`/org/${orgSlug}/courses/new`)}>
                            Create Course
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <TabsList>
                            <TabsTrigger value="all">All</TabsTrigger>
                            <TabsTrigger value="published">Published</TabsTrigger>
                            <TabsTrigger value="draft">Drafts</TabsTrigger>
                            <TabsTrigger value="archived">Archived</TabsTrigger>
                        </TabsList>

                        <div className="relative w-full sm:w-64">
                            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search courses..."
                                className="pl-8"
                                value={searchQuery}
                                onChange={(event) => setSearchQuery(event.target.value)}
                            />
                        </div>
                    </div>

                    <TabsContent value={activeTab} className="m-0">
                        {isLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                            </div>
                        ) : (
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-[360px]">Course</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Enrollments</TableHead>
                                        <TableHead>Modules</TableHead>
                                        <TableHead>Created</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredCourses.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                                                No courses found.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        filteredCourses.map((course) => (
                                            <TableRow key={course.uuid}>
                                                <TableCell>
                                                    <div className="flex items-center gap-3">
                                                        <div className="h-10 w-16 bg-slate-100 rounded overflow-hidden flex-shrink-0">
                                                            {course.featured_image_url ? (
                                                                <img src={course.featured_image_url} alt="" className="h-full w-full object-cover" />
                                                            ) : (
                                                                <div className="h-full w-full flex items-center justify-center text-slate-400">
                                                                    <BookOpen className="h-5 w-5" />
                                                                </div>
                                                            )}
                                                        </div>
                                                        <div>
                                                            <div className="font-medium">{course.title}</div>
                                                            <div className="text-xs text-muted-foreground truncate max-w-[220px]">
                                                                {course.short_description || 'No description'}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="secondary" className={`capitalize ${getStatusColor(course.status)}`}>
                                                        {course.status}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex items-center gap-2">
                                                        <Users className="h-4 w-4 text-muted-foreground" />
                                                        <span>{course.enrollment_count}</span>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex items-center gap-2">
                                                        <FileText className="h-4 w-4 text-muted-foreground" />
                                                        <span>{course.module_count}</span>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <div className="text-sm text-muted-foreground">
                                                        {format(new Date(course.created_at), 'MMM d, yyyy')}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <Button variant="ghost" className="h-8 w-8 p-0">
                                                                <span className="sr-only">Open menu</span>
                                                                <MoreVertical className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end">
                                                            <DropdownMenuItem onClick={() => navigate(`/org/${orgSlug}/courses/${course.slug}`)}>
                                                                Manage Course
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={() => navigate(`/courses/${course.slug}`)}>
                                                                View Public Page
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        )}
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
};

export default OrgCoursesOverview;
