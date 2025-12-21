import React from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

export const StepDetails = () => {
    const { formData, updateFormData } = useEventWizard();

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Event Details</h2>
                <p className="text-sm text-muted-foreground">Provide a comprehensive description for your attendees.</p>
            </div>

            <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                    placeholder="What will attendees learn? Who are the speakers?"
                    className="min-h-[200px] text-base"
                    value={formData.description || ''}
                    onChange={(e) => updateFormData({ description: e.target.value })}
                />
            </div>

            <div className="space-y-2">
                <Label>Cover Image</Label>
                <div className="border-2 border-dashed border-border rounded-lg p-8 text-center bg-muted/30/50 hover:bg-muted/30 transition-colors cursor-not-allowed opacity-60">
                    <p className="text-sm text-muted-foreground">Drag and drop or click to upload</p>
                    <p className="text-xs text-slate-400 mt-1">(Image upload coming soon)</p>
                </div>
            </div>
        </div>
    );
};
