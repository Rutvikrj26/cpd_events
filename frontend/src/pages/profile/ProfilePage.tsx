import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { getCurrentUser, updateProfile } from '@/api/accounts';
import { User } from '@/api/accounts/types';
import { getPaymentMethods, deletePaymentMethod, getSubscription } from '@/api/billing';
import { PaymentMethod, Subscription } from '@/api/billing/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { PaymentMethodModal } from '@/components/billing/PaymentMethodModal';
import { useToast } from '@/components/ui/use-toast';
import { CreditCard, Trash2, Loader2, Plus, CheckCircle, AlertCircle } from 'lucide-react';

export const ProfilePage = () => {
    const { toast } = useToast();
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Form state
    const [fullName, setFullName] = useState('');

    // Billing state
    const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [loadingBilling, setLoadingBilling] = useState(true);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [paymentModalOpen, setPaymentModalOpen] = useState(false);

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

    const loadBillingData = async () => {
        setLoadingBilling(true);
        try {
            const [methods, sub] = await Promise.all([
                getPaymentMethods(),
                getSubscription(),
            ]);
            setPaymentMethods(methods);
            setSubscription(sub);
        } catch (error) {
            console.error("Failed to load billing data:", error);
        } finally {
            setLoadingBilling(false);
        }
    };

    useEffect(() => {
        loadBillingData();
    }, []);

    const handleDeletePaymentMethod = async (uuid: string) => {
        setDeletingId(uuid);
        try {
            await deletePaymentMethod(uuid);
            setPaymentMethods(prev => prev.filter(m => m.uuid !== uuid));
            toast({ title: "Payment method removed" });
        } catch (error: any) {
            toast({ variant: "destructive", title: error.message || "Failed to remove payment method" });
        } finally {
            setDeletingId(null);
        }
    };

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
        <div className="max-w-2xl space-y-8">
            <h1 className="text-3xl font-bold text-foreground">Profile Settings</h1>

            {/* Profile Form */}
            <form onSubmit={handleSave} className="bg-card p-8 rounded-xl border shadow-sm space-y-6">
                <h2 className="text-lg font-semibold">Account Information</h2>

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

                <div className="pt-2">
                    <Button type="submit" disabled={saving}>
                        {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                </div>
            </form>

            {/* Billing Section */}
            <div className="bg-card p-8 rounded-xl border shadow-sm space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Payment Methods</h2>
                    {paymentMethods.length > 0 && (
                        <Button variant="outline" size="sm" onClick={() => setPaymentModalOpen(true)}>
                            <Plus className="h-4 w-4 mr-1" />
                            Add
                        </Button>
                    )}
                </div>

                {loadingBilling ? (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                ) : paymentMethods.length === 0 ? (
                    <div className="text-center py-6 space-y-4">
                        <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center">
                            <CreditCard className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <div>
                            <p className="font-medium">No payment methods</p>
                            <p className="text-sm text-muted-foreground">
                                Add a payment method to continue after your trial ends.
                            </p>
                        </div>
                        <Button onClick={() => setPaymentModalOpen(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            Add Payment Method
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {paymentMethods.map((method) => (
                            <div
                                key={method.uuid}
                                className="flex items-center justify-between p-4 border rounded-lg bg-muted/30"
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 bg-background rounded-md flex items-center justify-center border">
                                        <CreditCard className="h-5 w-5 text-muted-foreground" />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium capitalize">{method.card_brand}</span>
                                            <span className="text-muted-foreground">•••• {method.card_last4}</span>
                                            {method.is_default && (
                                                <Badge variant="secondary" className="text-xs">Default</Badge>
                                            )}
                                            {method.is_expired && (
                                                <Badge variant="destructive" className="text-xs">Expired</Badge>
                                            )}
                                        </div>
                                        <p className="text-sm text-muted-foreground">
                                            Expires {method.card_exp_month}/{method.card_exp_year}
                                        </p>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => handleDeletePaymentMethod(method.uuid)}
                                    disabled={deletingId === method.uuid}
                                >
                                    {deletingId === method.uuid ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Trash2 className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        ))}
                    </div>
                )}

                <Separator />

                {/* Subscription Status */}
                <div className="space-y-4">
                    <h3 className="text-sm font-medium text-muted-foreground">Subscription Status</h3>
                    {subscription ? (
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Plan</span>
                                <span className="font-medium capitalize">{subscription.plan}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Status</span>
                                <Badge variant={subscription.is_active ? "default" : "secondary"}>
                                    {subscription.status_display}
                                </Badge>
                            </div>
                            {subscription.is_trialing && subscription.days_until_trial_ends !== null && (
                                <div className="flex items-center justify-between">
                                    <span className="text-sm">Trial</span>
                                    <span className="text-sm font-medium">
                                        {subscription.days_until_trial_ends} days left
                                    </span>
                                </div>
                            )}

                            {subscription.has_payment_method ? (
                                <div className="flex items-center gap-2 text-success text-sm bg-success/10 p-3 rounded-lg">
                                    <CheckCircle className="h-4 w-4" />
                                    Billing set up. You'll be charged when your trial ends.
                                </div>
                            ) : subscription.is_trialing ? (
                                <div className="flex items-center gap-2 text-warning text-sm bg-warning/10 p-3 rounded-lg">
                                    <AlertCircle className="h-4 w-4" />
                                    Add billing to keep features after trial.
                                </div>
                            ) : null}
                        </div>
                    ) : (
                        <p className="text-sm text-muted-foreground">No subscription info available.</p>
                    )}
                </div>
            </div>

            {/* Payment Method Modal */}
            <PaymentMethodModal
                open={paymentModalOpen}
                onOpenChange={setPaymentModalOpen}
                subscription={subscription}
                onSuccess={() => loadBillingData()}
            />
        </div>
    );
};
