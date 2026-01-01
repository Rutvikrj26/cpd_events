import React, { useState } from 'react';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    CardFooter,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Organization } from '@/api/organizations/types';
import { connectStripe, getStripeStatus } from '@/api/organizations';
import {
    Loader2,
    Store,
    ExternalLink,
    CheckCircle2,
    AlertTriangle,
    RefreshCw,
} from 'lucide-react';

interface StripeConnectSettingsProps {
    organization: Organization;
    onUpdate: () => void;
}

const StripeConnectSettings: React.FC<StripeConnectSettingsProps> = ({
    organization,
    onUpdate,
}) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const isConnected = organization.stripe_charges_enabled;
    const accountStatus = organization.stripe_account_status;
    const isRestricted = accountStatus === 'restricted' || accountStatus === 'pending_verification';

    const handleConnect = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await connectStripe(organization.uuid);
            if (response.url) {
                window.location.href = response.url;
            } else {
                setError('Failed to get onboarding URL');
            }
        } catch (err: any) {
            setError(err.message || 'Failed to initiate Stripe connection');
            setIsLoading(false);
        }
    };

    const handleSyncStatus = async () => {
        setIsLoading(true);
        setError(null);
        try {
            await getStripeStatus(organization.uuid);
            onUpdate(); // Trigger parent refresh
        } catch (err: any) {
            setError(err.message || 'Failed to sync status');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Store className="h-5 w-5 text-primary" />
                            Payouts & Payments
                        </CardTitle>
                        <CardDescription>
                            Connect your Stripe account to receive payments from attendees.
                        </CardDescription>
                    </div>
                    {organization.stripe_connect_id && (
                        <Badge
                            variant={isConnected ? 'default' : 'destructive'}
                            className="capitalize"
                        >
                            {isConnected ? 'Payments Active' : accountStatus || 'Pending'}
                        </Badge>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {error && (
                    <Alert variant="destructive">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle>Error</AlertTitle>
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {!organization.stripe_connect_id ? (
                    <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-lg bg-muted/30">
                        <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-sm mb-4">
                            {/* Stripe-ish generic icon or Store icon */}
                            <Store className="h-8 w-8 text-[#635BFF]" />
                        </div>
                        <h3 className="text-lg font-semibold mb-2">Setup Payouts</h3>
                        <p className="text-center text-muted-foreground max-w-md mb-6">
                            To sell tickets and collect payments, you need to connect a Stripe account.
                            Funds will be transferred directly to your bank account.
                        </p>
                        <Button
                            onClick={handleConnect}
                            disabled={isLoading}
                            className="bg-[#635BFF] hover:bg-[#534AC2] text-white"
                        >
                            {isLoading ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <ExternalLink className="mr-2 h-4 w-4" />
                            )}
                            Connect with Stripe
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="p-4 rounded-lg border bg-card">
                                <p className="text-sm font-medium text-muted-foreground mb-1">
                                    Stripe Account ID
                                </p>
                                <div className="flex items-center space-x-2">
                                    <code className="text-sm bg-muted px-2 py-1 rounded">
                                        {organization.stripe_connect_id}
                                    </code>
                                </div>
                            </div>
                            <div className="p-4 rounded-lg border bg-card">
                                <p className="text-sm font-medium text-muted-foreground mb-1">
                                    Status
                                </p>
                                <div className="flex items-center space-x-2">
                                    {isConnected ? (
                                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                                    ) : (
                                        <AlertTriangle className="h-4 w-4 text-yellow-500" />
                                    )}
                                    <span className="capitalize font-medium">
                                        {accountStatus?.replace('_', ' ') || 'Unknown'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Actions for connected accounts */}
                        {isRestricted && (
                            <Alert className="bg-yellow-50 border-yellow-200 text-yellow-800">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertTitle>Attention Needed</AlertTitle>
                                <AlertDescription>
                                    Your account has missing requirements. Please complete onboarding to enable payouts.
                                </AlertDescription>
                            </Alert>
                        )}

                        <div className="flex justify-end gap-4">
                            <Button
                                variant="outline"
                                onClick={handleSyncStatus}
                                disabled={isLoading}
                            >
                                <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                                Sync Status
                            </Button>

                            {!isConnected || isRestricted ? (
                                <Button
                                    onClick={handleConnect}
                                    disabled={isLoading}
                                    className="bg-[#635BFF] hover:bg-[#534AC2] text-white"
                                >
                                    {isLoading ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <ExternalLink className="mr-2 h-4 w-4" />
                                    )}
                                    Resume Onboarding
                                </Button>
                            ) : (
                                <Button
                                    variant="outline"
                                    onClick={handleConnect} // Stripe works by "logging in" via the same link essentially for Express dashboard
                                    disabled={isLoading}
                                >
                                    <ExternalLink className="mr-2 h-4 w-4" />
                                    View Payouts Dashboard
                                </Button>
                            )}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default StripeConnectSettings;
