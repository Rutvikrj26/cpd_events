import client from '@/api/client';

export interface Notification {
    uuid: string;
    notification_type: string;
    title: string;
    message: string;
    action_url: string;
    metadata: Record<string, any>;
    read_at: string | null;
    is_read: boolean;
    created_at: string;
}

export interface NotificationListParams {
    status?: 'unread';
}

export const getNotifications = async (params?: NotificationListParams): Promise<Notification[]> => {
    const response = await client.get<Notification[]>('/users/me/notifications/inbox/', { params });
    return response.data;
};

export const markNotificationRead = async (uuid: string): Promise<Notification> => {
    const response = await client.post<Notification>(`/users/me/notifications/inbox/${uuid}/read/`);
    return response.data;
};

export const markAllNotificationsRead = async (): Promise<{ read_count: number }> => {
    const response = await client.post<{ read_count: number }>('/users/me/notifications/inbox/read-all/');
    return response.data;
};

export const deleteNotification = async (uuid: string): Promise<void> => {
    await client.delete(`/users/me/notifications/inbox/${uuid}/`);
};
