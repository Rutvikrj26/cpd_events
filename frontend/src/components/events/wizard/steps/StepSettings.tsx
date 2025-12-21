import React from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';

export const StepSettings = () => {
    const { formData, updateFormData } = useEventWizard();

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-slate-900">Event Configuration</h2>
                <p className="text-sm text-slate-500">Fine-tune your event settings.</p>
            </div>

            {/* Registration Settings */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Registration</Label>
                        <p className="text-sm text-muted-foreground">Enable attendees to register for this event.</p>
                    </div>
                    <Switch
                        checked={formData.registration_enabled}
                        onCheckedChange={(checked) => updateFormData({ registration_enabled: checked })}
                    />
                </div>

                {formData.registration_enabled && (
                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                        <div className="space-y-2">
                            <Label>Max Attendees</Label>
                            <Input
                                type="number"
                                className="max-w-[200px]"
                                placeholder="Unlimited"
                                value={formData.max_attendees || ''}
                                onChange={(e) => updateFormData({ max_attendees: e.target.value ? parseInt(e.target.value) : undefined })}
                            />
                            <p className="text-xs text-muted-foreground">Leave blank for unlimited capacity.</p>
                        </div>
                    </div>
                )}
            </div>

            <Separator />

            {/* CPD Settings */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">CPD / CME Credits</Label>
                        <p className="text-sm text-muted-foreground">Award credits to attendees upon completion.</p>
                    </div>
                    <Switch
                        checked={formData.cpd_enabled}
                        onCheckedChange={(checked) => updateFormData({ cpd_enabled: checked })}
                    />
                </div>

                {formData.cpd_enabled && (
                    <div className="pl-6 border-l-2 border-slate-100 ml-2 grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Credit Value</Label>
                            <Input
                                type="number"
                                value={formData.cpd_credit_value || ''}
                                onChange={(e) => updateFormData({ cpd_credit_value: parseFloat(e.target.value) })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Credit Type</Label>
                            <Input
                                placeholder="e.g. Clinical, Ethics"
                                value={formData.cpd_credit_type || ''}
                                onChange={(e) => updateFormData({ cpd_credit_type: e.target.value })}
                            />
                        </div>
                    </div>
                )}
            </div>

            <Separator />

            {/* Zoom Settings - Placeholder for now as integration is backend-heavy */}
            <div className="space-y-4 opacity-75">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Zoom Integration</Label>
                        <p className="text-sm text-muted-foreground">Automatically create a Zoom meeting.</p>
                    </div>
                    <Switch
                        checked={!!formData.zoom_settings?.enabled}
                        onCheckedChange={(checked) => updateFormData({ zoom_settings: { ...formData.zoom_settings, enabled: checked } })}
                    />
                </div>
            </div>
        </div>
    );
};
