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
from .tasks import send_email_verification

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
    """POST /api/v1/auth/signup/ - Disabled self-service signup endpoint."""

    serializer_class = serializers.SignupSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "error": {
                    "code": "REGISTRATION_DISABLED",
                    "message": "Registration is by invitation only. Contact your administrator.",
                }
            },
            status=status.HTTP_403_FORBIDDEN,
        )


@roles("public", route_name="resend_verification")
class ResendVerificationEmailView(generics.GenericAPIView):
    """POST /api/v1/auth/resend-verification/ - Resend email verification link."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        generic_response = {
            "message": "If an unverified account exists for that email, a new verification link has been sent."
        }

        if not email:
            return error_response("Email is required.", code="EMAIL_REQUIRED", status_code=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email).first()
        if user is None or user.email_verified:
            return Response(generic_response, status=status.HTTP_200_OK)

        token = user.generate_email_verification_token()
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        send_email_verification(user.uuid, verification_url)

        return Response(generic_response, status=status.HTTP_200_OK)


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


@roles("learner", "organizer", "instructor", "admin", route_name="password_change")
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
# Email Change (Self-service)
# =============================================================================


EMAIL_CHANGE_TOKEN_HOURS = 24


@roles("learner", "organizer", "instructor", "admin", route_name="email_change_request")
class EmailChangeRequestView(generics.GenericAPIView):
    """POST /api/v1/users/me/email-change/request/

    Starts a self-service email change. Requires current-password reauth.
    Stores the desired email on the user as `pending_email` and sends a
    confirmation link to that new address. Also notifies the old address so
    the user can react if the request wasn't them.
    """

    serializer_class = serializers.EmailChangeRequestSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .audit import log_audit_event
        from common.utils import generate_verification_code

        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_email = serializer.validated_data["new_email"]

        user.pending_email = new_email
        user.email_change_token = generate_verification_code(48)
        user.email_change_requested_at = timezone.now()
        user.save(update_fields=[
            "pending_email",
            "email_change_token",
            "email_change_requested_at",
            "updated_at",
        ])

        confirm_url = f"{settings.FRONTEND_URL}/auth/confirm-email-change?token={user.email_change_token}"

        print("\n" + "=" * 80)
        print("📧 EMAIL CHANGE CONFIRMATION LINK:")
        print(f"   {confirm_url}")
        print("=" * 80 + "\n")

        # Confirmation to the NEW address
        try:
            send_mail(
                subject=f"Confirm your new email for {INSTITUTION_NAME}",
                message=(
                    f"Hello {user.full_name},\n\n"
                    f"A request was made to change your {INSTITUTION_NAME} email "
                    f"to this address. Click the link below to confirm:\n\n"
                    f"{confirm_url}\n\n"
                    f"This link expires in {EMAIL_CHANGE_TOKEN_HOURS} hours.\n\n"
                    f"If you didn't request this, you can ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[new_email],
                fail_silently=True,
            )
        except Exception:
            pass

        # Notification to the OLD address
        try:
            send_mail(
                subject=f"Email change requested on your {INSTITUTION_NAME} account",
                message=(
                    f"Hello {user.full_name},\n\n"
                    f"A request was made to change your {INSTITUTION_NAME} email "
                    f"from {user.email} to {new_email}.\n\n"
                    f"If this wasn't you, contact your institution administrator "
                    f"immediately — someone may have access to your account."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        log_audit_event(
            actor=user,
            action="email_change_requested",
            object_type="User",
            object_uuid=str(user.uuid),
            metadata={"from": user.email, "to": new_email},
            request=request,
        )

        return Response(
            {
                "message": f"Confirmation link sent to {new_email}.",
                "pending_email": new_email,
            }
        )


@roles("public", route_name="email_change_confirm")
class EmailChangeConfirmView(generics.GenericAPIView):
    """POST /api/v1/auth/email-change/confirm/

    Public endpoint. Validates the token, swaps `email` with `pending_email`,
    re-links any guest Registrations for the new address, and invalidates
    all refresh tokens so every device must log in again.
    """

    serializer_class = serializers.EmailChangeConfirmSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        from django.db import IntegrityError
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        from .audit import log_audit_event

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        try:
            user = User.objects.get(email_change_token=token)
        except User.DoesNotExist:
            return error_response("Invalid or expired token.", code="INVALID_TOKEN")

        # Atomic claim: blank the token in a single UPDATE that still matches
        # the incoming value. If two requests arrive concurrently (React
        # double-submit, client retry), only the first UPDATE affects a row;
        # the loser sees rowcount 0 and bails instead of duplicating the email
        # swap and the audit log entry.
        claimed = User.objects.filter(pk=user.pk, email_change_token=token).update(email_change_token="")
        if claimed == 0:
            return error_response("Invalid or expired token.", code="INVALID_TOKEN")
        user.email_change_token = ""

        if not user.pending_email or not user.email_change_requested_at:
            return error_response("No email change is pending.", code="NO_PENDING_CHANGE")

        expiry = user.email_change_requested_at + timezone.timedelta(hours=EMAIL_CHANGE_TOKEN_HOURS)
        if timezone.now() > expiry:
            return error_response("This email change link has expired.", code="TOKEN_EXPIRED")

        new_email = user.pending_email
        old_email = user.email

        # Cheap pre-check so we can surface a friendly error before the DB
        # raises. The real guarantee is the unique constraint on User.email.
        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            user.pending_email = ""
            user.email_change_token = ""
            user.email_change_requested_at = None
            user.save(update_fields=[
                "pending_email",
                "email_change_token",
                "email_change_requested_at",
                "updated_at",
            ])
            return error_response(
                "This email is now in use by another account.",
                code="EMAIL_TAKEN",
            )

        user.email = new_email
        user.pending_email = ""
        user.email_change_token = ""
        user.email_change_requested_at = None
        user.email_verified = True
        user.email_verified_at = timezone.now()
        try:
            user.save(update_fields=[
                "email",
                "pending_email",
                "email_change_token",
                "email_change_requested_at",
                "email_verified",
                "email_verified_at",
                "updated_at",
            ])
        except IntegrityError:
            # Someone claimed the email between the pre-check and save.
            return error_response(
                "This email is now in use by another account.",
                code="EMAIL_TAKEN",
            )

        # Link any guest registrations whose email now matches. Best-effort —
        # failures here must not roll back the email swap.
        try:
            from registrations.models import Registration

            Registration.link_registrations_for_user(user)
        except Exception:
            pass

        # Invalidate all outstanding refresh tokens for this user so every
        # device has to log in again with the new email. Best-effort.
        try:
            for ot in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=ot)
        except Exception:
            pass

        log_audit_event(
            actor=user,
            action="email_change_confirmed",
            object_type="User",
            object_uuid=str(user.uuid),
            metadata={"from": old_email, "to": new_email},
            request=request,
        )

        return Response({"message": "Email address updated. Please log in again."})


# =============================================================================
# Session Management Views
# =============================================================================


@roles("learner", "organizer", "instructor", "admin", route_name="user_sessions")
class UserSessionListView(generics.ListAPIView):
    """GET /api/v1/users/me/sessions/ - List active sessions."""

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True).order_by("-last_activity_at")


@roles("learner", "organizer", "instructor", "admin", route_name="user_session_revoke")
class UserSessionRevokeView(generics.DestroyAPIView):
    """DELETE /api/v1/users/me/sessions/{uuid}/ - Revoke a specific session."""

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSessionSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.deactivate()


@roles("learner", "organizer", "instructor", "admin", route_name="user_sessions_logout_all")
class UserSessionLogoutAllView(generics.GenericAPIView):
    """POST /api/v1/users/me/sessions/logout-all/ - Logout from all sessions."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        UserSession.deactivate_all_for_user(request.user)
        return Response({"message": "Logged out from all sessions."})


