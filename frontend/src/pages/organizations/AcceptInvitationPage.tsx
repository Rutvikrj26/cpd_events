/**
 * Accept Organization Invitation Page
 *
 * Allows users to accept invitations to join organizations.
 * Fetches invitation details on load and displays actual data.
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle, XCircle, Building2, Shield, Calendar, BookOpen, User as UserIcon } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/contexts/AuthContext';
import { getInvitationDetails, acceptInvitation, InvitationDetails } from '@/api/organizations';

interface InvitationState {
  status: 'loading' | 'ready' | 'success' | 'error' | 'already_accepted';
  invitation?: InvitationDetails;
  error?: string;
}

const AcceptInvitationPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [state, setState] = useState<InvitationState>({ status: 'loading' });
  const [isAccepting, setIsAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      // Redirect to login with return URL
      navigate(`/login?returnUrl=/accept-invite/${token}`);
      return;
    }

    // Fetch invitation details
    const loadInvitation = async () => {
      if (!token) {
        setState({ status: 'error', error: 'Invalid invitation link.' });
        return;
      }

      try {
        const details = await getInvitationDetails(token);
        setState({ status: 'ready', invitation: details });
      } catch (error: any) {
        const errorMessage = error.response?.data?.detail || 'Failed to load invitation details.';
        if (errorMessage.includes('already been accepted')) {
          setState({ status: 'already_accepted', error: errorMessage });
        } else {
          setState({ status: 'error', error: errorMessage });
        }
      }
    };

    loadInvitation();
  }, [isAuthenticated, token, navigate]);

  const handleAccept = async () => {
    if (!token) return;

    setIsAccepting(true);
    setAcceptError(null);

    try {
      const response = await acceptInvitation(token);

      setState({
        status: 'success',
        invitation: state.invitation,
      });

      // Redirect to organization dashboard after 2 seconds
      setTimeout(() => {
        navigate(`/org/${response.organization.slug}`);
      }, 2000);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to accept invitation';
      const errorCode = error.response?.data?.code;

      if (errorCode === 'ORGANIZER_SUBSCRIPTION_REQUIRED') {
        setAcceptError(errorMessage);
        setIsAccepting(false);
        return;
      }

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
      case 'admin':
        return <Shield className="h-5 w-5 text-purple-600" />;
      case 'organizer':
        return <Calendar className="h-5 w-5 text-blue-600" />;
      case 'course_manager':
        return <BookOpen className="h-5 w-5 text-emerald-600" />;
      case 'instructor':
        return <UserIcon className="h-5 w-5 text-green-600" />;
      default:
        return <UserIcon className="h-5 w-5 text-gray-600" />;
    }
  };

  const getRoleDescription = (role?: string) => {
    switch (role) {
      case 'admin':
        return 'Manage org settings, members, and templates';
      case 'organizer':
        return 'Create and manage events';
      case 'course_manager':
        return 'Create and manage courses';
      case 'instructor':
        return 'Teach assigned courses';
      default:
        return 'Organization member';
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
              You've successfully joined <strong>{state.invitation?.organization.name}</strong>
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

  const invitation = state.invitation;

  // Ready to accept state
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center pb-4">
          <div className="flex justify-center mb-4">
            {invitation?.organization.logo_url ? (
              <Avatar className="h-20 w-20">
                <AvatarImage src={invitation.organization.logo_url} alt={invitation.organization.name} />
                <AvatarFallback className="text-2xl">{invitation.organization.name.charAt(0)}</AvatarFallback>
              </Avatar>
            ) : (
              <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center">
                <Building2 className="h-10 w-10 text-primary" />
              </div>
            )}
          </div>
          <CardTitle className="text-3xl">You're Invited!</CardTitle>
          <CardDescription className="text-base mt-2">
            Join <strong>{invitation?.organization.name}</strong>
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {invitation?.requires_subscription && invitation?.billing_payer === 'organizer' && (
            <Alert>
              <AlertTitle>Organizer Subscription Required</AlertTitle>
              <AlertDescription>
                This invitation requires an active organizer subscription. Upgrade your plan to continue.
                <div className="mt-3">
                  <Button size="sm" variant="outline" onClick={() => navigate('/billing')}>
                    View Plans
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {acceptError && (
            <Alert variant="destructive">
              <AlertDescription>{acceptError}</AlertDescription>
            </Alert>
          )}
          {/* Invitation Details */}
          <div className="bg-muted/50 rounded-lg p-6 space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Organization</p>
              <div className="flex items-center gap-3">
                <Avatar className="h-12 w-12">
                  {invitation?.organization.logo_url ? (
                    <AvatarImage src={invitation.organization.logo_url} alt={invitation.organization.name} />
                  ) : null}
                  <AvatarFallback className="bg-primary/10 text-primary text-lg font-semibold">
                    {invitation?.organization.name.charAt(0) || 'O'}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-semibold text-lg">{invitation?.organization.name}</p>
                  <p className="text-sm text-muted-foreground">
                    Invited by: {invitation?.invited_by}
                  </p>
                </div>
              </div>
            </div>

            <div>
              <p className="text-sm text-muted-foreground mb-2">Your Role</p>
              <div className="flex items-center gap-2">
                {getRoleIcon(invitation?.role)}
                <Badge variant="outline" className="text-base px-3 py-1 capitalize">
                  {invitation?.role_display || invitation?.role}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                {getRoleDescription(invitation?.role)}
              </p>
            </div>
          </div>

          {/* What You'll Get */}
          <div className="space-y-3">
            <h3 className="font-semibold">What you'll be able to do:</h3>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm">Access organization events and courses</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm">Use organization branding and templates</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-sm">Collaborate with other team members</span>
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
