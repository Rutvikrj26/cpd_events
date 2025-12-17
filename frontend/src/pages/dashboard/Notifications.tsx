import React, { useState } from "react";
import { 
  Bell, 
  Calendar, 
  Award, 
  Info, 
  Check, 
  Trash2, 
  Clock 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/custom/PageHeader";
import { toast } from "sonner";

// Mock Notifications Data
const mockNotifications = [
  {
    id: "1",
    type: "reminder",
    title: "Upcoming Event: Advanced Cardiology Symposium",
    message: "The event starts in 24 hours. Check your email for the joining link.",
    time: "2 hours ago",
    read: false,
  },
  {
    id: "2",
    type: "award",
    title: "Certificate Issued",
    message: "You have earned a new certificate for 'Medical Ethics 2024'.",
    time: "1 day ago",
    read: false,
  },
  {
    id: "3",
    type: "system",
    title: "Maintenance Scheduled",
    message: "The platform will undergo maintenance on Sunday at 2 AM EST.",
    time: "3 days ago",
    read: true,
  },
  {
    id: "4",
    type: "reminder",
    title: "Registration Confirmed",
    message: "Your spot for the 'Annual Health Summit' has been confirmed.",
    time: "1 week ago",
    read: true,
  },
];

export function Notifications() {
  const [notifications, setNotifications] = useState(mockNotifications);
  const [filter, setFilter] = useState("all");

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleMarkAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    toast.success("All notifications marked as read");
  };

  const handleDelete = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
    toast.success("Notification removed");
  };

  const handleMarkRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "reminder": return <Calendar className="h-5 w-5 text-blue-600" />;
      case "award": return <Award className="h-5 w-5 text-green-600" />;
      case "system": return <Info className="h-5 w-5 text-gray-600" />;
      default: return <Bell className="h-5 w-5 text-gray-600" />;
    }
  };

  const filteredNotifications = notifications.filter(n => {
    if (filter === "unread") return !n.read;
    return true;
  });

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
          {filteredNotifications.length > 0 ? (
            filteredNotifications.map((notification) => (
              <Card key={notification.id} className={`transition-all ${notification.read ? 'bg-white' : 'bg-blue-50/50 border-blue-100'}`}>
                <div className="p-4 flex gap-4 items-start">
                  <div className={`mt-1 p-2 rounded-full shrink-0 ${notification.read ? 'bg-gray-100' : 'bg-white shadow-sm'}`}>
                    {getIcon(notification.type)}
                  </div>
                  
                  <div className="flex-1 space-y-1">
                    <div className="flex justify-between items-start">
                      <h4 className={`text-sm font-semibold ${notification.read ? 'text-gray-900' : 'text-blue-900'}`}>
                        {notification.title}
                      </h4>
                      <span className="text-xs text-gray-500 flex items-center gap-1 shrink-0 ml-2">
                        <Clock className="h-3 w-3" /> {notification.time}
                      </span>
                    </div>
                    <p className={`text-sm ${notification.read ? 'text-gray-600' : 'text-blue-800'}`}>
                      {notification.message}
                    </p>
                  </div>

                  <div className="flex gap-1 shrink-0 ml-2">
                    {!notification.read && (
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-800 hover:bg-blue-100" onClick={() => handleMarkRead(notification.id)} title="Mark as read">
                        <Check className="h-4 w-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-red-600 hover:bg-red-50" onClick={() => handleDelete(notification.id)} title="Delete">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-16 px-4 bg-gray-50 rounded-lg border border-dashed border-gray-200">
              <div className="h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-gray-400">
                <Bell className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-1">
                All caught up!
              </h3>
              <p className="text-gray-500 text-center max-w-sm">
                You have no {filter === 'unread' ? 'unread' : ''} notifications at this time.
              </p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
