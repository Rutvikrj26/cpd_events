import { useEffect, useState } from "react";
import { Activity, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import client from "@/api/client";
import { unwrapList } from "@/api/pagination";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { JoinButton } from "@/components/video/JoinButton";

type RoomTarget =
    | { kind: "event"; event_uuid: string; title: string }
    | { kind: "course_session"; course_uuid: string; session_uuid: string; title: string };

interface ActiveRoom {
    uuid: string;
    room_name: string;
    status: string;
    started_at: string | null;
    target: RoomTarget | null;
}

/**
 * Admin-only widget listing platform-wide active video rooms with one-click
 * host-join. Backed by `GET /video/rooms/?status=active` (admin queryset returns
 * all rooms; status filter narrows to active).
 */
export function AdminLiveRoomsWidget() {
    const [rooms, setRooms] = useState<ActiveRoom[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        client
            .get("/video/rooms/", { params: { status: "active" } })
            .then((res) => {
                if (cancelled) return;
                setRooms(unwrapList<ActiveRoom>(res.data));
            })
            .catch(() => { /* widget is best-effort; skip on error */ })
            .finally(() => { if (!cancelled) setLoading(false); });
        return () => { cancelled = true; };
    }, []);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                    <Activity className="h-4 w-4 text-destructive" /> Live rooms
                </CardTitle>
                <CardDescription>
                    Active video rooms across the platform — admin override lets you join any as host.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" /> Checking…
                    </div>
                ) : rooms.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No live rooms right now.</p>
                ) : (
                    <div className="space-y-3">
                        {rooms.map((room) => {
                            const target = room.target;
                            if (!target) return null;
                            return (
                                <div key={room.uuid} className="flex items-center justify-between gap-3 rounded-md border p-3">
                                    <div className="min-w-0">
                                        <p className="font-medium truncate">{target.title || room.room_name}</p>
                                        <p className="text-xs text-muted-foreground">
                                            Started {room.started_at ? `${formatDistanceToNow(new Date(room.started_at))} ago` : "recently"} · {target.kind === "event" ? "Event" : "Course session"}
                                        </p>
                                    </div>
                                    {target.kind === "event" ? (
                                        <JoinButton
                                            eventUuid={target.event_uuid}
                                            role="host"
                                            state="meeting_live"
                                            size="sm"
                                        />
                                    ) : (
                                        <JoinButton
                                            courseUuid={target.course_uuid}
                                            sessionUuid={target.session_uuid}
                                            role="host"
                                            state="meeting_live"
                                            size="sm"
                                        />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
