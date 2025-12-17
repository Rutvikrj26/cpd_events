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

urlpatterns = [
    # Authentication
    path('auth/signup/', views.SignupView.as_view(), name='signup'),
    path('auth/token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify-email/', views.EmailVerificationView.as_view(), name='verify_email'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/password-change/', views.PasswordChangeView.as_view(), name='password_change'),
    # Current user
    path('users/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('users/me/organizer-profile/', views.OrganizerProfileView.as_view(), name='organizer_profile'),
    path('users/me/notifications/', views.NotificationPreferencesView.as_view(), name='notifications'),
    path('users/me/upgrade/', views.UpgradeToOrganizerView.as_view(), name='upgrade'),
    path('users/me/delete-account/', views.DeleteAccountView.as_view(), name='delete_account'),
    path('users/me/export-data/', views.DataExportView.as_view(), name='export_data'),  # H6: GDPR
    # Public organizer profiles
    path('organizers/<uuid:uuid>/', views.PublicOrganizerView.as_view(), name='public_organizer'),
    # ViewSets
    path('', include(router.urls)),
]
