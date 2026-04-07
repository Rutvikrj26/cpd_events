"""
Accounts app views and viewsets.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from common.config.deployment import (
    DEPLOYMENT_MODE,
    INSTITUTION_LOGO_URL,
    INSTITUTION_NAME,
    REGISTRATION_MODE,
)
from common.rbac import roles
from common.utils import error_response

from . import cpd_serializers, serializers
from .models import CPDRequirement, Notification, UserSession

User = get_user_model()


# =============================================================================
# Throttle Classes
# =============================================================================


class AuthThrottle(AnonRateThrottle):
    """Stricter throttle for auth endpoints."""

    scope = "auth"


# =============================================================================
# Authentication Views
# =============================================================================


@roles("public", route_name="signup")
class SignupView(generics.CreateAPIView):
    """POST /api/v1/auth/signup/ - Create new user account."""

    serializer_class = serializers.SignupSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def create(self, request, *args, **kwargs):
        # Gate self-service registration based on deployment mode
        if REGISTRATION_MODE == "invite_only":
            return Response(
                {"error": {"code": "REGISTRATION_DISABLED", "message": "Registration is by invitation only. Contact your administrator."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if REGISTRATION_MODE == "admin_approval":
            # Create user but set inactive until admin approves
            user = serializer.save()
            user.is_active = False
            user.save(update_fields=["is_active"])
            return Response(
                {"message": "Registration submitted. An administrator will review and activate your account."},
                status=status.HTTP_201_CREATED,
            )

        user = serializer.save()

        # Generate verification token
        token = user.generate_email_verification_token()

        # Send verification email
        try:
            verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"

            print("\n" + "=" * 80)
            print("📧 VERIFICATION LINK (copy this, NOT the email body below):")
            print(f"   {verification_url}")
            print("=" * 80 + "\n")

            send_mail(
                subject="Verify your email address",
                message=f"Please click the following link to verify your email address: {verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send verification email to {user.email}: {e}")

        return Response(
            {
                "message": "Account created successfully. Please check your email to verify your account.",
                "user": {
                    "uuid": str(user.uuid),
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": user.role_names,
                },
            },
            status=status.HTTP_201_CREATED,
        )


@roles("public", route_name="token_obtain")
class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/token/ - Obtain JWT token pair."""

    serializer_class = serializers.CustomTokenObtainPairSerializer
    throttle_classes = [AuthThrottle]


@roles("public", route_name="email_verification")
class EmailVerificationView(generics.GenericAPIView):
    """POST /api/v1/auth/verify-email/ - Verify email with token."""

    serializer_class = serializers.EmailVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        try:
            user = User.objects.get(email_verification_token=token)

            if user.email_verified:
                from rest_framework_simplejwt.tokens import RefreshToken

                refresh = RefreshToken.for_user(user)

                return Response(
                    {
                        "message": "Email already verified.",
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                        "user": {
                            "uuid": str(user.uuid),
                            "email": user.email,
                            "full_name": user.full_name,
                            "roles": user.role_names,
                        },
                    }
                )

        except User.DoesNotExist:
            return Response(
                {"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired token."}}, status=status.HTTP_400_BAD_REQUEST
            )

        if user.email_verification_expires_at and user.email_verification_expires_at < timezone.now():
            return Response(
                {"error": {"code": "TOKEN_EXPIRED", "message": "Token has expired."}}, status=status.HTTP_400_BAD_REQUEST
            )

        user.email_verified = True
        user.email_verification_token = ""
        user.save(update_fields=["email_verified", "email_verification_token", "updated_at"])

        # Link any guest registrations
        from registrations.models import Registration

        Registration.link_registrations_for_user(user)

        # Generate JWT tokens for auto-login
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Email verified successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "uuid": str(user.uuid),
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": user.role_names,
                },
            }
        )


@roles("public", route_name="password_reset_request")
class PasswordResetRequestView(generics.GenericAPIView):
    """POST /api/v1/auth/password-reset/ - Request password reset."""

    serializer_class = serializers.PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email__iexact=email)
            user.generate_password_reset_token()

            from django.conf import settings

            from .tasks import send_password_reset

            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={user.password_reset_token}&email={user.email}"

            print("\n" + "=" * 80)
            print("🔐 PASSWORD RESET LINK (copy this, NOT the email body below):")
            print(f"   {reset_url}")
            print("=" * 80 + "\n")

            send_password_reset.delay(user.uuid, reset_url)
        except User.DoesNotExist:
            pass  # Don't reveal if email exists

        return Response({"message": "If an account exists, a password reset email has been sent."})


