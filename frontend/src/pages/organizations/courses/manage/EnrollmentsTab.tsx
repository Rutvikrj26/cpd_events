import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import { Loader2, Search, UserCircle, Mail, Calendar, Filter } from 'lucide-react';
import { format } from 'date-fns';
import client from '@/api/client';

interface CourseEnrollment {
    uuid: string;
    user_uuid: string;
    user_email: string;
    user_name?: string | null;
    status: 'active' | 'completed' | 'dropped' | 'pending';
    enrolled_at: string;
    started_at?: string;
    completed_at?: string;
    progress_percent: number;
    certificate_issued?: boolean;
}

interface EnrollmentsTabProps {
    courseUuid: string;
}

export function EnrollmentsTab({ courseUuid }: EnrollmentsTabProps) {
    const { toast } = useToast();
    const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');

    useEffect(() => {
        const fetchEnrollments = async () => {
            try {
                // Call the course enrollments endpoint
                const response = await client.get(`/courses/${courseUuid}/enrollments/`);
                const data = Array.isArray(response.data) ? response.data : response.data.results || [];
                setEnrollments(data);
            } catch (error) {
                console.error('Failed to fetch enrollments:', error);
                toast({
                    variant: 'destructive',
                    title: 'Error',
                    description: 'Failed to load enrollments.',
                });
            } finally {
                setLoading(false);
            }
        };

        fetchEnrollments();
    }, [courseUuid, toast]);

    // Filter enrollments
    const filteredEnrollments = enrollments.filter(enrollment => {
        const matchesSearch =
            enrollment.user_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            enrollment.user_name?.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesStatus = statusFilter === 'all' || enrollment.status === statusFilter;

        return matchesSearch && matchesStatus;
    });

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'completed':
                return <Badge className="bg-green-500">Completed</Badge>;
            case 'active':
                return <Badge className="bg-blue-500">Active</Badge>;
            case 'dropped':
                return <Badge variant="destructive">Dropped</Badge>;
            case 'pending':
                return <Badge variant="secondary">Pending</Badge>;
            default:
                return <Badge variant="outline">{status}</Badge>;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search by name or email..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-9"
                    />
                </div>
                <div className="flex gap-2">
                    {['all', 'active', 'completed', 'pending', 'dropped'].map((status) => (
                        <Button
                            key={status}
                            variant={statusFilter === status ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setStatusFilter(status)}
                            className="capitalize"
                        >
                            {status}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Stats Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold">{enrollments.length}</p>
                        <p className="text-sm text-muted-foreground">Total</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-blue-500">
                            {enrollments.filter(e => e.status === 'active').length}
                        </p>
                        <p className="text-sm text-muted-foreground">Active</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-green-500">
                            {enrollments.filter(e => e.status === 'completed').length}
                        </p>
                        <p className="text-sm text-muted-foreground">Completed</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-amber-500">
                            {enrollments.filter(e => e.certificate_issued).length}
                        </p>
                        <p className="text-sm text-muted-foreground">Certified</p>
                    </CardContent>
                </Card>
            </div>

            {/* Enrollments List */}
            {filteredEnrollments.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <UserCircle className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                        <p className="text-muted-foreground">
                            {enrollments.length === 0
                                ? 'No enrollments yet'
                                : 'No enrollments match your search'}
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle>Enrolled Learners</CardTitle>
                        <CardDescription>{filteredEnrollments.length} learner(s)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="divide-y">
                            {filteredEnrollments.map((enrollment) => (
                                <div key={enrollment.uuid} className="flex items-center justify-between py-4">
                                    <div className="flex items-center gap-4">
                                        <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                                            <UserCircle className="h-6 w-6 text-muted-foreground" />
                                        </div>
                                        <div>
                                            <p className="font-medium">
                                                {enrollment.user_name || 'Unknown Learner'}
                                            </p>
                                            <p className="text-sm text-muted-foreground flex items-center gap-1">
                                                <Mail className="h-3 w-3" />
                                                {enrollment.user_email || 'No email'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-6">
                                        <div className="text-right">
                                            <p className="text-sm font-medium">{enrollment.progress_percent}%</p>
                                            <p className="text-xs text-muted-foreground">Progress</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-sm flex items-center gap-1">
                                                <Calendar className="h-3 w-3" />
                                                {enrollment.enrolled_at
                                                    ? format(new Date(enrollment.enrolled_at), 'MMM d, yyyy')
                                                    : 'N/A'}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Enrolled</p>
                                        </div>
                                        {getStatusBadge(enrollment.status)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

export default EnrollmentsTab;
