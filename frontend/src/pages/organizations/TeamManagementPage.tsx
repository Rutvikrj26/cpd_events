/**
 * Team Management Page
 *
 * Manage organization members: invite, update roles, remove.
 */

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
    Users,
    Plus,
    Shield,
    Calendar,
    BookOpen,
    User as UserIcon,
    MoreVertical,
    Mail,
    Trash2,
    Edit,
    Check,
    CheckCircle,
    X,
    Loader2,
    ArrowLeft,
    CreditCard,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

import {
    getOrganization,
    getOrganizations,
    getOrganizationMembers,
    inviteMember,
    updateMember,
    removeMember,
    getOrganizationPlans,
    addOrganizationSeats,
    lookupUser,
    linkOrganizerToOrg,
    createOrganizationPortalSession,
} from '@/api/organizations';
import { Organization, OrganizationMember, OrganizationRole, LinkResult } from '@/api/organizations/types';
import { getOrganizationCourses, Course } from '@/api/courses';
import { useOrganization } from '@/contexts/OrganizationContext';
import { useAuth } from '@/contexts/AuthContext';

const ROLE_OPTIONS: { value: OrganizationRole; label: string; description: string; billable: boolean }[] = [
    { value: 'admin', label: 'Admin', description: 'Org settings, members, templates', billable: false },
    { value: 'organizer', label: 'Organizer', description: 'Create and manage events', billable: true },
    { value: 'course_manager', label: 'Course Manager', description: 'Create and manage all courses', billable: true },
    { value: 'instructor', label: 'Instructor', description: 'Manage assigned course only', billable: false },
];

