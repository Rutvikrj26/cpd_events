import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { User, MessageSquare } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RatingDisplay } from './StarRating';
import { EventFeedback } from '@/api/feedback/types';

interface FeedbackCardProps {
    feedback: EventFeedback;
    showEventTitle?: boolean;
    eventTitle?: string;
}

export function FeedbackCard({ feedback, showEventTitle, eventTitle }: FeedbackCardProps) {
    const timeAgo = formatDistanceToNow(new Date(feedback.created_at), { addSuffix: true });

    return (
        <Card>
            <CardContent className="pt-4">
                <div className="flex items-start justify-between gap-4">
                    {/* Left: User info and ratings */}
                    <div className="flex-1 space-y-3">
                        {/* Header */}
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
                                Feedback for: <span className="font-medium">{eventTitle}</span>
                            </p>
                        )}

                        {/* Ratings Grid */}
                        <div className="grid grid-cols-3 gap-4">
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">Overall</p>
                                <RatingDisplay value={feedback.rating} size="sm" showValue={false} />
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">Content</p>
                                <RatingDisplay value={feedback.content_quality_rating} size="sm" showValue={false} />
                            </div>
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">Speaker</p>
                                <RatingDisplay value={feedback.speaker_rating} size="sm" showValue={false} />
                            </div>
                        </div>

                        {/* Comments */}
                        {feedback.comments && (
                            <div className="pt-2 border-t">
                                <div className="flex items-start gap-2">
                                    <MessageSquare className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                                    <p className="text-sm text-muted-foreground">
                                        {feedback.comments}
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right: Overall rating highlight */}
                    <div className="text-center shrink-0">
                        <div className="text-3xl font-bold text-primary">{feedback.rating}</div>
                        <div className="text-xs text-muted-foreground">/5</div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
