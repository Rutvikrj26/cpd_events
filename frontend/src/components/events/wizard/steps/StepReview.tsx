import React from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Card, CardContent } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Calendar, Clock, MapPin, Tag, Users } from 'lucide-react';
import { sanitizeHtml, hasVisibleContent } from '@/lib/sanitize';

export const StepReview = () => {
    const { formData } = useEventWizard();
    const credits = Number(formData.cpd_credit_value ?? 0);
    const creditsLabel = `${credits} ${credits === 1 ? 'Credit' : 'Credits'}`;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Review & Create</h2>
                <p className="text-sm text-muted-foreground">Please verify your event details before finalizing.</p>
            </div>

            <div className="grid gap-6">
                <Card className="bg-muted/50 border-border shadow-sm">
                    {/* Image Preview */}
                    {(formData._imageFile || formData.featured_image_url) && (
                        <div className="relative w-full h-48 sm:h-64 overflow-hidden rounded-t-lg bg-muted">
                            <img
                                src={
                                    formData._imageFile
                                        ? URL.createObjectURL(formData._imageFile)
                                        : formData.featured_image_url
                                }
                                alt="Event Cover"
                                className="w-full h-full object-cover"
                            />
                        </div>
                    )}
                    <CardContent className="p-6 space-y-6">
                        <div>
                            <h3 className="text-2xl font-bold text-foreground mb-2">{formData.title || 'Untitled Event'}</h3>
                            {hasVisibleContent(formData.description) ? (
                                <div
                                    className="text-muted-foreground prose prose-sm dark:prose-invert max-w-none"
                                    dangerouslySetInnerHTML={{ __html: sanitizeHtml(formData.description) }}
                                />
                            ) : (
                                <p className="text-muted-foreground italic">No description provided.</p>
                            )}
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                            <div className="flex items-center gap-2 text-foreground">
                                <Tag className="h-4 w-4 text-primary" />
                                <span className="capitalize">{formData.event_type}</span>
                            </div>
                            <div className="flex items-center gap-2 text-foreground">
                                <MapPin className="h-4 w-4 text-primary" />
                                <span className="capitalize">{formData.format}</span>
                            </div>
                            <div className="flex items-center gap-2 text-foreground">
                                <Calendar className="h-4 w-4 text-primary" />
                                <span>{formData.starts_at ? new Date(formData.starts_at).toLocaleString() : 'Date not set'}</span>
                            </div>
                            <div className="flex items-center gap-2 text-foreground">
                                <Clock className="h-4 w-4 text-primary" />
                                <span>{formData.duration_minutes} Minutes</span>
                            </div>
                            {formData.max_attendees && (
                                <div className="flex items-center gap-2 text-foreground">
                                    <Users className="h-4 w-4 text-primary" />
                                    <span>Max {formData.max_attendees} Attendees</span>
                                </div>
                            )}
                            <div className="flex items-center gap-2 text-foreground">
                                <Tag className="h-4 w-4 text-primary" />
                                <span>{(formData.price ?? 0) === 0 ? 'Free Event' : `${formData.price} ${formData.currency}`}</span>
                            </div>

                        </div>
                    </CardContent>
                </Card>

                {formData.is_multi_session && (formData._sessions?.length ?? 0) > 0 && (
                    <Card className="bg-muted/50 border-border shadow-sm">
                        <CardContent className="p-6">
                            <h4 className="text-base font-semibold text-foreground mb-3">
                                Sessions ({formData._sessions!.length})
                            </h4>
                            <ol className="space-y-2">
                                {[...formData._sessions!]
                                    .sort((a, b) => a.order - b.order)
                                    .map((session, idx) => {
                                        const start = session.starts_at ? new Date(session.starts_at) : null;
                                        const valid = start && !isNaN(start.getTime());
                                        const end =
                                            valid && session.duration_minutes
                                                ? new Date(start!.getTime() + session.duration_minutes * 60000)
                                                : null;
                                        return (
                                            <li
                                                key={idx}
                                                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 text-sm pb-2 border-b border-border last:border-0 last:pb-0"
                                            >
                                                <div className="flex items-center gap-2 min-w-0">
                                                    <span className="text-muted-foreground shrink-0">
                                                        {idx + 1}.
                                                    </span>
                                                    <span className="font-medium text-foreground truncate">
                                                        {session.title || 'Untitled session'}
                                                    </span>
                                                    {session.is_mandatory && (
                                                        <Badge variant="secondary" className="shrink-0">
                                                            Required
                                                        </Badge>
                                                    )}
                                                </div>
                                                <span className="text-muted-foreground sm:text-right shrink-0">
                                                    {valid
                                                        ? `${start!.toLocaleDateString(undefined, {
                                                              weekday: 'short',
                                                              month: 'short',
                                                              day: 'numeric',
                                                          })} · ${start!.toLocaleTimeString(undefined, {
                                                              hour: 'numeric',
                                                              minute: '2-digit',
                                                          })}${
                                                              end
                                                                  ? ` – ${end.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
                                                                  : ''
                                                          }`
                                                        : 'Date not set'}
                                                </span>
                                            </li>
                                        );
                                    })}
                            </ol>
                        </CardContent>
                    </Card>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm border-t pt-4">
                    <div>
                        <span className="font-semibold text-foreground block mb-1">Registration</span>
                        <span className={formData.registration_enabled ? "text-green-600 font-medium" : "text-muted-foreground"}>
                            {formData.registration_enabled ? "Enabled" : "Disabled"}
                        </span>
                    </div>
                    <div>
                        <span className="font-semibold text-foreground block mb-1">CPD Credits</span>
                        <span className={formData.cpd_enabled ? "text-green-600 font-medium" : "text-muted-foreground"}>
                            {formData.cpd_enabled ? creditsLabel : "Disabled"}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};
