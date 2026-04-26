import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Circle, Eye, EyeOff, Loader2, Video } from "lucide-react";

import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { getVideoRecordings, publishRecording, unpublishRecording } from "@/api/video";
import type { VideoRecording } from "@/api/video/types";
import { toast } from "sonner";

interface EventRecordingPanelProps {
    eventUuid: string;
}

const STATUS_LABEL: Record<VideoRecording["status"], string> = {
    recording: "Recording in progress",
    processing: "Processing",
    available: "Ready",
    error: "Failed",
    deleted: "Deleted",
};

function formatDuration(seconds: number): string {
    if (!seconds) return "--";
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${String(s).padStart(2, "0")}s`;
}

function formatSize(bytes: number): string {
    if (!bytes) return "--";
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
}

export function EventRecordingPanel({ eventUuid }: EventRecordingPanelProps) {
    const [recordings, setRecordings] = useState<VideoRecording[]>([]);
    const [loading, setLoading] = useState(true);
    const [actingOn, setActingOn] = useState<string | null>(null);

    const fetchRecordings = async () => {
        try {
            const data = await getVideoRecordings({ event_uuid: eventUuid, manage: true });
            setRecordings(data);
        } catch (error) {
            console.error("Failed to load event recordings", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRecordings();
    }, [eventUuid]);

    const handlePublish = async (rec: VideoRecording) => {
        setActingOn(rec.uuid);
        try {
            await publishRecording(rec.uuid);
            toast.success("Recording published. Attendees can now view it.");
            await fetchRecordings();
        } catch (e: any) {
            toast.error(e?.response?.data?.error || "Failed to publish");
        } finally {
            setActingOn(null);
        }
    };

    const handleUnpublish = async (rec: VideoRecording) => {
        setActingOn(rec.uuid);
        try {
            await unpublishRecording(rec.uuid);
            toast.success("Recording unpublished.");
            await fetchRecordings();
        } catch (e: any) {
            toast.error(e?.response?.data?.error || "Failed to unpublish");
        } finally {
            setActingOn(null);
        }
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                        <Video className="h-4 w-4" /> Recordings
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (recordings.length === 0) {
        return null; // Don't render the card when there's nothing to show.
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                    <Video className="h-4 w-4" /> Recordings
                </CardTitle>
                <CardDescription>
                    {recordings.length === 1 ? "1 recording" : `${recordings.length} recordings`} for this event.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-3">
                    {recordings.map((rec) => {
                        const isAvailable = rec.status === "available";
                        const isError = rec.status === "error";
                        const isInFlight = rec.status === "recording" || rec.status === "processing";
                        return (
                            <div key={rec.uuid} className="flex items-center justify-between gap-3 rounded-md border p-3">
                                <div className="flex items-start gap-3 min-w-0">
                                    {isAvailable ? (
                                        <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0 text-success" />
                                    ) : isError ? (
                                        <Circle className="h-4 w-4 mt-0.5 shrink-0 text-destructive" />
                                    ) : (
                                        <Loader2 className="h-4 w-4 mt-0.5 shrink-0 animate-spin text-muted-foreground" />
                                    )}
                                    <div className="min-w-0">
                                        <p className="font-medium text-sm">
                                            {STATUS_LABEL[rec.status] || rec.status}
                                            {isAvailable && (
                                                <Badge
                                                    variant={rec.is_published ? "default" : "outline"}
                                                    className="ml-2 text-xs"
                                                >
                                                    {rec.is_published ? "Published" : "Unpublished"}
                                                </Badge>
                                            )}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {formatDuration(rec.duration_seconds)} · {formatSize(rec.total_size_bytes)}
                                            {rec.recording_end && (
                                                <> · ended {new Date(rec.recording_end).toLocaleString()}</>
                                            )}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                    {isAvailable && rec.is_published && (
                                        <>
                                            <Button asChild variant="outline" size="sm">
                                                <Link to={`/events/${eventUuid}/recording/${rec.uuid}`}>Watch</Link>
                                            </Button>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => handleUnpublish(rec)}
                                                disabled={actingOn === rec.uuid}
                                            >
                                                <EyeOff className="h-3 w-3 mr-1" /> Unpublish
                                            </Button>
                                        </>
                                    )}
                                    {isAvailable && !rec.is_published && (
                                        <Button
                                            size="sm"
                                            onClick={() => handlePublish(rec)}
                                            disabled={actingOn === rec.uuid}
                                        >
                                            <Eye className="h-3 w-3 mr-1" /> Publish
                                        </Button>
                                    )}
                                    {isInFlight && (
                                        <span className="text-xs text-muted-foreground italic">
                                            {rec.status === "recording" ? "Live recording" : "Processing"}
                                        </span>
                                    )}
                                    {isError && (
                                        <span className="text-xs text-destructive italic">
                                            Recording failed — contact support.
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
}
