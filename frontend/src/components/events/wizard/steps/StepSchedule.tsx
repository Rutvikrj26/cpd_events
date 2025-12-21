import React, { useEffect, useState } from 'react';
import { useEventWizard } from '../EventWizardContext';
import { DateTimePicker } from '@/components/ui/date-time-picker';
import { Clock } from 'lucide-react';
import { Label } from '@/components/ui/label';

export const StepSchedule = () => {
    const { formData, updateFormData } = useEventWizard();

    // Local state for end time to facilitate duration calculation
    const [endTime, setEndTime] = useState<string>('');

    // Initialize end time if starts_at and duration exist
    useEffect(() => {
        if (formData.starts_at && formData.duration_minutes) {
            // Handle backend ISO format (YYYY-MM-DDTHH:MM:SSZ) -> Input format (YYYY-MM-DDTHH:MM)
            // DateTimePicker handles formatting for display, but for calculation we need standard Date objects
            const startStr = formData.starts_at;
            const start = new Date(startStr);

            if (!isNaN(start.getTime())) {
                const end = new Date(start.getTime() + formData.duration_minutes * 60000);

                // For endTime local state, we should match what DateTimePicker expects or produces
                // Our DateTimePicker accepts ISO strings.
                // We'll store ISO string in endTime state.
                setEndTime(end.toISOString());
            }
        }
    }, [formData.starts_at, formData.duration_minutes]);

    const handleStartChange = (value: string) => {
        updateFormData({ starts_at: value });
        recalcDuration(value, endTime);
    };

    const handleEndChange = (value: string) => {
        setEndTime(value);
        recalcDuration(formData.starts_at, value);
    };

    const recalcDuration = (startStr?: string, endStr?: string) => {
        if (startStr && endStr) {
            const start = new Date(startStr);
            const end = new Date(endStr);

            if (!isNaN(start.getTime()) && !isNaN(end.getTime())) {
                const diffMs = end.getTime() - start.getTime();
                const minutes = Math.round(diffMs / 60000);
                if (minutes > 0) {
                    updateFormData({ duration_minutes: minutes });
                }
            }
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Schedule</h2>
                <p className="text-sm text-muted-foreground">When will your event take place?</p>
            </div>

            <div className="grid gap-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <DateTimePicker
                            label="Start Date & Time"
                            value={formData.starts_at}
                            onDateTimeChange={handleStartChange}
                        />
                    </div>
                    <div className="space-y-2">
                        <DateTimePicker
                            label="End Date & Time"
                            value={endTime}
                            onDateTimeChange={handleEndChange}
                        />
                    </div>
                </div>

                <div className="flex items-center gap-4 p-4 bg-muted/30 rounded-lg border border-border">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                        <Clock className="h-5 w-5" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-foreground">Duration</p>
                        <p className="text-2xl font-bold text-foreground">
                            {formData.duration_minutes ? `${Math.floor(formData.duration_minutes / 60)}h ${formData.duration_minutes % 60}m` : '--'}
                        </p>
                        {(formData.duration_minutes || 0) < 15 && (
                            <p className="text-xs text-red-500 mt-1">Minimum 15 mins required</p>
                        )}
                    </div>
                    <div className="ml-auto">
                        <div className="space-y-1 text-right">
                            <Label className="text-xs text-muted-foreground">Timezone</Label>
                            <div className="font-medium">{formData.timezone}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