@roles("public", route_name="password_reset_confirm")
class PasswordResetConfirmView(generics.GenericAPIView):
    """POST /api/v1/auth/password-reset/confirm/ - Confirm password reset."""

    serializer_class = serializers.PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(password_reset_token=token)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return error_response("Invalid or expired token.", code="INVALID_TOKEN")

        user.set_password(password)
        user.password_reset_token = ""
        user.save(update_fields=["password", "password_reset_token", "updated_at"])

        return Response({"message": "Password reset successfully."})


@roles("learner", "educator", "course_manager", "admin", route_name="password_change")
class PasswordChangeView(generics.GenericAPIView):
    """POST /api/v1/auth/password-change/ - Change password."""

    serializer_class = serializers.PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])

        return Response({"message": "Password changed successfully."})


# =============================================================================
# Session Management Views
# =============================================================================


@roles("learner", "educator", "course_manager", "admin", route_name="user_sessions")
class UserSessionListView(generics.ListAPIView):
    """GET /api/v1/users/me/sessions/ - List active sessions."""

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True).order_by("-last_activity_at")


@roles("learner", "educator", "course_manager", "admin", route_name="user_session_revoke")
class UserSessionRevokeView(generics.DestroyAPIView):
    """DELETE /api/v1/users/me/sessions/{uuid}/ - Revoke a specific session."""

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSessionSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.deactivate()


@roles("learner", "educator", "course_manager", "admin", route_name="user_sessions_logout_all")
class UserSessionLogoutAllView(generics.GenericAPIView):
    """POST /api/v1/users/me/sessions/logout-all/ - Logout from all sessions."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        UserSession.deactivate_all_for_user(request.user)
        return Response({"message": "Logged out from all sessions."})


# =============================================================================
# User Profile Views
# =============================================================================


@roles("learner", "educator", "course_manager", "admin", route_name="current_user")
class CurrentUserView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/ - Current user profile."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return serializers.UserProfileUpdateSerializer
        return serializers.UserSerializer

    def get_object(self):
        return self.request.user


@roles("learner", "educator", "course_manager", "admin", route_name="notification_preferences")
class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/notifications/ - Notification preferences."""

    serializer_class = serializers.NotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@roles("learner", "educator", "course_manager", "admin", route_name="user_notifications")
class UserNotificationViewSet(viewsets.ModelViewSet):
    """User notification inbox."""

    serializer_class = serializers.NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "delete", "post"]
    lookup_field = "uuid"

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user).order_by("-created_at")
        status_filter = self.request.query_params.get("status")
        if status_filter == "unread":
            queryset = queryset.filter(read_at__isnull=True)
        return queryset

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        """Mark all notifications as read."""
        now = timezone.now()
        updated = Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=now, updated_at=now)
        return Response({"read_count": updated})

    @action(detail=True, methods=["post"], url_path="read")
    def read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.mark_read()
        return Response(self.get_serializer(notification).data)


# =============================================================================
# Account Deletion (GDPR)
# =============================================================================


@roles("learner", "educator", "course_manager", "admin", route_name="delete_account")
class DeleteAccountView(generics.GenericAPIView):
    """POST /api/v1/users/me/delete-account/ - Delete/anonymize account."""

    serializer_class = serializers.DeleteAccountSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        serializer.validated_data.get("reason", "")

        user.anonymize()

        return Response({"message": "Account has been deleted."})


# =============================================================================
# GDPR Data Export
# =============================================================================


