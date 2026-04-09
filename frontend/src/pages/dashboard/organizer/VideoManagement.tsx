import { useEffect, useState } from 'react';
import { Video, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/custom/PageHeader';
import { getVideoStatus, getVideoRooms } from '@/api/video';
import type { VideoRoom, VideoStatus } from '@/api/video/types';

export default function VideoManagement() {
  const [status, setStatus] = useState<VideoStatus | null>(null);
  const [rooms, setRooms] = useState<VideoRoom[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [statusData, roomsData] = await Promise.all([
          getVideoStatus(),
          getVideoRooms(),
        ]);
        setStatus(statusData);
        setRooms(roomsData);
      } catch (err) {
        console.error('Failed to load video data:', err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Video Rooms"
        description="Manage video conferencing for your events and courses"
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="h-5 w-5" />
            Video Provider Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            {status?.configured ? (
              <>
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span>Connected</span>
                <Badge variant="secondary">{status.provider}</Badge>
              </>
            ) : (
              <>
                <XCircle className="h-5 w-5 text-destructive" />
                <span className="text-muted-foreground">Not configured</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active Rooms</CardTitle>
        </CardHeader>
        <CardContent>
          {rooms.length === 0 ? (
            <p className="text-muted-foreground text-sm">No video rooms yet. Create an event with video enabled to get started.</p>
          ) : (
            <div className="space-y-3">
              {rooms.map((room) => (
                <div
                  key={room.uuid}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <Video className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium text-sm">{room.room_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {room.started_at
                          ? `Started ${new Date(room.started_at).toLocaleString()}`
                          : `Created ${new Date(room.created_at).toLocaleString()}`}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={
                      room.status === 'active'
                        ? 'default'
                        : room.status === 'ended'
                          ? 'secondary'
                          : room.status === 'error'
                            ? 'destructive'
                            : 'outline'
                    }
                  >
                    {room.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
