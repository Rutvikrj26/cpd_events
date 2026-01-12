import React, { useEffect, useMemo, useState } from "react";
import {
  Bell,
  Calendar,
  Info,
  Check,
  Trash2,
  Clock,
  Building2,
  CreditCard,
  DollarSign,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/custom/PageHeader";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  Notification,
} from "@/api/notifications";

export function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const unreadCount = notifications.filter(n => !n.is_read).length;

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await getNotifications();
        setNotifications(data);
      } catch (error: any) {
        console.error("Failed to load notifications:", error);
        toast.error(error?.message || "Failed to load notifications.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true, read_at: new Date().toISOString() })));
      toast.success("All notifications marked as read");
    } catch (error: any) {
      console.error("Failed to mark all read:", error);
      toast.error(error?.message || "Failed to mark all read.");
    }
  };

  const handleDelete = async (uuid: string) => {
    try {
      await deleteNotification(uuid);
      setNotifications(prev => prev.filter(n => n.uuid !== uuid));
      toast.success("Notification removed");
    } catch (error: any) {
      console.error("Failed to delete notification:", error);
      toast.error(error?.message || "Failed to delete notification.");
    }
  };

  const handleMarkRead = async (uuid: string) => {
    try {
      const updated = await markNotificationRead(uuid);
      setNotifications(prev => prev.map(n => n.uuid === uuid ? updated : n));
    } catch (error: any) {
      console.error("Failed to mark notification read:", error);
      toast.error(error?.message || "Failed to mark as read.");
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "org_invite":
        return <Building2 className="h-5 w-5 text-primary" />;
      case "payment_failed":
        return <CreditCard className="h-5 w-5 text-destructive" />;
      case "refund_processed":
        return <DollarSign className="h-5 w-5 text-green-600" />;
      case "trial_ending":
        return <Calendar className="h-5 w-5 text-amber-600" />;
      case "payment_method_expired":
        return <CreditCard className="h-5 w-5 text-amber-600" />;
      case "system":
        return <Info className="h-5 w-5 text-muted-foreground" />;
      default:
        return <Bell className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const filteredNotifications = useMemo(() => {
    if (filter === "unread") {
      return notifications.filter(n => !n.is_read);
    }
    return notifications;
  }, [filter, notifications]);

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <PageHeader
        title="Notifications"
        description="Stay updated on your events and account activity."
        actions={
          unreadCount > 0 && (
            <Button variant="outline" onClick={handleMarkAllRead}>
              <Check className="mr-2 h-4 w-4" /> Mark all as read
            </Button>
          )
        }
      />

      <Tabs defaultValue="all" className="w-full" onValueChange={setFilter}>
        <TabsList className="mb-6">
          <TabsTrigger value="all">All Notifications</TabsTrigger>
          <TabsTrigger value="unread">
            Unread
            {unreadCount > 0 && (
              <Badge variant="secondary" className="ml-2 h-5 px-1.5 min-w-[20px]">
                {unreadCount}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value={filter} className="mt-0 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              Loading notifications...
            </div>
          ) : filteredNotifications.length > 0 ? (
            filteredNotifications.map((notification) => (
              <Card key={notification.uuid} className={`transition-all ${notification.is_read ? 'bg-card' : 'bg-primary/5 border-primary/20'}`}>
                <div className="p-4 flex gap-4 items-start">
                  <div className={`mt-1 p-2 rounded-full shrink-0 ${notification.is_read ? 'bg-muted' : 'bg-card shadow-sm'}`}>
                    {getIcon(notification.notification_type)}
                  </div>

                  <div className="flex-1 space-y-1">
                    <div className="flex justify-between items-start">
                      <h4 className={`text-sm font-semibold ${notification.is_read ? 'text-foreground' : 'text-primary'}`}>
                        {notification.title}
                      </h4>
                      <span className="text-xs text-muted-foreground flex items-center gap-1 shrink-0 ml-2">
                        <Clock className="h-3 w-3" /> {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                      </span>
                    </div>
                    <p className={`text-sm ${notification.is_read ? 'text-muted-foreground' : 'text-primary/80'}`}>
                      {notification.message}
                    </p>
                    {notification.action_url && (
                      <Button
                        variant="link"
                        className="h-auto p-0 text-xs"
                        onClick={() => window.location.assign(notification.action_url)}
                      >
                        View details
                      </Button>
                    )}
                  </div>

                  <div className="flex gap-1 shrink-0 ml-2">
                    {!notification.is_read && (
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-primary hover:text-primary hover:bg-primary/10" onClick={() => handleMarkRead(notification.uuid)} title="Mark as read">
                        <Check className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10" onClick={() => handleDelete(notification.uuid)} title="Delete">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-16 px-4 bg-muted/50 rounded-lg border border-dashed border-border">
              <div className="h-12 w-12 bg-muted rounded-full flex items-center justify-center mb-4 text-muted-foreground">
                <Bell className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-medium text-foreground mb-1">
                All caught up!
              </h3>
              <p className="text-muted-foreground text-center max-w-sm">
                You have no {filter === 'unread' ? 'unread' : ''} notifications at this time.
              </p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
