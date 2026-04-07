import React, { useState, useEffect } from 'react';
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
import { UserPlus, Search, Mail } from 'lucide-react';
import client from '@/api/client';
import { User } from '@/api/accounts/types';

interface AdminUser extends User {
    last_login_at: string | null;
    is_staff: boolean;
}

export const UserManagementPage: React.FC = () => {
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [inviteOpen, setInviteOpen] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);

    const fetchUsers = async () => {
        setIsLoading(true);
        try {
            const params = new URLSearchParams();
            if (search) params.set('search', search);
            if (roleFilter) params.set('role', roleFilter);
            const response = await client.get(`/admin/users/?${params.toString()}`);
            setUsers(response.data.results || response.data);
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
                        <SelectItem value="">All roles</SelectItem>
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
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => toggleActive(u.uuid)}
                                            >
                                                {u.is_active ? 'Deactivate' : 'Activate'}
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};

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
