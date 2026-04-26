import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, User } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RatingDisplay } from './StarRating';
import { EventFeedback, FeedbackFieldResponse } from '@/api/feedback/types';

interface FeedbackCardProps {
    feedback: EventFeedback;
    showEventTitle?: boolean;
    eventTitle?: string;
}

function formatValue(r: FeedbackFieldResponse): string {
    const v = r.value;
    if (v === null || v === undefined || v === '') return '';
    if (Array.isArray(v)) return v.join(', ');
    if (typeof v === 'boolean') return v ? 'Yes' : 'No';
    return String(v);
}

export function FeedbackCard({ feedback, showEventTitle, eventTitle }: FeedbackCardProps) {
    const timeAgo = formatDistanceToNow(new Date(feedback.created_at), { addSuffix: true });
    const responses = [...(feedback.field_responses ?? [])].sort(
        (a, b) => a.field_order - b.field_order,
    );
    const ratings = responses.filter((r) => r.field_type === 'rating');
    const nonRatings = responses.filter((r) => r.field_type !== 'rating');
    const headline = ratings.length > 0 ? Number(ratings[0].value ?? 0) : null;

    return (
        <Card>
            <CardContent className="pt-4">
                <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-3">
                        <div className="flex items-center gap-2">
                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <User className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="font-medium text-sm">
                                        {feedback.attendee_name}
                                    </span>
                                    {feedback.is_anonymous && (
                                        <Badge variant="secondary" className="text-xs">
                                            Anonymous
                                        </Badge>
                                    )}
                                </div>
                                <span className="text-xs text-muted-foreground">{timeAgo}</span>
                            </div>
                        </div>

                        {showEventTitle && eventTitle && (
                            <p className="text-sm text-muted-foreground">
                                Feedback for:{' '}
                                <span className="font-medium">{eventTitle}</span>
                            </p>
                        )}

                        {ratings.length > 0 && (
                            <div
                                className="grid gap-4"
                                style={{
                                    gridTemplateColumns: `repeat(${Math.min(ratings.length, 3)}, minmax(0, 1fr))`,
                                }}
                            >
                                {ratings.map((r) => (
                                    <div key={r.uuid}>
                                        <p className="text-xs text-muted-foreground mb-1">
                                            {r.field_label}
                                        </p>
                                        <RatingDisplay
                                            value={Number(r.value ?? 0) || 0}
                                            size="sm"
                                            showValue={false}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}

                        {nonRatings.length > 0 && (
                            <div className="pt-2 border-t space-y-2">
                                {nonRatings.map((r) => {
                                    const formatted = formatValue(r);
                                    if (!formatted) return null;
                                    return (
                                        <div key={r.uuid} className="flex items-start gap-2">
                                            <MessageSquare className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                                            <div>
                                                <p className="text-xs text-muted-foreground">
                                                    {r.field_label}
                                                </p>
                                                <p className="text-sm text-muted-foreground">
                                                    {formatted}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {headline !== null && (
                        <div className="text-center shrink-0">
                            <div className="text-3xl font-bold text-primary">{headline}</div>
                            <div className="text-xs text-muted-foreground">/5</div>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
