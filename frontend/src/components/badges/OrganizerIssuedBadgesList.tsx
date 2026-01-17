import React, { useState, useEffect } from "react";
import { format } from "date-fns";
import {
    Search,
    Award,
    Loader2,
    Calendar,
    User,
    CheckCircle,
    XCircle,
    Download
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { getIssuedBadgesByMe } from "@/api/badges";
import { IssuedBadge } from "@/api/badges/types";

export function OrganizerIssuedBadgesList() {
    const [badges, setBadges] = useState<IssuedBadge[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");

    useEffect(() => {
        fetchBadges();
    }, []);

    async function fetchBadges() {
        try {
            const response = await getIssuedBadgesByMe();
            setBadges(response.results);
        } catch (error) {
            toast.error("Failed to load issued badges");
        } finally {
            setLoading(false);
        }
    }

    const filteredBadges = badges.filter(badge =>
        (badge.recipient_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (badge.template_name || '').toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="relative w-full max-w-sm">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search by recipient or badge name..."
                        className="pl-8"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                {/* Future: Add Bulk Issue Button here */}
                {/* <Button variant="outline">Bulk Issue</Button> */}
            </div>

            {badges.length === 0 ? (
                <Card>
                    <CardContent className="py-16 text-center">
                        <div className="h-16 w-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                            <Award className="h-8 w-8 text-gray-400" />
                        </div>
                        <h3 className="text-lg font-medium text-foreground mb-2">No badges issued yet</h3>
                        <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
                            You haven't issued any badges to attendees yet.
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <div className="border rounded-md">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Recipient</TableHead>
                                <TableHead>Badge</TableHead>
                                <TableHead>Event/Course</TableHead>
                                <TableHead>Issued Date</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {filteredBadges.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center">
                                        No results found.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredBadges.map((badge) => (
                                    <TableRow key={badge.uuid}>
                                        <TableCell className="font-medium">
                                            <div className="flex items-center gap-2">
                                                <User className="h-4 w-4 text-muted-foreground" />
                                                {badge.recipient_name}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <Award className="h-4 w-4 text-purple-500" />
                                                {badge.template_name}
                                            </div>
                                        </TableCell>
                                        <TableCell>{badge.event_title || badge.course_title || 'N/A'}</TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2 text-muted-foreground">
                                                <Calendar className="h-3 w-3" />
                                                {format(new Date(badge.issued_at), 'MMM d, yyyy')}
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={badge.status === 'active' ? 'default' : 'destructive'} className="capitalize">
                                                {badge.status}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {badge.image_url && (
                                                <Button variant="ghost" size="sm" asChild>
                                                    <a href={badge.image_url} target="_blank" rel="noreferrer" download>
                                                        <Download className="h-4 w-4" />
                                                    </a>
                                                </Button>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </div>
            )}
        </div>
    );
}