const TeamManagementPage: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const location = useLocation();
    const { user } = useAuth();
    const { hasRole, currentOrg } = useOrganization();

    const [org, setOrg] = useState<Organization | null>(null);
    const [members, setMembers] = useState<OrganizationMember[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [seatPrice, setSeatPrice] = useState(129);
    const [planPrice, setPlanPrice] = useState(199);
    const [orgCourses, setOrgCourses] = useState<Course[]>([]);

    // Invite dialog state
    const [showInviteDialog, setShowInviteDialog] = useState(false);
    const [showLinkDialog, setShowLinkDialog] = useState(false);

    // Auto-open invite dialog if requested
    useEffect(() => {
        const query = new URLSearchParams(location.search);
        if (query.get('action') === 'invite') {
            setShowInviteDialog(true);
        }
    }, [location.search]);

    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState<OrganizationRole>('instructor');
    const [inviteTitle, setInviteTitle] = useState('');
    const [inviteAssignedCourseUuid, setInviteAssignedCourseUuid] = useState<string | null>(null);
    const [inviteBillingPayer, setInviteBillingPayer] = useState<'organization' | 'organizer'>('organization');
    const [isInviting, setIsInviting] = useState(false);
    const [inviteError, setInviteError] = useState<string | null>(null);
    const [seatLimitError, setSeatLimitError] = useState<{ price: number; needed: number } | null>(null);
    const [buyingSeat, setBuyingSeat] = useState(false);
    const [inviteSuccess, setInviteSuccess] = useState<{ token: string; email: string } | null>(null);

    // Link organizer dialog state
    const [linkEmail, setLinkEmail] = useState('');
    const [linkRole, setLinkRole] = useState<OrganizationRole>('organizer');
    const [linkTransfer, setLinkTransfer] = useState(true);
    const [linkError, setLinkError] = useState<string | null>(null);
    const [linkResult, setLinkResult] = useState<LinkResult | null>(null);
    const [isLinking, setIsLinking] = useState(false);

    // Edit member dialog state
    const [editingMember, setEditingMember] = useState<OrganizationMember | null>(null);
    const [editRole, setEditRole] = useState<OrganizationRole>('organizer');
    const [editAssignedCourseUuid, setEditAssignedCourseUuid] = useState<string | null>(null);
    const [isUpdating, setIsUpdating] = useState(false);
    const [isManagingBilling, setIsManagingBilling] = useState(false);

    // User lookup state
    const [lookupResult, setLookupResult] = useState<{ found: boolean; user?: { email: string; full_name: string } } | null>(null);
    const [isLookingUp, setIsLookingUp] = useState(false);

    const handleLookup = async () => {
        if (!org || !inviteEmail || !inviteEmail.includes('@')) return;
        setIsLookingUp(true);
        setLookupResult(null);
        try {
            const result = await lookupUser(org.uuid, inviteEmail);
            setLookupResult(result);
        } catch (err) {
            console.error('Lookup failed:', err);
        } finally {
            setIsLookingUp(false);
        }
    };

    useEffect(() => {
        loadData();
    }, [slug]);

    const loadData = async () => {
        if (!slug) return;

        setIsLoading(true);
        try {
            const orgs = await getOrganizations();
            const found = orgs.find(o => o.slug === slug);
            if (!found) {
                setError('Organization not found');
                return;
            }

            const [fullOrg, membersList, plans, courses] = await Promise.all([
                getOrganization(found.uuid),
                getOrganizationMembers(found.uuid),
                getOrganizationPlans(),
                getOrganizationCourses(slug),
            ]);

            setOrg(fullOrg);
            setMembers(membersList);
            setOrgCourses(courses);

            // Determine prices from plans
            const planKey = fullOrg.subscription?.plan || 'organization';
            const planData = plans[planKey];
            if (planData) {
                if (planData.seat_price_cents !== undefined) {
                    setSeatPrice(planData.seat_price_cents / 100);
                }
                if (planData.price_cents !== undefined) {
                    setPlanPrice(planData.price_cents / 100);
                } else if (planData.base_price_cents !== undefined) {
                    setPlanPrice(planData.base_price_cents / 100);
                }
            }

        } catch (err: any) {
            setError(err.message || 'Failed to load data');
        } finally {
            setIsLoading(false);
        }
    };

    const handleInvite = async () => {
        if (!org || !inviteEmail) return;

        setIsInviting(true);
        setInviteError(null);
        setSeatLimitError(null);

        try {
            if (inviteRole === 'instructor' && !inviteAssignedCourseUuid) {
                setInviteError('Please select a course for this instructor.');
                setIsInviting(false);
                return;
            }

            const inviteData: any = {
                email: inviteEmail,
                role: inviteRole,
                title: inviteTitle || undefined,
            };

            // Add billing_payer for organizer role
            if (inviteRole === 'organizer') {
                inviteData.billing_payer = inviteBillingPayer;
            }

            if (inviteRole === 'instructor') {
                inviteData.assigned_course_uuid = inviteAssignedCourseUuid;
            }

            const result = await inviteMember(org.uuid, inviteData);

            // Show success with copy link
            setInviteSuccess({
                token: result.invitation_token,
                email: inviteEmail,
            });
            setInviteEmail('');
            setInviteRole('instructor');
            setInviteTitle('');
            setInviteAssignedCourseUuid(null);
            setInviteBillingPayer('organization');
            await loadData();
        } catch (err: any) {
            const errorData = err.response?.data?.error;
            if (errorData?.code === 'SEAT_LIMIT_REACHED') {
                setSeatLimitError({
                    price: (errorData.details?.seat_price_cents || 12900) / 100,
                    needed: 1
                });
                setInviteError(errorData.message);
            } else {
                setInviteError(
                    err.response?.data?.detail ||
                    errorData?.message ||
                    'Failed to send invitation'
                );
            }
        } finally {
            setIsInviting(false);
        }
    };

    const handleLinkOrganizer = async () => {
        if (!org) return;

        setIsLinking(true);
        setLinkError(null);
        setLinkResult(null);

        try {
            const payload: any = {
                role: linkRole,
                transfer_data: linkTransfer,
            };

            if (linkEmail.trim()) {
                payload.organizer_email = linkEmail.trim();
            }

            const result = await linkOrganizerToOrg(org.uuid, payload);
            setLinkResult(result);
            setLinkEmail('');
            await loadData();
        } catch (err: any) {
            setLinkError(
                err.response?.data?.detail ||
                err.response?.data?.error?.message ||
                'Failed to link organizer'
            );
        } finally {
            setIsLinking(false);
        }
    };

    const handleBuySeatAndInvite = async () => {
        if (!org || !inviteEmail) return;
        setBuyingSeat(true);
        setInviteError(null);

        try {
            // 1. Buy seat
            await addOrganizationSeats(org.uuid, 1);

            // 2. Retry invite
            await inviteMember(org.uuid, {
                email: inviteEmail,
                role: inviteRole,
                title: inviteTitle || undefined,
            });

            setShowInviteDialog(false);
            setInviteEmail('');
            setInviteRole('organizer');
            setInviteTitle('');
            setSeatLimitError(null);
            await loadData();
        } catch (err: any) {
            setInviteError(
                err.response?.data?.detail ||
                err.response?.data?.error?.message ||
                'Failed to buy seat and invite'
            );
        } finally {
            setBuyingSeat(false);
        }
    };

    const handleUpdateRole = async () => {
        if (!org || !editingMember) return;

        setIsUpdating(true);
        try {
            if (editRole === 'instructor' && !editAssignedCourseUuid) {
                setIsUpdating(false);
                return;
            }

            await updateMember(org.uuid, editingMember.uuid, {
                role: editRole,
                assigned_course_uuid: editRole === 'instructor' ? editAssignedCourseUuid : null,
            });
            setEditingMember(null);
            await loadData();
        } catch (err: any) {
            console.error('Failed to update member:', err);
        } finally {
            setIsUpdating(false);
        }
    };

    const handleRemoveMember = async (member: OrganizationMember) => {
        if (!org) return;
        if (!confirm(`Remove ${member.user_name || member.user_email} from the organization?`)) return;

        try {
            await removeMember(org.uuid, member.uuid);
            await loadData();
        } catch (err: any) {
            console.error('Failed to remove member:', err);
        }
    };

    const handleManageBilling = async () => {
        if (!org) return;
        setIsManagingBilling(true);
        try {
            const { url } = await createOrganizationPortalSession(org.uuid);
            window.location.href = url;
        } catch (err) {
            console.error('Failed to create portal session:', err);
            alert('Failed to open billing portal. Please try again.');
        } finally {
            setIsManagingBilling(false);
        }
    };

    const getRoleIcon = (role: OrganizationRole) => {
        switch (role) {
            case 'admin':
                return <Shield className="h-4 w-4 text-primary" />;
            case 'organizer':
                return <Calendar className="h-4 w-4 text-info" />;
            case 'course_manager':
                return <BookOpen className="h-4 w-4 text-success" />;
            case 'instructor':
                return <UserIcon className="h-4 w-4 text-success" />;
            default:
                return <UserIcon className="h-4 w-4 text-muted-foreground" />;
        }
    };

    const getRoleBadgeColor = (role: OrganizationRole) => {
        switch (role) {
            case 'admin':
                return 'bg-primary/10 text-primary border-primary';
            case 'course_manager':
                return 'bg-success-subtle text-success border-success';
            case 'instructor':
                return 'bg-success-subtle text-success border-success';
            case 'organizer':
                return 'bg-info-subtle text-info border-info';
            default:
                return 'bg-muted text-muted-foreground border-border';
        }
    };

    const canManageMembers = org?.user_role === 'admin' || org?.user_role === 'course_manager';
    const isCurrentUserAdmin = org?.user_role === 'admin';

    const canManageTargetMember = (member: OrganizationMember) => {
        if (org?.user_role === 'admin') return true;
        if (org?.user_role === 'course_manager') return member.role === 'instructor';
        return false;
    };

    const filteredRoleOptions = useMemo(() => {
        if (currentOrg?.user_role === 'course_manager') {
            return ROLE_OPTIONS.filter(opt => opt.value === 'instructor');
        }
        return ROLE_OPTIONS;
    }, [currentOrg?.user_role]);

    if (isLoading) {
        return (
            <div className="container mx-auto py-8 px-4 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error || !org) {
        return (
            <div className="container mx-auto py-16 px-4 text-center">
                <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h2 className="text-2xl font-bold mb-2">Unable to Load Team</h2>
                <p className="text-muted-foreground mb-4">{error}</p>
                <Button onClick={() => navigate('/organizations')}>
                    Back to Organizations
                </Button>
            </div>
        );
    }

    return (
        <div className="container mx-auto py-8 px-4 max-w-4xl">
            {/* Header */}
            <div className="flex items-center gap-4 mb-8">
                <Button variant="ghost" size="icon" onClick={() => navigate(`/org/${slug}`)}>
                    <ArrowLeft className="h-5 w-5" />
                </Button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold">Team Management</h1>
                    <p className="text-muted-foreground">{org.name}</p>
                </div>
                <div className="flex items-center gap-2">
                    {isCurrentUserAdmin && (
                        <Button variant="outline" onClick={() => setShowLinkDialog(true)}>
                            <Users className="h-4 w-4 mr-2" />
                            Link Organizer
                        </Button>
                    )}
                    {canManageMembers && (
                        <Button onClick={() => setShowInviteDialog(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            Invite Member
                        </Button>
                    )}
                </div>
            </div>

            {/* Subscription Usage Card */}
            {org.subscription && (
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle>Subscription Usage</CardTitle>
                        <CardDescription>
                            Admin, Organizer, and Course Manager roles count toward billable seats.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <Alert>
                                <Users className="h-4 w-4" />
                                <AlertTitle>Automatic Seat Provisioning</AlertTitle>
                                <AlertDescription>
                                    Seats are automatically added to your subscription when you invite new Organizers
                                    and removed when they leave. Additional seats are billed at <strong>${seatPrice}/month</strong>.
                                </AlertDescription>
                            </Alert>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="p-4 rounded-lg border">
                                    <p className="text-sm font-medium mb-1">Included Seats</p>
                                    <p className="text-2xl font-bold">{org.subscription.included_seats || 1}</p>
                                    <p className="text-xs text-muted-foreground">Base plan</p>
                                </div>
                                <div className="p-4 rounded-lg border">
                                    <p className="text-sm font-medium mb-1">Additional Seats</p>
                                    <p className="text-2xl font-bold">{org.subscription.additional_seats || 0}</p>
                                    <p className="text-xs text-muted-foreground">Auto-provisioned</p>
                                </div>
                            </div>

                            <div className="p-4 bg-muted/30 rounded-lg flex justify-between items-center animate-in fade-in slide-in-from-bottom-2">
                                <div>
                                    <p className="text-sm font-medium">Estimated Monthly Total</p>
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                        Base Plan ({planPrice.toLocaleString('en-US', { style: 'currency', currency: 'USD' })})
                                        {org.subscription.additional_seats > 0 && ` + ${org.subscription.additional_seats} seat${org.subscription.additional_seats > 1 ? 's' : ''}`}
                                    </p>
                                </div>
                                <p className="text-xl font-bold">
                                    {((planPrice + (org.subscription.additional_seats || 0) * seatPrice)).toLocaleString('en-US', {
                                        style: 'currency',
                                        currency: 'USD',
                                    })}
                                </p>
                            </div>

                            <div className="pt-4 border-t flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                                <div>
                                    <p className="text-sm font-medium">Manage Subscription</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        Update your plan, view invoices, or change payment methods.
                                    </p>
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleManageBilling}
                                    disabled={isManagingBilling}
                                >
                                    {isManagingBilling ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CreditCard className="h-4 w-4 mr-2" />}
                                    Manage Billing
                                </Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Members List */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Team Members ({members.length})
                    </CardTitle>
                    <CardDescription>
                        Manage your organization's team members and their roles
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-3">
                        {members.map((member) => (
                            <div
                                key={member.uuid}
                                className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <Avatar className="h-10 w-10">
                                        <AvatarFallback>
                                            {(member.user_name?.[0] || member.user_email[0]).toUpperCase()}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div>
                                        <p className="font-medium">{member.user_name || member.user_email}</p>
                                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                            <span>{member.user_email}</span>
                                            {member.title && (
                                                <>
                                                    <span>•</span>
                                                    <span>{member.title}</span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3">
                                    {/* Link Status */}
                                    {member.linked_from_individual && (
                                        <Badge variant="secondary" className="text-xs">
                                            Linked
                                        </Badge>
                                    )}

                                    {/* Role Badge */}
                                    <Badge
                                        variant="outline"
                                        className={`capitalize ${getRoleBadgeColor(member.role)}`}
                                    >
                                        {getRoleIcon(member.role)}
                                        <span className="ml-1">{member.role}</span>
                                    </Badge>

                                    {member.role === 'instructor' && member.assigned_course_title && (
                                        <Badge variant="secondary" className="text-xs">
                                            Assigned: {member.assigned_course_title}
                                        </Badge>
                                    )}
                                    {member.role === 'instructor' && !member.assigned_course_title && (
                                        <Badge variant="secondary" className="text-xs">
                                            Unassigned
                                        </Badge>
                                    )}

                                    {/* Pending/Active Status */}
                                    {!member.is_active && !member.accepted_at && (
                                        <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 border-yellow-200">
                                            Pending
                                        </Badge>
                                    )}

                                    {/* Actions dropdown - only for admins */}
                                    {canManageMembers && member.user_uuid !== user?.uuid && canManageTargetMember(member) && (
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                                    <MoreVertical className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuItem
                                                    onClick={() => {
                                                        setEditingMember(member);
                                                        setEditRole(member.role);
                                                        setEditAssignedCourseUuid(member.assigned_course_uuid || null);
                                                    }}
                                                >
                                                    <Edit className="h-4 w-4 mr-2" />
                                                    Change Role
                                                </DropdownMenuItem>

                                                {/* Re-invite option for pending members */}
                                                {!member.is_active && !member.accepted_at && (
                                                    <>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem
                                                            onClick={() => {
                                                                setInviteEmail(member.user_email);
                                                                setInviteRole(member.role);
                                                                setInviteTitle(member.title);
                                                                setInviteAssignedCourseUuid(member.assigned_course_uuid || null);
                                                                setShowInviteDialog(true);
                                                            }}
                                                        >
                                                            <Mail className="h-4 w-4 mr-2" />
                                                            Resend Invite
                                                        </DropdownMenuItem>
                                                    </>
                                                )}

                                                {/* Only admins can remove members */}
                                                {isCurrentUserAdmin && (
                                                    <>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem
                                                            onClick={() => handleRemoveMember(member)}
                                                            className="text-destructive"
                                                        >
                                                            <Trash2 className="h-4 w-4 mr-2" />
                                                            Remove
                                                        </DropdownMenuItem>
                                                    </>
                                                )}
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Link Organizer Dialog */}
            <Dialog open={showLinkDialog} onOpenChange={setShowLinkDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Link Organizer Data</DialogTitle>
                        <DialogDescription>
                            Connect an organizer account and optionally transfer their existing events and templates.
                        </DialogDescription>
                    </DialogHeader>

                    {linkError && (
                        <Alert variant="destructive">
                            <AlertDescription>{linkError}</AlertDescription>
                        </Alert>
                    )}

                    {linkResult && (
                        <Alert>
                            <AlertTitle>Success</AlertTitle>
                            <AlertDescription>
                                {linkResult.detail} {linkResult.events_transferred || linkResult.templates_transferred ? `Transferred ${linkResult.events_transferred} event(s) and ${linkResult.templates_transferred} template(s).` : ''}
                            </AlertDescription>
                        </Alert>
                    )}

                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="linkEmail">Organizer Email (Optional)</Label>
                            <Input
                                id="linkEmail"
                                type="email"
                                placeholder="organizer@example.com"
                                value={linkEmail}
                                onChange={(e) => setLinkEmail(e.target.value)}
                            />
                            <p className="text-xs text-muted-foreground">
                                Leave blank to link your own organizer data to this organization.
                            </p>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="linkRole">Role</Label>
                            <Select value={linkRole} onValueChange={(v) => setLinkRole(v as OrganizationRole)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ROLE_OPTIONS.map((role) => (
                                        <SelectItem key={role.value} value={role.value}>
                                            <div className="flex flex-col">
                                                <span>{role.label}</span>
                                                <span className="text-xs text-muted-foreground">{role.description}</span>
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex items-center justify-between rounded-lg border p-3">
                            <div>
                                <p className="text-sm font-medium">Transfer existing data</p>
                                <p className="text-xs text-muted-foreground">
                                    Move events and templates into this organization.
                                </p>
                            </div>
                            <Switch checked={linkTransfer} onCheckedChange={setLinkTransfer} />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowLinkDialog(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleLinkOrganizer} disabled={isLinking}>
                            {isLinking ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Linking...
                                </>
                            ) : (
                                <>
                                    <Users className="h-4 w-4 mr-2" />
                                    {linkEmail ? 'Send Invite' : 'Link My Data'}
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Invite Dialog */}
            <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Invite Team Member</DialogTitle>
                        <DialogDescription>
                            Send an invitation to join {org.name}
                        </DialogDescription>
                    </DialogHeader>

                    {inviteError && (
                        <Alert variant="destructive">
                            <div className="flex flex-col gap-2 w-full">
                                <AlertDescription>{inviteError}</AlertDescription>
                                {seatLimitError && (
                                    <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={handleBuySeatAndInvite}
                                        disabled={buyingSeat}
                                        className="w-full mt-2 bg-white/10 hover:bg-white/20 text-white border-white/20"
                                    >
                                        {buyingSeat ? (
                                            <>
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                Processing...
                                            </>
                                        ) : (
                                            <>
                                                <CreditCard className="h-4 w-4 mr-2" />
                                                Add Seat ${seatLimitError.price}/mo & Invite
                                            </>
                                        )}
                                    </Button>
                                )}
                            </div>
                        </Alert>
                    )}

                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email Address</Label>
                            <div className="flex gap-2">
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="colleague@company.com"
                                    value={inviteEmail}
                                    onChange={(e) => {
                                        setInviteEmail(e.target.value);
                                        setLookupResult(null);
                                    }}
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={handleLookup}
                                    disabled={isLookingUp || !inviteEmail || !inviteEmail.includes('@')}
                                >
                                    {isLookingUp ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Lookup'}
                                </Button>
                            </div>
                            {lookupResult && (
                                <div className="p-2 bg-muted/30 rounded border text-sm mt-1 animate-in fade-in slide-in-from-top-1">
                                    {lookupResult.found ? (
                                        <div className="flex items-center gap-2 text-success">
                                            <Check className="h-4 w-4" />
                                            <span>Found existing user: <strong>{lookupResult.user?.full_name}</strong></span>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 text-info">
                                            <Mail className="h-4 w-4" />
                                            <span>User not found. They will be invited to join the platform.</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="role">Role</Label>
                            <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as OrganizationRole)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {filteredRoleOptions.map((role) => (
                                        <SelectItem key={role.value} value={role.value}>
                                            <div className="flex flex-col">
                                                <span>{role.label}</span>
                                                <span className="text-xs text-muted-foreground">{role.description}</span>
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {inviteRole === 'instructor' && (
                            <div className="space-y-2">
                                <Label htmlFor="assignedCourse">Assign Course</Label>
                                <Select
                                    value={inviteAssignedCourseUuid || ''}
                                    onValueChange={(v) => setInviteAssignedCourseUuid(v || null)}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select a course" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {orgCourses.length === 0 && (
                                            <SelectItem value="none" disabled>
                                                No courses available
                                            </SelectItem>
                                        )}
                                        {orgCourses.map((course) => (
                                            <SelectItem key={course.uuid} value={course.uuid}>
                                                {course.title}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        )}

                        {/* Billing payer selector - only for organizer role */}
                        {inviteRole === 'organizer' && (
                            <div className="space-y-2">
                                <Label htmlFor="billing">Who pays for organizer subscription?</Label>
                                <Select
                                    value={inviteBillingPayer}
                                    onValueChange={(v) => setInviteBillingPayer(v as 'organization' | 'organizer')}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="organization">
                                            <div className="flex flex-col">
                                                <span>Organization Pays</span>
                                                <span className="text-xs text-muted-foreground">
                                                    Auto-provision seat (${seatPrice}/mo)
                                                </span>
                                            </div>
                                        </SelectItem>
                                        <SelectItem value="organizer">
                                            <div className="flex flex-col">
                                                <span>Organizer Pays</span>
                                                <span className="text-xs text-muted-foreground">
                                                    Organizer subscribes to their own plan
                                                </span>
                                            </div>
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                                <Alert className="mt-2 bg-muted/50 border-none">
                                    <AlertDescription className="text-xs text-muted-foreground">
                                        {inviteBillingPayer === 'organization'
                                            ? `A seat will be automatically added to your subscription ($${seatPrice}/mo) if none are available.`
                                            : 'The organizer will need to subscribe to their own Organizer plan to accept the invitation.'}
                                    </AlertDescription>
                                </Alert>
                            </div>
                        )}

                        <div className="space-y-2">
                            <Label htmlFor="title">Job Title (Optional)</Label>
                            <Input
                                id="title"
                                placeholder="e.g., Training Coordinator"
                                value={inviteTitle}
                                onChange={(e) => setInviteTitle(e.target.value)}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowInviteDialog(false)}>
                            Cancel
                        </Button>
                        <Button onClick={handleInvite} disabled={isInviting || !inviteEmail}>
                            {isInviting ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Sending...
                                </>
                            ) : (
                                <>
                                    <Mail className="h-4 w-4 mr-2" />
                                    Send Invitation
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Edit Role Dialog */}
            <Dialog open={!!editingMember} onOpenChange={() => setEditingMember(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Change Role</DialogTitle>
                        <DialogDescription>
                            Update role for {editingMember?.user_name || editingMember?.user_email}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="py-4">
                        <Label htmlFor="editRole">New Role</Label>
                        <Select value={editRole} onValueChange={(v) => setEditRole(v as OrganizationRole)}>
                            <SelectTrigger className="mt-2">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                {filteredRoleOptions.map((role) => (
                                    <SelectItem key={role.value} value={role.value}>
                                        <div className="flex items-center gap-2">
                                            {role.label}
                                            <span className="text-xs text-muted-foreground">- {role.description}</span>
                                        </div>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {editRole === 'instructor' && (
                        <div className="space-y-2 pb-4">
                            <Label htmlFor="editAssignedCourse">Assigned Course</Label>
                            <Select
                                value={editAssignedCourseUuid || ''}
                                onValueChange={(v) => setEditAssignedCourseUuid(v || null)}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select a course" />
                                </SelectTrigger>
                                <SelectContent>
                                    {orgCourses.length === 0 && (
                                        <SelectItem value="none" disabled>
                                            No courses available
                                        </SelectItem>
                                    )}
                                    {orgCourses.map((course) => (
                                        <SelectItem key={course.uuid} value={course.uuid}>
                                            {course.title}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    )}

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditingMember(null)}>
                            Cancel
                        </Button>
                        <Button onClick={handleUpdateRole} disabled={isUpdating}>
                            {isUpdating ? (
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                                <Check className="h-4 w-4 mr-2" />
                            )}
                            Save Changes
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Invite Success Dialog */}
            <Dialog open={!!inviteSuccess} onOpenChange={() => setInviteSuccess(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <CheckCircle className="h-5 w-5 text-success" />
                            Invitation Sent!
                        </DialogTitle>
                        <DialogDescription>
                            An invitation has been sent to <strong>{inviteSuccess?.email}</strong>.
                            They can also use the link below to accept.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="py-4">
                        <Label>Invitation Link</Label>
                        <div className="flex gap-2 mt-2">
                            <Input
                                readOnly
                                value={`${window.location.origin}/accept-invite/${inviteSuccess?.token}`}
                                className="text-sm"
                            />
                            <Button
                                variant="outline"
                                onClick={() => {
                                    navigator.clipboard.writeText(
                                        `${window.location.origin}/accept-invite/${inviteSuccess?.token}`
                                    );
                                }}
                            >
                                Copy
                            </Button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                            Share this link with the invitee to let them accept the invitation.
                        </p>
                    </div>

                    <DialogFooter>
                        <Button
                            onClick={() => {
                                setInviteSuccess(null);
                                setShowInviteDialog(false);
                            }}
                        >
                            Done
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default TeamManagementPage;
