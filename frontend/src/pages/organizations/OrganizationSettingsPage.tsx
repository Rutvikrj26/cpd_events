/**
 * Organization Settings Page
 *
 * Edit organization branding, details, and manage subscription.
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Settings,
    Building2,
    Palette,
    Globe,
    Check,
    ArrowLeft,
    Loader2,
    Upload,
    CreditCard,
    AlertTriangle,
    BookOpen,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { getOrganizations, getOrganization, updateOrganization } from '@/api/organizations';
import { Organization } from '@/api/organizations/types';
import { useOrganization } from '@/contexts/OrganizationContext';
import StripeConnectSettings from '@/components/organizations/StripeConnectSettings';

interface FormData {
    name: string;
    description: string;
    website: string;
    contact_email: string;
    contact_phone: string;
    gst_hst_number: string;
    primary_color: string;
    secondary_color: string;
}

const OrganizationSettingsPage: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { isOwner, refreshOrganizations } = useOrganization();

    const [org, setOrg] = useState<Organization | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const [formData, setFormData] = useState<FormData>({
        name: '',
        description: '',
        website: '',
        contact_email: '',
        contact_phone: '',
        gst_hst_number: '',
        primary_color: '#0066CC',
        secondary_color: '#004499',
    });

    useEffect(() => {
        loadOrganization();
    }, [slug]);

    const loadOrganization = async () => {
        if (!slug) return;

        setIsLoading(true);
        try {
            const orgs = await getOrganizations();
            const found = orgs.find(o => o.slug === slug);
            if (!found) {
                setError('Organization not found');
                return;
            }

            const fullOrg = await getOrganization(found.uuid);
            setOrg(fullOrg);
            setFormData({
                name: fullOrg.name,
                description: fullOrg.description || '',
                website: fullOrg.website || '',
                contact_email: fullOrg.contact_email || '',
                contact_phone: fullOrg.contact_phone || '',
                gst_hst_number: fullOrg.gst_hst_number || '',
                primary_color: fullOrg.primary_color || '#0066CC',
                secondary_color: fullOrg.secondary_color || '#004499',
            });
        } catch (err: any) {
            setError(err.message || 'Failed to load organization');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        if (!org) return;

        setIsSaving(true);
        setError(null);
        setSuccessMessage(null);

        try {
            await updateOrganization(org.uuid, formData);
            setSuccessMessage('Settings saved successfully');
            refreshOrganizations();
            setTimeout(() => setSuccessMessage(null), 3000);
        } catch (err: any) {
            setError(err.response?.data?.error?.message || 'Failed to save settings');
        } finally {
            setIsSaving(false);
        }
    };

    const handleInputChange = (field: keyof FormData, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const canEdit = org?.user_role === 'owner' || org?.user_role === 'admin';

    if (isLoading) {
        return (
            <div className="container mx-auto py-8 px-4 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error && !org) {
        return (
            <div className="container mx-auto py-16 px-4 text-center">
                <Settings className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h2 className="text-2xl font-bold mb-2">Unable to Load Settings</h2>
                <p className="text-muted-foreground mb-4">{error}</p>
                <Button onClick={() => navigate('/organizations')}>
                    Back to Organizations
                </Button>
            </div>
        );
    }

    if (!org) return null;

    return (
        <div className="container mx-auto py-8 px-4 max-w-4xl">
            {/* Header */}
            <div className="flex items-center gap-4 mb-8">
                <Button variant="ghost" size="icon" onClick={() => navigate(`/org/${slug}`)}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold">Organization Settings</h1>
                    <p className="text-muted-foreground">{org.name}</p>
                </div>
            </div>

            {/* Status Messages */}
            {successMessage && (
                <Alert className="mb-6 border-green-200 bg-green-50 text-green-800">
                    <Check className="h-4 w-4" />
                    <AlertDescription>{successMessage}</AlertDescription>
                </Alert>
            )}

            {error && (
                <Alert variant="destructive" className="mb-6">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Settings Tabs */}
            <Tabs defaultValue="general" className="space-y-6">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="general">
                        <Building2 className="h-4 w-4 mr-2" />
                        General
                    </TabsTrigger>
                    <TabsTrigger value="branding">
                        <Palette className="h-4 w-4 mr-2" />
                        Branding
                    </TabsTrigger>
                    <TabsTrigger value="billing">
                        <CreditCard className="h-4 w-4 mr-2" />
                        Billing
                    </TabsTrigger>
                    <TabsTrigger value="payments">
                        <CreditCard className="h-4 w-4 mr-2" />
                        Payments & Payouts
                    </TabsTrigger>

                </TabsList>

                {/* General Settings */}
                <TabsContent value="general">
                    <Card>
                        <CardHeader>
                            <CardTitle>General Information</CardTitle>
                            <CardDescription>Basic details about your organization</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="name">Organization Name</Label>
                                <Input
                                    id="name"
                                    value={formData.name}
                                    onChange={(e) => handleInputChange('name', e.target.value)}
                                    disabled={!canEdit}
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="description">Description</Label>
                                <Textarea
                                    id="description"
                                    value={formData.description}
                                    onChange={(e) => handleInputChange('description', e.target.value)}
                                    disabled={!canEdit}
                                    rows={4}
                                    placeholder="Tell people about your organization..."
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="website">Website</Label>
                                    <Input
                                        id="website"
                                        type="url"
                                        value={formData.website}
                                        onChange={(e) => handleInputChange('website', e.target.value)}
                                        disabled={!canEdit}
                                        placeholder="https://"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="contact_email">Contact Email</Label>
                                    <Input
                                        id="contact_email"
                                        type="email"
                                        value={formData.contact_email}
                                        onChange={(e) => handleInputChange('contact_email', e.target.value)}
                                        disabled={!canEdit}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="contact_phone">Contact Phone</Label>
                                <Input
                                    id="contact_phone"
                                    value={formData.contact_phone}
                                    onChange={(e) => handleInputChange('contact_phone', e.target.value)}
                                    disabled={!canEdit}
                                    placeholder="+1 (555) 000-0000"
                                />
                            </div>

                            {canEdit && (
                                <div className="pt-4">
                                    <Button onClick={handleSave} disabled={isSaving}>
                                        {isSaving ? (
                                            <>
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                Saving...
                                            </>
                                        ) : (
                                            <>
                                                <Check className="h-4 w-4 mr-2" />
                                                Save Changes
                                            </>
                                        )}
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Branding Settings */}
                <TabsContent value="branding">
                    <Card>
                        <CardHeader>
                            <CardTitle>Branding</CardTitle>
                            <CardDescription>Customize your organization's appearance</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-4">
                                <Label>Logo</Label>
                                <div className="flex items-center gap-4">
                                    <div className="w-20 h-20 rounded-lg border-2 border-dashed border-muted-foreground/25 flex items-center justify-center bg-muted/50">
                                        {org.logo_url ? (
                                            <img src={org.logo_url} alt="Logo" className="w-full h-full object-contain rounded-lg" />
                                        ) : (
                                            <Building2 className="h-8 w-8 text-muted-foreground" />
                                        )}
                                    </div>
                                    {canEdit && (
                                        <Button variant="outline" disabled>
                                            <Upload className="h-4 w-4 mr-2" />
                                            Upload Logo
                                        </Button>
                                    )}
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    Recommended: 200x200px PNG or JPG
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="primary_color">Primary Color</Label>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="color"
                                            id="primary_color"
                                            value={formData.primary_color}
                                            onChange={(e) => handleInputChange('primary_color', e.target.value)}
                                            disabled={!canEdit}
                                            className="w-12 h-10 rounded border cursor-pointer"
                                        />
                                        <Input
                                            value={formData.primary_color}
                                            onChange={(e) => handleInputChange('primary_color', e.target.value)}
                                            disabled={!canEdit}
                                            className="flex-1"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="secondary_color">Secondary Color</Label>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="color"
                                            id="secondary_color"
                                            value={formData.secondary_color}
                                            onChange={(e) => handleInputChange('secondary_color', e.target.value)}
                                            disabled={!canEdit}
                                            className="w-12 h-10 rounded border cursor-pointer"
                                        />
                                        <Input
                                            value={formData.secondary_color}
                                            onChange={(e) => handleInputChange('secondary_color', e.target.value)}
                                            disabled={!canEdit}
                                            className="flex-1"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="p-4 rounded-lg border" style={{ background: `linear-gradient(135deg, ${formData.primary_color}20, ${formData.secondary_color}20)` }}>
                                <p className="text-sm font-medium mb-2">Preview</p>
                                <div className="flex gap-2">
                                    <div className="px-4 py-2 rounded text-white text-sm font-medium" style={{ backgroundColor: formData.primary_color }}>
                                        Primary Button
                                    </div>
                                    <div className="px-4 py-2 rounded text-white text-sm font-medium" style={{ backgroundColor: formData.secondary_color }}>
                                        Secondary Button
                                    </div>
                                </div>
                            </div>

                            {canEdit && (
                                <div className="pt-4">
                                    <Button onClick={handleSave} disabled={isSaving}>
                                        {isSaving ? (
                                            <>
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                Saving...
                                            </>
                                        ) : (
                                            <>
                                                <Check className="h-4 w-4 mr-2" />
                                                Save Changes
                                            </>
                                        )}
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Billing Settings */}
                <TabsContent value="billing">
                    <Card>
                        <CardHeader>
                            <CardTitle>Subscription & Billing</CardTitle>
                            <CardDescription>Manage your plan and payment methods</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="gst_hst_number">GST/HST Number</Label>
                                <Input
                                    id="gst_hst_number"
                                    value={formData.gst_hst_number}
                                    onChange={(e) => handleInputChange('gst_hst_number', e.target.value)}
                                    placeholder="Optional (for your records)"
                                    disabled={!canEdit}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Taxes on ticket sales are calculated by the platform. This is for your records.
                                </p>
                            </div>

                            {org.subscription && (
                                <>
                                    <div className="flex items-center justify-between p-4 rounded-lg border bg-accent/50">
                                        <div>
                                            <p className="text-sm text-muted-foreground">Current Plan</p>
                                            <p className="text-2xl font-bold capitalize">{org.subscription.plan}</p>
                                        </div>
                                        <Badge variant={org.subscription.status === 'active' ? 'default' : 'destructive'} className="capitalize">
                                            {org.subscription.status}
                                        </Badge>
                                    </div>

                                    <div className="grid grid-cols-3 gap-4">
                                        <div className="p-4 rounded-lg border text-center">
                                            <p className="text-sm text-muted-foreground">Seats Used</p>
                                            <p className="text-xl font-bold">
                                                {org.subscription.active_organizer_seats} / {org.subscription.total_seats}
                                            </p>
                                            <p className="text-xl font-bold">{org.subscription.events_created_this_period || 0}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <BookOpen className="h-4 w-4 text-muted-foreground" />
                                        <div>
                                            <p className="text-sm font-medium leading-none">Courses</p>
                                            <p className="text-muted-foreground text-xs">Cycles monthly</p>
                                            <p className="text-xl font-bold">{org.subscription.courses_created_this_period || 0}</p>
                                        </div>
                                    </div>

                                    {org.user_role === 'owner' && (
                                        <div className="flex gap-4">
                                            <Button variant="outline" disabled>
                                                <CreditCard className="h-4 w-4 mr-2" />
                                                Manage Payment Methods
                                            </Button>
                                            <Button disabled>
                                                Upgrade Plan
                                            </Button>
                                        </div>
                                    )}

                                    <p className="text-sm text-muted-foreground">
                                        Billing integration coming soon. Contact support to change your plan.
                                    </p>
                                </>
                            )}

                            {canEdit && (
                                <div className="pt-4">
                                    <Button onClick={handleSave} disabled={isSaving}>
                                        {isSaving ? (
                                            <>
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                Saving...
                                            </>
                                        ) : (
                                            <>
                                                <Check className="h-4 w-4 mr-2" />
                                                Save Changes
                                            </>
                                        )}
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Payments & Payouts (Stripe Connect) */}
                <TabsContent value="payments">
                    <StripeConnectSettings
                        organization={org}
                        onUpdate={() => {
                            loadOrganization();
                            refreshOrganizations();
                        }}
                    />
                </TabsContent>

            </Tabs>
        </div>
    );
};

export default OrganizationSettingsPage;
