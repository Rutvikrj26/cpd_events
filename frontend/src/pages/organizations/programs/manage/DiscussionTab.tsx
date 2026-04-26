import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/components/ui/use-toast';
import { Loader2, MessagesSquare, MessageCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import {
    getProgramDiscussion,
    type ProgramDiscussionDigest,
} from '@/api/programs';

/**
 * Discussion at the program level is an aggregated view. Learners still
 * post inside individual courses — there's no program-only thread concept.
 * This tab surfaces the most recent threads across every member course so a
 * program owner has one place to spot what's active.
 */
export function DiscussionTab({ programUuid }: { programUuid: string }) {
    const { toast } = useToast();
    const [digest, setDigest] = useState<ProgramDiscussionDigest | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        getProgramDiscussion(programUuid)
            .then(setDigest)
            .catch((err) => {
                toast({
                    variant: 'destructive',
                    title: 'Failed to load discussion',
                    description: err?.message,
                });
            })
            .finally(() => setLoading(false));
    }, [programUuid, toast]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle>Recent discussion</CardTitle>
                    <CardDescription>
                        Threads posted in this program's {digest?.member_course_count ?? 0} member course
                        {digest?.member_course_count === 1 ? '' : 's'}. Learners discuss inside individual
                        courses — this view shows the latest activity across the bundle.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {!digest?.threads.length ? (
                        <div className="text-center py-8 text-muted-foreground">
                            <MessagesSquare className="h-10 w-10 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No discussion threads yet.</p>
                        </div>
                    ) : (
                        <div className="divide-y">
                            {digest.threads.map((t) => (
                                <div key={t.uuid} className="py-3 flex items-start justify-between gap-4">
                                    <div className="min-w-0 flex-1">
                                        <p className="font-medium truncate">{t.title}</p>
                                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                                            {t.course && (
                                                <Link
                                                    to={`/courses/manage/${t.course.slug}?tab=discussion`}
                                                    className="hover:underline flex items-center gap-1"
                                                >
                                                    <Badge variant="outline" className="text-xs">
                                                        {t.course.title}
                                                    </Badge>
                                                </Link>
                                            )}
                                            {t.author?.full_name && <span>by {t.author.full_name}</span>}
                                            <span>·</span>
                                            <span>
                                                {formatDistanceToNow(new Date(t.last_activity_at), {
                                                    addSuffix: true,
                                                })}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                                        <MessageCircle className="h-3 w-3" />
                                        {t.reply_count}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default DiscussionTab;
