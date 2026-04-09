import { useState } from 'react';
import { Video, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog';
import { joinEventVideo, joinCourseSessionVideo } from '@/api/video';
import { VideoRoom } from './VideoRoom';

interface JoinButtonProps {
  eventUuid?: string;
  courseUuid?: string;
  sessionUuid?: string;
  label?: string;
  variant?: 'default' | 'outline' | 'secondary';
  size?: 'default' | 'sm' | 'lg';
  className?: string;
}

export function JoinButton({
  eventUuid,
  courseUuid,
  sessionUuid,
  label = 'Join Video',
  variant = 'default',
  size = 'default',
  className,
}: JoinButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoSession, setVideoSession] = useState<{
    token: string;
    ws_url: string;
    room_name: string;
  } | null>(null);

  const handleJoin = async () => {
    setLoading(true);
    setError(null);

    try {
      let response;
      if (eventUuid) {
        response = await joinEventVideo(eventUuid);
      } else if (courseUuid && sessionUuid) {
        response = await joinCourseSessionVideo(courseUuid, sessionUuid);
      } else {
        throw new Error('No event or course session specified');
      }
      setVideoSession(response);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to join video room';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        onClick={handleJoin}
        disabled={loading}
      >
        {loading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Video className="mr-2 h-4 w-4" />
        )}
        {label}
      </Button>

      {error && (
        <p className="text-sm text-destructive mt-1">{error}</p>
      )}

      <Dialog
        open={!!videoSession}
        onOpenChange={(open) => {
          if (!open) setVideoSession(null);
        }}
      >
        <DialogContent className="max-w-6xl h-[85vh] p-0">
          <DialogTitle className="sr-only">Video Room</DialogTitle>
          {videoSession && (
            <VideoRoom
              token={videoSession.token}
              serverUrl={videoSession.ws_url}
              roomName={videoSession.room_name}
              onDisconnected={() => setVideoSession(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