@roles("learner", "educator", "course_manager", "admin", route_name="data_export")
class DataExportView(generics.GenericAPIView):
    """POST /api/v1/users/me/export-data/ - Request GDPR data export."""

    serializer_class = serializers.DataExportSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import json

        from django.http import HttpResponse

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        options = serializer.validated_data
        export_format = options.get("format", "json")

        export_data = {
            "user": {
                "uuid": str(user.uuid),
                "email": user.email,
                "full_name": user.full_name,
                "professional_title": user.professional_title,
                "organization_name": user.organization_name,
                "bio": user.bio,
                "roles": user.role_names,
                "timezone": user.timezone,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        }

        if options.get("include_registrations", True):
            from registrations.models import Registration

            registrations = Registration.all_objects.filter(user=user)
            export_data["registrations"] = [
                {
                    "uuid": str(r.uuid),
                    "event_title": r.event.title if r.event else None,
                    "email": r.email,
                    "full_name": r.full_name,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "attended": r.attended,
                    "attendance_eligible": r.attendance_eligible,
                }
                for r in registrations
            ]

        if options.get("include_certificates", True):
            from certificates.models import Certificate

            certificates = Certificate.objects.filter(registration__user=user)
            export_data["certificates"] = [
                {
                    "uuid": str(c.uuid),
                    "event_title": c.registration.event.title if c.registration and c.registration.event else None,
                    "credential_id": c.credential_id,
                    "cpd_credits": str(c.cpd_credits) if c.cpd_credits else None,
                    "issued_at": c.issued_at.isoformat() if c.issued_at else None,
                }
                for c in certificates
            ]

        if options.get("include_attendance", True):
            from registrations.models import AttendanceRecord

            attendance = AttendanceRecord.objects.filter(registration__user=user)
            export_data["attendance_records"] = [
                {
                    "event_title": a.event.title if a.event else None,
                    "join_time": a.join_time.isoformat() if a.join_time else None,
                    "leave_time": a.leave_time.isoformat() if a.leave_time else None,
                    "duration_minutes": a.duration_minutes,
                }
                for a in attendance
            ]

        if export_format == "json":
            response = HttpResponse(
                json.dumps(export_data, indent=2, default=str),
                content_type="application/json",
            )
            response["Content-Disposition"] = f'attachment; filename="data_export_{user.uuid}.json"'
            return response

        return Response(export_data)


# =============================================================================
# Onboarding Completion
# =============================================================================


@roles("learner", "educator", "course_manager", "admin", route_name="complete_onboarding")
class CompleteOnboardingView(generics.GenericAPIView):
    """POST /api/v1/users/me/onboarding/complete/ - Mark onboarding as complete."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.onboarding_completed:
            user.onboarding_completed = True
            user.save(update_fields=["onboarding_completed", "updated_at"])

        return Response(
            {
                "message": "Onboarding completed.",
                "onboarding_completed": user.onboarding_completed,
            }
        )


# =============================================================================
# CPD Requirement Views
# =============================================================================


@roles("learner", "educator", "course_manager", "admin", route_name="cpd_requirements")
class CPDRequirementViewSet(viewsets.ModelViewSet):
    """
    CRUD for user CPD requirements.
    GET /api/v1/cpd-requirements/
    POST /api/v1/cpd-requirements/
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return cpd_serializers.CPDRequirementCreateSerializer
        return cpd_serializers.CPDRequirementSerializer

    def get_queryset(self):
        return CPDRequirement.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="CPD progress",
        operation_description="Get CPD progress summary across all requirements.",
    )
    @action(detail=False, methods=["get"])
    def progress(self, request):
        """Get CPD progress summary."""
        requirements = self.get_queryset()

        from decimal import Decimal

        total_credits = request.user.total_cpd_credits or Decimal("0")

        data = {
            "total_requirements": requirements.count(),
            "completed_requirements": sum(1 for r in requirements if r.completion_percent >= 100),
            "in_progress_requirements": sum(1 for r in requirements if 0 < r.completion_percent < 100),
            "total_credits_earned": total_credits,
            "requirements": cpd_serializers.CPDRequirementSerializer(requirements, many=True).data,
        }
        return Response(data)

    @swagger_auto_schema(
        operation_summary="Export CPD report",
        operation_description="Export CPD report in various formats. Use export_format=json|csv|txt.",
    )
    @action(detail=False, methods=["get"])
    def export(self, request):
        """Export CPD report."""
        from datetime import datetime

        from .cpd_export_service import CPDExportService

        export_format = request.query_params.get("export_format", "json").lower()
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        cpd_type = request.query_params.get("cpd_type")

        filters = {}
        if start_date:
            try:
                filters["start_date"] = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid start_date format. Use YYYY-MM-DD."}, status=400)
        if end_date:
            try:
                filters["end_date"] = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid end_date format. Use YYYY-MM-DD."}, status=400)
        if cpd_type:
            filters["cpd_type"] = cpd_type

        service = CPDExportService(request.user)

        if export_format == "csv":
            return service.export_csv(**filters)
        elif export_format == "txt":
            return service.export_txt(**filters)
        elif export_format == "pdf":
            return service.export_pdf(**filters)
        else:
            return service.export_json(**filters)


