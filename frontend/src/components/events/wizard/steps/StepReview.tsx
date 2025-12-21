import React from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Card, CardContent } from '@/components/ui/card';
import { Calendar, Clock, MapPin, Tag, Users } from 'lucide-react';

export const StepReview = () => {
    const { formData } = useEventWizard();

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Review & Create</h2>
                <p className="text-sm text-muted-foreground">Please verify your event details before finalizing.</p>
            </div>

            <div className="grid gap-6">
                <Card className="bg-muted/30/50 border-border shadow-sm">
                    {/* Image Preview */}
                    {(formData._imageFile || formData.featured_image_url) && (
                        <div className="relative w-full h-48 sm:h-64 overflow-hidden rounded-t-lg bg-slate-100">
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
                            <p className="text-slate-600 whitespace-pre-wrap">{formData.description || 'No description provided.'}</p>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                            <div className="flex items-center gap-2 text-slate-700">
                                <Tag className="h-4 w-4 text-primary" />
                                <span className="capitalize">{formData.event_type}</span>
                            </div>
                            <div className="flex items-center gap-2 text-slate-700">
                                <MapPin className="h-4 w-4 text-primary" />
                                <span className="capitalize">{formData.format}</span>
                            </div>
                            <div className="flex items-center gap-2 text-slate-700">
                                <Calendar className="h-4 w-4 text-primary" />
                                <span>{formData.starts_at ? new Date(formData.starts_at).toLocaleString() : 'Date not set'}</span>
                            </div>
                            <div className="flex items-center gap-2 text-slate-700">
                                <Clock className="h-4 w-4 text-primary" />
                                <span>{formData.duration_minutes} Minutes</span>
                            </div>
                            {formData.max_attendees && (
                                <div className="flex items-center gap-2 text-slate-700">
                                    <Users className="h-4 w-4 text-primary" />
                                    <span>Max {formData.max_attendees} Attendees</span>
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

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
                            {formData.cpd_enabled ? `${formData.cpd_credit_value} Credits` : "Disabled"}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};