# =============================================================================
# User Profile Views
# =============================================================================


@roles("learner", "organizer", "instructor", "admin", route_name="current_user")
class CurrentUserView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/ - Current user profile."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return serializers.UserProfileUpdateSerializer
        return serializers.UserSerializer

    def get_object(self):
        return self.request.user


@roles("learner", "organizer", "instructor", "admin", route_name="notification_preferences")
class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/notifications/ - Notification preferences."""

    serializer_class = serializers.NotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@roles("learner", "organizer", "instructor", "admin", route_name="my_accreditations")
class MyAccreditationsView(generics.GenericAPIView):
    """GET /api/v1/users/me/accreditations/

    Unified list of a learner's earned artifacts — certificates and badges —
    normalized into a common envelope so the UI can render them side by side
    without issuing two round-trips and reconciling schemas.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q

        from badges.models import IssuedBadge
        from certificates.models import Certificate

        user = request.user

        certs = (
            Certificate.objects.filter(
                Q(registration__user=user) | Q(course_enrollment__user=user),
                deleted_at__isnull=True,
                status=Certificate.Status.ACTIVE,
            )
            .select_related(
                'template',
                'registration__event',
                'course_enrollment__course',
            )
        )

        badges = (
            IssuedBadge.objects.filter(
                recipient=user,
                deleted_at__isnull=True,
                status=IssuedBadge.Status.ACTIVE,
            )
            .select_related('template', 'registration__event', 'course_enrollment__course')
        )

        items = []
        for cert in certs:
            event = cert.registration.event if cert.registration_id else None
            course = cert.course_enrollment.course if cert.course_enrollment_id else None
            items.append(
                {
                    'kind': 'certificate',
                    'uuid': str(cert.uuid),
                    'title': cert.template.name if cert.template_id else 'Certificate',
                    'source_title': event.title if event else (course.title if course else ''),
                    'source_kind': 'event' if event else ('course' if course else None),
                    'issued_at': cert.created_at.isoformat(),
                    'verification_code': cert.verification_code,
                    'verify_url': cert.get_verification_url() if hasattr(cert, 'get_verification_url') else None,
                    'artifact_url': cert.file_url or None,
                    'short_code': cert.short_code,
                }
            )

        for badge in badges:
            event = badge.registration.event if badge.registration_id else None
            course = badge.course_enrollment.course if badge.course_enrollment_id else None
            items.append(
                {
                    'kind': 'badge',
                    'uuid': str(badge.uuid),
                    'title': badge.template.name if badge.template_id else 'Badge',
                    'source_title': event.title if event else (course.title if course else ''),
                    'source_kind': 'event' if event else ('course' if course else None),
                    'issued_at': badge.issued_at.isoformat(),
                    'verification_code': badge.verification_code,
                    'verify_url': None,
                    'artifact_url': badge.image_url or None,
                    'short_code': badge.short_code,
                }
            )

        items.sort(key=lambda item: item['issued_at'], reverse=True)
        return Response({'count': len(items), 'results': items})

    def get_object(self):
        return self.request.user