# =============================================================================
# RBAC Manifest View
# =============================================================================


@roles("learner", "educator", "course_manager", "admin", route_name="manifest")
class ManifestView(generics.GenericAPIView):
    """
    GET /api/v1/auth/manifest/

    Returns the allowed routes and features for the current user.
    Used by frontend to determine which UI elements to show.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get user manifest",
        operation_description="Returns allowed routes and features for the authenticated user.",
    )
    def get(self, request):
        from common.rbac import get_allowed_routes_for_user, get_features_for_user

        user = request.user

        data = {
            "routes": get_allowed_routes_for_user(user),
            "features": get_features_for_user(user),
            "user": {
                "roles": user.role_names,
                "primary_role": user.primary_role,
                "is_staff": user.is_staff,
            },
            "deployment": {
                "mode": DEPLOYMENT_MODE,
                "registration_mode": REGISTRATION_MODE,
                "institution_name": INSTITUTION_NAME,
                "institution_logo_url": INSTITUTION_LOGO_URL,
            },
        }

        return Response(data)


# =============================================================================
# Google OAuth Views
# =============================================================================


@roles("public", route_name="google_auth")
class GoogleAuthView(generics.GenericAPIView):
    """
    GET /api/v1/auth/google/login/

    Returns the Google OAuth authorization URL for user to authenticate.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get(self, request):
        import secrets

        from django.core.cache import cache

        from .google_oauth import get_google_auth_url

        state = secrets.token_urlsafe(32)
        cache.set(f"oauth_state:{state}", True, timeout=600)  # valid for 10 minutes
        url = get_google_auth_url(state=state)
        return Response({"url": url})


