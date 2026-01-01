/**
 * Create Organization Page
 *
 * Wizard for creating a new organization.
 * Supports two modes:
 * 1. Fresh creation
 * 2. Upgrade from individual organizer account (transfers data)
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Building2, ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { createOrganization, createOrgFromAccount, getLinkableDataPreview } from '@/api/organizations';
import { useAuth } from '@/contexts/AuthContext';
import { useOrganization } from '@/contexts/OrganizationContext';

interface FormData {
    name: string;
    description: string;
    website: string;
    contact_email: string;
}

const CreateOrganizationPage: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { user, hasFeature } = useAuth();
    const { refreshOrganizations } = useOrganization();

    const isFromAccount = searchParams.get('from') === 'account';

    // Redirect if user cannot create organization
    useEffect(() => {
        if (!hasFeature('can_create_organization')) {
            navigate('/organizations', { replace: true });
        }
    }, [hasFeature, navigate]);

    const [formData, setFormData] = useState<FormData>({
        name: user?.organization_name || '',
        description: '',
        website: user?.organizer_website || '',
        contact_email: user?.email || '',
    });
    const [linkableData, setLinkableData] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    // Fetch linkable data preview if upgrading
    useEffect(() => {
        if (isFromAccount) {
            getLinkableDataPreview()
                .then(setLinkableData)
                .catch(() => { });
        }
    }, [isFromAccount]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData(prev => ({
            ...prev,
            [e.target.name]: e.target.value,
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            let org;

            if (isFromAccount) {
                // Create from existing organizer account (transfers data)
                org = await createOrgFromAccount({
                    name: formData.name || undefined,
                    transfer_data: true,
                });
            } else {
                // Fresh creation
                org = await createOrganization({
                    name: formData.name,
                    description: formData.description,
                    website: formData.website,
                    contact_email: formData.contact_email,
                });
            }

            setSuccess(true);
            await refreshOrganizations();

            // Navigate to new org after short delay
            setTimeout(() => {
                navigate(`/org/${org.slug}`);
            }, 1500);

        } catch (err: any) {
            console.error('Failed to create organization:', err);
            setError(err.response?.data?.error?.message || err.message || 'Failed to create organization');
        } finally {
            setIsLoading(false);
        }
    };

    if (success) {
        return (
            <div className="container mx-auto py-16 px-4 max-w-lg text-center">
                <div className="bg-green-50 rounded-full p-4 w-16 h-16 mx-auto mb-6 flex items-center justify-center">
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                </div>
                <h1 className="text-2xl font-bold mb-2">Organization Created!</h1>
                <p className="text-muted-foreground mb-4">
                    Redirecting to your new organization dashboard...
                </p>
                <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8 px-4 max-w-lg">
            <Card>
                <CardHeader className="text-center">
                    <div className="mx-auto bg-primary/10 rounded-full p-3 w-12 h-12 flex items-center justify-center mb-2">
                        <Building2 className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-2xl">
                        {isFromAccount ? 'Upgrade to Organization' : 'Create Organization'}
                    </CardTitle>
                    <CardDescription>
                        {isFromAccount
                            ? 'Create an organization and transfer your existing events and templates.'
                            : 'Set up your organization to collaborate with team members.'}
                    </CardDescription>
                </CardHeader>

                <CardContent>
                    {/* Data Transfer Notice */}
                    {isFromAccount && linkableData && (
                        <Alert className="mb-6 bg-blue-50 border-blue-200">
                            <AlertDescription>
                                <strong className="text-blue-800">Your data will be transferred:</strong>
                                <ul className="mt-2 text-sm text-blue-700 list-disc list-inside">
                                    <li>{linkableData.events_count} event{linkableData.events_count !== 1 ? 's' : ''}</li>
                                    <li>{linkableData.templates_count} certificate template{linkableData.templates_count !== 1 ? 's' : ''}</li>
                                </ul>
                            </AlertDescription>
                        </Alert>
                    )}

                    {error && (
                        <Alert variant="destructive" className="mb-6">
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="name">Organization Name *</Label>
                            <Input
                                id="name"
                                name="name"
                                value={formData.name}
                                onChange={handleChange}
                                placeholder="Acme Training Co."
                                required
                            />
                        </div>

                        {!isFromAccount && (
                            <>
                                <div className="space-y-2">
                                    <Label htmlFor="description">Description</Label>
                                    <ReactQuill
                                        theme="snow"
                                        value={formData.description}
                                        onChange={(content) => setFormData(prev => ({ ...prev, description: content }))}
                                        placeholder="Brief description of your organization..."
                                        className="bg-white mb-4"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="website">Website</Label>
                                    <Input
                                        id="website"
                                        name="website"
                                        type="url"
                                        value={formData.website}
                                        onChange={handleChange}
                                        placeholder="https://example.com"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="contact_email">Contact Email</Label>
                                    <Input
                                        id="contact_email"
                                        name="contact_email"
                                        type="email"
                                        value={formData.contact_email}
                                        onChange={handleChange}
                                        placeholder="contact@example.com"
                                    />
                                </div>
                            </>
                        )}

                        <Button type="submit" className="w-full" disabled={isLoading || !formData.name}>
                            {isLoading ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Creating...
                                </>
                            ) : (
                                <>
                                    Create Organization
                                    <ArrowRight className="h-4 w-4 ml-2" />
                                </>
                            )}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
};

export default CreateOrganizationPage;
