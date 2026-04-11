import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
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
import { UserPlus, Search, Mail, Upload, MoreVertical } from 'lucide-react';
import { toast } from 'sonner';
import client from '@/api/client';
import { unwrapList } from '@/api/pagination';
import { User } from '@/api/accounts/types';
import { bulkInviteUsers, BulkInviteUser, updateAdminUser } from '@/api/accounts';

interface AdminUser extends User {
    last_login_at: string | null;
    is_staff: boolean;
}

export const UserManagementPage: React.FC = () => {
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState('all');
    const [isLoading, setIsLoading] = useState(true);
    const [inviteOpen, setInviteOpen] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);
    const [bulkInviteOpen, setBulkInviteOpen] = useState(false);
    const [changeRoleOpen, setChangeRoleOpen] = useState(false);
    const [changeRoleUser, setChangeRoleUser] = useState<AdminUser | null>(null);

    const fetchUsers = async () => {
        setIsLoading(true);
        try {
            const params = new URLSearchParams();
            if (search) params.set('search', search);
            if (roleFilter && roleFilter !== 'all') params.set('role', roleFilter);
            const response = await client.get(`/admin/users/?${params.toString()}`);
            setUsers(unwrapList<AdminUser>(response.data));
        } catch (err) {
            console.error('Failed to fetch users:', err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, [search, roleFilter]);

    const toggleActive = async (userUuid: string) => {
        try {
            await client.post(`/admin/users/${userUuid}/deactivate/`);
            fetchUsers();
        } catch (err) {
            console.error('Failed to toggle user status:', err);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">User Management</h1>
                    <p className="text-muted-foreground">Manage users and send invitations</p>
                </div>
                <div className="flex gap-2">
                    <BulkInviteDialog open={bulkInviteOpen} onOpenChange={setBulkInviteOpen} onSuccess={fetchUsers} />
                    <InviteDialog open={inviteOpen} onOpenChange={setInviteOpen} onSuccess={fetchUsers} />
                    <CreateUserDialog open={createOpen} onOpenChange={setCreateOpen} onSuccess={fetchUsers} />
                </div>
            </div>

            {/* Filters */}
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

            {/* User Table */}
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
                                {isLoading ? (
                                    <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">Loading...</td></tr>
                                ) : users.length === 0 ? (
                                    <tr><td colSpan={5} className="p-8 text-center text-muted-foreground">No users found</td></tr>
                                ) : users.map((u) => (
                                    <tr key={u.uuid} className="border-b last:border-0 hover:bg-muted/30">
                                        <td className="p-4">
                                            <div>
                                                <div className="font-medium">{u.full_name}</div>
                                                <div className="text-sm text-muted-foreground">{u.email}</div>
                                            </div>
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
            {/* Change Role Dialog */}
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

                    {results && results.errors.length > 0 && (
                        <div className="space-y-2">
                            <div className="text-sm font-medium text-destructive">
                                {results.errors.length} error(s):
                            </div>
                            <div className="max-h-40 overflow-y-auto border rounded-md p-2 text-sm">
                                {results.errors.map((err, i) => (
                                    <div key={i}><span className="font-medium">{err.email}</span>: {err.error}</div>
                                ))}
                            </div>
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
            setError(err.response?.data?.detail || 'Failed to update roles');
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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);
        try {
            await client.post('/admin/users/invite/', { email, full_name: fullName, role });
            onOpenChange(false);
            setEmail('');
            setFullName('');
            setRole('learner');
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.email?.[0] || err.response?.data?.detail || 'Failed to send invitation');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogTrigger asChild>
                <Button variant="outline"><Mail className="mr-2 h-4 w-4" />Invite User</Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Invite User</DialogTitle>
                    <DialogDescription>Send an invitation email to a new user.</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">{error}</div>}
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
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading ? 'Sending...' : 'Send Invitation'}
                    </Button>
                </form>
            </DialogContent>
        </Dialog>
    );
}

// Create User Dialog
function CreateUserDialog({ open, onOpenChange, onSuccess }: { open: boolean; onOpenChange: (v: boolean) => void; onSuccess: () => void }) {
    const [email, setEmail] = useState('');
    const [fullName, setFullName] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('learner');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);
        try {
            await client.post('/admin/users/', { email, full_name: fullName, password, roles: [role] });
            onOpenChange(false);
            setEmail('');
            setFullName('');
            setPassword('');
            setRole('learner');
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.email?.[0] || err.response?.data?.detail || 'Failed to create user');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogTrigger asChild>
                <Button><UserPlus className="mr-2 h-4 w-4" />Create User</Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Create User</DialogTitle>
                    <DialogDescription>Create a new user account directly.</DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">{error}</div>}
                    <div className="space-y-2">
                        <Label htmlFor="cr-email">Email</Label>
                        <Input id="cr-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="cr-name">Full Name</Label>
                        <Input id="cr-name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="cr-pass">Password</Label>
                        <Input id="cr-pass" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
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
                    <Button type="submit" className="w-full" disabled={isLoading}>
                        {isLoading ? 'Creating...' : 'Create User'}
                    </Button>
                </form>
            </DialogContent>
        </Dialog>
    );
}

export default UserManagementPage;