@roles("public", route_name="google_callback")
class GoogleCallbackView(generics.GenericAPIView):
    """
    GET /api/v1/auth/google/callback/

    Handles the OAuth callback from Google.
    Exchanges code for tokens, gets user info, logs in or creates user.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get(self, request):
        from django.core.cache import cache

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        if error:
            return error_response(f"Google OAuth error: {error}", code="GOOGLE_AUTH_ERROR")

        if not code:
            return error_response("Authorization code missing.", code="MISSING_CODE")

        # Validate CSRF state parameter
        if not state or not cache.get(f"oauth_state:{state}"):
            return error_response("Invalid or expired state parameter.", code="INVALID_STATE")
        cache.delete(f"oauth_state:{state}")  # single-use

        from django.conf import settings
        from django.db import transaction
        from rest_framework_simplejwt.tokens import RefreshToken

        from .google_oauth import exchange_code_for_token, get_google_user_info
        from .models import User

        # 1. Exchange code for tokens
        token_data = exchange_code_for_token(code)
        if not token_data:
            return error_response("Failed to exchange code for token.", code="TOKEN_EXCHANGE_FAILED")

        access_token = token_data.get("access_token")

        # 2. Get user info from Google
        user_info = get_google_user_info(access_token)
        if not user_info:
            return error_response("Failed to fetch user info from Google.", code="USER_INFO_FAILED")

        google_user_id = user_info.get("id")
        email = user_info.get("email", "").lower()
        name = user_info.get("name", "")
        given_name = user_info.get("given_name", "")
        family_name = user_info.get("family_name", "")
        picture = user_info.get("picture", "")
        email_verified = user_info.get("verified_email", False)

        if not email:
            return error_response("Google account must have an email address.", code="MISSING_EMAIL")

        if not email_verified:
            return error_response("Google email must be verified.", code="EMAIL_NOT_VERIFIED")

        full_name = name or f"{given_name} {family_name}".strip() or email.split("@")[0]

        # 3. Find or create user
        with transaction.atomic():
            user = User.objects.filter(google_user_id=google_user_id).first()

            if user:
                pass  # Existing Google user - just log them in
            else:
                user = User.objects.filter(email=email).first()

                if user:
                    # Link Google account to existing user
                    user.google_user_id = google_user_id
                    if not user.email_verified:
                        user.email_verified = True
                        user.email_verified_at = timezone.now()
                    if user.auth_provider == "local":
                        user.auth_provider = "google"
                    if picture and not user.profile_photo_url:
                        user.profile_photo_url = picture
                    user.save(
                        update_fields=[
                            "google_user_id",
                            "email_verified",
                            "email_verified_at",
                            "auth_provider",
                            "profile_photo_url",
                            "updated_at",
                        ]
                    )
                else:
                    # Check registration mode
                    if REGISTRATION_MODE == "invite_only":
                        return error_response(
                            "Registration is by invitation only. Contact your administrator.",
                            code="REGISTRATION_DISABLED",
                        )

                    # Create new user with Google OAuth
                    user = User.objects.create_user(
                        email=email,
                        full_name=full_name,
                        email_verified=True,
                        password=None,
                        google_user_id=google_user_id,
                        auth_provider="google",
                        profile_photo_url=picture,
                    )
                    # Assign default learner role
                    user.assign_role("learner")

            if not user.is_active:
                return error_response("Account is disabled.", code="ACCOUNT_DISABLED")

            # Link any guest registrations
            from registrations.models import Registration

            Registration.link_registrations_for_user(user)

            user.record_login()

            # 4. Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            # 5. Redirect to frontend with tokens
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else "http://localhost:5173"
            redirect_url = f"{frontend_url}/auth/callback?access={str(refresh.access_token)}&refresh={str(refresh)}"

            from django.http import HttpResponseRedirect

            return HttpResponseRedirect(redirect_url)


# =============================================================================
# Admin User Management Views
# =============================================================================


@roles("admin", route_name="admin_users")
class AdminUserListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/admin/users/ - List all users (admin only)
    POST /api/v1/admin/users/ - Create user directly (admin only)
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializers.AdminUserCreateSerializer
        return serializers.AdminUserListSerializer

    def get_queryset(self):
        qs = User.objects.filter(deleted_at__isnull=True).order_by("-created_at")
        # Search/filter
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                models.Q(email__icontains=search) |
                models.Q(full_name__icontains=search)
            )
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(groups__name=role)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs.distinct()


@roles("admin", route_name="admin_user_detail")
class AdminUserUpdateView(generics.RetrieveUpdateAPIView):
    """
    GET /api/v1/admin/users/{uuid}/ - Get user details
    PATCH /api/v1/admin/users/{uuid}/ - Update user role/status
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return serializers.AdminUserUpdateSerializer
        return serializers.AdminUserListSerializer

    def get_queryset(self):
        return User.objects.filter(deleted_at__isnull=True)


@roles("admin", route_name="admin_user_deactivate")
class AdminUserDeactivateView(generics.GenericAPIView):
    """POST /api/v1/admin/users/{uuid}/deactivate/ - Deactivate a user."""

    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        return User.objects.filter(deleted_at__isnull=True)

    def post(self, request, uuid):
        user = self.get_queryset().get(uuid=uuid)
        if user == request.user:
            return error_response("You cannot deactivate your own account.", code="SELF_DEACTIVATE")
        user.is_active = not user.is_active
        user.save(update_fields=["is_active", "updated_at"])
        action = "activated" if user.is_active else "deactivated"
        return Response({"message": f"User {action} successfully.", "is_active": user.is_active})


