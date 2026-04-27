import React, { useEffect, useState, useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
    MessageSquare,
    Plus,
    Pin,
    Lock,
    EyeOff,
    ArrowLeft,
    Flag,
    Loader2,
    Send,
    Trash2,
} from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { toast } from 'sonner';
import {
    listThreads,
    createThread,
    getThread,
    createReply,
    pinThread,
    unpinThread,
    lockThread,
    unlockThread,
    hideThread,
    unhideThread,
    hideReply,
    unhideReply,
    flagThread,
    flagReply,
    deleteThread,
    deleteReply,
    DiscussionThread,
    DiscussionThreadList,
    DiscussionReply,
} from '@/api/courses';
import { RichTextEditor } from './RichTextEditor';
import { FlagDialog } from './FlagDialog';
import { ThreadActionsMenu } from './ThreadActionsMenu';

interface DiscussionPanelProps {
    courseUuid: string;
    currentUserUuid?: string;
    isStaff: boolean;
}

export function DiscussionPanel({ courseUuid, currentUserUuid, isStaff }: DiscussionPanelProps) {
    const [threads, setThreads] = useState<DiscussionThreadList[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeThread, setActiveThread] = useState<DiscussionThread | null>(null);
    const [composerOpen, setComposerOpen] = useState(false);
    const [flagTarget, setFlagTarget] = useState<
        | { type: 'thread'; threadUuid: string; label: string }
        | { type: 'reply'; threadUuid: string; replyUuid: string; label: string }
        | null
    >(null);

    const loadThreads = useCallback(async () => {
        setLoading(true);
        try {
            const data = await listThreads(courseUuid);
            setThreads(data);
        } catch {
            toast.error('Failed to load discussions.');
        } finally {
            setLoading(false);
        }
    }, [courseUuid]);

    useEffect(() => {
        loadThreads();
    }, [loadThreads]);

    const openThread = async (uuid: string) => {
        try {
            const thread = await getThread(courseUuid, uuid);
            setActiveThread(thread);
        } catch {
            toast.error('Failed to load thread.');
        }
    };

    const handleReplySent = async () => {
        if (activeThread) {
            await openThread(activeThread.uuid);
            await loadThreads();
        }
    };

    const handleModerate = async (
        verb: 'pin' | 'unpin' | 'lock' | 'unlock' | 'hide' | 'unhide',
        threadUuid: string
    ) => {
        try {
            const actions: Record<string, (cu: string, tu: string) => Promise<DiscussionThread>> = {
                pin: pinThread,
                unpin: unpinThread,
                lock: lockThread,
                unlock: unlockThread,
                hide: hideThread,
                unhide: unhideThread,
            };
            await actions[verb](courseUuid, threadUuid);
            toast.success(`Thread ${verb}${verb.endsWith('e') ? 'd' : 'ed'}.`);
            await loadThreads();
            if (activeThread?.uuid === threadUuid) {
                await openThread(threadUuid);
            }
        } catch {
            toast.error('Action failed.');
        }
    };

    const handleDeleteThread = async (uuid: string) => {
        if (!window.confirm('Delete this thread? This cannot be undone.')) return;
        try {
            await deleteThread(courseUuid, uuid);
            toast.success('Thread deleted.');
            setActiveThread(null);
            await loadThreads();
        } catch {
            toast.error('Delete failed.');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    // Dialogs (FlagDialog, ThreadComposerDialog) must mount regardless of
    // which sub-view is active — otherwise opening a flag from inside the
    // thread detail view sets state that no rendered dialog reads.
    const dialogs = (
        <>
            <ThreadComposerDialog
                open={composerOpen}
                onOpenChange={setComposerOpen}
                courseUuid={courseUuid}
                onCreated={async (thread) => {
                    setComposerOpen(false);
                    await loadThreads();
                    await openThread(thread.uuid);
                }}
            />
            <FlagDialog
                open={!!flagTarget}
                onOpenChange={(open) => !open && setFlagTarget(null)}
                targetLabel={flagTarget?.label ?? 'this post'}
                onSubmit={async (data) => {
                    if (!flagTarget) return;
                    if (flagTarget.type === 'thread') {
                        await flagThread(courseUuid, flagTarget.threadUuid, data);
                    } else {
                        await flagReply(
                            courseUuid,
                            flagTarget.threadUuid,
                            flagTarget.replyUuid,
                            data
                        );
                    }
                }}
            />
        </>
    );

    if (activeThread) {
        return (
            <>
                <ThreadView
                    courseUuid={courseUuid}
                    thread={activeThread}
                    currentUserUuid={currentUserUuid}
                    isStaff={isStaff}
                    onBack={() => {
                        setActiveThread(null);
                        loadThreads();
                    }}
                    onReplySent={handleReplySent}
                    onModerate={(verb) => handleModerate(verb, activeThread.uuid)}
                    onDelete={() => handleDeleteThread(activeThread.uuid)}
                    onFlagReply={(replyUuid, label) =>
                        setFlagTarget({ type: 'reply', threadUuid: activeThread.uuid, replyUuid, label })
                    }
                    onFlagThread={(label) =>
                        setFlagTarget({ type: 'thread', threadUuid: activeThread.uuid, label })
                    }
                    onReload={() => openThread(activeThread.uuid)}
                />
                {dialogs}
            </>
        );
    }

    return (
        <>
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-lg font-semibold">Discussion</h3>
                    <p className="text-sm text-muted-foreground">
                        Ask questions, share ideas with other learners.
                    </p>
                </div>
                <Button onClick={() => setComposerOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    New Thread
                </Button>
            </div>

            {threads.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-10 text-center">
                        <MessageSquare className="h-10 w-10 text-muted-foreground/40 mb-3" />
                        <p className="text-muted-foreground">No discussions yet. Be the first!</p>
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-2">
                    {threads.map((thread) => (
                        <Card
                            key={thread.uuid}
                            className="cursor-pointer hover:border-primary/40 transition-colors"
                            onClick={() => openThread(thread.uuid)}
                        >
                            <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {thread.is_pinned && (
                                            <Badge variant="secondary" className="gap-1">
                                                <Pin className="h-3 w-3" /> Pinned
                                            </Badge>
                                        )}
                                        {thread.is_locked && (
                                            <Badge variant="outline" className="gap-1">
                                                <Lock className="h-3 w-3" /> Locked
                                            </Badge>
                                        )}
                                        {thread.is_hidden && (
                                            <Badge variant="destructive" className="gap-1">
                                                <EyeOff className="h-3 w-3" /> Hidden
                                            </Badge>
                                        )}
                                        {isStaff && thread.open_flag_count > 0 && (
                                            <Badge variant="destructive" className="gap-1">
                                                <Flag className="h-3 w-3" /> {thread.open_flag_count}
                                            </Badge>
                                        )}
                                    </div>
                                    <CardTitle className="text-base mt-1">{thread.title}</CardTitle>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {thread.author?.full_name ?? 'Deleted user'} ·{' '}
                                        {thread.reply_count}{' '}
                                        {thread.reply_count === 1 ? 'reply' : 'replies'} · last activity{' '}
                                        {formatDistanceToNow(new Date(thread.last_activity_at), {
                                            addSuffix: true,
                                        })}
                                    </p>
                                </div>
                                {isStaff && (
                                    <div onClick={(e) => e.stopPropagation()}>
                                        <ThreadActionsMenu
                                            thread={thread}
                                            onPin={() => handleModerate('pin', thread.uuid)}
                                            onUnpin={() => handleModerate('unpin', thread.uuid)}
                                            onLock={() => handleModerate('lock', thread.uuid)}
                                            onUnlock={() => handleModerate('unlock', thread.uuid)}
                                            onHide={() => handleModerate('hide', thread.uuid)}
                                            onUnhide={() => handleModerate('unhide', thread.uuid)}
                                            onDelete={() => handleDeleteThread(thread.uuid)}
                                        />
                                    </div>
                                )}
                            </CardHeader>
                        </Card>
                    ))}
                </div>
            )}

            {dialogs}
        </>
    );
}

// ==========================================================================
// Thread composer
// ==========================================================================

function ThreadComposerDialog({
    open,
    onOpenChange,
    courseUuid,
    onCreated,
}: {
    open: boolean;
    onOpenChange: (o: boolean) => void;
    courseUuid: string;
    onCreated: (thread: DiscussionThread) => void;
}) {
    const [title, setTitle] = useState('');
    const [body, setBody] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const reset = () => {
        setTitle('');
        setBody('');
    };

    const handleSubmit = async () => {
        if (!title.trim()) {
            toast.error('Title is required.');
            return;
        }
        if (!body.replace(/<[^>]+>/g, '').trim()) {
            toast.error('Body cannot be empty.');
            return;
        }
        setSubmitting(true);
        try {
            const thread = await createThread(courseUuid, { title, body_html: body });
            toast.success('Thread posted.');
            reset();
            onCreated(thread);
        } catch {
            toast.error('Failed to post thread.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Dialog
            open={open}
            onOpenChange={(o) => {
                if (!o) reset();
                onOpenChange(o);
            }}
        >
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Start a new thread</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-2">
                        <Label htmlFor="thread-title">Title</Label>
                        <Input
                            id="thread-title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="What would you like to discuss?"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label>Body</Label>
                        <RichTextEditor
                            value={body}
                            onChange={setBody}
                            placeholder="Share your thoughts. Type @ to mention someone."
                            courseUuid={courseUuid}
                            minHeight={200}
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
                        Cancel
                    </Button>
                    <Button onClick={handleSubmit} disabled={submitting}>
                        {submitting ? 'Posting…' : 'Post Thread'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ==========================================================================
// Thread detail view
// ==========================================================================

function ThreadView({
    courseUuid,
    thread,
    currentUserUuid,
    isStaff,
    onBack,
    onReplySent,
    onModerate,
    onDelete,
    onFlagReply,
    onFlagThread,
    onReload,
}: {
    courseUuid: string;
    thread: DiscussionThread;
    currentUserUuid?: string;
    isStaff: boolean;
    onBack: () => void;
    onReplySent: () => Promise<void>;
    onModerate: (verb: 'pin' | 'unpin' | 'lock' | 'unlock' | 'hide' | 'unhide') => void;
    onDelete: () => void;
    onFlagReply: (replyUuid: string, label: string) => void;
    onFlagThread: (label: string) => void;
    onReload: () => Promise<void>;
}) {
    const [replyBody, setReplyBody] = useState('');
    const [submittingReply, setSubmittingReply] = useState(false);

    const sendReply = async () => {
        if (!replyBody.replace(/<[^>]+>/g, '').trim()) {
            toast.error('Reply cannot be empty.');
            return;
        }
        setSubmittingReply(true);
        try {
            await createReply(courseUuid, thread.uuid, { body_html: replyBody });
            setReplyBody('');
            toast.success('Reply posted.');
            await onReplySent();
        } catch (error: any) {
            toast.error(error?.response?.data?.detail ?? 'Failed to post reply.');
        } finally {
            setSubmittingReply(false);
        }
    };

    const handleHideReply = async (replyUuid: string, isHidden: boolean) => {
        try {
            if (isHidden) {
                await unhideReply(courseUuid, thread.uuid, replyUuid);
            } else {
                await hideReply(courseUuid, thread.uuid, replyUuid);
            }
            await onReload();
        } catch {
            toast.error('Action failed.');
        }
    };

    const handleDeleteReply = async (replyUuid: string) => {
        if (!window.confirm('Delete this reply?')) return;
        try {
            await deleteReply(courseUuid, thread.uuid, replyUuid);
            await onReload();
        } catch {
            toast.error('Delete failed.');
        }
    };

    const canReply = !thread.is_locked || isStaff;

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={onBack}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    All threads
                </Button>
            </div>

            <Card>
                <CardHeader className="pb-3 flex flex-row items-start justify-between gap-3">
                    <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                            {thread.is_pinned && (
                                <Badge variant="secondary" className="gap-1">
                                    <Pin className="h-3 w-3" /> Pinned
                                </Badge>
                            )}
                            {thread.is_locked && (
                                <Badge variant="outline" className="gap-1">
                                    <Lock className="h-3 w-3" /> Locked
                                </Badge>
                            )}
                            {thread.is_hidden && (
                                <Badge variant="destructive" className="gap-1">
                                    <EyeOff className="h-3 w-3" /> Hidden
                                </Badge>
                            )}
                        </div>
                        <CardTitle className="text-lg mt-1">{thread.title}</CardTitle>
                        <p className="text-xs text-muted-foreground mt-1">
                            {thread.author?.full_name ?? 'Deleted user'} ·{' '}
                            {formatDistanceToNow(new Date(thread.created_at), { addSuffix: true })}
                        </p>
                    </div>
                    <div className="flex items-center gap-1">
                        {isStaff && (
                            <ThreadActionsMenu
                                thread={thread}
                                onPin={() => onModerate('pin')}
                                onUnpin={() => onModerate('unpin')}
                                onLock={() => onModerate('lock')}
                                onUnlock={() => onModerate('unlock')}
                                onHide={() => onModerate('hide')}
                                onUnhide={() => onModerate('unhide')}
                                onDelete={onDelete}
                            />
                        )}
                        {!isStaff && thread.author?.uuid !== currentUserUuid && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => onFlagThread(thread.title)}
                                title="Flag thread"
                            >
                                <Flag className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </CardHeader>
                <CardContent>
                    <div
                        className="prose prose-sm max-w-none dark:prose-invert"
                        // Body HTML is server-sanitized via bleach.
                        dangerouslySetInnerHTML={{ __html: thread.body_html }}
                    />
                </CardContent>
            </Card>

            <div className="space-y-3">
                <h4 className="text-sm font-semibold text-muted-foreground">
                    {thread.replies.length}{' '}
                    {thread.replies.length === 1 ? 'Reply' : 'Replies'}
                </h4>
                {thread.replies.map((reply) => (
                    <ReplyRow
                        key={reply.uuid}
                        reply={reply}
                        currentUserUuid={currentUserUuid}
                        isStaff={isStaff}
                        onHideToggle={() => handleHideReply(reply.uuid, reply.is_hidden)}
                        onDelete={() => handleDeleteReply(reply.uuid)}
                        onFlag={() =>
                            onFlagReply(
                                reply.uuid,
                                `reply by ${reply.author?.full_name ?? 'user'}`
                            )
                        }
                    />
                ))}
            </div>

            {canReply ? (
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Your reply</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <RichTextEditor
                            value={replyBody}
                            onChange={setReplyBody}
                            placeholder="Type @ to mention someone."
                            courseUuid={courseUuid}
                            minHeight={120}
                            disabled={submittingReply}
                        />
                        <div className="flex justify-end">
                            <Button onClick={sendReply} disabled={submittingReply}>
                                <Send className="mr-2 h-4 w-4" />
                                {submittingReply ? 'Posting…' : 'Post Reply'}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <Card className="border-dashed">
                    <CardContent className="py-4 text-center text-sm text-muted-foreground">
                        This thread is locked. Only staff can reply.
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

function ReplyRow({
    reply,
    currentUserUuid,
    isStaff,
    onHideToggle,
    onDelete,
    onFlag,
}: {
    reply: DiscussionReply;
    currentUserUuid?: string;
    isStaff: boolean;
    onHideToggle: () => void;
    onDelete: () => void;
    onFlag: () => void;
}) {
    const isAuthor = reply.author?.uuid === currentUserUuid;
    return (
        <Card className={reply.is_hidden ? 'opacity-60 border-dashed' : ''}>
            <CardHeader className="pb-2 flex flex-row items-start justify-between gap-2">
                <div className="flex-1">
                    <p className="text-sm font-medium">
                        {reply.author?.full_name ?? 'Deleted user'}
                        {reply.is_hidden && (
                            <Badge variant="destructive" className="ml-2 gap-1">
                                <EyeOff className="h-3 w-3" /> Hidden
                            </Badge>
                        )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(reply.created_at), { addSuffix: true })}
                    </p>
                </div>
                <div className="flex items-center gap-1">
                    {isStaff && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={onHideToggle}
                            title={reply.is_hidden ? 'Unhide' : 'Hide'}
                        >
                            <EyeOff className="h-4 w-4" />
                        </Button>
                    )}
                    {(isStaff || isAuthor) && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-red-500 hover:text-red-600"
                            onClick={onDelete}
                            title="Delete"
                        >
                            <Trash2 className="h-4 w-4" />
                        </Button>
                    )}
                    {!isAuthor && !isStaff && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={onFlag}
                            title="Flag reply"
                        >
                            <Flag className="h-4 w-4" />
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                <div
                    className="prose prose-sm max-w-none dark:prose-invert"
                    dangerouslySetInnerHTML={{ __html: reply.body_html }}
                />
            </CardContent>
        </Card>
    );
}
