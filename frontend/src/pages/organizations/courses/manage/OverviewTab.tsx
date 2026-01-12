import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Course } from '@/api/courses/types';
import { Users, BookOpen, Award, DollarSign, TrendingUp, Calendar } from 'lucide-react';

interface OverviewTabProps {
    course: Course;
}

export function OverviewTab({ course }: OverviewTabProps) {
    // Format currency
    const formatCurrency = (cents: number, currency: string = 'GBP') => {
        return new Intl.NumberFormat('en-GB', {
            style: 'currency',
            currency,
            minimumFractionDigits: 0,
        }).format(cents / 100);
    };

    const stats = [
        {
            title: 'Total Enrollments',
            value: course.enrollment_count ?? 0,
            icon: Users,
            color: 'text-blue-500',
        },
        {
            title: 'Completions',
            value: course.completion_count ?? 0,
            icon: Award,
            color: 'text-green-500',
        },
        {
            title: 'Modules',
            value: course.module_count ?? 0,
            icon: BookOpen,
            color: 'text-purple-500',
        },
        {
            title: 'Revenue',
            value: formatCurrency((course.enrollment_count ?? 0) * (course.price_cents ?? 0), course.currency),
            icon: DollarSign,
            color: 'text-amber-500',
        },
    ];

    const completionRate = course.enrollment_count && course.enrollment_count > 0
        ? Math.round((course.completion_count ?? 0) / course.enrollment_count * 100)
        : 0;

    return (
        <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat) => (
                    <Card key={stat.title}>
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">{stat.title}</p>
                                    <p className="text-2xl font-bold">{stat.value}</p>
                                </div>
                                <stat.icon className={`h-8 w-8 ${stat.color}`} />
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Course Info */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5" />
                            Performance
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="text-muted-foreground">Completion Rate</span>
                                    <span className="font-medium">{completionRate}%</span>
                                </div>
                                <div className="h-2 bg-muted rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-green-500 transition-all"
                                        style={{ width: `${completionRate}%` }}
                                    />
                                </div>
                            </div>
                            <div className="flex items-center justify-between py-2 border-t">
                                <span className="text-sm text-muted-foreground">CPD Credits</span>
                                <Badge variant="secondary">{course.cpd_credits ?? 0} credits</Badge>
                            </div>
                            <div className="flex items-center justify-between py-2 border-t">
                                <span className="text-sm text-muted-foreground">Estimated Duration</span>
                                <span className="font-medium">{course.estimated_hours ?? 0} hours</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Calendar className="h-5 w-5" />
                            Course Details
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between py-2">
                                <span className="text-sm text-muted-foreground">Status</span>
                                <Badge variant={course.status === 'published' ? 'default' : 'secondary'}>
                                    {course.status}
                                </Badge>
                            </div>
                            <div className="flex items-center justify-between py-2 border-t">
                                <span className="text-sm text-muted-foreground">Format</span>
                                <Badge variant="outline" className="capitalize">
                                    {course.format || 'online'}
                                </Badge>
                            </div>
                            <div className="flex items-center justify-between py-2 border-t">
                                <span className="text-sm text-muted-foreground">Visibility</span>
                                <span className="font-medium">{course.is_public ? 'Public' : 'Private'}</span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-t">
                                <span className="text-sm text-muted-foreground">Price</span>
                                <span className="font-medium">
                                    {course.is_free ? 'Free' : formatCurrency(course.price_cents, course.currency)}
                                </span>
                            </div>
                            <div className="flex items-center justify-between py-2 border-t">
                                <span className="text-sm text-muted-foreground">Enrollment</span>
                                <Badge variant={course.enrollment_open ? 'default' : 'secondary'}>
                                    {course.enrollment_open ? 'Open' : 'Closed'}
                                </Badge>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}

export default OverviewTab;
