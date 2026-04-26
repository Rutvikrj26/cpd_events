import { Award, Calendar, Download, Loader2, Share2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/shared/ui/button';
import { Card, CardContent } from '@/shared/ui/card';
import { EmptyState } from '@/shared/ui/empty-state';
import { useMyBadges } from '@/features/badges';
import type { IssuedBadge } from '@/api/badges/types';

export function MyBadgesPage() {
    const { data: badges = [], isLoading, isError } = useMyBadges();

    if (isLoading) {
        return (
            <div className="flex min-h-[50vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    if (isError) {
        toast.error('Failed to load badges');
    }

    return (
        <div className="space-y-card">
            <header>
                <h1 className="text-h1 text-foreground">My badges</h1>
                <p className="text-body text-muted-foreground">
                    Digital badges you've earned from events and courses.
                </p>
            </header>

            {badges.length === 0 ? (
                <EmptyState
                    tone="dashed"
                    icon={Award}
                    title="No badges earned yet"
                    description="Complete courses or attend events to start building your digital badge collection."
                />
            ) : (
                <div className="grid grid-cols-1 gap-card sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                    {badges.map((badge) => (
                        <BadgeCard key={badge.uuid} badge={badge} />
                    ))}
                </div>
            )}
        </div>
    );
}

function BadgeCard({ badge }: { badge: IssuedBadge }) {
    const copyShareLink = () => {
        const url = `${window.location.origin}/badges/verify/${badge.short_code}`;
        navigator.clipboard.writeText(url);
        toast.success('Verification link copied!');
    };

    return (
        <Card elevation="interactive" className="overflow-hidden">
            <div className="flex aspect-square items-center justify-center border-b bg-muted/40 p-card">
                {badge.image_url ? (
                    <img
                        src={badge.image_url}
                        alt={badge.template_name}
                        className="h-full w-full object-contain drop-shadow-md"
                    />
                ) : (
                    <Award className="h-16 w-16 text-muted-foreground/40" />
                )}
            </div>
            <CardContent className="space-y-1 p-card">
                <h3 className="truncate text-h3 text-foreground" title={badge.template_name}>
                    {badge.template_name}
                </h3>
                <p
                    className="truncate text-caption text-muted-foreground"
                    title={badge.event_title || badge.course_title}
                >
                    {badge.event_title || badge.course_title}
                </p>
                <div className="flex items-center gap-1 text-caption text-muted-foreground/80">
                    <Calendar className="h-3 w-3" />
                    {new Date(badge.issued_at).toLocaleDateString()}
                </div>

                <div className="mt-card flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={copyShareLink}
                    >
                        <Share2 className="mr-2 h-3 w-3" /> Share
                    </Button>
                    {badge.image_url && (
                        <a href={badge.image_url} download target="_blank" rel="noreferrer">
                            <Button variant="outline" size="icon" className="h-8 w-8">
                                <Download className="h-4 w-4" />
                            </Button>
                        </a>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
