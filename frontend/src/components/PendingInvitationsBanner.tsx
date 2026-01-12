/**
 * Pending Invitations Banner
 * 
 * Shows pending organization invitations on the dashboard.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Check, X, Loader2 } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { getMyInvitations, acceptInvitation, PendingInvitation } from '@/api/organizations';

export const PendingInvitationsBanner: React.FC = () => {
    const navigate = useNavigate();
    const [invitations, setInvitations] = useState<PendingInvitation[]>([]);
    const [loading, setLoading] = useState(true);
    const [acceptingToken, setAcceptingToken] = useState<string | null>(null);
    const [dismissedTokens, setDismissedTokens] = useState<string[]>([]);

    useEffect(() => {
        const fetchInvitations = async () => {
            try {
                const data = await getMyInvitations();
                setInvitations(data);
            } catch (err) {
                console.error('Failed to fetch invitations:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchInvitations();
    }, []);

    const handleAccept = async (token: string, slug: string) => {
        setAcceptingToken(token);
        try {
            await acceptInvitation(token);
            // Full page reload to ensure fresh organization data
            window.location.href = `/org/${slug}`;
        } catch (err) {
            console.error('Failed to accept invitation:', err);
            alert('Failed to accept invitation. Please try again.');
        } finally {
            setAcceptingToken(null);
        }
    };

    const handleDismiss = (token: string) => {
        setDismissedTokens([...dismissedTokens, token]);
    };

    // Filter out dismissed invitations
    const visibleInvitations = invitations.filter(
        inv => !dismissedTokens.includes(inv.token)
    );

    if (loading || visibleInvitations.length === 0) {
        return null;
    }

    return (
        <div className="space-y-3 mb-6">
            {visibleInvitations.map(invitation => (
                <Alert key={invitation.token} className="border-primary/20 bg-primary/5">
                    <Building2 className="h-5 w-5 text-primary" />
                    <AlertTitle className="flex items-center gap-2">
                        <Avatar className="h-6 w-6">
                            {invitation.organization.logo_url ? (
                                <AvatarImage src={invitation.organization.logo_url} />
                            ) : null}
                            <AvatarFallback className="text-xs">
                                {invitation.organization.name.charAt(0)}
                            </AvatarFallback>
                        </Avatar>
                        <span>You've been invited to join <strong>{invitation.organization.name}</strong></span>
                    </AlertTitle>
                    <AlertDescription className="mt-2">
                        <div className="flex flex-wrap items-center gap-4">
                            <div className="flex-1">
                                <span className="text-muted-foreground">Role: </span>
                                <Badge variant="outline" className="ml-1 capitalize">
                                    {invitation.role_display}
                                </Badge>
                                <span className="text-muted-foreground ml-2">
                                    · Invited by {invitation.invited_by}
                                </span>
                            </div>
                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleDismiss(invitation.token)}
                                    disabled={acceptingToken === invitation.token}
                                >
                                    <X className="h-4 w-4 mr-1" />
                                    Decline
                                </Button>
                                <Button
                                    size="sm"
                                    onClick={() => handleAccept(invitation.token, invitation.organization.slug)}
                                    disabled={acceptingToken === invitation.token}
                                >
                                    {acceptingToken === invitation.token ? (
                                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                    ) : (
                                        <Check className="h-4 w-4 mr-1" />
                                    )}
                                    Accept
                                </Button>
                            </div>
                        </div>
                    </AlertDescription>
                </Alert>
            ))}
        </div>
    );
};

export default PendingInvitationsBanner;
