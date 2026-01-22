import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Video } from "lucide-react";
import { ZoomStatus } from "@/api/integrations/types";

interface ZoomIntegrationCardProps {
    zoomStatus: ZoomStatus | null;
    onConnect: () => void;
    onDisconnect: () => void;
}

export function ZoomIntegrationCard({ zoomStatus, onConnect, onDisconnect }: ZoomIntegrationCardProps) {
    return (
        <Card className={`border shadow-sm transition-all ${zoomStatus?.is_connected ? 'bg-card border-primary/20' : 'bg-card border-border'}`}>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center justify-between">
                    <span>Zoom Integration</span>
                    <span className={`relative flex h-2.5 w-2.5`}>
                        {zoomStatus?.is_connected && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary/50 opacity-75"></span>}
                        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${zoomStatus?.is_connected ? 'bg-primary' : 'bg-muted-foreground'}`}></span>
                    </span>
                </CardTitle>
                <CardDescription className={zoomStatus?.is_connected ? "text-primary/80" : "text-muted-foreground"}>
                    {zoomStatus?.is_connected ? 'Automated meeting creation active' : 'Connect for auto-meetings'}
                </CardDescription>
            </CardHeader>
            <CardContent>
                {zoomStatus?.is_connected ? (
                    <>
                        <div className="flex items-center gap-3 mb-6 p-3 rounded-lg bg-secondary/50 border border-border">
                            <Video className="h-8 w-8 text-primary" />
                            <div className="overflow-hidden">
                                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Connected Account</p>
                                <p className="text-sm font-semibold truncate hover:text-clip" title={zoomStatus.zoom_email}>{zoomStatus.zoom_email}</p>
                            </div>
                        </div>
                        <Button
                            size="sm"
                            variant="destructive"
                            className="w-full bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/20"
                            onClick={onDisconnect}
                        >
                            Disconnect Integration
                        </Button>
                    </>
                ) : (
                    <div className="text-center">
                        <div className="h-12 w-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3">
                            <Video className="h-6 w-6 text-primary" />
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">
                            Enable one-click Zoom meetings for your webinars and workshops.
                        </p>
                        <Button
                            size="sm"
                            className="w-full bg-primary hover:bg-primary/90"
                            onClick={onConnect}
                        >
                            Connect Zoom Account
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