@roles("learner", "organizer", "instructor", "admin", route_name="user_notifications")
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


@roles("learner", "organizer", "instructor", "admin", route_name="delete_account")
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


@roles("learner", "organizer", "instructor", "admin", route_name="data_export")
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


@roles("learner", "organizer", "instructor", "admin", route_name="complete_onboarding")
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


@roles("learner", "organizer", "instructor", "admin", route_name="cpd_requirements")
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


@roles("learner", "organizer", "instructor", "admin", route_name="manifest")
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

        from common.config.deployment import get_branding

        data = {
            "routes": get_allowed_routes_for_user(user),
            "features": get_features_for_user(user),
            "user": {
                "roles": user.role_names,
                "primary_role": user.primary_role,
            },
            "deployment": {
                "mode": DEPLOYMENT_MODE,
                "registration_mode": REGISTRATION_MODE,
                **get_branding(),
            },
        }

        return Response(data)


# =============================================================================
# Public Deployment Config
# =============================================================================


@roles("public", route_name="deployment_config")
class DeploymentConfigView(generics.GenericAPIView):
    """GET /api/v1/auth/deployment/ - Public deployment metadata.

    Exposed to unauthenticated clients so login pages can gate UI
    (e.g. hide the signup form when the institution is invite-only).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from common.config.deployment import get_branding

        return Response(
            {
                "mode": DEPLOYMENT_MODE,
                "registration_mode": REGISTRATION_MODE,
                **get_branding(),
            }
        )


# =============================================================================
# Admin User Management Views
# =============================================================================


@roles("admin", route_name="admin_users")
class AdminUserListView(generics.ListAPIView):
    """
    GET /api/v1/admin/users/ - List all users (admin only).

    POST is intentionally not supported — use the invitation flow instead
    (`POST /admin/users/invite/` or `POST /admin/users/bulk-invite/`).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.AdminUserListSerializer

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


