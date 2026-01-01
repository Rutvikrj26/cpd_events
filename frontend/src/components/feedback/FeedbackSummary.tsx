import React from 'react';
import { Star, MessageSquare, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { RatingDisplay } from './StarRating';

interface FeedbackSummaryProps {
    summary: {
        total_count: number;
        average_rating: number;
        average_content_quality: number;
        average_speaker_rating: number;
        rating_distribution: {
            1: number;
            2: number;
            3: number;
            4: number;
            5: number;
        };
    };
}

export function FeedbackSummary({ summary }: FeedbackSummaryProps) {
    const maxDistribution = Math.max(...Object.values(summary.rating_distribution), 1);

    if (summary.total_count === 0) {
        return (
            <Card>
                <CardContent className="py-8 text-center">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/40 mb-3" />
                    <h3 className="text-lg font-medium mb-1">No Feedback Yet</h3>
                    <p className="text-sm text-muted-foreground">
                        Feedback will appear here once attendees submit their reviews.
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Star className="h-5 w-5 text-yellow-500" />
                    Feedback Summary
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Overall Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                        <div className="text-3xl font-bold text-primary">
                            {summary.average_rating}
                        </div>
                        <p className="text-sm text-muted-foreground">Overall Rating</p>
                        <RatingDisplay value={summary.average_rating} size="sm" showValue={false} />
                    </div>
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                        <div className="text-3xl font-bold text-primary">
                            {summary.average_content_quality}
                        </div>
                        <p className="text-sm text-muted-foreground">Content Quality</p>
                        <RatingDisplay value={summary.average_content_quality} size="sm" showValue={false} />
                    </div>
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                        <div className="text-3xl font-bold text-primary">
                            {summary.average_speaker_rating}
                        </div>
                        <p className="text-sm text-muted-foreground">Speaker Rating</p>
                        <RatingDisplay value={summary.average_speaker_rating} size="sm" showValue={false} />
                    </div>
                    <div className="text-center p-4 bg-muted/30 rounded-lg">
                        <div className="flex items-center justify-center gap-2 mb-1">
                            <Users className="h-5 w-5 text-muted-foreground" />
                            <span className="text-3xl font-bold text-primary">
                                {summary.total_count}
                            </span>
                        </div>
                        <p className="text-sm text-muted-foreground">Total Responses</p>
                    </div>
                </div>

                {/* Rating Distribution */}
                <div className="space-y-3">
                    <h4 className="text-sm font-medium">Rating Distribution</h4>
                    {[5, 4, 3, 2, 1].map((rating) => {
                        const count = summary.rating_distribution[rating as keyof typeof summary.rating_distribution];
                        const percentage = summary.total_count > 0
                            ? (count / summary.total_count) * 100
                            : 0;

                        return (
                            <div key={rating} className="flex items-center gap-3">
                                <div className="flex items-center gap-1 w-12 shrink-0">
                                    <span className="text-sm font-medium">{rating}</span>
                                    <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                                </div>
                                <div className="flex-1">
                                    <Progress
                                        value={(count / maxDistribution) * 100}
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
            </CardContent>
        </Card>
    );
}
