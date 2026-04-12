import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Search, Mail, Upload, MoreVertical, RotateCw, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import client from '@/api/client';
import { unwrapList } from '@/api/pagination';
import { User } from '@/api/accounts/types';
import {
    bulkInviteUsers,
    BulkInviteUser,
    inviteUser,
    listInvitations,
    resendInvitation,
    revokeInvitation,
    updateAdminUser,
    UserInvitation,
} from '@/api/accounts';

interface AdminUser extends User {
    last_login_at: string | null;
}

export const UserManagementPage: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'users' | 'invitations'>('users');

    const [users, setUsers] = useState<AdminUser[]>([]);
    const [usersLoading, setUsersLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState('all');

    const [invitations, setInvitations] = useState<UserInvitation[]>([]);
    const [invitationsLoading, setInvitationsLoading] = useState(false);
    const [invitationStatus, setInvitationStatus] = useState<'pending' | 'accepted' | 'expired' | 'revoked' | 'all'>('pending');
    const [invitationSearch, setInvitationSearch] = useState('');

    const [inviteOpen, setInviteOpen] = useState(false);
    const [bulkInviteOpen, setBulkInviteOpen] = useState(false);
    const [changeRoleOpen, setChangeRoleOpen] = useState(false);
    const [changeRoleUser, setChangeRoleUser] = useState<AdminUser | null>(null);

    const fetchUsers = useCallback(async () => {
        setUsersLoading(true);
        try {
            const params = new URLSearchParams();
            if (search) params.set('search', search);
            if (roleFilter && roleFilter !== 'all') params.set('role', roleFilter);
            const response = await client.get(`/admin/users/?${params.toString()}`);
            setUsers(unwrapList<AdminUser>(response.data));
        } catch (err) {
            console.error('Failed to fetch users:', err);
        } finally {
            setUsersLoading(false);
        }
    }, [search, roleFilter]);

    const fetchInvitations = useCallback(async () => {
        setInvitationsLoading(true);
        try {
            const data = await listInvitations({
                status: invitationStatus === 'all' ? undefined : invitationStatus,
                search: invitationSearch || undefined,
            });
            setInvitations(data);
        } catch (err) {
            console.error('Failed to fetch invitations:', err);
        } finally {
            setInvitationsLoading(false);
        }
    }, [invitationStatus, invitationSearch]);

    useEffect(() => {
        if (activeTab === 'users') fetchUsers();
    }, [activeTab, fetchUsers]);

    useEffect(() => {
        if (activeTab === 'invitations') fetchInvitations();
    }, [activeTab, fetchInvitations]);

    const toggleActive = async (userUuid: string) => {
        try {
            await client.post(`/admin/users/${userUuid}/deactivate/`);
            fetchUsers();
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            if (code === 'LAST_ADMIN') {
                toast.error('Cannot deactivate the last active admin.');
            } else {
                toast.error('Failed to change user status');
            }
        }
    };

    const handleInviteSuccess = () => {
        if (activeTab === 'invitations') fetchInvitations();
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">User Management</h1>
                    <p className="text-muted-foreground">Manage users and send invitations</p>
                </div>
                <div className="flex gap-2">
                    <BulkInviteDialog open={bulkInviteOpen} onOpenChange={setBulkInviteOpen} onSuccess={handleInviteSuccess} />
                    <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} onSuccess={handleInviteSuccess} />
                </div>
            </div>

            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'users' | 'invitations')}>
                <TabsList>
                    <TabsTrigger value="users">All Users</TabsTrigger>
                    <TabsTrigger value="invitations">Pending Invitations</TabsTrigger>
                </TabsList>

                <TabsContent value="users" className="space-y-4">
                    <div className="flex gap-4">
                        <div className="relative flex-1 max-w-sm">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search by name or email..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="pl-9"
                            />
                        </div>
                        <Select value={roleFilter} onValueChange={setRoleFilter}>
                            <SelectTrigger className="w-[180px]">
                                <SelectValue placeholder="All roles" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">All roles</SelectItem>
                                <SelectItem value="learner">Learner</SelectItem>
                                <SelectItem value="educator">Educator</SelectItem>
                                <SelectItem value="course_manager">Course Manager</SelectItem>
                                <SelectItem value="admin">Admin</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <Card>
                        <CardContent className="p-0">
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b bg-muted/50">
                                            <th className="text-left p-4 font-medium">User</th>
                                            <th className="text-left p-4 font-medium">Roles</th>
                                            <th className="text-left p-4 font-medium">Status</th>
                                            <th className="text-left p-4 font-medium">Last Login</th>
                                            <th className="text-right p-4 font-medium">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {usersLoading ? (
                                            <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">Loading...</td></tr>
                                        ) : users.length === 0 ? (
                                            <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">No users found</td></tr>
                                        ) : users.map((u) => (
                                            <tr key={u.uuid} className="border-b last:border-0 hover:bg-muted/30">
                                                <td className="p-4">
                                                    <Link to={`/admin/users/${u.uuid}`} className="block hover:text-primary transition-colors">
                                                        <div className="font-medium">{u.full_name}</div>
                                                        <div className="text-sm text-muted-foreground">{u.email}</div>
                                                    </Link>
                                                </td>
                                                <td className="p-4">
                                                    <div className="flex gap-1 flex-wrap">
                                                        {u.roles?.map((role) => (
                                                            <Badge key={role} variant="secondary" className="text-xs">
                                                                {role}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                </td>
                                                <td className="p-4">
                                                    <Badge variant={u.is_active ? "default" : "destructive"}>
                                                        {u.is_active ? 'Active' : 'Inactive'}
                                                    </Badge>
                                                </td>
                                                <td className="p-4 text-sm text-muted-foreground">
                                                    {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                                                </td>
                                                <td className="p-4 text-right">
                                                    <DropdownMenu>
                                                        <DropdownMenuTrigger asChild>
                                                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                                                <MoreVertical className="h-4 w-4" />
                                                            </Button>
                                                        </DropdownMenuTrigger>
                                                        <DropdownMenuContent align="end">
                                                            <DropdownMenuItem onClick={() => toggleActive(u.uuid)}>
                                                                {u.is_active ? 'Deactivate' : 'Activate'}
                                                            </DropdownMenuItem>
                                                            <DropdownMenuItem onClick={() => { setChangeRoleUser(u); setChangeRoleOpen(true); }}>
                                                                Change Role
                                                            </DropdownMenuItem>
                                                        </DropdownMenuContent>
                                                    </DropdownMenu>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="invitations" className="space-y-4">
                    <InvitationsTab
                        invitations={invitations}
                        loading={invitationsLoading}
                        statusFilter={invitationStatus}
                        onStatusFilterChange={setInvitationStatus}
                        search={invitationSearch}
                        onSearchChange={setInvitationSearch}
                        onRefresh={fetchInvitations}
                    />
                </TabsContent>
            </Tabs>

            {changeRoleUser && (
                <ChangeRoleDialog
                    open={changeRoleOpen}
                    onOpenChange={(v) => { setChangeRoleOpen(v); if (!v) setChangeRoleUser(null); }}
                    user={changeRoleUser}
                    onSuccess={fetchUsers}
                />
            )}
        </div>
    );
};

function InvitationsTab({
    invitations,
    loading,
    statusFilter,
    onStatusFilterChange,
    search,
    onSearchChange,
    onRefresh,
}: {
    invitations: UserInvitation[];
    loading: boolean;
    statusFilter: 'pending' | 'accepted' | 'expired' | 'revoked' | 'all';
    onStatusFilterChange: (v: 'pending' | 'accepted' | 'expired' | 'revoked' | 'all') => void;
    search: string;
    onSearchChange: (v: string) => void;
    onRefresh: () => void;
}) {
    const [busyUuid, setBusyUuid] = useState<string | null>(null);

    const handleResend = async (inv: UserInvitation) => {
        setBusyUuid(inv.uuid);
        try {
            await resendInvitation(inv.uuid);
            toast.success(`Invitation re-sent to ${inv.email}`);
            onRefresh();
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            if (code === 'INVITATION_ALREADY_ACCEPTED') {
                toast.error('This invitation has already been accepted.');
            } else if (code === 'INVITATION_REVOKED') {
                toast.error('This invitation has been revoked.');
            } else {
                toast.error('Failed to resend invitation');
            }
        } finally {
            setBusyUuid(null);
        }
    };

    const handleRevoke = async (inv: UserInvitation) => {
        setBusyUuid(inv.uuid);
        try {
            await revokeInvitation(inv.uuid);
            toast.success(`Invitation for ${inv.email} revoked`);
            onRefresh();
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            if (code === 'INVITATION_ALREADY_ACCEPTED') {
                toast.error('Cannot revoke an invitation that has already been accepted.');
            } else {
                toast.error('Failed to revoke invitation');
            }
        } finally {
            setBusyUuid(null);
        }
    };

    const statusBadge = (status: UserInvitation['status']) => {
        const variants: Record<UserInvitation['status'], 'default' | 'secondary' | 'destructive' | 'outline'> = {
            pending: 'default',
            accepted: 'secondary',
            expired: 'outline',
            revoked: 'destructive',
        };
        return <Badge variant={variants[status]}>{status}</Badge>;
    };

    return (
        <div className="space-y-4">
            <div className="flex gap-4">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search by email or name..."
                        value={search}
                        onChange={(e) => onSearchChange(e.target.value)}
                        className="pl-9"
                    />
                </div>
                <Select value={statusFilter} onValueChange={(v) => onStatusFilterChange(v as any)}>
                    <SelectTrigger className="w-[180px]">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="pending">Pending</SelectItem>
                        <SelectItem value="accepted">Accepted</SelectItem>
                        <SelectItem value="expired">Expired</SelectItem>
                        <SelectItem value="revoked">Revoked</SelectItem>
                        <SelectItem value="all">All</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            <Card>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b bg-muted/50">
                                    <th className="text-left p-4 font-medium">Invitee</th>
                                    <th className="text-left p-4 font-medium">Role</th>
                                    <th className="text-left p-4 font-medium">Invited By</th>
                                    <th className="text-left p-4 font-medium">Sent</th>
                                    <th className="text-left p-4 font-medium">Expires</th>
                                    <th className="text-left p-4 font-medium">Status</th>
                                    <th className="text-right p-4 font-medium">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr><td colSpan={7} className="p-8 text-center text-muted-foreground">Loading...</td></tr>
                                ) : invitations.length === 0 ? (
                                    <tr><td colSpan={7} className="p-8 text-center text-muted-foreground">No invitations found</td></tr>
                                ) : invitations.map((inv) => {
                                    const canManage = inv.status === 'pending' || inv.status === 'expired';
                                    return (
                                        <tr key={inv.uuid} className="border-b last:border-0 hover:bg-muted/30">
                                            <td className="p-4">
                                                <div>
                                                    <div className="font-medium">{inv.full_name}</div>
                                                    <div className="text-sm text-muted-foreground">{inv.email}</div>
                                                </div>
                                            </td>
                                            <td className="p-4">
                                                <Badge variant="secondary" className="text-xs">{inv.role}</Badge>
                                            </td>
                                            <td className="p-4 text-sm text-muted-foreground">{inv.invited_by_name || '—'}</td>
                                            <td className="p-4 text-sm text-muted-foreground">
                                                {new Date(inv.last_sent_at).toLocaleDateString()}
                                                {inv.resent_count > 0 && (
                                                    <span className="ml-2 text-xs">(+{inv.resent_count} resend{inv.resent_count > 1 ? 's' : ''})</span>
                                                )}
                                            </td>
                                            <td className="p-4 text-sm text-muted-foreground">
                                                {new Date(inv.expires_at).toLocaleDateString()}
                                            </td>
                                            <td className="p-4">{statusBadge(inv.status)}</td>
                                            <td className="p-4 text-right">
                                                {canManage && (
                                                    <div className="flex justify-end gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleResend(inv)}
                                                            disabled={busyUuid === inv.uuid}
                                                        >
                                                            <RotateCw className="h-4 w-4 mr-1" />
                                                            Resend
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleRevoke(inv)}
                                                            disabled={busyUuid === inv.uuid}
                                                        >
                                                            <XCircle className="h-4 w-4 mr-1" />
                                                            Revoke
                                                        </Button>
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

// Bulk Invite Dialog
function BulkInviteDialog({ open, onOpenChange, onSuccess }: { open: boolean; onOpenChange: (v: boolean) => void; onSuccess: () => void }) {
    const [csvUsers, setCsvUsers] = useState<BulkInviteUser[]>([]);
    const [parseError, setParseError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [results, setResults] = useState<{ invited: number; errors: Array<{ email: string; error: string }> } | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const resetState = () => {
        setCsvUsers([]);
        setParseError(null);
        setError(null);
        setResults(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setParseError(null);
        setError(null);
        setResults(null);
        const file = e.target.files?.[0];
        if (!file) { setCsvUsers([]); return; }

        const reader = new FileReader();
        reader.onload = (evt) => {
            try {
                const text = evt.target?.result as string;
                const lines = text.split(/\r?\n/).filter(l => l.trim());
                if (lines.length < 2) { setParseError('CSV must have a header row and at least one data row'); return; }

                const header = lines[0].split(',').map(h => h.trim().toLowerCase());
                const emailIdx = header.indexOf('email');
                const nameIdx = header.indexOf('full_name');
                const roleIdx = header.indexOf('role');

                if (emailIdx === -1 || nameIdx === -1 || roleIdx === -1) {
                    setParseError('CSV must have columns: email, full_name, role');
                    return;
                }

                const parsed: BulkInviteUser[] = [];
                for (let i = 1; i < lines.length; i++) {
                    const cols = lines[i].split(',').map(c => c.trim());
                    if (cols.length < 3) continue;
                    const email = cols[emailIdx];
                    const full_name = cols[nameIdx];
                    const role = cols[roleIdx];
                    if (email && full_name && role) {
                        parsed.push({ email, full_name, role });
                    }
                }

                if (parsed.length === 0) { setParseError('No valid rows found in CSV'); return; }
                setCsvUsers(parsed);
            } catch {
                setParseError('Failed to parse CSV file');
            }
        };
        reader.readAsText(file);
    };

    const handleSubmit = async () => {
        if (csvUsers.length === 0) return;
        setError(null);
        setIsLoading(true);
        try {
            const res = await bulkInviteUsers(csvUsers);
            setResults(res);
            toast.success(`${res.invited} invitation(s) sent`);
            if (res.errors.length === 0) {
                onSuccess();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to send bulk invitations');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) resetState(); }}>
            <DialogTrigger asChild>
                <Button variant="outline"><Upload className="mr-2 h-4 w-4" />Bulk Invite</Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>Bulk Invite Users</DialogTitle>
                    <DialogDescription>Upload a CSV file with columns: email, full_name, role</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                    {error && <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">{error}</div>}
                    {parseError && <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">{parseError}</div>}

                    <div className="space-y-2">
                        <Label htmlFor="csv-file">CSV File</Label>
                        <Input id="csv-file" type="file" accept=".csv" ref={fileInputRef} onChange={handleFileChange} />
                    </div>

                    {csvUsers.length > 0 && !results && (
                        <>
                            <div className="text-sm font-medium">Preview ({csvUsers.length} users)</div>
                            <div className="max-h-60 overflow-y-auto border rounded-md">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b bg-muted/50">
                                            <th className="text-left p-2">Email</th>
                                            <th className="text-left p-2">Name</th>
                                            <th className="text-left p-2">Role</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {csvUsers.map((u, i) => (
                                            <tr key={i} className="border-b last:border-0">
                                                <td className="p-2">{u.email}</td>
                                                <td className="p-2">{u.full_name}</td>
                                                <td className="p-2">{u.role}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            <Button onClick={handleSubmit} className="w-full" disabled={isLoading}>
                                {isLoading ? 'Sending Invitations...' : `Send ${csvUsers.length} Invitation(s)`}
                            </Button>
                        </>
                    )}

                    {results && (
                        <div className="space-y-2">
                            <div className="text-sm font-medium">
                                {results.invited} invited, {results.errors.length} error{results.errors.length === 1 ? '' : 's'}
                            </div>
                            {results.errors.length > 0 && (
                                <div className="max-h-40 overflow-y-auto border rounded-md p-2 text-sm">
                                    {results.errors.map((err, i) => (
                                        <div key={i}><span className="font-medium">{err.email}</span>: {err.error}</div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

// Change Role Dialog
function ChangeRoleDialog({ open, onOpenChange, user, onSuccess }: { open: boolean; onOpenChange: (v: boolean) => void; user: AdminUser; onSuccess: () => void }) {
    const [selectedRoles, setSelectedRoles] = useState<string[]>(user.roles || []);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const allRoles = ['learner', 'educator', 'course_manager', 'admin'];

    const toggleRole = (role: string) => {
        setSelectedRoles(prev =>
            prev.includes(role) ? prev.filter(r => r !== role) : [...prev, role]
        );
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (selectedRoles.length === 0) { setError('Select at least one role'); return; }
        setError(null);
        setIsLoading(true);
        try {
            await updateAdminUser(user.uuid, { roles: selectedRoles });
            toast.success('Roles updated');
            onOpenChange(false);
            onSuccess();
        } catch (err: any) {
            const detail = err?.response?.data?.error?.message
                || err?.response?.data?.error?.details?.roles?.[0]
                || 'Failed to update roles';
            setError(detail);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Change Role</DialogTitle>
                    <DialogDescription>Update roles for {user.full_name} ({user.email})</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">{error}</div>}
                    <div className="space-y-2">
                        <Label>Roles</Label>
                        <div className="flex flex-wrap gap-2">
                            {allRoles.map(role => (
                                <Badge
                                    key={role}
                                    variant={selectedRoles.includes(role) ? "default" : "outline"}
                                    className="cursor-pointer select-none"
                                    onClick={() => toggleRole(role)}
                                >
                                    {role}
                                </Badge>
                            ))}
                        </div>
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading ? 'Updating...' : 'Update Roles'}
                    </Button>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// Invite Dialog
function InviteDialog({ open, onOpenChange, onSuccess }: { open: boolean; onOpenChange: (v: boolean) => void; onSuccess: () => void }) {
    const [email, setEmail] = useState('');
    const [fullName, setFullName] = useState('');
    const [role, setRole] = useState('learner');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [pendingUuid, setPendingUuid] = useState<string | null>(null);

    const resetForm = () => {
        setEmail('');
        setFullName('');
        setRole('learner');
        setError(null);
        setPendingUuid(null);
    };

    const findPendingInvitation = async (emailValue: string): Promise<string | null> => {
        try {
            const list = await listInvitations({ status: 'pending', search: emailValue });
            const match = list.find(i => i.email.toLowerCase() === emailValue.toLowerCase());
            return match?.uuid ?? null;
        } catch {
            return null;
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setPendingUuid(null);
        setIsLoading(true);
        try {
            await inviteUser({ email, full_name: fullName, role });
            toast.success(`Invitation sent to ${email}`);
            onOpenChange(false);
            resetForm();
            onSuccess();
        } catch (err: any) {
            const code = err?.response?.data?.error?.code;
            if (code === 'INVITATION_PENDING') {
                const uuid = await findPendingInvitation(email);
                setPendingUuid(uuid);
                setError('An invitation is already pending for this email.');
            } else {
                setError(err?.response?.data?.error?.message || err?.response?.data?.detail || 'Failed to send invitation');
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleResendPending = async () => {
        if (!pendingUuid) return;
        setIsLoading(true);
        try {
            await resendInvitation(pendingUuid);
            toast.success(`Invitation re-sent to ${email}`);
            onOpenChange(false);
            resetForm();
            onSuccess();
        } catch {
            toast.error('Failed to resend invitation');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) resetForm(); }}>
            <DialogTrigger asChild>
                <Button><Mail className="mr-2 h-4 w-4" />Invite User</Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Invite User</DialogTitle>
                    <DialogDescription>Send an invitation email to a new user.</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && (
                        <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md space-y-2">
                            <div>{error}</div>
                            {pendingUuid && (
                                <Button type="button" variant="outline" size="sm" onClick={handleResendPending} disabled={isLoading}>
                                    <RotateCw className="h-4 w-4 mr-1" />
                                    Resend instead
                                </Button>
                            )}
                        </div>
                    )}
                    <div className="space-y-2">
                        <Label htmlFor="inv-email">Email</Label>
                        <Input id="inv-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="inv-name">Full Name</Label>
                        <Input id="inv-name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
                    </div>
                    <div className="space-y-2">
                        <Label>Role</Label>
                        <Select value={role} onValueChange={setRole}>
                            <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="learner">Learner</SelectItem>
                                <SelectItem value="educator">Educator</SelectItem>
                                <SelectItem value="course_manager">Course Manager</SelectItem>
                                <SelectItem value="admin">Admin</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <DialogFooter>
                        <Button type="submit" className="w-full" disabled={isLoading}>
                            {isLoading ? 'Sending...' : 'Send Invitation'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

export default UserManagementPage;
