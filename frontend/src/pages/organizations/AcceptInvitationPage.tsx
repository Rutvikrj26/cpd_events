/**
 * Accept Organization Invitation Page
 *
 * Allows users to accept invitations to join organizations.
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle, XCircle, Building2, Crown, Shield, UserCog, User as UserIcon } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/contexts/AuthContext';
import { acceptOrganizationInvitation } from '@/api/organizations';

interface InvitationState {
  status: 'loading' | 'ready' | 'success' | 'error' | 'already_accepted';
  organization?: {
    uuid: string;
    name: string;
    logo_url?: string;
    slug: string;
  };
  role?: string;
  error?: string;
}

const AcceptInvitationPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();

  const [state, setState] = useState<InvitationState>({ status: 'loading' });
  const [isAccepting, setIsAccepting] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      // Redirect to login with return URL
      navigate(`/login?returnUrl=/accept-invite/${token}`);
      return;
    }

    // Page is ready for user to accept
    setState({ status: 'ready' });
  }, [isAuthenticated, token, navigate]);

  const handleAccept = async () => {
    if (!token) return;

    setIsAccepting(true);

    try {
      const response = await acceptOrganizationInvitation(token);

      setState({
        status: 'success',
        organization: response.organization,
        role: response.organization?.user_role || undefined,
      });

      // Redirect to organization dashboard after 2 seconds
      setTimeout(() => {
        navigate(`/org/${response.organization.slug}`);
      }, 2000);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.response?.data?.error?.message || 'Failed to accept invitation';

      if (errorMessage.includes('already been accepted')) {
        setState({
          status: 'already_accepted',
          error: errorMessage,
        });
      } else {
        setState({
          status: 'error',
          error: errorMessage,
        });
      }
    } finally {
      setIsAccepting(false);
    }
  };

  const handleDecline = () => {
    navigate('/organizations');
  };

  const getRoleIcon = (role?: string) => {
    switch (role) {
      case 'owner':
        return <Crown className="h-5 w-5 text-yellow-600" />;
      case 'admin':
        return <Shield className="h-5 w-5 text-blue-600" />;
      case 'manager':
        return <UserCog className="h-5 w-5 text-green-600" />;
      default:
        return <UserIcon className="h-5 w-5 text-gray-600" />;
    }
  };

  const getRoleDescription = (role?: string) => {
    switch (role) {
      case 'owner':
        return 'Full control including billing and member management';
      case 'admin':
        return 'Manage members and all content';
      case 'manager':
        return 'Create and edit events and courses';
      case 'member':
        return 'View-only access (free seat)';
      default:
        return 'Team member';
    }
  };

  // Loading state
  if (state.status === 'loading') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">Loading invitation...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  if (state.status === 'success') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-green-200 bg-green-50/50">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Welcome aboard!</h2>
            <p className="text-muted-foreground mb-4">
              You've successfully joined <strong>{state.organization?.name}</strong>
            </p>
            <p className="text-sm text-muted-foreground">
              Redirecting to organization dashboard...
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Already accepted state
  if (state.status === 'already_accepted') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="py-12">
            <Alert>
              <AlertTitle>Invitation Already Accepted</AlertTitle>
              <AlertDescription>{state.error}</AlertDescription>
            </Alert>
            <div className="flex justify-center mt-6">
              <Button onClick={() => navigate('/organizations')}>
                Go to My Organizations
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  if (state.status === 'error') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-destructive/20">
          <CardContent className="py-12">
            <div className="flex flex-col items-center text-center mb-6">
              <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
                <XCircle className="h-8 w-8 text-destructive" />
              </div>
              <h2 className="text-2xl font-bold mb-2">Unable to Accept Invitation</h2>
              <p className="text-muted-foreground">{state.error}</p>
            </div>
            <div className="flex justify-center gap-4">
              <Button variant="outline" onClick={() => navigate('/organizations')}>
                Go to My Organizations
              </Button>
              <Button onClick={() => window.location.reload()}>
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Ready to accept state
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center pb-4">
          <div className="flex justify-center mb-4">
            <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center">
              <Building2 className="h-10 w-10 text-primary" />
            </div>
          </div>
          <CardTitle className="text-3xl">You're Invited!</CardTitle>
          <CardDescription className="text-base mt-2">
            You've been invited to join an organization
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Invitation Details */}
          <div className="bg-muted/50 rounded-lg p-6 space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Organization</p>
              <div className="flex items-center gap-3">
                <Avatar className="h-12 w-12">
                  <AvatarFallback className="bg-primary/10 text-primary text-lg font-semibold">
                    ORG
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-semibold text-lg">Organization Name</p>
                  <p className="text-sm text-muted-foreground">Invited by: Team Admin</p>
                </div>
              </div>
            </div>

            <div>
              <p className="text-sm text-muted-foreground mb-2">Your Role</p>
              <div className="flex items-center gap-2">
                {getRoleIcon('manager')}
                <Badge variant="outline" className="text-base px-3 py-1 capitalize">
                  Manager
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                {getRoleDescription('manager')}
              </p>
            </div>
          </div>

          {/* What You'll Get */}
          <div className="space-y-3">
            <h3 className="font-semibold">What you'll be able to do:</h3>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm">Create and manage events</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm">Create and manage courses</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm">Access shared templates and contacts</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm">Use organization branding</span>
              </li>
            </ul>
          </div>

          {/* Actions */}
          <div className="flex gap-4 pt-4">
            <Button
              variant="outline"
              className="flex-1"
              onClick={handleDecline}
              disabled={isAccepting}
            >
              Decline
            </Button>
            <Button
              className="flex-1"
              onClick={handleAccept}
              disabled={isAccepting}
            >
              {isAccepting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Accepting...
                </>
              ) : (
                'Accept Invitation'
              )}
            </Button>
          </div>

          <p className="text-xs text-center text-muted-foreground">
            By accepting, you agree to become a member of this organization.
            You can leave at any time from your account settings.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default AcceptInvitationPage;
