import {
  LiveKitRoom,
  VideoConference,
  RoomAudioRenderer,
} from '@livekit/components-react';
import '@livekit/components-styles';
import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface VideoRoomProps {
  token: string;
  serverUrl: string;
  roomName: string;
  onDisconnected?: () => void;
}

export function VideoRoom({ token, serverUrl, roomName, onDisconnected }: VideoRoomProps) {
  const [error, setError] = useState<string | null>(null);

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="flex flex-col items-center gap-4 p-8">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={() => setError(null)}>
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="h-full w-full" data-room={roomName}>
      <LiveKitRoom
        token={token}
        serverUrl={serverUrl}
        connect={true}
        onDisconnected={onDisconnected}
        onError={(err) => {
          console.error('LiveKit error:', err);
          setError(err?.message || 'Failed to connect to video room');
        }}
        style={{ height: '100%' }}
      >
        <VideoConference />
        <RoomAudioRenderer />
      </LiveKitRoom>
    </div>
  );
}
