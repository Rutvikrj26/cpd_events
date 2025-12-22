import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Plus, Search, BookOpen, Clock, Users, MoreVertical, FileText, CheckCircle, Archive } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Skeleton } from '@/components/ui/skeleton';
import { useOrganization } from '@/contexts/OrganizationContext';
import { getOrganizationCourses, deleteCourse, Course } from '@/api/courses';
import { format } from 'date-fns';
import { toast } from 'sonner';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const OrgCoursesPage = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { currentOrg, isManager } = useOrganization();

    const [courses, setCourses] = useState<Course[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeTab, setActiveTab] = useState('all');
    const [courseToDelete, setCourseToDelete] = useState<Course | null>(null);

    useEffect(() => {
        loadCourses();
    }, [slug]);

    const loadCourses = async () => {
        if (!slug) return;
        setIsLoading(true);
        try {
            const data = await getOrganizationCourses(slug);
            setCourses(data);
        } catch (error) {
            console.error('Failed to load courses', error);
            toast.error('Failed to load courses');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDeleteCourse = async () => {
        if (!courseToDelete) return;

        try {
            await deleteCourse(courseToDelete.uuid);
            toast.success('Course deleted successfully');
            setCourses(courses.filter(c => c.uuid !== courseToDelete.uuid));
            setCourseToDelete(null);
        } catch (error) {
            console.error('Failed to delete course', error);
            toast.error('Failed to delete course');
        }
    };

    const filteredCourses = courses.filter(course => {
        const matchesSearch = course.title.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesTab = activeTab === 'all' || course.status === activeTab;
        return matchesSearch && matchesTab;
    });

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'published': return 'bg-green-100 text-green-800';
            case 'draft': return 'bg-yellow-100 text-yellow-800';
            case 'archived': return 'bg-gray-100 text-gray-800';
            default: return 'bg-slate-100 text-slate-800';
        }
    };

    if (isLoading) {
        return (
            <div className="container mx-auto py-8 px-4 space-y-6">
                <div className="flex justify-between items-center">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-10 w-32" />
                </div>
                <div className="space-y-4">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full" />)}
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8 px-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Courses</h1>
                    <p className="text-muted-foreground">Manage your self-paced learning content.</p>
                </div>

                {isManager && (
                    <Button onClick={() => navigate(`/org/${slug}/courses/new`)}>
                        <Plus className="mr-2 h-4 w-4" />
                        Create Course
                    </Button>
                )}
            </div>

            <Tabs defaultValue="all" value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
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
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                <TabsContent value={activeTab} className="m-0">
                    <Card>
                        <CardContent className="p-0">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-[400px]">Course</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Waitlist / Enrolled</TableHead>
                                        <TableHead>Modules</TableHead>
                                        <TableHead>Created</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {filteredCourses.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={6} className="h-24 text-center">
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
                                                            <div className="text-xs text-muted-foreground truncate max-w-[250px]">
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
                                                        {course.max_enrollments && (
                                                            <span className="text-muted-foreground text-xs">
                                                                / {course.max_enrollments}
                                                            </span>
                                                        )}
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
                                                            <DropdownMenuItem onClick={() => navigate(`/org/${slug}/courses/${course.slug}`)}>
                                                                Manage Course
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={() => navigate(`/courses/${course.slug}`)}>
                                                                View Public Page
                                                            </DropdownMenuItem>
                                                            {course.status === 'draft' && (
                                                                <DropdownMenuItem
                                                                    className="text-destructive focus:text-destructive"
                                                                    onClick={() => setCourseToDelete(course)}
                                                                >
                                                                    Delete
                                                                </DropdownMenuItem>
                                                            )}
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>


            <AlertDialog open={!!courseToDelete} onOpenChange={(open) => !open && setCourseToDelete(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Course</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete "{courseToDelete?.title}"? This action cannot be undone and will remove all associated modules, lessons, and enrollment data.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setCourseToDelete(null)}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteCourse}
                            className="bg-red-600 hover:bg-red-700"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div >
    );
};

export default OrgCoursesPage;
