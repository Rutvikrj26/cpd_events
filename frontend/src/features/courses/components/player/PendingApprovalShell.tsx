import { Link } from 'react-router-dom';
import { Clock, Mail } from 'lucide-react';

import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';

import type { CoursePlayerPendingApproval } from '@/features/courses/hooks/useCoursePlayerBootstrap';

/**
 * PendingApprovalShell — rendered by the player route when the bootstrap
 * returns `access.kind === 'pending_approval'`.
 *
 * The learner has an enrollment row but it hasn't been approved by an
 * instructor yet, so they don't see course content. We surface what they
 * need: the course they're waiting on, when they requested access, and a
 * way to follow up. No CTA to enter the course (no access yet); the
 * primary action is to go back to My Learning where the request appears
 * in the list with the same pending badge.
 */
interface Props {
    data: CoursePlayerPendingApproval;
}

export function PendingApprovalShell({ data }: Props) {
    const { course, requested_at } = data.access;
    const requestedDate = requested_at ? new Date(requested_at) : null;

    return (
        <div className="flex min-h-[80vh] items-center justify-center px-4">
            <Card className="w-full max-w-lg">
                <CardContent className="pt-6 text-center">
                    <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-warning/10">
                        <Clock className="h-8 w-8 text-warning" />
                    </div>
                    <h1 className="mb-2 text-2xl font-bold text-foreground">
                        Awaiting approval
                    </h1>
                    <p className="mb-1 text-muted-foreground">
                        Your enrollment in <span className="font-medium text-foreground">{course.title}</span> is
                        pending an instructor's approval.
                    </p>
                    {requestedDate && (
                        <p className="mb-6 text-sm text-muted-foreground">
                            Requested on{' '}
                            {requestedDate.toLocaleDateString(undefined, {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                            })}
                            . You'll be notified by email once your access is granted.
                        </p>
                    )}
                    <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
                        <Link to="/registrations?tab=courses">
                            <Button className="w-full sm:w-auto">
                                Back to My Learning
                            </Button>
                        </Link>
                        <Link to={`/courses/${course.slug}`}>
                            <Button variant="outline" className="w-full sm:w-auto">
                                <Mail className="mr-2 h-4 w-4" />
                                Course details
                            </Button>
                        </Link>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
