"""
Accounts app URL routing.
"""

from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'accounts'

router = SimpleRouter()
router.register(r'cpd-requirements', views.CPDRequirementViewSet, basename='cpd-requirement')
router.register(r'users/me/notifications/inbox', views.UserNotificationViewSet, basename='user-notifications')

urlpatterns = [
    # Authentication
    path('auth/signup/', views.SignupView.as_view(), name='signup'),
    path('auth/token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    path('auth/resend-verification/', views.ResendVerificationEmailView.as_view(), name='resend_verification'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/password-change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('auth/email-change/confirm/', views.EmailChangeConfirmView.as_view(), name='email_change_confirm'),
    path('auth/manifest/', views.ManifestView.as_view(), name='manifest'),
    path('auth/deployment/', views.DeploymentConfigView.as_view(), name='deployment_config'),
    path('auth/accept-invitation/', views.AcceptInvitationView.as_view(), name='accept_invitation'),
    path('auth/firebase/', views.FirebaseAuthView.as_view(), name='firebase_auth'),
    # Current user
    path('users/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/me/notifications/', views.NotificationPreferencesView.as_view(), name='notifications'),
    path('users/me/accreditations/', views.MyAccreditationsView.as_view(), name='my_accreditations'),
    path('users/me/delete-account/', views.DeleteAccountView.as_view(), name='delete_account'),
    path('users/me/export-data/', views.DataExportView.as_view(), name='export_data'),
    path('users/me/onboarding/complete/', views.CompleteOnboardingView.as_view(), name='complete_onboarding'),
    path('users/me/email-change/request/', views.EmailChangeRequestView.as_view(), name='email_change_request'),
    path('users/me/sessions/', views.UserSessionListView.as_view(), name='user_sessions'),
    path('users/me/sessions/logout-all/', views.UserSessionLogoutAllView.as_view(), name='user_sessions_logout_all'),
    path('users/me/sessions/<uuid:uuid>/', views.UserSessionRevokeView.as_view(), name='user_session_revoke'),
    # Admin user management
    path('admin/users/', views.AdminUserListView.as_view(), name='admin_users'),
    path('admin/users/invite/', views.AdminInviteUserView.as_view(), name='admin_invite_user'),
    path('admin/users/bulk-invite/', views.AdminBulkInviteView.as_view(), name='admin_bulk_invite'),
    path('admin/users/<uuid:uuid>/detail/', views.AdminUserDetailView.as_view(), name='admin_user_detail_full'),
    path('admin/users/<uuid:uuid>/', views.AdminUserUpdateView.as_view(), name='admin_user_detail'),
    path('admin/users/<uuid:uuid>/deactivate/', views.AdminUserDeactivateView.as_view(), name='admin_user_deactivate'),
    path('admin/users/invitations/', views.AdminInvitationListView.as_view(), name='admin_invitations'),
    path('admin/users/invitations/<uuid:uuid>/resend/', views.AdminInvitationResendView.as_view(), name='admin_invitation_resend'),
    path('admin/users/invitations/<uuid:uuid>/revoke/', views.AdminInvitationRevokeView.as_view(), name='admin_invitation_revoke'),
    # Learning invitations (event/course invites — distinct from user
    # platform-join invites above). Public GET/POST is at /public/...;
    # host-only resend/cancel is on the row itself.
    path('public/invitations/<uuid:uuid>/', views.PublicLearningInvitationView.as_view(), name='public_learning_invitation'),
    path('public/invitations/<uuid:uuid>/accept/', views.PublicLearningInvitationAcceptView.as_view(), name='public_learning_invitation_accept'),
    path('invitations/<uuid:uuid>/resend/', views.LearningInvitationResendView.as_view(), name='learning_invitation_resend'),
    path('invitations/<uuid:uuid>/cancel/', views.LearningInvitationCancelView.as_view(), name='learning_invitation_cancel'),
    # Magic links (registration claim + email sign-in). Public verify/accept;
    # sign-in-link request lives under /auth/ so it sits next to other
    # auth endpoints in the API surface.
    path('public/magic-link/<uuid:uuid>/verify/', views.MagicLinkVerifyView.as_view(), name='magic_link_verify'),
    path('public/magic-link/<uuid:uuid>/accept/', views.MagicLinkAcceptView.as_view(), name='magic_link_accept'),
    path('auth/sign-in-link/', views.EmailSignInRequestView.as_view(), name='email_sign_in_request'),
    path('auth/find-my-registration/', views.FindMyRegistrationView.as_view(), name='find_my_registration'),
    path('', include(router.urls)),
]
