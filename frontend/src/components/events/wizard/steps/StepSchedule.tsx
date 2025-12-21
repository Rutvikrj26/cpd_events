import React, { useEffect, useState } from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Clock } from 'lucide-react';

export const StepSchedule = () => {
    const { formData, updateFormData } = useEventWizard();

    // Local state for end time to facilitate duration calculation
    const [endTime, setEndTime] = useState<string>('');

    // Initialize end time if starts_at and duration exist
    useEffect(() => {
        if (formData.starts_at && formData.duration_minutes && !endTime) {
            const start = new Date(formData.starts_at);
            const end = new Date(start.getTime() + formData.duration_minutes * 60000);
            // Format to datetime-local string: YYYY-MM-DDThh:mm
            const formatted = end.toISOString().slice(0, 16);
            setEndTime(formatted);
        }
    }, []);

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
            const diffMs = end.getTime() - start.getTime();
            const minutes = Math.round(diffMs / 60000);
            if (minutes > 0) {
                updateFormData({ duration_minutes: minutes });
            }
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-slate-900">Schedule</h2>
                <p className="text-sm text-slate-500">When will your event take place?</p>
            </div>

            <div className="grid gap-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <Label>Start Date & Time</Label>
                        <Input
                            type="datetime-local"
                            value={formData.starts_at || ''}
                            onChange={(e) => handleStartChange(e.target.value)}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label>End Date & Time</Label>
                        <Input
                            type="datetime-local"
                            value={endTime}
                            onChange={(e) => handleEndChange(e.target.value)}
                        />
                    </div>
                </div>

                <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                        <Clock className="h-5 w-5" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-slate-900">Duration</p>
                        <p className="text-2xl font-bold text-slate-900">
                            {formData.duration_minutes ? `${Math.floor(formData.duration_minutes / 60)}h ${formData.duration_minutes % 60}m` : '--'}
                        </p>
                    </div>
                    <div className="ml-auto">
                        <div className="space-y-1 text-right">
                            <Label className="text-xs text-slate-500">Timezone</Label>
                            <div className="font-medium">{formData.timezone}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
