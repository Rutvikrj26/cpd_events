import React, { useEffect, useState } from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getCertificateTemplates, CertificateTemplate } from '@/api/certificates';
import { toast } from 'sonner';

export const StepSettings = () => {
    const { formData, updateFormData } = useEventWizard();
    const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
    const [loadingTemplates, setLoadingTemplates] = useState(false);

    useEffect(() => {
        const fetchTemplates = async () => {
            if (formData.certificates_enabled) {
                setLoadingTemplates(true);
                try {
                    const data = await getCertificateTemplates();
                    setTemplates(data);
                } catch (error) {
                    console.error("Failed to fetch templates", error);
                    toast.error("Failed to load certificate templates.");
                } finally {
                    setLoadingTemplates(false);
                }
            }
        };

        fetchTemplates();
    }, [formData.certificates_enabled]);

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Event Configuration</h2>
                <p className="text-sm text-muted-foreground">Fine-tune your event settings.</p>
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

            {/* Certificate Settings */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Certificates</Label>
                        <p className="text-sm text-muted-foreground">Issue certificates to verified attendees.</p>
                    </div>
                    <Switch
                        checked={formData.certificates_enabled}
                        onCheckedChange={(checked) => updateFormData({ certificates_enabled: checked })}
                    />
                </div>

                {formData.certificates_enabled && (
                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                        <div className="space-y-2">
                            <Label>Certificate Template</Label>
                            <Select
                                value={formData.certificate_template || ''}
                                onValueChange={(value) => updateFormData({ certificate_template: value === 'none' ? null : value })}
                            >
                                <SelectTrigger className="w-full max-w-sm">
                                    <SelectValue placeholder={loadingTemplates ? "Loading templates..." : "Select a template"} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">None</SelectItem>
                                    {templates.map((tpl) => (
                                        <SelectItem key={tpl.uuid} value={tpl.uuid}>
                                            {tpl.name}
                                        </SelectItem>
                                    ))}
                                    {templates.length === 0 && !loadingTemplates && (
                                        <div className="p-2 text-sm text-muted-foreground">No templates found. Create one first.</div>
                                    )}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">The PDF template used for generating certificates.</p>
                        </div>

                        <div className="flex items-center justify-between max-w-sm">
                            <div className="space-y-0.5">
                                <Label className="text-sm">Auto-issue</Label>
                                <p className="text-xs text-muted-foreground">Issue automatically when event completes.</p>
                            </div>
                            <Switch
                                checked={formData.auto_issue_certificates}
                                onCheckedChange={(checked) => updateFormData({ auto_issue_certificates: checked })}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4 pt-2 max-w-sm">
                            <div className="space-y-2">
                                <Label className="text-sm">Min. Attendance (Minutes)</Label>
                                <Input
                                    type="number"
                                    min="0"
                                    value={formData.minimum_attendance_minutes ?? 0}
                                    onChange={(e) => updateFormData({ minimum_attendance_minutes: parseInt(e.target.value) || 0 })}
                                />
                                <p className="text-xs text-muted-foreground">0 for no minimum.</p>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm">Min. Attendance (%)</Label>
                                <Input
                                    type="number"
                                    min="0"
                                    max="100"
                                    value={formData.minimum_attendance_percent ?? 80}
                                    onChange={(e) => updateFormData({ minimum_attendance_percent: parseInt(e.target.value) || 0 })}
                                />
                                <p className="text-xs text-muted-foreground">Usually 80%.</p>
                            </div>
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
