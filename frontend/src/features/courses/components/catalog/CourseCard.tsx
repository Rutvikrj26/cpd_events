import { Award, BookOpen, Clock, Layers, Users, ArrowRight, Video, MonitorPlay } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Card, CardContent, CardDescription, CardFooter } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar';
import type { Course } from '@/api/courses/types';
import { formatCpdLabel } from '@/lib/completion-criteria';
import { cn } from '@/lib/utils';

const FORMAT_META: Record<string, { label: string; icon: LucideIcon; tone: string }> = {
    online: {
        label: 'Self-paced',
        icon: MonitorPlay,
        tone: 'bg-secondary/90 text-secondary-foreground',
    },
    live: {
        label: 'Live cohort',
        icon: Video,
        tone: 'bg-status-progress/90 text-status-progress-foreground',
    },
    hybrid: {
        label: 'Hybrid',
        icon: Layers,
        tone: 'bg-accent/90 text-accent-foreground',
    },
};

interface CourseCardProps {
    course: Course;
    onView: (course: Course) => void;
}

/**
 * CourseCard — used in the public catalog grid. Cover image with three
 * status pills (CPD, format, price), descriptive body, and a footer
 * with organizer chip + hover-revealed "View course →".
 */
export function CourseCard({ course, onView }: CourseCardProps) {
    const fmt = FORMAT_META[course.format] || FORMAT_META.online;
    const FormatIcon = fmt.icon;
    const cpdLabel = course.cpd_credits
        ? formatCpdLabel({
              credits: course.cpd_credits,
              criteria: course.hybrid_completion_criteria,
              isCompleted: false,
          })
        : null;

    return (
        <Card
            elevation="interactive"
            className="group flex cursor-pointer flex-col overflow-hidden focus-within:ring-2 focus-within:ring-ring/60"
            onClick={() => onView(course)}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onView(course);
                }
            }}
            role="link"
            tabIndex={0}
            aria-label={`View course: ${course.title}`}
        >
            <div className="relative aspect-video overflow-hidden bg-gradient-to-br from-primary/10 via-primary/5 to-accent/10">
                {course.featured_image_url ? (
                    <img
                        src={course.featured_image_url}
                        alt=""
                        className="h-full w-full object-cover transition-transform duration-300 ease-out group-hover:scale-[1.03]"
                        loading="lazy"
                    />
                ) : (
                    <div className="flex h-full w-full items-center justify-center">
                        <BookOpen
                            className="h-16 w-16 text-primary/30"
                            strokeWidth={1.5}
                            aria-hidden="true"
                        />
                    </div>
                )}
                <div className="absolute bottom-3 left-3">
                    <span
                        className={cn(
                            'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-caption font-semibold backdrop-blur-md',
                            fmt.tone
                        )}
                    >
                        <FormatIcon
                            className="h-3.5 w-3.5"
                            strokeWidth={1.75}
                            aria-hidden="true"
                        />
                        {fmt.label}
                    </span>
                </div>
                <div className="absolute right-3 top-3">
                    {course.is_free ? (
                        <Badge variant="success" className="text-caption">
                            Free
                        </Badge>
                    ) : (
                        <span className="inline-flex items-center rounded-full bg-card/90 px-2.5 py-1 text-caption font-semibold text-foreground backdrop-blur-md">
                            {(course.currency || 'USD').toUpperCase()} $
                            {(course.price_cents / 100).toFixed(0)}
                        </span>
                    )}
                </div>
                {cpdLabel && (
                    <div className="absolute left-3 top-3">
                        <span className="inline-flex items-center gap-1 rounded-full bg-card/90 px-2.5 py-1 text-caption font-semibold text-foreground backdrop-blur-md">
                            <Award
                                className="h-3.5 w-3.5 text-warning"
                                strokeWidth={1.75}
                                aria-hidden="true"
                            />
                            {cpdLabel}
                        </span>
                    </div>
                )}
            </div>

            <CardContent className="flex flex-grow flex-col gap-tight p-card">
                <h3 className="text-h2 leading-tight text-foreground transition-colors group-hover:text-primary line-clamp-2">
                    {course.title}
                </h3>

                <CardDescription className="line-clamp-3">
                    {course.short_description || course.description}
                </CardDescription>

                <div className="mt-auto flex flex-wrap items-center gap-card text-body text-muted-foreground">
                    {course.estimated_hours ? (
                        <span className="inline-flex items-center gap-1">
                            <Clock className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
                            {course.estimated_hours}h
                        </span>
                    ) : null}
                    {course.module_count > 0 ? (
                        <span className="inline-flex items-center gap-1">
                            <Layers className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
                            {course.module_count}{' '}
                            {course.module_count === 1 ? 'module' : 'modules'}
                        </span>
                    ) : null}
                    {course.enrollment_count > 0 ? (
                        <span className="inline-flex items-center gap-1">
                            <Users className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
                            {course.enrollment_count} enrolled
                        </span>
                    ) : null}
                </div>
            </CardContent>

            <CardFooter className="flex items-center justify-between gap-tight border-t bg-muted/30 px-card py-tight">
                {course.organization_name ? (
                    <div className="flex min-w-0 items-center gap-tight">
                        <Avatar className="h-7 w-7">
                            {course.organization_logo_url ? (
                                <AvatarImage src={course.organization_logo_url} alt="" />
                            ) : null}
                            <AvatarFallback className="text-xs">
                                {course.organization_name[0]}
                            </AvatarFallback>
                        </Avatar>
                        <span className="truncate text-caption font-medium text-muted-foreground">
                            {course.organization_name}
                        </span>
                    </div>
                ) : (
                    <span className="text-caption text-muted-foreground/70">Browse course</span>
                )}
                <span
                    className={cn(
                        'inline-flex shrink-0 items-center gap-1 text-caption font-semibold text-primary transition-opacity',
                        course.organization_name
                            ? 'opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'
                            : 'opacity-100'
                    )}
                >
                    View course{' '}
                    <ArrowRight
                        className="h-3.5 w-3.5"
                        strokeWidth={1.75}
                        aria-hidden="true"
                    />
                </span>
            </CardFooter>
        </Card>
    );
}
