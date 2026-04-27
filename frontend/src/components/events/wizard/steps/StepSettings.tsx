import React, { useEffect, useState } from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Label } from '@/shared/ui/label';
import { Input } from '@/shared/ui/input';
import { Switch } from '@/shared/ui/switch';
import { Separator } from '@/shared/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select';
import { getAvailableCertificateTemplates, CertificateTemplate } from '@/api/certificates';
import { getBadgeTemplates, BadgeTemplate } from '@/api/badges';
import { toast } from 'sonner';

export const StepSettings = () => {
    const { formData, updateFormData } = useEventWizard();
    const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
    const [badgeTemplates, setBadgeTemplates] = useState<BadgeTemplate[]>([]);
    const [loadingTemplates, setLoadingTemplates] = useState(false);
    const [loadingBadgeTemplates, setLoadingBadgeTemplates] = useState(false);

    // Note: payouts/Stripe Connect UI was removed in the single-tenant
    // migration — money for paid events goes directly to the institution's
    // single Stripe account; organizers don't need to connect their own.

    const attendanceMinutes = formData.minimum_attendance_minutes ?? 0;
    const durationMinutes = formData.duration_minutes ?? 0;
    const derivedAttendancePercent = durationMinutes
        ? Math.round((attendanceMinutes / durationMinutes) * 100)
        : null;

    useEffect(() => {
        const fetchTemplates = async () => {
            if (formData.certificates_enabled) {
                setLoadingTemplates(true);
                try {
                    const response = await getAvailableCertificateTemplates();
                    setTemplates(response.templates);
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

    // Fetch badge templates when badges are enabled
    useEffect(() => {
        const fetchBadgeTemplates = async () => {
            if (formData.badges_enabled) {
                setLoadingBadgeTemplates(true);
                try {
                    const response = await getBadgeTemplates();
                    setBadgeTemplates(response.results);
                } catch (error) {
                    console.error("Failed to fetch badge templates", error);
                    toast.error("Failed to load badge templates.");
                } finally {
                    setLoadingBadgeTemplates(false);
                }
            }
        };

        fetchBadgeTemplates();
    }, [formData.badges_enabled]);

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
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="registration_opens_at">Registration opens</Label>
                                <Input
                                    id="registration_opens_at"
                                    type="datetime-local"
                                    value={formData.registration_opens_at ?? ''}
                                    onChange={(e) =>
                                        updateFormData({
                                            registration_opens_at: e.target.value || undefined,
                                        })
                                    }
                                />
                                <p className="text-xs text-muted-foreground">
                                    Leave blank to open registration immediately.
                                </p>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="registration_closes_at">Registration closes</Label>
                                <Input
                                    id="registration_closes_at"
                                    type="datetime-local"
                                    value={formData.registration_closes_at ?? ''}
                                    onChange={(e) =>
                                        updateFormData({
                                            registration_closes_at: e.target.value || undefined,
                                        })
                                    }
                                />
                                <p className="text-xs text-muted-foreground">
                                    Leave blank to allow registration until the event starts.
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <Separator />


            {/* Payment Settings */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Paid Event</Label>
                        <p className="text-sm text-muted-foreground">Charge attendees to register for this event.</p>
                    </div>
                    <Switch
                        checked={!formData.is_free}
                        onCheckedChange={(checked) => {
                            updateFormData({
                                is_free: !checked,
                                // Force price to 0 when toggled to free to ensure backend persistence
                                ...(!checked ? { price: 0 } : {})
                            });
                        }}
                    />
                </div>

                {!formData.is_free && (
                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                        <div className="grid grid-cols-2 gap-4 max-w-sm">
                            <div className="space-y-2">
                                <Label>Price</Label>
                                <div className="relative">
                                    <span className="absolute left-3 top-2.5 text-muted-foreground">$</span>
                                    <Input
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        className="pl-7"
                                        value={formData.price || ''}
                                        onChange={(e) => updateFormData({ price: parseFloat(e.target.value) || 0 })}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label>Currency</Label>
                                <Select
                                    value={formData.currency || 'USD'}
                                    onValueChange={(value) => updateFormData({ currency: value })}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select currency" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="USD">USD ($)</SelectItem>
                                        <SelectItem value="EUR">EUR (€)</SelectItem>
                                        <SelectItem value="GBP">GBP (£)</SelectItem>
                                        <SelectItem value="CAD">CAD ($)</SelectItem>
                                        <SelectItem value="AUD">AUD ($)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
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
                                            {tpl.is_org_template && ` (${tpl.organization_name || 'Shared'})`}
                                        </SelectItem>
                                    ))}
                                    {templates.length === 0 && !loadingTemplates && (
                                        <div className="p-2 text-sm text-muted-foreground">No templates found. Create one first.</div>
                                    )}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">The PDF template used for generating certificates.</p>
                            {formData.certificates_enabled && !formData.certificate_template && (
                                <p className="text-xs text-red-600">Select a template to enable certificates.</p>
                            )}
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
                                    value={attendanceMinutes}
                                    onChange={(e) => updateFormData({ minimum_attendance_minutes: parseInt(e.target.value) || 0 })}
                                />
                                <p className="text-xs text-muted-foreground">0 for no minimum.</p>
                            </div>
                            <div className="space-y-2">
                                <Label className="text-sm">Min. Attendance (%)</Label>
                                <div className="h-10 px-3 flex items-center rounded-md border bg-muted text-sm text-muted-foreground">
                                    {attendanceMinutes === 0
                                        ? 'No minimum'
                                        : durationMinutes
                                            ? `${derivedAttendancePercent}% of event duration`
                                            : 'Set a duration to calculate'}
                                </div>
                                <p className="text-xs text-muted-foreground">Calculated from minutes and duration.</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <Separator />

            {/* Badge Settings */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Badges</Label>
                        <p className="text-sm text-muted-foreground">Issue digital badges to verified attendees.</p>
                    </div>
                    <Switch
                        checked={formData.badges_enabled}
                        onCheckedChange={(checked) => updateFormData({ badges_enabled: checked })}
                    />
                </div>

                {formData.badges_enabled && (
                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                        <div className="space-y-2">
                            <Label>Badge Template</Label>
                            <Select
                                value={formData.badge_template || ''}
                                onValueChange={(value) => updateFormData({ badge_template: value === 'none' ? null : value })}
                            >
                                <SelectTrigger className="w-full max-w-sm">
                                    <SelectValue placeholder={loadingBadgeTemplates ? "Loading templates..." : "Select a template"} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">None</SelectItem>
                                    {badgeTemplates.map((tpl) => (
                                        <SelectItem key={tpl.uuid} value={tpl.uuid}>
                                            {tpl.name}
                                        </SelectItem>
                                    ))}
                                    {badgeTemplates.length === 0 && !loadingBadgeTemplates && (
                                        <div className="p-2 text-sm text-muted-foreground">No badge templates found. Create one first.</div>
                                    )}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">The image template used for generating badges.</p>
                            {formData.badges_enabled && !formData.badge_template && (
                                <p className="text-xs text-amber-600">Select a template to enable badge issuance.</p>
                            )}
                        </div>

                        <div className="flex items-center justify-between max-w-sm">
                            <div className="space-y-0.5">
                                <Label className="text-sm">Auto-issue</Label>
                                <p className="text-xs text-muted-foreground">Issue automatically when event completes.</p>
                            </div>
                            <Switch
                                checked={formData.auto_issue_badges}
                                onCheckedChange={(checked) => updateFormData({ auto_issue_badges: checked })}
                            />
                        </div>
                    </div>
                )}
            </div>

            <Separator />

            {/* Video Conferencing */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Video Conferencing</Label>
                        <p className="text-sm text-muted-foreground">
                            Provision a LiveKit room so attendees can join online. Required for online / hybrid events if you want the in-app join button.
                        </p>
                    </div>
                    <Switch
                        checked={!!formData.video_settings?.enabled}
                        onCheckedChange={(checked) =>
                            updateFormData({
                                video_settings: {
                                    enabled: checked,
                                    recording_enabled: checked ? (formData.video_settings?.recording_enabled ?? false) : false,
                                    screen_share: formData.video_settings?.screen_share ?? true,
                                },
                            })
                        }
                    />
                </div>

                {formData.video_settings?.enabled && (
                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                        <div className="flex items-center justify-between max-w-sm">
                            <div className="space-y-0.5">
                                <Label className="text-sm">Record this event</Label>
                                <p className="text-xs text-muted-foreground">
                                    Start a LiveKit room-composite egress when the event goes live. The MP4 appears on the event page after completion.
                                </p>
                            </div>
                            <Switch
                                checked={!!formData.video_settings?.recording_enabled}
                                onCheckedChange={(checked) =>
                                    updateFormData({
                                        video_settings: {
                                            ...formData.video_settings,
                                            enabled: true,
                                            recording_enabled: checked,
                                            screen_share: formData.video_settings?.screen_share ?? true,
                                        },
                                    })
                                }
                            />
                        </div>

                        {formData.video_settings?.recording_enabled && (
                            <div className="flex items-center justify-between max-w-sm pl-4 border-l-2 border-slate-100 ml-2">
                                <div className="space-y-0.5">
                                    <Label className="text-sm">Auto-publish recording</Label>
                                    <p className="text-xs text-muted-foreground">
                                        When off, the recording stays unpublished after processing — visible only to you until you publish it from the event page.
                                    </p>
                                </div>
                                <Switch
                                    checked={formData.video_settings?.auto_publish_recording !== false}
                                    onCheckedChange={(checked) =>
                                        updateFormData({
                                            video_settings: {
                                                ...formData.video_settings,
                                                enabled: true,
                                                recording_enabled: true,
                                                auto_publish_recording: checked,
                                            },
                                        })
                                    }
                                />
                            </div>
                        )}

                        <div className="flex items-center justify-between max-w-sm">
                            <div className="space-y-0.5">
                                <Label className="text-sm">Allow screen share</Label>
                                <p className="text-xs text-muted-foreground">Participants can share their screen during the session.</p>
                            </div>
                            <Switch
                                checked={formData.video_settings?.screen_share !== false}
                                onCheckedChange={(checked) =>
                                    updateFormData({
                                        video_settings: {
                                            ...formData.video_settings,
                                            enabled: true,
                                            screen_share: checked,
                                        },
                                    })
                                }
                            />
                        </div>

                        <div className="flex items-center justify-between max-w-sm">
                            <div className="space-y-0.5">
                                <Label className="text-sm">Waiting room</Label>
                                <p className="text-xs text-muted-foreground">
                                    Hold attendees until the host admits them. The host can admit or deny from the room controls.
                                </p>
                            </div>
                            <Switch
                                checked={!!formData.video_settings?.waiting_room_enabled}
                                onCheckedChange={(checked) =>
                                    updateFormData({
                                        video_settings: {
                                            ...formData.video_settings,
                                            enabled: true,
                                            waiting_room_enabled: checked,
                                        },
                                    })
                                }
                            />
                        </div>
                    </div>
                )}
            </div>

            <Separator />

            {/* Event Visibility */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Public Event</Label>
                        <p className="text-sm text-muted-foreground">Show this event in the public events catalog.</p>
                    </div>
                    <Switch
                        checked={formData.is_public !== false}
                        onCheckedChange={(checked) => updateFormData({ is_public: checked })}
                    />
                </div>

                {formData.is_public === false && (
                    <div className="pl-6 border-l-2 border-amber-200 ml-2 bg-amber-50/50 p-3 rounded-r-md">
                        <p className="text-sm text-amber-800">
                            Private events are not listed publicly. Attendees can only register via direct link.
                        </p>
                    </div>
                )}
            </div>
        </div >
    );
};
