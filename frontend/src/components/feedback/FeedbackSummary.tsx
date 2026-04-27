import { MessageSquare, Star, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Progress } from '@/shared/ui/progress';
import { RatingDisplay } from './StarRating';
import { FeedbackSummary as FeedbackSummaryData } from '@/api/feedback/types';

interface FeedbackSummaryProps {
    summary: FeedbackSummaryData;
}

export function FeedbackSummary({ summary }: FeedbackSummaryProps) {
    if (summary.total_count === 0) {
        return (
            <Card>
                <CardContent className="py-8 text-center">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
                    <h3 className="text-lg font-medium mb-1">No feedback yet</h3>
                    <p className="text-sm text-muted-foreground">
                        Feedback will appear here once attendees submit their reviews.
                    </p>
                </CardContent>
            </Card>
        );
    }

    const ratings = summary.per_field.filter((f) => f.field_type === 'rating');
    const primary = ratings[0];
    const distribution = primary?.distribution || {};
    const maxBucket = Math.max(
        ...[1, 2, 3, 4, 5].map((n) => distribution[String(n)] || 0),
        1,
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Star className="h-5 w-5 text-yellow-500" />
                    Feedback summary
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                <div
                    className="grid gap-4"
                    style={{
                        gridTemplateColumns: `repeat(${Math.min(ratings.length + 1, 4)}, minmax(0, 1fr))`,
                    }}
                >
                    {ratings.map((f) => (
                        <div key={f.field_uuid} className="text-center p-4 bg-muted/30 rounded-lg">
                            <div className="text-3xl font-bold text-primary">
                                {f.average ?? '—'}
                            </div>
                            <p className="text-sm text-muted-foreground">{f.field_label}</p>
                            <RatingDisplay
                                value={f.average ?? 0}
                                size="sm"
                                showValue={false}
                            />
                        </div>
                    ))}
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                        <div className="flex items-center justify-center gap-2 mb-1">
                            <Users className="h-5 w-5 text-muted-foreground" />
                            <span className="text-3xl font-bold text-primary">
                                {summary.total_count}
                            </span>
                        </div>
                        <p className="text-sm text-muted-foreground">Total responses</p>
                    </div>
                </div>

                {primary && (
                    <div className="space-y-3">
                        <h4 className="text-sm font-medium">
                            {primary.field_label} distribution
                        </h4>
                        {[5, 4, 3, 2, 1].map((rating) => {
                            const count = distribution[String(rating)] || 0;
                            const percentage =
                                primary.responses > 0 ? (count / primary.responses) * 100 : 0;
                            return (
                                <div key={rating} className="flex items-center gap-3">
                                    <div className="flex items-center gap-1 w-12 shrink-0">
                                        <span className="text-sm font-medium">{rating}</span>
                                        <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                                    </div>
                                    <div className="flex-1">
                                        <Progress
                                            value={(count / maxBucket) * 100}
                                            className="h-2"
                                        />
                                    </div>
                                    <div className="w-16 text-right">
                                        <span className="text-sm text-muted-foreground">
                                            {count} ({percentage.toFixed(0)}%)
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