@roles("admin", route_name="admin_invite_user")
class AdminInviteUserView(generics.GenericAPIView):
    """POST /api/v1/admin/users/invite/ - Send invitation to a new user."""

    serializer_class = serializers.InviteUserSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .models import UserInvitation

        invitation = UserInvitation.create_invitation(
            email=serializer.validated_data["email"],
            full_name=serializer.validated_data["full_name"],
            role=serializer.validated_data["role"],
            invited_by=request.user,
            message=serializer.validated_data.get("message", ""),
        )

        # Send invitation email
        try:
            invite_url = f"{settings.FRONTEND_URL}/auth/accept-invitation?token={invitation.token}"

            print("\n" + "=" * 80)
            print("📧 INVITATION LINK (copy this, NOT the email body below):")
            print(f"   {invite_url}")
            print("=" * 80 + "\n")

            send_mail(
                subject=f"You've been invited to {INSTITUTION_NAME}",
                message=(
                    f"Hello {invitation.full_name},\n\n"
                    f"You've been invited to join {INSTITUTION_NAME}.\n\n"
                    f"Click the following link to set up your account:\n{invite_url}\n\n"
                    f"This invitation expires in 7 days.\n\n"
                    f"{invitation.message}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=False,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send invitation email to {invitation.email}: {e}")

        return Response(
            {
                "message": f"Invitation sent to {invitation.email}.",
                "invitation": serializers.UserInvitationSerializer(invitation).data,
            },
            status=status.HTTP_201_CREATED,
        )


@roles("admin", route_name="admin_bulk_invite")
class AdminBulkInviteView(generics.GenericAPIView):
    """POST /api/v1/admin/users/bulk-invite/ - Bulk invite users."""

    serializer_class = serializers.BulkInviteSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .models import UserInvitation

        results = []
        for invite_data in serializer.validated_data["invitations"]:
            # Skip if user already exists
            if User.objects.filter(email__iexact=invite_data["email"]).exists():
                results.append({"email": invite_data["email"], "status": "skipped", "reason": "User already exists"})
                continue

            invitation = UserInvitation.create_invitation(
                email=invite_data["email"],
                full_name=invite_data["full_name"],
                role=invite_data.get("role", "learner"),
                invited_by=request.user,
                message=invite_data.get("message", ""),
            )

            # Send email (best effort)
            try:
                invite_url = f"{settings.FRONTEND_URL}/auth/accept-invitation?token={invitation.token}"
                send_mail(
                    subject=f"You've been invited to {INSTITUTION_NAME}",
                    message=f"Hello {invitation.full_name},\n\nYou've been invited to join {INSTITUTION_NAME}.\n\nSet up your account: {invite_url}\n\nThis invitation expires in 7 days.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[invitation.email],
                    fail_silently=True,
                )
                results.append({"email": invite_data["email"], "status": "sent"})
            except Exception:
                results.append({"email": invite_data["email"], "status": "created", "reason": "Email failed"})

        return Response({"results": results, "total": len(results)}, status=status.HTTP_201_CREATED)


@roles("admin", route_name="admin_invitations")
class AdminInvitationListView(generics.ListAPIView):
    """GET /api/v1/admin/invitations/ - List all invitations."""

    serializer_class = serializers.UserInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import UserInvitation
        return UserInvitation.objects.all().order_by("-created_at")


# =============================================================================
# Invitation Acceptance (Public)
# =============================================================================


@roles("public", route_name="accept_invitation")
class AcceptInvitationView(generics.GenericAPIView):
    """
    POST /api/v1/auth/accept-invitation/

    Public endpoint. Validates invitation token, creates user account,
    assigns role, returns JWT tokens.
    """

    serializer_class = serializers.AcceptInvitationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .models import UserInvitation

        token = serializer.validated_data["token"]

        try:
            invitation = UserInvitation.objects.get(token=token)
        except UserInvitation.DoesNotExist:
            return error_response("Invalid invitation token.", code="INVALID_TOKEN")

        if not invitation.is_valid:
            if invitation.is_used:
                return error_response("This invitation has already been used.", code="INVITATION_USED")
            return error_response("This invitation has expired.", code="INVITATION_EXPIRED")

        # Check if user already exists
        if User.objects.filter(email__iexact=invitation.email).exists():
            return error_response("An account with this email already exists.", code="USER_EXISTS")

        # Create user
        user = User.objects.create_user(
            email=invitation.email,
            full_name=invitation.full_name,
            password=serializer.validated_data["password"],
            email_verified=True,
        )

        # Assign role from invitation
        user.assign_role(invitation.role)

        # Mark invitation as accepted
        invitation.accept(user)

        # Generate JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Account created successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "uuid": str(user.uuid),
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": user.role_names,
                },
            },
            status=status.HTTP_201_CREATED,
        )