@roles("admin", route_name="admin_user_detail_full")
class AdminUserDetailView(generics.GenericAPIView):
    """GET /api/v1/admin/users/{uuid}/detail/

    Aggregated detail view for the admin user management UI. Returns profile,
    group memberships, per-course staff assignments, owned events and courses,
    recent certificates, recent activity, and pending invitation (if any) in
    a single response so the admin user detail page can render without N+1s.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get(self, request, uuid):
        from certificates.models import Certificate
        from events.models import Event
        from learning.models import Course, CourseStaff
        from .models import AuditLog, UserInvitation, UserRoleChange

        try:
            user = User.objects.filter(deleted_at__isnull=True).get(uuid=uuid)
        except User.DoesNotExist:
            return error_response("User not found.", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

        profile = serializers.AdminUserListSerializer(user).data

        course_staff_rows = CourseStaff.objects.filter(user=user).select_related("course")[:50]
        course_staff = [
            {
                "uuid": str(row.uuid),
                "course_uuid": str(row.course.uuid),
                "course_slug": row.course.slug,
                "course_title": row.course.title,
                "role": row.role,
                "created_at": row.created_at.isoformat(),
            }
            for row in course_staff_rows
        ]

        owned_events = [
            {
                "uuid": str(e.uuid),
                "title": e.title,
                "status": e.status,
                "starts_at": e.starts_at.isoformat() if e.starts_at else None,
            }
            for e in Event.objects.filter(owner=user, deleted_at__isnull=True).order_by("-created_at")[:10]
        ]

        owned_courses = [
            {
                "uuid": str(c.uuid),
                "slug": c.slug,
                "title": c.title,
                "status": c.status,
            }
            for c in Course.objects.filter(created_by=user).order_by("-created_at")[:10]
        ]

        certificates = [
            {
                "uuid": str(c.uuid),
                "short_code": getattr(c, "short_code", "") or "",
                "title": (
                    c.registration.event.title
                    if c.registration and c.registration.event
                    else (c.course_enrollment.course.title if c.course_enrollment else "")
                ),
                "issued_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in Certificate.objects.filter(
                models.Q(registration__user=user) | models.Q(course_enrollment__user=user),
                deleted_at__isnull=True,
            ).select_related("registration__event", "course_enrollment__course").order_by("-created_at")[:10]
        ]

        # Role changes + audit log rows targeting this user, merged and sorted.
        role_rows = UserRoleChange.objects.filter(user=user).select_related("changed_by").order_by("-created_at")[:20]
        audit_rows = AuditLog.objects.filter(object_uuid=str(user.uuid)).select_related("actor").order_by("-created_at")[:20]

        def _role_label(slug):
            return (slug or "").replace("_", " ").title()

        def _summarize_role_change(from_roles, to_roles):
            before = set(from_roles or [])
            after = set(to_roles or [])
            added = sorted(_role_label(r) for r in after - before)
            removed = sorted(_role_label(r) for r in before - after)
            if added and removed:
                return f"Added {', '.join(added)}; removed {', '.join(removed)}"
            if added:
                return f"Added role: {', '.join(added)}"
            if removed:
                return f"Removed role: {', '.join(removed)}"
            current = sorted(_role_label(r) for r in after) or ["None"]
            return f"Roles unchanged ({', '.join(current)})"

        recent_activity = []
        for row in role_rows:
            recent_activity.append(
                {
                    "type": "role_change",
                    "at": row.created_at.isoformat(),
                    "changed_by_name": row.changed_by.full_name if row.changed_by else None,
                    "summary": _summarize_role_change(row.from_roles, row.to_roles),
                    "metadata": {"from": row.from_roles, "to": row.to_roles, "reason": row.reason},
                }
            )
        for row in audit_rows:
            recent_activity.append(
                {
                    "type": row.action,
                    "at": row.created_at.isoformat(),
                    "changed_by_name": row.actor.full_name if row.actor else None,
                    "summary": row.action.replace("_", " ").capitalize(),
                    "metadata": row.metadata or {},
                }
            )
        recent_activity.sort(key=lambda r: r["at"], reverse=True)
        recent_activity = recent_activity[:20]

        pending_invitation = None
        pending = UserInvitation.objects.filter(
            email__iexact=user.email,
            is_used=False,
            revoked_at__isnull=True,
        ).order_by("-created_at").first()
        if pending:
            pending_invitation = {
                "uuid": str(pending.uuid),
                "status": pending.status,
                "expires_at": pending.expires_at.isoformat(),
            }

        return Response(
            {
                "profile": profile,
                "groups": user.role_names,
                "course_staff": course_staff,
                "owned_events": owned_events,
                "owned_courses": owned_courses,
                "certificates": certificates,
                "recent_activity": recent_activity,
                "pending_invitation": pending_invitation,
            }
        )


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
        from .audit import log_audit_event

        user = self.get_queryset().get(uuid=uuid)
        if user == request.user:
            return error_response("You cannot deactivate your own account.", code="SELF_DEACTIVATE")

        # If this action would *deactivate* the last active admin, block it.
        will_deactivate = user.is_active
        if will_deactivate and user.groups.filter(name="admin").exists():
            other_admin_exists = User.objects.filter(
                groups__name="admin",
                is_active=True,
                deleted_at__isnull=True,
            ).exclude(pk=user.pk).exists()
            if not other_admin_exists:
                return error_response(
                    "Cannot deactivate the last active admin.",
                    code="LAST_ADMIN",
                )

        user.is_active = not user.is_active
        user.save(update_fields=["is_active", "updated_at"])
        action = "activated" if user.is_active else "deactivated"

        log_audit_event(
            actor=request.user,
            action=f"user_{action}",
            object_type="User",
            object_uuid=str(user.uuid),
            metadata={"target_email": user.email},
            request=request,
        )

        return Response({"message": f"User {action} successfully.", "is_active": user.is_active})


@roles("admin", route_name="admin_invite_user")
class AdminInviteUserView(generics.GenericAPIView):
    """POST /api/v1/admin/users/invite/ - Send invitation to a new user."""

    serializer_class = serializers.InviteUserSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .emails import send_invitation_email
        from .models import UserInvitation

        email = serializer.validated_data["email"]
        pending = UserInvitation.objects.filter(
            email__iexact=email,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).exists()
        if pending:
            return error_response(
                "An invitation is already pending for this email.",
                code="INVITATION_PENDING",
            )

        invitation = UserInvitation.create_invitation(
            email=email,
            full_name=serializer.validated_data["full_name"],
            role=serializer.validated_data["role"],
            invited_by=request.user,
            message=serializer.validated_data.get("message", ""),
        )

        send_invitation_email(invitation, fail_silently=True)

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

        from .emails import send_invitation_email
        from .models import UserInvitation

        invited = 0
        errors = []
        now = timezone.now()

        for invite_data in serializer.validated_data["invitations"]:
            email = invite_data["email"]

            if User.objects.filter(email__iexact=email).exists():
                errors.append({"email": email, "error": "A user with this email already exists."})
                continue

            pending = UserInvitation.objects.filter(
                email__iexact=email,
                is_used=False,
                expires_at__gt=now,
            ).exists()
            if pending:
                errors.append({"email": email, "error": "An invitation is already pending for this email."})
                continue

            invitation = UserInvitation.create_invitation(
                email=email,
                full_name=invite_data["full_name"],
                role=invite_data.get("role", "learner"),
                invited_by=request.user,
                message=invite_data.get("message", ""),
            )

            send_invitation_email(invitation, fail_silently=True)
            invited += 1

        return Response(
            {"invited": invited, "errors": errors},
            status=status.HTTP_201_CREATED,
        )


@roles("admin", route_name="admin_invitations")
class AdminInvitationListView(generics.ListAPIView):
    """GET /api/v1/admin/users/invitations/ - List invitations with filters.

    Query params:
    - status: pending | accepted | expired | revoked
    - search: matches email or full_name
    - include_revoked: if 'true', includes revoked rows (otherwise excluded)
    """

    serializer_class = serializers.UserInvitationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import UserInvitation

        qs = UserInvitation.objects.all().order_by("-created_at")
        now = timezone.now()

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                models.Q(email__icontains=search) | models.Q(full_name__icontains=search)
            )

        status_filter = self.request.query_params.get("status")
        include_revoked = self.request.query_params.get("include_revoked", "").lower() == "true"

        if status_filter == "pending":
            qs = qs.filter(is_used=False, revoked_at__isnull=True, expires_at__gt=now)
        elif status_filter == "accepted":
            qs = qs.filter(is_used=True)
        elif status_filter == "expired":
            qs = qs.filter(is_used=False, revoked_at__isnull=True, expires_at__lte=now)
        elif status_filter == "revoked":
            qs = qs.filter(revoked_at__isnull=False)
        elif not include_revoked:
            # Default list hides revoked rows unless explicitly requested or a
            # status filter narrows the view itself.
            qs = qs.filter(revoked_at__isnull=True)

        return qs


@roles("admin", route_name="admin_invitation_resend")
class AdminInvitationResendView(generics.GenericAPIView):
    """POST /api/v1/admin/users/invitations/{uuid}/resend/"""

    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def post(self, request, uuid):
        from .emails import send_invitation_email
        from .models import UserInvitation

        try:
            invitation = UserInvitation.objects.get(uuid=uuid)
        except UserInvitation.DoesNotExist:
            return error_response("Invitation not found.", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

        if invitation.is_used:
            return error_response(
                "Cannot resend an invitation that has already been accepted.",
                code="INVITATION_ALREADY_ACCEPTED",
            )
        if invitation.is_revoked:
            return error_response(
                "Cannot resend a revoked invitation.",
                code="INVITATION_REVOKED",
            )

        expires_days = getattr(settings, "INVITATION_EXPIRY_DAYS", 30)
        now = timezone.now()
        invitation.last_sent_at = now
        invitation.expires_at = now + timezone.timedelta(days=expires_days)
        invitation.resent_count = models.F("resent_count") + 1
        invitation.save(update_fields=["last_sent_at", "expires_at", "resent_count", "updated_at"])
        invitation.refresh_from_db()

        send_invitation_email(invitation, fail_silently=True)

        return Response(
            {
                "message": f"Invitation re-sent to {invitation.email}.",
                "invitation": serializers.UserInvitationSerializer(invitation).data,
            }
        )


@roles("admin", route_name="admin_invitation_revoke")
class AdminInvitationRevokeView(generics.GenericAPIView):
    """POST /api/v1/admin/users/invitations/{uuid}/revoke/"""

    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def post(self, request, uuid):
        from .models import UserInvitation

        try:
            invitation = UserInvitation.objects.get(uuid=uuid)
        except UserInvitation.DoesNotExist:
            return error_response("Invitation not found.", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

        if invitation.is_used:
            return error_response(
                "Cannot revoke an invitation that has already been accepted.",
                code="INVITATION_ALREADY_ACCEPTED",
            )

        invitation.revoke()

        return Response(
            {
                "message": f"Invitation for {invitation.email} revoked.",
                "invitation": serializers.UserInvitationSerializer(invitation).data,
            }
        )


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
            if invitation.is_revoked:
                return error_response("This invitation has been revoked.", code="INVITATION_REVOKED")
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

        # Assign role from invitation via set_roles so the change is audited.
        user.set_roles([invitation.role], changed_by=invitation.invited_by, reason="invitation_accepted")

        # Mark invitation as accepted
        invitation.accept(user)

        from .audit import log_audit_event

        log_audit_event(
            actor=invitation.invited_by,
            action="invitation_accepted",
            object_type="User",
            object_uuid=str(user.uuid),
            metadata={"email": user.email, "role": invitation.role},
            request=request,
        )

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
