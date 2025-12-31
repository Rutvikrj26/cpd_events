import React, { useEffect, useState } from 'react';
import { Video, AlertTriangle, ExternalLink, Loader2 } from 'lucide-react';
import { useEventWizard } from '../EventWizardContext';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { getAvailableCertificateTemplates, CertificateTemplate } from '@/api/certificates';
import { useOrganization } from '@/contexts/OrganizationContext';
import { useAuth } from '@/contexts/AuthContext';
import { getPayoutsStatus, PayoutsStatus } from '@/api/payouts';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';

export const StepSettings = () => {
    const { formData, updateFormData } = useEventWizard();
    const { currentOrg } = useOrganization();
    const { user } = useAuth();
    const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
    const [loadingTemplates, setLoadingTemplates] = useState(false);

    // Payouts state for individual organizers
    const [userPayoutsEnabled, setUserPayoutsEnabled] = useState(false);
    const [loadingUserPayouts, setLoadingUserPayouts] = useState(true);

    // Check if Stripe is connected (org OR individual user)
    const orgStripeConnected = currentOrg?.stripe_charges_enabled || false;
    const stripeConnected = orgStripeConnected || userPayoutsEnabled;
    const isPaidEvent = !formData.is_free;

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

    // Fetch individual user payouts status if not using an org
    useEffect(() => {
        const fetchUserPayouts = async () => {
            // Only fetch if user is an organizer and not using an org with stripe enabled
            if (user?.account_type !== 'organizer' || orgStripeConnected) {
                setLoadingUserPayouts(false);
                return;
            }
            try {
                const status = await getPayoutsStatus();
                setUserPayoutsEnabled(status.charges_enabled);
            } catch (error) {
                console.error('Failed to fetch user payouts status', error);
            } finally {
                setLoadingUserPayouts(false);
            }
        };
        fetchUserPayouts();
    }, [user?.account_type, orgStripeConnected]);

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


            {/* Payment Settings */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                        <Label className="text-base">Paid Event</Label>
                        <p className="text-sm text-muted-foreground">Charge attendees to register for this event.</p>
                    </div>
                    <Switch
                        checked={!formData.is_free}
                        onCheckedChange={(checked) => updateFormData({ is_free: !checked })}
                    />
                </div>

                {!formData.is_free && (
                    <div className="pl-6 border-l-2 border-slate-100 ml-2 space-y-4">
                        {/* Stripe Connect Warning */}
                        {loadingUserPayouts ? (
                            <div className="flex items-center gap-2 text-muted-foreground text-sm">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Checking payouts setup...
                            </div>
                        ) : !stripeConnected && (
                            <Alert variant="destructive" className="border-amber-300 bg-amber-50 text-amber-800">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertDescription className="flex items-center justify-between">
                                    <span>
                                        {currentOrg
                                            ? 'Connect your organization\'s Stripe account to accept payments.'
                                            : 'Link your bank account to accept payments for this event.'}
                                    </span>
                                    <Link to={currentOrg ? `/organizations/${currentOrg.slug}/settings` : '/settings?tab=payouts'}>
                                        <Button size="sm" variant="outline" className="ml-4">
                                            <ExternalLink className="h-3 w-3 mr-1" />
                                            {currentOrg ? 'Setup Stripe' : 'Link Payouts'}
                                        </Button>
                                    </Link>
                                </AlertDescription>
                            </Alert>
                        )}

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

            {/* Zoom Settings - Only shown for online/hybrid events */}
            {
                (formData.format === 'online' || formData.format === 'hybrid') && (
                    <>
                        <Separator />

                        <div className="space-y-4">
                            <div className="space-y-2 p-4 bg-blue-50/50 rounded-lg border border-blue-100">
                                <Label className="flex items-center gap-2">
                                    <Video className="h-4 w-4 text-blue-600" />
                                    Online Meeting
                                </Label>
                                <p className="text-sm text-muted-foreground">
                                    {formData.zoom_settings?.enabled
                                        ? "A Zoom meeting will be created automatically when you publish the event."
                                        : "Enable Zoom integration below, or manually add meeting details after creating the event."
                                    }
                                </p>
                            </div>

                            <div className="flex items-center justify-between">
                                <div className="space-y-0.5">
                                    <Label className="text-base">Zoom Integration</Label>
                                    <p className="text-sm text-muted-foreground">Automatically create a Zoom meeting for this event.</p>
                                </div>
                                <Switch
                                    checked={!!formData.zoom_settings?.enabled}
                                    onCheckedChange={(checked) => updateFormData({ zoom_settings: { ...formData.zoom_settings, enabled: checked } })}
                                />
                            </div>

                            {formData.zoom_settings?.enabled && (
                                <div className="pl-6 border-l-2 border-slate-100 ml-2">
                                    <p className="text-sm text-muted-foreground">
                                        A Zoom meeting will be created when you publish this event. Make sure you have connected your Zoom account in Settings → Integrations.
                                    </p>
                                </div>
                            )}
                        </div>
                    </>
                )
            }

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
