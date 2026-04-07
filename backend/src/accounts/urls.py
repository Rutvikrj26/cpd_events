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
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/password-change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('auth/manifest/', views.ManifestView.as_view(), name='manifest'),
    path('auth/accept-invitation/', views.AcceptInvitationView.as_view(), name='accept_invitation'),
    # OAuth
    path('auth/google/login/', views.GoogleAuthView.as_view(), name='google_auth'),
    path('auth/google/callback/', views.GoogleCallbackView.as_view(), name='google_callback'),
    # Current user
    path('users/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/me/notifications/', views.NotificationPreferencesView.as_view(), name='notifications'),
    path('users/me/delete-account/', views.DeleteAccountView.as_view(), name='delete_account'),
    path('users/me/export-data/', views.DataExportView.as_view(), name='export_data'),
    path('users/me/onboarding/complete/', views.CompleteOnboardingView.as_view(), name='complete_onboarding'),
    path('users/me/sessions/', views.UserSessionListView.as_view(), name='user_sessions'),
    path('users/me/sessions/logout-all/', views.UserSessionLogoutAllView.as_view(), name='user_sessions_logout_all'),
    path('users/me/sessions/<uuid:uuid>/', views.UserSessionRevokeView.as_view(), name='user_session_revoke'),
    # Admin user management
    path('admin/users/', views.AdminUserListCreateView.as_view(), name='admin_users'),
    path('admin/users/invite/', views.AdminInviteUserView.as_view(), name='admin_invite_user'),
    path('admin/users/bulk-invite/', views.AdminBulkInviteView.as_view(), name='admin_bulk_invite'),
    path('admin/users/<uuid:uuid>/', views.AdminUserUpdateView.as_view(), name='admin_user_detail'),
    path('admin/users/<uuid:uuid>/deactivate/', views.AdminUserDeactivateView.as_view(), name='admin_user_deactivate'),
    path('admin/invitations/', views.AdminInvitationListView.as_view(), name='admin_invitations'),
    path('', include(router.urls)),
]
