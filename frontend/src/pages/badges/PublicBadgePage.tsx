import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { getBadgeByCode } from "@/api/badges";
import { IssuedBadge } from "@/api/badges/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function PublicBadgePage() {
    const { code } = useParams<{ code: string }>();
    const [badge, setBadge] = useState<IssuedBadge | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (code) {
            fetchBadge(code);
        }
    }, [code]);

    async function fetchBadge(code: string) {
        try {
            const data = await getBadgeByCode(code);
            setBadge(data);
        } catch (error) {
            setError("Badge not found or invalid.");
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (error || !badge) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background p-4">
                <Card className="max-w-md w-full">
                    <CardContent className="py-12 text-center">
                        <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-2">Verification Failed</h3>
                        <p className="text-muted-foreground">{error || "Badge not found"}</p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4">
            <Card className="max-w-3xl w-full mx-auto overflow-hidden shadow-xl">
                <div className="grid md:grid-cols-2">
                    <div className="bg-muted/30 p-8 flex items-center justify-center">
                        {badge.image_url && (
                            <img
                                src={badge.image_url}
                                alt={badge.template_name}
                                className="max-w-full h-auto drop-shadow-lg"
                            />
                        )}
                    </div>
                    <div className="p-8 flex flex-col justify-center">
                        <div className="flex items-center gap-2 text-success mb-6">
                            <CheckCircle className="h-5 w-5" />
                            <span className="font-medium text-sm uppercase tracking-wide">Verified Badge</span>
                        </div>

                        <h1 className="text-2xl font-bold text-foreground mb-2">{badge.template_name}</h1>
                        <p className="text-muted-foreground mb-6">
                            Issued to <span className="font-medium text-foreground">{badge.recipient_name}</span>
                        </p>

                        <div className="space-y-4 border-t pt-6">
                            <div>
                                <p className="text-xs text-uppercase text-muted-foreground font-semibold tracking-wider">EVENT/COURSE</p>
                                <p className="font-medium text-foreground">{badge.event_title || badge.course_title}</p>
                            </div>
                            <div>
                                <p className="text-xs text-uppercase text-muted-foreground font-semibold tracking-wider">ISSUED ON</p>
                                <p className="font-medium text-foreground">{new Date(badge.issued_at).toLocaleDateString()}</p>
                            </div>
                            <div>
                                <p className="text-xs text-uppercase text-muted-foreground font-semibold tracking-wider">BADGE ID</p>
                                <p className="font-mono text-sm text-muted-foreground">{badge.short_code}</p>
                            </div>
                        </div>

                        <div className="mt-8 pt-6 border-t">
                            <p className="text-xs text-muted-foreground text-center">
                                Verified by Accredit
                            </p>
                        </div>
                    </div>
                </div>
            </Card>
        </div>
    );
}
