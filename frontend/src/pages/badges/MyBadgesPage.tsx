import React, { useState, useEffect } from "react";
import { Loader2, Award, Share2, Download, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getMyBadges } from "@/api/badges";
import { IssuedBadge } from "@/api/badges/types";
import { toast } from "sonner";
import { DashboardLayout } from "@/components/layout/DashboardLayout";

export function MyBadgesPage() {
    const [badges, setBadges] = useState<IssuedBadge[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchBadges();
    }, []);

    async function fetchBadges() {
        try {
            const data = await getMyBadges();
            setBadges(data.results);
        } catch (error) {
            toast.error("Failed to load badges");
        } finally {
            setLoading(false);
        }
    }

    const copyShareLink = (code: string) => {
        const url = `${window.location.origin}/badges/verify/${code}`;
        navigator.clipboard.writeText(url);
        toast.success("Verification link copied!");
    };

    if (loading) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center min-h-[50vh]">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="space-y-6">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">My Badges</h1>
                    <p className="text-muted-foreground">
                        Digital badges you've earned from events and courses.
                    </p>
                </div>

                {badges.length === 0 ? (
                    <Card>
                        <CardContent className="py-16 text-center">
                            <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                                <Award className="h-8 w-8 text-gray-400" />
                            </div>
                            <h3 className="text-lg font-medium text-foreground mb-2">No badges earned yet</h3>
                            <p className="text-muted-foreground max-w-sm mx-auto">
                                Complete courses or attend events to start building your digital badge collection.
                            </p>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                        {badges.map((badge) => (
                            <Card key={badge.uuid} className="overflow-hidden hover:shadow-lg transition-shadow">
                                <div className="aspect-square bg-gray-50 flex items-center justify-center p-6 border-b">
                                    {badge.image_url ? (
                                        <img
                                            src={badge.image_url}
                                            alt={badge.template_name}
                                            className="w-full h-full object-contain drop-shadow-md"
                                        />
                                    ) : (
                                        <Award className="h-16 w-16 text-gray-300" />
                                    )}
                                </div>
                                <CardContent className="p-4">
                                    <h3 className="font-semibold truncate" title={badge.template_name}>
                                        {badge.template_name}
                                    </h3>
                                    <p className="text-sm text-muted-foreground truncate" title={badge.event_title || badge.course_title}>
                                        {badge.event_title || badge.course_title}
                                    </p>

                                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                                        <Calendar className="h-3 w-3" />
                                        <span>{new Date(badge.issued_at).toLocaleDateString()}</span>
                                    </div>

                                    <div className="mt-4 flex gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="flex-1"
                                            onClick={() => copyShareLink(badge.short_code)}
                                        >
                                            <Share2 className="mr-2 h-3 w-3" /> Share
                                        </Button>
                                        <a href={badge.image_url} download target="_blank" rel="noreferrer">
                                            <Button variant="outline" size="icon" className="h-8 w-8">
                                                <Download className="h-4 w-4" />
                                            </Button>
                                        </a>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
