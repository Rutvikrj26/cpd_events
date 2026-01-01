import React, { useState } from 'react';
import { Loader2, Send, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StarRating } from './StarRating';
import { createFeedback, updateFeedback } from '@/api/feedback';
import { EventFeedback, EventFeedbackCreateRequest } from '@/api/feedback/types';
import { toast } from 'sonner';

interface FeedbackFormProps {
    eventUuid: string;
    registrationUuid: string;
    eventTitle: string;
    existingFeedback?: EventFeedback | null;
    onSuccess?: (feedback: EventFeedback) => void;
    onCancel?: () => void;
    compact?: boolean;
}

interface FormData {
    rating: number;
    content_quality_rating: number;
    speaker_rating: number;
    comments: string;
    is_anonymous: boolean;
}

export function FeedbackForm({
    eventUuid,
    registrationUuid,
    eventTitle,
    existingFeedback,
    onSuccess,
    onCancel,
    compact = false
}: FeedbackFormProps) {
    const [formData, setFormData] = useState<FormData>({
        rating: existingFeedback?.rating || 0,
        content_quality_rating: existingFeedback?.content_quality_rating || 0,
        speaker_rating: existingFeedback?.speaker_rating || 0,
        comments: existingFeedback?.comments || '',
        is_anonymous: existingFeedback?.is_anonymous || false
    });
    const [isSubmitting, setIsSubmitting] = useState(false);

    const isValid = formData.rating > 0 &&
        formData.content_quality_rating > 0 &&
        formData.speaker_rating > 0;

    const isEditing = !!existingFeedback;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!isValid) {
            toast.error('Please provide all ratings');
            return;
        }

        setIsSubmitting(true);

        try {
            let feedback: EventFeedback;

            if (isEditing && existingFeedback) {
                feedback = await updateFeedback(existingFeedback.uuid, {
                    rating: formData.rating,
                    content_quality_rating: formData.content_quality_rating,
                    speaker_rating: formData.speaker_rating,
                    comments: formData.comments || undefined,
                    is_anonymous: formData.is_anonymous
                });
                toast.success('Feedback updated successfully!');
            } else {
                const request: EventFeedbackCreateRequest = {
                    event: eventUuid,
                    registration: registrationUuid,
                    rating: formData.rating,
                    content_quality_rating: formData.content_quality_rating,
                    speaker_rating: formData.speaker_rating,
                    comments: formData.comments || undefined,
                    is_anonymous: formData.is_anonymous
                };
                feedback = await createFeedback(request);
                toast.success('Thank you for your feedback!');
            }

            onSuccess?.(feedback);
        } catch (error) {
            // Error is already handled by the API client
        } finally {
            setIsSubmitting(false);
        }
    };

    const content = (
        <form onSubmit={handleSubmit} className="space-y-6">
            {/* Overall Rating */}
            <div className="space-y-2">
                <Label className="text-base font-medium">
                    Overall Experience <span className="text-destructive">*</span>
                </Label>
                <p className="text-sm text-muted-foreground">
                    How would you rate this event overall?
                </p>
                <StarRating
                    value={formData.rating}
                    onChange={(value) => setFormData(prev => ({ ...prev, rating: value }))}
                    size="lg"
                    showLabel
                />
            </div>

            {/* Content Quality Rating */}
            <div className="space-y-2">
                <Label className="text-base font-medium">
                    Content Quality <span className="text-destructive">*</span>
                </Label>
                <p className="text-sm text-muted-foreground">
                    How relevant and valuable was the content?
                </p>
                <StarRating
                    value={formData.content_quality_rating}
                    onChange={(value) => setFormData(prev => ({ ...prev, content_quality_rating: value }))}
                    size="lg"
                    showLabel
                />
            </div>

            {/* Speaker Rating */}
            <div className="space-y-2">
                <Label className="text-base font-medium">
                    Speaker Effectiveness <span className="text-destructive">*</span>
                </Label>
                <p className="text-sm text-muted-foreground">
                    How effective was the speaker/presenter?
                </p>
                <StarRating
                    value={formData.speaker_rating}
                    onChange={(value) => setFormData(prev => ({ ...prev, speaker_rating: value }))}
                    size="lg"
                    showLabel
                />
            </div>

            {/* Comments */}
            <div className="space-y-2">
                <Label htmlFor="comments" className="text-base font-medium">
                    Additional Comments
                </Label>
                <p className="text-sm text-muted-foreground">
                    Share any suggestions or feedback to help improve future events
                </p>
                <Textarea
                    id="comments"
                    value={formData.comments}
                    onChange={(e) => setFormData(prev => ({ ...prev, comments: e.target.value }))}
                    placeholder="What did you like? What could be improved?"
                    rows={4}
                    className="resize-none"
                />
            </div>

            {/* Anonymous Toggle */}
            <div className="flex items-start gap-3 p-4 bg-muted/30 rounded-lg border">
                <Checkbox
                    id="anonymous"
                    checked={formData.is_anonymous}
                    onCheckedChange={(checked) =>
                        setFormData(prev => ({ ...prev, is_anonymous: checked === true }))
                    }
                />
                <div className="space-y-1">
                    <Label htmlFor="anonymous" className="flex items-center gap-2 cursor-pointer">
                        {formData.is_anonymous ? (
                            <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                            <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                        Submit anonymously
                    </Label>
                    <p className="text-xs text-muted-foreground">
                        Your name will be hidden from the event organizer
                    </p>
                </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
                {onCancel && (
                    <Button type="button" variant="outline" onClick={onCancel}>
                        Cancel
                    </Button>
                )}
                <Button
                    type="submit"
                    disabled={!isValid || isSubmitting}
                    className="flex-1"
                >
                    {isSubmitting ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            {isEditing ? 'Updating...' : 'Submitting...'}
                        </>
                    ) : (
                        <>
                            <Send className="mr-2 h-4 w-4" />
                            {isEditing ? 'Update Feedback' : 'Submit Feedback'}
                        </>
                    )}
                </Button>
            </div>
        </form>
    );

    if (compact) {
        return content;
    }

    return (
        <Card className="w-full max-w-xl">
            <CardHeader>
                <CardTitle>Share Your Feedback</CardTitle>
                <CardDescription>
                    Help us improve by rating your experience at "{eventTitle}"
                </CardDescription>
            </CardHeader>
            <CardContent>
                {content}
            </CardContent>
        </Card>
    );
}
