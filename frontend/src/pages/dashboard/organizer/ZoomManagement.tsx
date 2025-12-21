import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
    Video,
    Copy,
    ExternalLink,
    Calendar,
    Link2,
    CheckCircle,
    XCircle,
    RefreshCw
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/custom/PageHeader";
import { toast } from "sonner";
import { getZoomStatus, getZoomMeetings, initiateZoomOAuth, disconnectZoom, ZoomMeeting } from "@/api/integrations";
import { ZoomStatus } from "@/api/integrations/types";

export function ZoomManagement() {
    const [zoomStatus, setZoomStatus] = useState<ZoomStatus | null>(null);
    const [meetings, setMeetings] = useState<ZoomMeeting[]>([]);
    const [loading, setLoading] = useState(true);
    const [connecting, setConnecting] = useState(false);

    useEffect(() => {
        async function fetchData() {
            try {
                const [statusData, meetingsData] = await Promise.all([
                    getZoomStatus(),
                    getZoomMeetings().catch(() => []) // May fail if not connected
                ]);
                setZoomStatus(statusData);
                setMeetings(meetingsData);
            } catch (e) {
                console.error("Failed to fetch Zoom data", e);
            } finally {
                setLoading(false);
            }
        }
        fetchData();
    }, []);

    const handleConnect = async () => {
        setConnecting(true);
        try {
            const authUrl = await initiateZoomOAuth();
            window.location.href = authUrl;
        } catch (e) {
            console.error("Failed to initiate Zoom connection", e);
            toast.error("Failed to connect to Zoom");
            setConnecting(false);
        }
    };

    const handleDisconnect = async () => {
        try {
            await disconnectZoom();
            setZoomStatus({ is_connected: false });
            setMeetings([]);
            toast.success("Zoom disconnected successfully");
        } catch (e) {
            console.error("Failed to disconnect Zoom", e);
            toast.error("Failed to disconnect Zoom");
        }
    };

    const copyToClipboard = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied`);
    };

    if (loading) {
        return <div className="p-8">Loading Zoom data...</div>;
    }

    return (
        <div className="space-y-8">
            <PageHeader
                title="Zoom Integration"
                description="Manage your Zoom connection and view all meetings linked to your events."
            />

            {/* Connection Status Card */}
            <Card className={zoomStatus?.is_connected
                ? "border-green-200 bg-green-50/50 dark:bg-green-950/20 dark:border-green-900"
                : "border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-900"
            }>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={`p-3 rounded-lg ${zoomStatus?.is_connected
                                ? "bg-green-100 dark:bg-green-900/50"
                                : "bg-amber-100 dark:bg-amber-900/50"
                                }`}>
                                <Video className={`h-6 w-6 ${zoomStatus?.is_connected
                                    ? "text-green-600 dark:text-green-400"
                                    : "text-amber-600 dark:text-amber-400"
                                    }`} />
                            </div>
                            <div>
                                <CardTitle className="flex items-center gap-2">
                                    Zoom Account
                                    {zoomStatus?.is_connected ? (
                                        <Badge variant="outline" className="text-green-600 bg-green-100 border-green-200">
                                            <CheckCircle className="h-3 w-3 mr-1" />
                                            Connected
                                        </Badge>
                                    ) : (
                                        <Badge variant="outline" className="text-amber-600 bg-amber-100 border-amber-200">
                                            <XCircle className="h-3 w-3 mr-1" />
                                            Not Connected
                                        </Badge>
                                    )}
                                </CardTitle>
                                <CardDescription className="mt-1">
                                    {zoomStatus?.is_connected
                                        ? `Connected as ${zoomStatus.zoom_email}`
                                        : "Connect your Zoom account to automatically create meetings for online events"
                                    }
                                </CardDescription>
                            </div>
                        </div>
                        {zoomStatus?.is_connected ? (
                            <Button variant="outline" onClick={handleDisconnect} className="text-red-600 hover:text-red-700 hover:bg-red-50">
                                Disconnect
                            </Button>
                        ) : (
                            <Button onClick={handleConnect} disabled={connecting} className="bg-blue-600 hover:bg-blue-700">
                                {connecting ? (
                                    <>
                                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                        Connecting...
                                    </>
                                ) : (
                                    <>
                                        <Link2 className="h-4 w-4 mr-2" />
                                        Connect Zoom
                                    </>
                                )}
                            </Button>
                        )}
                    </div>
                </CardHeader>
            </Card>

            {/* Meetings List */}
            {zoomStatus?.is_connected && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Zoom Meetings</CardTitle>
                        <CardDescription>
                            All events with Zoom meetings linked to your account
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {meetings.length === 0 ? (
                            <div className="text-center py-12 text-muted-foreground">
                                <Video className="h-12 w-12 mx-auto mb-4 opacity-30" />
                                <p className="text-lg font-medium">No Zoom meetings yet</p>
                                <p className="text-sm mt-1">Create an event with Zoom enabled to see meetings here</p>
                                <Link to="/events/create">
                                    <Button className="mt-4">Create Event</Button>
                                </Link>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-border">
                                    <thead className="bg-muted/50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Event</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Date</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Meeting ID</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                                            <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-card divide-y divide-border">
                                        {meetings.map((meeting) => (
                                            <tr key={meeting.uuid} className="hover:bg-muted/50">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <Link
                                                        to={`/organizer/events/${meeting.uuid}/manage`}
                                                        className="text-sm font-medium text-foreground hover:text-blue-600 hover:underline"
                                                    >
                                                        {meeting.title}
                                                    </Link>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                                                    <div className="flex items-center gap-1">
                                                        <Calendar className="h-4 w-4" />
                                                        {new Date(meeting.starts_at).toLocaleDateString()}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center gap-2">
                                                        <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                                                            {meeting.zoom_meeting_id}
                                                        </code>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="h-7 w-7"
                                                            onClick={() => copyToClipboard(meeting.zoom_meeting_id, "Meeting ID")}
                                                        >
                                                            <Copy className="h-3 w-3" />
                                                        </Button>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <Badge
                                                        variant="outline"
                                                        className={
                                                            meeting.status === "published" || meeting.status === "live"
                                                                ? "text-green-600 border-green-200 bg-green-500/10"
                                                                : meeting.status === "draft"
                                                                    ? "text-amber-600 border-amber-200 bg-amber-500/10"
                                                                    : "text-muted-foreground"
                                                        }
                                                    >
                                                        {meeting.status}
                                                    </Badge>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right space-x-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => copyToClipboard(meeting.zoom_join_url, "Join URL")}
                                                    >
                                                        <Copy className="h-4 w-4 mr-1" />
                                                        Copy Link
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => window.open(meeting.zoom_join_url, "_blank")}
                                                    >
                                                        <ExternalLink className="h-4 w-4 mr-1" />
                                                        Open
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
