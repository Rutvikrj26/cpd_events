import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext'; // We can use this to get initial user but better to fetch fresh
import { getCurrentUser, updateProfile } from '@/api/accounts';
import { User } from '@/api/accounts/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';

export const ProfilePage = () => {
    const { toast } = useToast();
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Form state
    const [fullName, setFullName] = useState('');
    // const [email, setEmail] = useState(''); // Usually read-only or requires verify

    useEffect(() => {
        const loadProfile = async () => {
            try {
                const data = await getCurrentUser();
                setUser(data);
                setFullName(data.full_name || '');
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        loadProfile();
    }, []);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            const updated = await updateProfile({ full_name: fullName });
            setUser(updated);
            toast({ title: "Profile updated" });
        } catch (e) {
            toast({ variant: "destructive", title: "Failed to update profile" });
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div>Loading profile...</div>;

    return (
        <div className="max-w-2xl">
            <h1 className="text-3xl font-bold text-foreground mb-8">Profile Settings</h1>

            <form onSubmit={handleSave} className="bg-card p-8 rounded-xl border shadow-sm space-y-6">
                <div className="space-y-2">
                    <label className="text-sm font-medium">Email Address</label>
                    <Input disabled value={user?.email} className="bg-muted/30" />
                    <p className="text-xs text-muted-foreground">Email cannot be changed directly.</p>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium">Full Name</label>
                    <Input
                        value={fullName}
                        onChange={e => setFullName(e.target.value)}
                        placeholder="John Doe"
                    />
                </div>

                <div className="pt-4">
                    <Button type="submit" disabled={saving}>
                        {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                </div>
            </form>
        </div>
    );
};
