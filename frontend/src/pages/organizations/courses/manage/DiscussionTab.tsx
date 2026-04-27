import React, { useEffect, useState, useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Flag, Loader2, ShieldCheck, ShieldOff } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { toast } from 'sonner';
import { listOpenFlags, resolveFlag, DiscussionFlag } from '@/api/courses';
import { DiscussionPanel } from '@/components/courses/discussion/DiscussionPanel';
import { useAuth } from '@/features/auth';

interface DiscussionTabProps {
    courseUuid: string;
}

const REASON_LABEL: Record<string, string> = {
    spam: 'Spam',
    harassment: 'Harassment',
    off_topic: 'Off-topic',
    other: 'Other',
};

export function DiscussionTab({ courseUuid }: DiscussionTabProps) {
    const { user } = useAuth();
    const [flags, setFlags] = useState<DiscussionFlag[]>([]);
    const [loadingFlags, setLoadingFlags] = useState(true);
    const [resolvingUuid, setResolvingUuid] = useState<string | null>(null);

    const loadFlags = useCallback(async () => {
        setLoadingFlags(true);
        try {
            const data = await listOpenFlags(courseUuid, { status: 'open' });
            setFlags(data);
        } catch {
            toast.error('Failed to load flag queue.');
        } finally {
            setLoadingFlags(false);
        }
    }, [courseUuid]);

    useEffect(() => {
        loadFlags();
    }, [loadFlags]);

    const handleResolve = async (flagUuid: string, action: 'keep' | 'hide') => {
        setResolvingUuid(flagUuid);
        try {
            await resolveFlag(courseUuid, flagUuid, action);
            toast.success(action === 'hide' ? 'Content hidden.' : 'Content kept visible.');
            await loadFlags();
        } catch {
            toast.error('Failed to resolve flag.');
        } finally {
            setResolvingUuid(null);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-xl font-semibold">Discussion</h2>
                <p className="text-sm text-muted-foreground">
                    Moderate threads, resolve flags, and reply to learners.
                </p>
            </div>

            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Flag className="h-4 w-4 text-red-500" />
                        Open flags
                        {flags.length > 0 && (
                            <Badge variant="destructive">{flags.length}</Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {loadingFlags ? (
                        <div className="flex items-center justify-center py-6">
                            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        </div>
                    ) : flags.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No open flags. Nothing to review.</p>
                    ) : (
                        <div className="space-y-3">
                            {flags.map((flag) => (
                                <div
                                    key={flag.uuid}
                                    className="rounded-md border p-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"
                                >
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <Badge variant="outline" className="capitalize">
                                                {flag.target_type}
                                            </Badge>
                                            <Badge variant="secondary">
                                                {REASON_LABEL[flag.reason] ?? flag.reason}
                                            </Badge>
                                        </div>
                                        <p className="text-sm text-muted-foreground line-clamp-2">
                                            {flag.target_snippet || '(no preview)'}
                                        </p>
                                        {flag.note && (
                                            <p className="text-xs text-muted-foreground mt-1 italic">
                                                "{flag.note}"
                                            </p>
                                        )}
                                        <p className="text-xs text-muted-foreground mt-1">
                                            Reported by {flag.reporter?.full_name ?? 'unknown'} ·{' '}
                                            {formatDistanceToNow(new Date(flag.created_at), {
                                                addSuffix: true,
                                            })}
                                        </p>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => handleResolve(flag.uuid, 'keep')}
                                            disabled={resolvingUuid === flag.uuid}
                                        >
                                            <ShieldCheck className="mr-2 h-4 w-4" />
                                            Keep
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="destructive"
                                            onClick={() => handleResolve(flag.uuid, 'hide')}
                                            disabled={resolvingUuid === flag.uuid}
                                        >
                                            <ShieldOff className="mr-2 h-4 w-4" />
                                            Hide
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            <div>
                <DiscussionPanel
                    courseUuid={courseUuid}
                    currentUserUuid={user?.uuid}
                    isStaff={true}
                />
            </div>
        </div>
    );
}
