/**
 * Team Management Page
 *
 * Manage organization members: invite, update roles, remove.
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Users,
    Plus,
    Crown,
    Shield,
    UserCog,
    User as UserIcon,
    MoreVertical,
    Mail,
    Trash2,
    Edit,
    Check,
    X,
    Loader2,
    ArrowLeft,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
    getOrganization,
    getOrganizations,
    getOrganizationMembers,
    inviteMember,
    updateMember,
    removeMember,
} from '@/api/organizations';
import { Organization, OrganizationMember, OrganizationRole } from '@/api/organizations/types';
import { useOrganization } from '@/contexts/OrganizationContext';
import { useAuth } from '@/contexts/AuthContext';

const ROLE_OPTIONS: { value: OrganizationRole; label: string; description: string }[] = [
    { value: 'owner', label: 'Owner', description: 'Full control including billing' },
    { value: 'admin', label: 'Admin', description: 'Manage members and all content' },
    { value: 'manager', label: 'Manager', description: 'Create and edit events/courses' },
    { value: 'member', label: 'Member', description: 'View only (free seat)' },
];

const TeamManagementPage: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const { user } = useAuth();
    const { hasRole } = useOrganization();

    const [org, setOrg] = useState<Organization | null>(null);
    const [members, setMembers] = useState<OrganizationMember[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Invite dialog state
    const [showInviteDialog, setShowInviteDialog] = useState(false);
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState<OrganizationRole>('manager');
    const [inviteTitle, setInviteTitle] = useState('');
    const [isInviting, setIsInviting] = useState(false);
    const [inviteError, setInviteError] = useState<string | null>(null);

    // Edit member dialog state
    const [editingMember, setEditingMember] = useState<OrganizationMember | null>(null);
    const [editRole, setEditRole] = useState<OrganizationRole>('member');
    const [isUpdating, setIsUpdating] = useState(false);

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

            const [fullOrg, membersList] = await Promise.all([
                getOrganization(found.uuid),
                getOrganizationMembers(found.uuid),
            ]);

            setOrg(fullOrg);
            setMembers(membersList);
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

        try {
            await inviteMember(org.uuid, {
                email: inviteEmail,
                role: inviteRole,
                title: inviteTitle || undefined,
            });

            setShowInviteDialog(false);
            setInviteEmail('');
            setInviteRole('manager');
            setInviteTitle('');
            await loadData();
        } catch (err: any) {
            setInviteError(
                err.response?.data?.detail ||
                err.response?.data?.error?.message ||
                'Failed to send invitation'
            );
        } finally {
            setIsInviting(false);
        }
    };

    const handleUpdateRole = async () => {
        if (!org || !editingMember) return;

        setIsUpdating(true);
        try {
            await updateMember(org.uuid, editingMember.uuid, { role: editRole });
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

    const getRoleIcon = (role: OrganizationRole) => {
        switch (role) {
            case 'owner':
                return <Crown className="h-4 w-4 text-yellow-600" />;
            case 'admin':
                return <Shield className="h-4 w-4 text-blue-600" />;
            case 'manager':
                return <UserCog className="h-4 w-4 text-green-600" />;
            default:
                return <UserIcon className="h-4 w-4 text-gray-600" />;
        }
    };

    const getRoleBadgeColor = (role: OrganizationRole) => {
        switch (role) {
            case 'owner':
                return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'admin':
                return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'manager':
                return 'bg-green-100 text-green-800 border-green-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const canManageMembers = org?.user_role === 'owner' || org?.user_role === 'admin';
    const isCurrentUserOwner = org?.user_role === 'owner';

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
                {canManageMembers && (
                    <Button onClick={() => setShowInviteDialog(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        Invite Member
                    </Button>
                )}
            </div>

            {/* Seat Usage */}
            {org.subscription && (
                <Card className="mb-6">
                    <CardContent className="py-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">Organizer Seats</p>
                                <p className="text-lg font-semibold">
                                    {org.subscription.active_organizer_seats} / {org.subscription.total_seats} used
                                </p>
                            </div>
                            <Badge variant="outline" className="capitalize">
                                {org.subscription.plan} Plan
                            </Badge>
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

                                    {/* Pending/Active Status */}
                                    {!member.is_active && !member.accepted_at && (
                                        <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 border-yellow-200">
                                            Pending
                                        </Badge>
                                    )}

                                    {/* Actions dropdown - only for admins/owners */}
                                    {canManageMembers && member.user_uuid !== user?.uuid && (
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
                                                                setShowInviteDialog(true);
                                                            }}
                                                        >
                                                            <Mail className="h-4 w-4 mr-2" />
                                                            Resend Invite
                                                        </DropdownMenuItem>
                                                    </>
                                                )}

                                                {/* Only owners can remove members, and can't remove other owners */}
                                                {isCurrentUserOwner && member.role !== 'owner' && (
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
                            <AlertDescription>{inviteError}</AlertDescription>
                        </Alert>
                    )}

                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email Address</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="colleague@company.com"
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="role">Role</Label>
                            <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as OrganizationRole)}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {ROLE_OPTIONS.filter(r => isCurrentUserOwner || r.value !== 'owner').map((role) => (
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
                                {ROLE_OPTIONS.filter(r => isCurrentUserOwner || r.value !== 'owner').map((role) => (
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
        </div>
    );
};

export default TeamManagementPage;
