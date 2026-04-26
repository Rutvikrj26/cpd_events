import { useMemo, useState } from 'react';
import {
    Bell,
    Building2,
    Calendar,
    Check,
    Clock,
    CreditCard,
    DollarSign,
    Info,
    Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { Button } from '@/shared/ui/button';
import { Card } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs';
import { EmptyState } from '@/shared/ui/empty-state';
import { PageHeader } from '@/components/custom/PageHeader';
import {
    useNotifications,
    useMarkNotificationRead,
    useMarkAllNotificationsRead,
    useDeleteNotification,
} from '@/features/notifications';
import type { Notification } from '@/api/notifications';

export function Notifications() {
    const [filter, setFilter] = useState('all');
    const { data: notifications = [], isLoading } = useNotifications();
    const markRead = useMarkNotificationRead();
    const markAllRead = useMarkAllNotificationsRead();
    const remove = useDeleteNotification();

    const unreadCount = notifications.filter((n) => !n.is_read).length;

    const filteredNotifications = useMemo(() => {
        return filter === 'unread'
            ? notifications.filter((n) => !n.is_read)
            : notifications;
    }, [filter, notifications]);

    const handleMarkAllRead = async () => {
        try {
            await markAllRead.mutateAsync();
            toast.success('All notifications marked as read');
        } catch (e: any) {
            toast.error(e?.message || 'Failed to mark all read.');
        }
    };

    const handleMarkRead = async (uuid: string) => {
        try {
            await markRead.mutateAsync(uuid);
        } catch (e: any) {
            toast.error(e?.message || 'Failed to mark as read.');
        }
    };

    const handleDelete = async (uuid: string) => {
        try {
            await remove.mutateAsync(uuid);
            toast.success('Notification removed');
        } catch (e: any) {
            toast.error(e?.message || 'Failed to delete notification.');
        }
    };

    return (
        <div className="mx-auto max-w-4xl space-y-block pb-12">
            <PageHeader
                title="Notifications"
                description="Stay updated on your events and account activity."
                actions={
                    unreadCount > 0 ? (
                        <Button
                            variant="outline"
                            onClick={handleMarkAllRead}
                            disabled={markAllRead.isPending}
                        >
                            <Check className="mr-2 h-4 w-4" /> Mark all as read
                        </Button>
                    ) : null
                }
            />

            <Tabs defaultValue="all" className="w-full" onValueChange={setFilter}>
                <TabsList className="mb-card">
                    <TabsTrigger value="all">All Notifications</TabsTrigger>
                    <TabsTrigger value="unread">
                        Unread
                        {unreadCount > 0 && (
                            <Badge variant="secondary" className="ml-2 h-5 min-w-[20px] px-1.5">
                                {unreadCount}
                            </Badge>
                        )}
                    </TabsTrigger>
                </TabsList>

                <TabsContent value={filter} className="mt-0 space-y-tight">
                    {isLoading ? (
                        <NotificationsSkeleton />
                    ) : filteredNotifications.length > 0 ? (
                        filteredNotifications.map((notification) => (
                            <NotificationCard
                                key={notification.uuid}
                                notification={notification}
                                onMarkRead={() => handleMarkRead(notification.uuid)}
                                onDelete={() => handleDelete(notification.uuid)}
                            />
                        ))
                    ) : (
                        <EmptyState
                            tone="dashed"
                            icon={Bell}
                            title="All caught up!"
                            description={`You have no ${filter === 'unread' ? 'unread ' : ''}notifications at this time.`}
                        />
                    )}
                </TabsContent>
            </Tabs>
        </div>
    );
}

/* ------------------------------------------------------------------ */
/* Local sub-components                                                */
/* ------------------------------------------------------------------ */

function NotificationsSkeleton() {
    return (
        <div className="space-y-tight">
            {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />
            ))}
        </div>
    );
}

function NotificationCard({
    notification,
    onMarkRead,
    onDelete,
}: {
    notification: Notification;
    onMarkRead: () => void;
    onDelete: () => void;
}) {
    return (
        <Card
            elevation="rest"
            className={
                notification.is_read
                    ? 'bg-card'
                    : 'border-primary/20 bg-primary/5'
            }
        >
            <div className="flex items-start gap-tight p-card">
                <div
                    className={`mt-1 shrink-0 rounded-full p-2 ${
                        notification.is_read ? 'bg-muted' : 'bg-card shadow-sm'
                    }`}
                >
                    {getIcon(notification.notification_type)}
                </div>

                <div className="flex-1 space-y-1">
                    <div className="flex items-start justify-between">
                        <h4
                            className={`text-body font-semibold ${
                                notification.is_read ? 'text-foreground' : 'text-primary'
                            }`}
                        >
                            {notification.title}
                        </h4>
                        <span className="ml-2 inline-flex shrink-0 items-center gap-1 text-caption text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {formatDistanceToNow(new Date(notification.created_at), {
                                addSuffix: true,
                            })}
                        </span>
                    </div>
                    <p
                        className={`text-body ${
                            notification.is_read ? 'text-muted-foreground' : 'text-primary/80'
                        }`}
                    >
                        {notification.message}
                    </p>
                    {notification.action_url && (
                        <Button
                            variant="link"
                            className="h-auto p-0 text-caption"
                            onClick={() =>
                                window.location.assign(notification.action_url)
                            }
                        >
                            View details
                        </Button>
                    )}
                </div>

                <div className="ml-2 flex shrink-0 gap-1">
                    {!notification.is_read && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-primary hover:bg-primary/10 hover:text-primary"
                            onClick={onMarkRead}
                            title="Mark as read"
                        >
                            <Check className="h-4 w-4" />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        onClick={onDelete}
                        title="Delete"
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </Card>
    );
}

function getIcon(type: string) {
    switch (type) {
        case 'org_invite':
            return <Building2 className="h-5 w-5 text-primary" />;
        case 'payment_failed':
            return <CreditCard className="h-5 w-5 text-destructive" />;
        case 'refund_processed':
            return <DollarSign className="h-5 w-5 text-success" />;
        case 'trial_ending':
        case 'payment_method_expired':
            return <Calendar className="h-5 w-5 text-warning" />;
        case 'system':
            return <Info className="h-5 w-5 text-muted-foreground" />;
        default:
            return <Bell className="h-5 w-5 text-muted-foreground" />;
    }
}
