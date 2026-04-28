import React, { useEffect, useState } from 'react';
import { Loader2, Send, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Textarea } from '@/shared/ui/textarea';
import { Checkbox } from '@/shared/ui/checkbox';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { RadioGroup, RadioGroupItem } from '@/shared/ui/radio-group';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/shared/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { StarRating } from './StarRating';
import { createFeedback, getFeedbackFields, updateFeedback } from '@/api/feedback';
import {
    EventFeedback,
    EventFeedbackCreateRequest,
    FeedbackField,
} from '@/api/feedback/types';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/api/client';

interface FeedbackFormProps {
    eventUuid: string;
    registrationUuid: string;
    eventTitle: string;
    sessionUuid?: string | null;
    existingFeedback?: EventFeedback | null;
    onSuccess?: (feedback: EventFeedback) => void;
    onCancel?: () => void;
    compact?: boolean;
}

function responsesFromFeedback(fb: EventFeedback | null | undefined): Record<string, unknown> {
    if (!fb) return {};
    const out: Record<string, unknown> = {};
    for (const r of fb.field_responses || []) {
        out[r.field_uuid] = r.value;
    }
    return out;
}

export function FeedbackForm({
    eventUuid,
    registrationUuid,
    eventTitle,
    sessionUuid,
    existingFeedback,
    onSuccess,
    onCancel,
    compact = false,
}: FeedbackFormProps) {
    const [fields, setFields] = useState<FeedbackField[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [responses, setResponses] = useState<Record<string, unknown>>(
        responsesFromFeedback(existingFeedback),
    );
    const [isAnonymous, setIsAnonymous] = useState(existingFeedback?.is_anonymous ?? false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        let cancelled = false;
        getFeedbackFields(eventUuid)
            .then((data) => {
                if (cancelled) return;
                setFields(data);
                setLoadError(null);
            })
            .catch((err) => {
                if (cancelled) return;
                console.error(err);
                // Render inline inside the modal — the API wrapper passes
                // `silent: true` so the global toast doesn't fire. We
                // intentionally DON'T raise a toast here either: showing
                // both is the bug we're fixing. The empty/error state below
                // gives the user the same information without doubling up.
                setLoadError(getApiErrorMessage(err));
            })
            .finally(() => !cancelled && setLoading(false));
        return () => {
            cancelled = true;
        };
    }, [eventUuid]);

    const isEditing = !!existingFeedback;

    const missingRequired = fields
        .filter((f) => f.required)
        .filter((f) => {
            const v = responses[f.uuid];
            if (v === undefined || v === null || v === '') return true;
            if (Array.isArray(v) && v.length === 0) return true;
            if (f.field_type === 'rating' && Number(v) <= 0) return true;
            return false;
        })
        .map((f) => f.label);

    const isValid = missingRequired.length === 0;

    const setResponse = (uuid: string, value: unknown) =>
        setResponses((prev) => ({ ...prev, [uuid]: value }));

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!isValid) {
            toast.error(`Please fill required fields: ${missingRequired.join(', ')}`);
            return;
        }
        setIsSubmitting(true);
        try {
            let feedback: EventFeedback;
            if (isEditing && existingFeedback) {
                feedback = await updateFeedback(existingFeedback.uuid, {
                    is_anonymous: isAnonymous,
                    responses,
                });
                toast.success('Feedback updated');
            } else {
                const payload: EventFeedbackCreateRequest = {
                    event: eventUuid,
                    registration: registrationUuid,
                    is_anonymous: isAnonymous,
                    responses,
                };
                if (sessionUuid) payload.session = sessionUuid;
                feedback = await createFeedback(payload);
                toast.success('Thank you for your feedback!');
            }
            onSuccess?.(feedback);
        } catch {
            // handled by api client
        } finally {
            setIsSubmitting(false);
        }
    };

    const renderField = (field: FeedbackField) => {
        const value = responses[field.uuid];
        switch (field.field_type) {
            case 'rating':
                return (
                    <StarRating
                        value={typeof value === 'number' ? value : 0}
                        onChange={(v) => setResponse(field.uuid, v)}
                        size="lg"
                        showLabel
                    />
                );
            case 'text':
                return (
                    <Input
                        value={(value as string) ?? ''}
                        onChange={(e) => setResponse(field.uuid, e.target.value)}
                        placeholder={field.placeholder}
                    />
                );
            case 'textarea':
                return (
                    <Textarea
                        rows={4}
                        value={(value as string) ?? ''}
                        onChange={(e) => setResponse(field.uuid, e.target.value)}
                        placeholder={field.placeholder}
                    />
                );
            case 'number':
                return (
                    <Input
                        type="number"
                        min={field.min_value ?? undefined}
                        max={field.max_value ?? undefined}
                        value={value === undefined || value === null ? '' : String(value)}
                        onChange={(e) =>
                            setResponse(
                                field.uuid,
                                e.target.value === '' ? '' : Number(e.target.value),
                            )
                        }
                        placeholder={field.placeholder}
                    />
                );
            case 'date':
                return (
                    <Input
                        type="date"
                        value={(value as string) ?? ''}
                        onChange={(e) => setResponse(field.uuid, e.target.value)}
                    />
                );
            case 'select':
                return (
                    <Select
                        value={(value as string) ?? ''}
                        onValueChange={(v) => setResponse(field.uuid, v)}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder={field.placeholder || 'Select…'} />
                        </SelectTrigger>
                        <SelectContent>
                            {(field.options ?? []).map((o) => (
                                <SelectItem key={o} value={o}>
                                    {o}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                );
            case 'multiselect': {
                const current = Array.isArray(value) ? (value as string[]) : [];
                return (
                    <div className="space-y-2">
                        {(field.options ?? []).map((o) => {
                            const checked = current.includes(o);
                            return (
                                <div key={o} className="flex items-center space-x-2">
                                    <Checkbox
                                        id={`${field.uuid}-${o}`}
                                        checked={checked}
                                        onCheckedChange={(next) =>
                                            setResponse(
                                                field.uuid,
                                                next
                                                    ? [...current, o]
                                                    : current.filter((v) => v !== o),
                                            )
                                        }
                                    />
                                    <Label
                                        htmlFor={`${field.uuid}-${o}`}
                                        className="cursor-pointer font-normal"
                                    >
                                        {o}
                                    </Label>
                                </div>
                            );
                        })}
                    </div>
                );
            }
            case 'radio':
                return (
                    <RadioGroup
                        value={(value as string) ?? ''}
                        onValueChange={(v) => setResponse(field.uuid, v)}
                    >
                        {(field.options ?? []).map((o) => (
                            <div key={o} className="flex items-center space-x-2">
                                <RadioGroupItem id={`${field.uuid}-${o}`} value={o} />
                                <Label
                                    htmlFor={`${field.uuid}-${o}`}
                                    className="cursor-pointer font-normal"
                                >
                                    {o}
                                </Label>
                            </div>
                        ))}
                    </RadioGroup>
                );
            case 'checkbox':
                return (
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id={field.uuid}
                            checked={!!value}
                            onCheckedChange={(c) => setResponse(field.uuid, !!c)}
                        />
                        <Label htmlFor={field.uuid} className="cursor-pointer font-normal">
                            Yes
                        </Label>
                    </div>
                );
            default:
                return null;
        }
    };

    const content = (
        <form onSubmit={handleSubmit} className="space-y-6">
            {loading ? (
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading…
                </div>
            ) : loadError ? (
                <p className="text-sm text-destructive py-4">
                    Could not load the feedback form. {loadError}
                </p>
            ) : fields.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">
                    This event has no feedback form configured.
                </p>
            ) : (
                fields.map((field) => (
                    <div key={field.uuid} className="space-y-2">
                        <Label className="text-base font-medium">
                            {field.label}
                            {field.required && <span className="text-destructive ml-1">*</span>}
                        </Label>
                        {field.help_text && (
                            <p className="text-sm text-muted-foreground">{field.help_text}</p>
                        )}
                        {renderField(field)}
                    </div>
                ))
            )}

            {!loading && fields.length > 0 && (
                <div className="flex items-start gap-3 p-4 bg-muted/30 rounded-lg border">
                    <Checkbox
                        id="anonymous"
                        checked={isAnonymous}
                        onCheckedChange={(checked) => setIsAnonymous(checked === true)}
                    />
                    <div className="space-y-1">
                        <Label htmlFor="anonymous" className="flex items-center gap-2 cursor-pointer">
                            {isAnonymous ? (
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
            )}

            {!loading && fields.length > 0 && (
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
                                {isEditing ? 'Updating…' : 'Submitting…'}
                            </>
                        ) : (
                            <>
                                <Send className="mr-2 h-4 w-4" />
                                {isEditing ? 'Update feedback' : 'Submit feedback'}
                            </>
                        )}
                    </Button>
                </div>
            )}
        </form>
    );

    if (compact) return content;

    return (
        <Card className="w-full max-w-xl">
            <CardHeader>
                <CardTitle>Share your feedback</CardTitle>
                <CardDescription>
                    Help us improve by rating your experience at "{eventTitle}"
                </CardDescription>
            </CardHeader>
            <CardContent>{content}</CardContent>
        </Card>
    );
}
