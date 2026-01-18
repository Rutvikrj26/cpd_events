/**
 * Organization Onboarding Wizard
 *
 * Multi-step onboarding wizard for organizations.
 * Guides admins through initial setup after creating an organization.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
    getOrganizationBySlug,
    updateOrganization,
    inviteMember,
    completeOrganizationOnboarding,
} from '@/api/organizations';
import type { Organization } from '@/api/organizations/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import {
    Rocket,
    Building2,
    CreditCard,
    Users,
    CheckCircle,
    ArrowRight,
    ArrowLeft,
    Loader2,
    ExternalLink,
    SkipForward,
} from 'lucide-react';

interface Step {
    id: string;
    title: string;
    icon: React.ElementType;
    optional?: boolean;
}

const STEPS: Step[] = [
    { id: 'welcome', title: 'Welcome', icon: Rocket },
    { id: 'profile', title: 'Profile', icon: Building2 },
    { id: 'billing', title: 'Billing', icon: CreditCard, optional: true },
    { id: 'team', title: 'Team', icon: Users, optional: true },
    { id: 'complete', title: 'Complete', icon: CheckCircle },
];

export function OrganizationOnboardingWizard() {
    const navigate = useNavigate();
    const { slug } = useParams<{ slug: string }>();
    const [searchParams, setSearchParams] = useSearchParams();

    const [org, setOrg] = useState<Organization | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const [currentStep, setCurrentStep] = useState(() => {
        const stepParam = searchParams.get('step');
        return stepParam ? parseInt(stepParam, 10) : 0;
    });

    // Profile form state
    const [profileData, setProfileData] = useState({
        name: '',
        description: '',
        website: '',
        primary_color: '#3b82f6',
    });

    // Team invite state
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState<'organizer' | 'course_manager' | 'instructor'>('organizer');
    const [invitedEmails, setInvitedEmails] = useState<string[]>([]);

    const progress = ((currentStep + 1) / STEPS.length) * 100;

    // Load organization data
    useEffect(() => {
        if (!slug) return;

        const loadOrg = async () => {
            try {
                const data = await getOrganizationBySlug(slug);

                // If already completed onboarding, redirect to dashboard
                if (data.onboarding_completed) {
                    navigate(`/org/${slug}`, { replace: true });
                    return;
                }

                // Check if user is admin
                if (data.user_role !== 'admin') {
                    toast.error('Only admins can complete onboarding');
                    navigate(`/org/${slug}`, { replace: true });
                    return;
                }

                setOrg(data);
                setProfileData({
                    name: data.name || '',
                    description: data.description || '',
                    website: data.website || '',
                    primary_color: data.primary_color || '#3b82f6',
                });
            } catch (error) {
                console.error('Failed to load organization', error);
                toast.error('Failed to load organization');
                navigate('/organizations', { replace: true });
            } finally {
                setLoading(false);
            }
        };

        loadOrg();
    }, [slug, navigate]);

    // Update URL params when step changes
    useEffect(() => {
        setSearchParams({ step: currentStep.toString() }, { replace: true });
    }, [currentStep, setSearchParams]);

    const nextStep = () => {
        if (currentStep < STEPS.length - 1) {
            setCurrentStep((prev) => prev + 1);
        }
    };

    const prevStep = () => {
        if (currentStep > 0) {
            setCurrentStep((prev) => prev - 1);
        }
    };

    const handleProfileSave = async () => {
        if (!org) return;
        setSaving(true);
        try {
            const updated = await updateOrganization(org.uuid, profileData);
            setOrg(updated);
            toast.success('Profile saved!');
            nextStep();
        } catch (error) {
            console.error('Failed to save profile', error);
            toast.error('Failed to save profile');
        } finally {
            setSaving(false);
        }
    };

    const handleInvite = async () => {
        if (!org || !inviteEmail.trim()) return;
        setSaving(true);
        try {
            await inviteMember(org.uuid, {
                email: inviteEmail.trim(),
                role: inviteRole,
                billing_payer: inviteRole === 'organizer' ? 'organization' : undefined,
            });
            setInvitedEmails((prev) => [...prev, inviteEmail.trim()]);
            setInviteEmail('');
            toast.success(`Invitation sent to ${inviteEmail}`);
        } catch (error: any) {
            console.error('Failed to invite member', error);
            toast.error(error?.response?.data?.detail || 'Failed to send invitation');
        } finally {
            setSaving(false);
        }
    };

    const handleComplete = async () => {
        if (!org) return;
        setSaving(true);
        try {
            await completeOrganizationOnboarding(org.uuid);
            toast.success('Onboarding complete! Welcome to your organization.');
            navigate(`/org/${slug}`, { replace: true });
        } catch (error) {
            console.error('Failed to complete onboarding', error);
            toast.error('Failed to complete onboarding');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-background to-muted flex items-center justify-center">
                <Card className="w-full max-w-2xl mx-4">
                    <CardHeader>
                        <Skeleton className="h-8 w-64" />
                        <Skeleton className="h-4 w-96 mt-2" />
                    </CardHeader>
                    <CardContent>
                        <Skeleton className="h-64 w-full" />
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!org) {
        return null;
    }

    const stepId = STEPS[currentStep]?.id;
    const isOptionalStep = STEPS[currentStep]?.optional;

    return (
        <div className="min-h-screen bg-gradient-to-br from-background to-muted py-8 px-4">
            <div className="max-w-2xl mx-auto">
                {/* Progress */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-muted-foreground">
                            Step {currentStep + 1} of {STEPS.length}
                        </span>
                        <span className="text-sm font-medium">{STEPS[currentStep]?.title}</span>
                    </div>
                    <Progress value={progress} className="h-2" />

                    {/* Step indicators */}
                    <div className="flex justify-between mt-4">
                        {STEPS.map((step, index) => {
                            const Icon = step.icon;
                            const isComplete = index < currentStep;
                            const isCurrent = index === currentStep;

                            return (
                                <div
                                    key={step.id}
                                    className={`flex flex-col items-center gap-1 ${isCurrent
                                            ? 'text-primary'
                                            : isComplete
                                                ? 'text-primary/70'
                                                : 'text-muted-foreground'
                                        }`}
                                >
                                    <div
                                        className={`w-8 h-8 rounded-full flex items-center justify-center ${isCurrent
                                                ? 'bg-primary text-primary-foreground'
                                                : isComplete
                                                    ? 'bg-primary/20 text-primary'
                                                    : 'bg-muted'
                                            }`}
                                    >
                                        {isComplete ? (
                                            <CheckCircle className="h-4 w-4" />
                                        ) : (
                                            <Icon className="h-4 w-4" />
                                        )}
                                    </div>
                                    <span className="text-xs hidden sm:block">{step.title}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Step Content */}
                <Card className="shadow-lg">
                    {/* Step 0: Welcome */}
                    {stepId === 'welcome' && (
                        <>
                            <CardHeader className="text-center">
                                <div className="mx-auto mb-4 w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                                    <Rocket className="h-8 w-8 text-primary" />
                                </div>
                                <CardTitle className="text-2xl">Welcome to {org.name}!</CardTitle>
                                <CardDescription className="text-base">
                                    Let's get your organization set up. This will only take a few minutes.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {org.subscription?.is_trialing && (
                                    <div className="p-4 bg-warning-subtle rounded-lg border border-warning">
                                        <div className="flex items-center gap-2 text-warning">
                                            <Badge variant="outline" className="border-warning text-warning-muted">
                                                Trial Active
                                            </Badge>
                                            <span className="text-sm">
                                                {org.subscription.days_until_trial_ends} days remaining
                                            </span>
                                        </div>
                                        <p className="text-sm text-warning mt-2">
                                            Explore all features during your trial. No credit card required.
                                        </p>
                                    </div>
                                )}

                                <div className="space-y-4">
                                    <h3 className="font-semibold">What you'll set up:</h3>
                                    <ul className="space-y-2 text-sm text-muted-foreground">
                                        <li className="flex items-center gap-2">
                                            <Building2 className="h-4 w-4 text-primary" />
                                            Organization profile and branding
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <CreditCard className="h-4 w-4 text-primary" />
                                            Billing preferences (optional)
                                        </li>
                                        <li className="flex items-center gap-2">
                                            <Users className="h-4 w-4 text-primary" />
                                            Invite team members (optional)
                                        </li>
                                    </ul>
                                </div>

                                <Button onClick={nextStep} className="w-full" size="lg">
                                    Get Started
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                            </CardContent>
                        </>
                    )}

                    {/* Step 1: Profile */}
                    {stepId === 'profile' && (
                        <>
                            <CardHeader>
                                <CardTitle>Organization Profile</CardTitle>
                                <CardDescription>
                                    Update your organization's public-facing information.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="name">Organization Name</Label>
                                    <Input
                                        id="name"
                                        value={profileData.name}
                                        onChange={(e) =>
                                            setProfileData((prev) => ({ ...prev, name: e.target.value }))
                                        }
                                        placeholder="Your Organization"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="description">Description</Label>
                                    <Textarea
                                        id="description"
                                        value={profileData.description}
                                        onChange={(e) =>
                                            setProfileData((prev) => ({ ...prev, description: e.target.value }))
                                        }
                                        placeholder="Tell people about your organization..."
                                        rows={3}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="website">Website</Label>
                                    <Input
                                        id="website"
                                        type="url"
                                        value={profileData.website}
                                        onChange={(e) =>
                                            setProfileData((prev) => ({ ...prev, website: e.target.value }))
                                        }
                                        placeholder="https://yourorg.com"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="primary_color">Brand Color</Label>
                                    <div className="flex gap-2">
                                        <Input
                                            id="primary_color"
                                            type="color"
                                            value={profileData.primary_color}
                                            onChange={(e) =>
                                                setProfileData((prev) => ({
                                                    ...prev,
                                                    primary_color: e.target.value,
                                                }))
                                            }
                                            className="w-16 h-10 p-1 cursor-pointer"
                                        />
                                        <Input
                                            value={profileData.primary_color}
                                            onChange={(e) =>
                                                setProfileData((prev) => ({
                                                    ...prev,
                                                    primary_color: e.target.value,
                                                }))
                                            }
                                            placeholder="#3b82f6"
                                            className="flex-1"
                                        />
                                    </div>
                                </div>

                                <div className="flex gap-2 pt-4">
                                    <Button variant="outline" onClick={prevStep} disabled={saving}>
                                        <ArrowLeft className="mr-2 h-4 w-4" />
                                        Back
                                    </Button>
                                    <Button onClick={handleProfileSave} disabled={saving} className="flex-1">
                                        {saving ? (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <ArrowRight className="mr-2 h-4 w-4" />
                                        )}
                                        Save & Continue
                                    </Button>
                                </div>
                            </CardContent>
                        </>
                    )}

                    {/* Step 2: Billing */}
                    {stepId === 'billing' && (
                        <>
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <CardTitle>Billing Setup</CardTitle>
                                    <Badge variant="secondary">Optional</Badge>
                                </div>
                                <CardDescription>
                                    Set up billing now or skip and do it later from your settings.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {org.subscription?.is_trialing && (
                                    <div className="p-4 bg-info-subtle rounded-lg border border-info">
                                        <p className="text-sm text-info">
                                            You're on a free trial. You can add payment details now or after your
                                            trial ends.
                                        </p>
                                    </div>
                                )}

                                <div className="space-y-4">
                                    <Button
                                        variant="outline"
                                        className="w-full justify-between"
                                        onClick={() => window.open(`/org/${slug}/billing`, '_blank')}
                                    >
                                        <span>Manage Billing</span>
                                        <ExternalLink className="h-4 w-4" />
                                    </Button>
                                </div>

                                <div className="flex gap-2 pt-4">
                                    <Button variant="outline" onClick={prevStep} disabled={saving}>
                                        <ArrowLeft className="mr-2 h-4 w-4" />
                                        Back
                                    </Button>
                                    <Button variant="ghost" onClick={nextStep} disabled={saving}>
                                        <SkipForward className="mr-2 h-4 w-4" />
                                        Skip for Now
                                    </Button>
                                    <Button onClick={nextStep} disabled={saving}>
                                        Continue
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Button>
                                </div>
                            </CardContent>
                        </>
                    )}

                    {/* Step 3: Team */}
                    {stepId === 'team' && (
                        <>
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <CardTitle>Invite Your Team</CardTitle>
                                    <Badge variant="secondary">Optional</Badge>
                                </div>
                                <CardDescription>
                                    Invite team members to help manage your organization.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {invitedEmails.length > 0 && (
                                    <div className="space-y-2">
                                        <Label className="text-muted-foreground">Invitations sent:</Label>
                                        <div className="flex flex-wrap gap-2">
                                            {invitedEmails.map((email) => (
                                                <Badge key={email} variant="outline">
                                                    {email}
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <div className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="inviteEmail">Email Address</Label>
                                        <Input
                                            id="inviteEmail"
                                            type="email"
                                            value={inviteEmail}
                                            onChange={(e) => setInviteEmail(e.target.value)}
                                            placeholder="colleague@example.com"
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label>Role</Label>
                                        <div className="grid grid-cols-3 gap-2">
                                            {(['organizer', 'course_manager', 'instructor'] as const).map((role) => (
                                                <Button
                                                    key={role}
                                                    type="button"
                                                    variant={inviteRole === role ? 'default' : 'outline'}
                                                    size="sm"
                                                    onClick={() => setInviteRole(role)}
                                                    className="capitalize"
                                                >
                                                    {role.replace('_', ' ')}
                                                </Button>
                                            ))}
                                        </div>
                                    </div>

                                    <Button
                                        onClick={handleInvite}
                                        disabled={saving || !inviteEmail.trim()}
                                        variant="secondary"
                                        className="w-full"
                                    >
                                        {saving ? (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <Users className="mr-2 h-4 w-4" />
                                        )}
                                        Send Invitation
                                    </Button>
                                </div>

                                <div className="flex gap-2 pt-4">
                                    <Button variant="outline" onClick={prevStep} disabled={saving}>
                                        <ArrowLeft className="mr-2 h-4 w-4" />
                                        Back
                                    </Button>
                                    <Button variant="ghost" onClick={nextStep} disabled={saving}>
                                        <SkipForward className="mr-2 h-4 w-4" />
                                        Skip for Now
                                    </Button>
                                    <Button onClick={nextStep} disabled={saving}>
                                        Continue
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </Button>
                                </div>
                            </CardContent>
                        </>
                    )}

                    {/* Step 4: Complete */}
                    {stepId === 'complete' && (
                        <>
                            <CardHeader className="text-center">
                                <div className="icon-container-success mx-auto mb-4 w-16 h-16 flex items-center justify-center">
                                    <CheckCircle className="h-8 w-8 icon-success" />
                                </div>
                                <CardTitle className="text-2xl">You're All Set!</CardTitle>
                                <CardDescription className="text-base">
                                    Your organization is ready to go. Here's what you can do next:
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                <div className="grid gap-3">
                                    <Button
                                        variant="outline"
                                        className="justify-start h-auto py-3"
                                        onClick={() => navigate(`/org/${slug}/events`)}
                                    >
                                        <div className="text-left">
                                            <div className="font-medium">Create an Event</div>
                                            <div className="text-xs text-muted-foreground">
                                                Start organizing your first event
                                            </div>
                                        </div>
                                    </Button>

                                    <Button
                                        variant="outline"
                                        className="justify-start h-auto py-3"
                                        onClick={() => navigate(`/org/${slug}/courses`)}
                                    >
                                        <div className="text-left">
                                            <div className="font-medium">Create a Course</div>
                                            <div className="text-xs text-muted-foreground">
                                                Build your learning content
                                            </div>
                                        </div>
                                    </Button>

                                    <Button
                                        variant="outline"
                                        className="justify-start h-auto py-3"
                                        onClick={() => navigate(`/org/${slug}/team`)}
                                    >
                                        <div className="text-left">
                                            <div className="font-medium">Manage Team</div>
                                            <div className="text-xs text-muted-foreground">
                                                View and invite team members
                                            </div>
                                        </div>
                                    </Button>
                                </div>

                                <div className="flex gap-2 pt-4">
                                    <Button variant="outline" onClick={prevStep} disabled={saving}>
                                        <ArrowLeft className="mr-2 h-4 w-4" />
                                        Back
                                    </Button>
                                    <Button onClick={handleComplete} disabled={saving} className="flex-1">
                                        {saving ? (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <CheckCircle className="mr-2 h-4 w-4" />
                                        )}
                                        Complete Setup
                                    </Button>
                                </div>
                            </CardContent>
                        </>
                    )}
                </Card>
            </div>
        </div>
    );
}

export default OrganizationOnboardingWizard;
