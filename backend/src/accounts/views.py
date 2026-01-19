"""
Accounts app views and viewsets.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from billing.capability_service import capability_service
from common.permissions import CanCreateEvents, CanCreateCourses
from common.utils import error_response

from . import cpd_serializers, serializers
from .models import CPDRequirement, Notification, UserSession

User = get_user_model()


# =============================================================================
# RBAC Helper Functions
# =============================================================================


def get_allowed_routes_for_user(user) -> list[str]:
    """
    Get list of allowed routes for a user based on their subscription.

    Returns route identifiers that the frontend uses to show/hide navigation items.
    """
    from billing.capability_service import capability_service

    # Base routes available to all authenticated users
    routes = [
        "/dashboard",
        "/profile",
        "/settings",
        "/events",  # View events (attendee)
        "/certificates",  # View earned certificates
        "/cpd",  # CPD tracking
    ]

    # Check subscription-based capabilities
    if capability_service.can_create_events(user):
        routes.extend(
            [
                "/events/create",
                "/events/manage",
                "/organizer",
                "/organizer/analytics",
            ]
        )

    if capability_service.can_create_courses(user):
        routes.extend(
            [
                "/courses/create",
                "/courses/manage",
                "/lms",
                "/lms/analytics",
            ]
        )

    if capability_service.can_issue_certificates(user):
        routes.extend(
            [
                "/certificates/issue",
                "/certificates/templates",
            ]
        )

    # Staff-only routes
    if user.is_staff:
        routes.extend(
            [
                "/admin",
                "/admin/users",
                "/admin/subscriptions",
            ]
        )

    return sorted(set(routes))


def get_features_for_user(user) -> dict:
    """
    Get feature flags for a user based on their subscription.

    Returns a dict of feature names to enabled status.
    """
    from billing.capability_service import capability_service

    access_status = capability_service.get_access_status(user)
    plan_key = (access_status.plan or "").lower()

    return {
        # Core capabilities
        "can_create_events": capability_service.can_create_events(user),
        "can_create_courses": capability_service.can_create_courses(user),
        "can_issue_certificates": capability_service.can_issue_certificates(user),
        # Subscription status
        "has_active_subscription": access_status.is_active,
        "is_trialing": access_status.is_trialing,
        "is_trial_expired": access_status.is_trial_expired,
        "is_in_grace_period": access_status.is_in_grace_period,
        "is_access_blocked": access_status.is_access_blocked,
        # Plan info
        "plan": access_status.plan,
        "has_payment_method": access_status.has_payment_method,
        # Premium features (can be extended based on StripeProduct feature flags)
        "zoom_integration": capability_service.can_create_events(user),
        "custom_branding": plan_key == "pro",
        "api_access": plan_key == "pro",
        "white_label": plan_key == "pro",
    }


# =============================================================================
# Throttle Classes
# =============================================================================


class AuthThrottle(AnonRateThrottle):
    """Stricter throttle for auth endpoints."""

    scope = "auth"


# =============================================================================
# Authentication Views
# =============================================================================


class SignupView(generics.CreateAPIView):
    """POST /api/v1/auth/signup/ - Create new user account."""

    serializer_class = serializers.SignupSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate verification token
        token = user.generate_email_verification_token()

        # Send verification email
        try:
            verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"

            # Print URL prominently for dev testing (the email body below is mangled by quoted-printable encoding)
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
            # Log error but don't fail signup? Or fail?
            # Better to log and maybe return a warning, or fail if critical.
            # Ideally use a task so it doesn't fail the request.
            # For now, let's log.
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
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/token/ - Obtain JWT token pair."""

    serializer_class = serializers.CustomTokenObtainPairSerializer
    throttle_classes = [AuthThrottle]


class EmailVerificationView(generics.GenericAPIView):
    """POST /api/v1/auth/verify-email/ - Verify email with token."""

    serializer_class = serializers.EmailVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        try:
            # First check if user exists with this token (including verified ones)
            # We don't check email_verified=False yet
            user = User.objects.get(email_verification_token=token)

            # If already verified, return success (idempotency)
            if user.email_verified:
                # Generate tokens for auto-login just in case
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
        user.email_verified_at = timezone.now()
        user.email_verification_token = ""
        user.email_verification_sent_at = None
        user.save(
            update_fields=[
                "email_verified",
                "email_verified_at",
                "email_verification_token",
                "email_verification_sent_at",
                "updated_at",
            ]
        )

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
                },
            }
        )


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

            # Construct reset URL
            reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={user.password_reset_token}&email={user.email}"

            # Print URL prominently for dev testing
            print("\n" + "=" * 80)
            print("🔐 PASSWORD RESET LINK (copy this, NOT the email body below):")
            print(f"   {reset_url}")
            print("=" * 80 + "\n")

            send_password_reset.delay(user.uuid, reset_url)
        except User.DoesNotExist:
            pass  # Don't reveal if email exists

        return Response({"message": "If an account exists, a password reset email has been sent."})


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


class UserSessionListView(generics.ListAPIView):
    """GET /api/v1/users/me/sessions/ - List active sessions."""

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True).order_by("-last_activity_at")


class UserSessionRevokeView(generics.DestroyAPIView):
    """DELETE /api/v1/users/me/sessions/{uuid}/ - Revoke a specific session."""

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.UserSessionSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        instance.deactivate()


class UserSessionLogoutAllView(generics.GenericAPIView):
    """POST /api/v1/users/me/sessions/logout-all/ - Logout from all sessions."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        UserSession.deactivate_all_for_user(request.user)
        return Response({"message": "Logged out from all sessions."})


# =============================================================================
# User Profile Views
# =============================================================================


class CurrentUserView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/ - Current user profile."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return serializers.UserProfileUpdateSerializer
        return serializers.UserSerializer

    def get_object(self):
        return self.request.user


class OrganizerProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/organizer-profile/ - Organizer profile."""

    serializer_class = serializers.OrganizerProfileUpdateSerializer
    permission_classes = [IsAuthenticated, CanCreateEvents]

    def get_object(self):
        return self.request.user


class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/notifications/ - Notification preferences."""

    serializer_class = serializers.NotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


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


class PublicOrganizerView(generics.RetrieveAPIView):
    """GET /api/v1/organizers/{uuid}/ - Public organizer profile."""

    serializer_class = serializers.PublicOrganizerSerializer
    permission_classes = [AllowAny]
    lookup_field = "uuid"

    def get_queryset(self):
        # Return users who have public profiles and can create events (ORGANIZER, LMS, or PRO subscription)
        from billing.models import Subscription

        return User.objects.filter(
            is_organizer_profile_public=True,
            deleted_at__isnull=True,
            subscription__plan__in=[
                Subscription.Plan.ORGANIZER,
                Subscription.Plan.LMS,
                Subscription.Plan.PRO,
            ],
        )


# =============================================================================
# Account Deletion (H7)
# =============================================================================


class DeleteAccountView(generics.GenericAPIView):
    """POST /api/v1/users/me/delete-account/ - Delete/anonymize account."""

    serializer_class = serializers.DeleteAccountSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        serializer.validated_data.get("reason", "")

        # Anonymize user data (GDPR compliant)
        user.anonymize()

        return Response({"message": "Account has been deleted."})


# =============================================================================
# GDPR Data Export (H6)
# =============================================================================


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

        # Collect user data
        export_data = {
            "user": {
                "uuid": str(user.uuid),
                "email": user.email,
                "full_name": user.full_name,
                "professional_title": user.professional_title,
                "organization_name": user.organization_name,
                "bio": user.bio,
                "timezone": user.timezone,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        }

        # Include registrations
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

        # Include certificates
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

        # Include attendance records
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

        # Return as JSON download
        if export_format == "json":
            response = HttpResponse(
                json.dumps(export_data, indent=2, default=str),
                content_type="application/json",
            )
            response["Content-Disposition"] = f'attachment; filename="data_export_{user.uuid}.json"'
            return response

        # CSV would require more complex handling for nested data
        return Response(export_data)


# =============================================================================
# Account Downgrade
# =============================================================================


class DowngradeToAttendeeView(generics.GenericAPIView):
    """POST /api/v1/users/me/downgrade/ - Downgrade account to attendee."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        from billing.models import Subscription

        subscription = capability_service.get_subscription(user)
        if not subscription or subscription.plan == Subscription.Plan.ATTENDEE:
            return Response({"message": "Account is already on attendee plan."})

        from billing.services import stripe_service
        from events.models import Event
        from learning.models import Course

        has_active_events = Event.objects.filter(
            owner=user,
            status__in=[Event.Status.DRAFT, Event.Status.PUBLISHED, Event.Status.LIVE],
            deleted_at__isnull=True,
        ).exists()
        has_active_courses = Course.objects.filter(
            owner=user,
            status__in=[Course.Status.DRAFT, Course.Status.PUBLISHED],
            deleted_at__isnull=True,
        ).exists()

        if has_active_events or has_active_courses:
            return error_response(
                "You must archive or cancel active events/courses before downgrading.",
                code="ACTIVE_CONTENT",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        subscription = capability_service.get_subscription(user)
        if subscription and subscription.plan != Subscription.Plan.ATTENDEE:
            if not stripe_service.cancel_subscription(subscription, immediate=True, reason="user_downgrade"):
                return error_response("Failed to cancel subscription.", code="CANCEL_FAILED")

        user.downgrade_to_attendee()
        return Response({"message": "Account downgraded to attendee."})


class UpgradeToOrganizerView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/upgrade/ - Upgrade account to organizer plan.

    This view initiates the upgrade process. For paid upgrades, it returns
    a Stripe Checkout session URL. For direct upgrades (e.g., admin action),
    it updates the subscription directly.

    Request body (optional):
        {
            "plan": "organizer" | "lms" | "pro"  (default: "organizer")
        }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from billing.capability_service import capability_service
        from billing.services import stripe_service
        from common.messages import CAPABILITY_MESSAGES

        user = request.user
        target_plan = request.data.get("plan", "organizer").lower()

        # Validate plan
        valid_plans = {"organizer", "lms", "pro"}
        if target_plan not in valid_plans:
            return error_response(
                f"Invalid plan: {target_plan}. Must be one of: {', '.join(valid_plans)}",
                code="INVALID_PLAN",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Check if already on this plan
        subscription = capability_service.get_subscription(user)
        if subscription and subscription.plan.lower() == target_plan:
            return error_response(
                CAPABILITY_MESSAGES["already_on_plan"].format(plan=target_plan.title()),
                code="ALREADY_ON_PLAN",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Create Stripe Checkout session for paid upgrade
        try:
            # Use create_checkout_session for new subscriptions/upgrades
            result = stripe_service.create_checkout_session(
                user=user,
                plan=target_plan,
                success_url=f"{settings.FRONTEND_URL}/settings?upgrade=success",
                cancel_url=f"{settings.FRONTEND_URL}/settings?upgrade=cancelled",
            )

            if result.get("success") and result.get("url"):
                return Response(
                    {
                        "checkout_url": result.get("url"),
                        "message": f"Redirect to complete {target_plan.title()} plan upgrade.",
                    }
                )

            # If Stripe is not configured or fails silently, log it
            if not result.get("success"):
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Stripe checkout creation failed: {result.get('error')}")

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create checkout session for user {user.id}: {e}")

        # Fallback: If no Stripe integration or free upgrade, update directly
        # This is primarily for development or if stripe is disabled
        result = capability_service.upgrade_to_plan(user, target_plan)

        if not result.allowed:
            return error_response(
                result.error_message or "Upgrade failed.",
                code=result.error_code or "UPGRADE_FAILED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"Successfully upgraded to {target_plan.title()} plan.",
                "plan": target_plan,
            }
        )


# =============================================================================
# Onboarding Completion
# =============================================================================


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

        # Parse dates if provided
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
# RBAC Manifest Views
# =============================================================================


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
        user = request.user

        data = {
            "routes": get_allowed_routes_for_user(user),
            "features": get_features_for_user(user),
            "user": {
                "is_staff": user.is_staff,
            },
        }

        return Response(data)


# =============================================================================
# Zoom SSO Views
# =============================================================================


class ZoomAuthView(generics.GenericAPIView):
    """
    GET /api/v1/auth/zoom/login/

    Redirects the user to Zoom's OAuth authorization page.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get(self, request):
        from .oauth import get_zoom_auth_url

        url = get_zoom_auth_url()
        return Response({"url": url})


class ZoomCallbackView(generics.GenericAPIView):
    """
    GET /api/v1/auth/zoom/callback/

    Handles the OAuth callback from Zoom.
    Exchanges code for token, gets user info, logs in or creates user.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get(self, request):
        code = request.query_params.get("code")
        error = request.query_params.get("error")

        if error:
            return error_response(f"Zoom OAuth error: {error}", code="ZOOM_AUTH_ERROR")

        if not code:
            return error_response("Authorization code missing.", code="MISSING_CODE")

        from django.conf import settings
        from django.db import transaction
        from rest_framework_simplejwt.tokens import RefreshToken

        from .models import User, ZoomConnection
        from .oauth import exchange_code_for_token, get_zoom_user_info

        # 1. Exchange code for tokens
        token_data = exchange_code_for_token(code)
        if not token_data:
            return error_response("Failed to exchange code for token.", code="TOKEN_EXCHANGE_FAILED")

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # 2. Get user info
        user_info = get_zoom_user_info(access_token)
        if not user_info:
            return error_response("Failed to fetch user info from Zoom.", code="USER_INFO_FAILED")

        zoom_user_id = user_info.get("id")
        email = user_info.get("email").lower()
        first_name = user_info.get("first_name", "")
        last_name = user_info.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()

        if not email:
            return error_response("Zoom account must have an email address.", code="MISSING_EMAIL")

        # 3. Find or create user
        with transaction.atomic():
            # Try to match by ZoomConnection first
            zoom_conn = ZoomConnection.objects.filter(zoom_user_id=zoom_user_id).select_related("user").first()

            if zoom_conn:
                user = zoom_conn.user
            else:
                # Try to match by email
                user = User.objects.filter(email=email).first()

                if not user:
                    # Create new user
                    user = User.objects.create_user(
                        email=email,
                        full_name=full_name or email.split("@")[0],
                        email_verified=True,  # Zoom emails are verified
                        password=None,  # Unusable password
                    )

            # 4. Update/Create ZoomConnection
            # Even for attendees, we store this to separate Zoom ID from Email
            if not hasattr(user, "zoom_connection"):
                ZoomConnection.objects.create(
                    user=user,
                    zoom_user_id=zoom_user_id,
                    zoom_account_id=user_info.get("account_id", ""),
                    zoom_email=email,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=timezone.now() + timezone.timedelta(seconds=expires_in),
                )
            else:
                # Update tokens
                conn = user.zoom_connection
                conn.zoom_user_id = zoom_user_id  # Ensure consistent
                conn.zoom_email = email
                conn.update_tokens(access_token, refresh_token, expires_in)

            # Ensure user is active
            if not user.is_active:
                return error_response("Account is disabled.", code="ACCOUNT_DISABLED")

            # Record login
            user.record_login()

            # 5. Generate JWT
            refresh = RefreshToken.for_user(user)

            # 6. Redirect to frontend
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0]  # Assuming first one is main frontend
            redirect_url = f"{frontend_url}/auth/callback?access={str(refresh.access_token)}&refresh={str(refresh)}"

            from django.http import HttpResponseRedirect

            return HttpResponseRedirect(redirect_url)


# =============================================================================
# Google OAuth Views
# =============================================================================


class GoogleAuthView(generics.GenericAPIView):
    """
    GET /api/v1/auth/google/login/

    Returns the Google OAuth authorization URL for user to authenticate.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get(self, request):
        from .google_oauth import get_google_auth_url

        url = get_google_auth_url()
        return Response({"url": url})


class GoogleCallbackView(generics.GenericAPIView):
    """
    GET /api/v1/auth/google/callback/

    Handles the OAuth callback from Google.
    Exchanges code for tokens, gets user info, logs in or creates user.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get(self, request):
        code = request.query_params.get("code")
        error = request.query_params.get("error")

        if error:
            return error_response(f"Google OAuth error: {error}", code="GOOGLE_AUTH_ERROR")

        if not code:
            return error_response("Authorization code missing.", code="MISSING_CODE")

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
        id_token = token_data.get("id_token")

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

        # Use name from Google, fallback to constructing from given/family names
        full_name = name or f"{given_name} {family_name}".strip() or email.split("@")[0]

        # 3. Find or create user
        with transaction.atomic():
            # Try to match by google_user_id first
            user = User.objects.filter(google_user_id=google_user_id).first()

            if user:
                # Existing Google user - just log them in
                pass
            else:
                # Try to match by email (link accounts)
                user = User.objects.filter(email=email).first()

                if user:
                    # Existing user with same email - link Google account
                    # Since Google verifies emails, we can safely link
                    user.google_user_id = google_user_id
                    if not user.email_verified:
                        user.email_verified = True
                        user.email_verified_at = timezone.now()
                    # Update auth provider if it was local
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
                    # Create new user with Google OAuth
                    user = User.objects.create_user(
                        email=email,
                        full_name=full_name,
                        email_verified=True,
                        password=None,  # No password for OAuth users
                        google_user_id=google_user_id,
                        auth_provider="google",
                        profile_photo_url=picture,
                    )

            # Ensure user is active
            if not user.is_active:
                return error_response("Account is disabled.", code="ACCOUNT_DISABLED")

            # Link any guest registrations
            from registrations.models import Registration

            Registration.link_registrations_for_user(user)

            # Record login
            user.record_login()

            # 4. Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            # 5. Redirect to frontend with tokens
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else "http://localhost:5173"
            redirect_url = f"{frontend_url}/auth/callback?access={str(refresh.access_token)}&refresh={str(refresh)}"

            from django.http import HttpResponseRedirect

            return HttpResponseRedirect(redirect_url)


# =============================================================================
# Individual Organizer Payouts (Stripe Connect)
# =============================================================================


class PayoutsConnectView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/payouts/connect/

    Initiates Stripe Connect Express onboarding for the individual organizer.
    Returns the Stripe hosted onboarding URL.
    """

    permission_classes = [IsAuthenticated, CanCreateCourses]

    def post(self, request):
        from django.conf import settings

        from billing.services import stripe_connect_service

        user = request.user

        # 1. Create Connect Account if not exists
        if not user.stripe_connect_id:
            account_id = stripe_connect_service.create_account(
                email=user.email,
                country="US",  # Default; can be made dynamic
            )
            if not account_id:
                return error_response("Failed to create Stripe account.", code="CONNECT_CREATE_FAILED")

            user.stripe_connect_id = account_id
            user.stripe_account_status = "pending"
            user.save(update_fields=["stripe_connect_id", "stripe_account_status", "updated_at"])

        # 2. Generate Onboarding Link
        frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else "http://localhost:5173"
        refresh_url = f"{frontend_url}/settings?tab=payouts&refresh=true"
        return_url = f"{frontend_url}/settings?tab=payouts&success=true"

        onboarding_url = stripe_connect_service.create_account_link(
            account_id=user.stripe_connect_id,
            refresh_url=refresh_url,
            return_url=return_url,
        )

        if not onboarding_url:
            return error_response("Failed to generate onboarding link.", code="CONNECT_LINK_FAILED")

        return Response({"url": onboarding_url})


class PayoutsStatusView(generics.GenericAPIView):
    """
    GET /api/v1/users/me/payouts/status/

    Checks and syncs the Stripe Connect status for the individual organizer.
    """

    permission_classes = [IsAuthenticated, CanCreateCourses]

    def get(self, request):
        from billing.services import stripe_connect_service

        user = request.user

        if not user.stripe_connect_id:
            return Response(
                {
                    "connected": False,
                    "status": "not_connected",
                    "charges_enabled": False,
                }
            )

        status_info = stripe_connect_service.get_account_status(user.stripe_connect_id)

        if "error" in status_info:
            return Response(
                {"detail": "Failed to retrieve status from Stripe."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Update local state
        user.stripe_charges_enabled = status_info.get("charges_enabled", False)
        if status_info.get("charges_enabled"):
            user.stripe_account_status = "active"
        elif status_info.get("details_submitted"):
            user.stripe_account_status = "pending_verification"
        else:
            user.stripe_account_status = "restricted"

        user.save(update_fields=["stripe_charges_enabled", "stripe_account_status", "updated_at"])

        return Response(
            {
                "connected": True,
                "status": user.stripe_account_status,
                "charges_enabled": user.stripe_charges_enabled,
                "stripe_id": user.stripe_connect_id,
                "details": status_info,
            }
        )


class PayoutsDashboardView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/payouts/dashboard/

    Returns a Stripe Express dashboard login link.
    """

    permission_classes = [IsAuthenticated, CanCreateCourses]

    def post(self, request):
        from billing.services import stripe_connect_service

        user = request.user

        if not user.stripe_connect_id:
            return error_response("Stripe account not connected.", code="NOT_CONNECTED")

        login_url = stripe_connect_service.create_login_link(user.stripe_connect_id)
        if not login_url:
            return error_response("Failed to create Stripe dashboard link.", code="DASHBOARD_LINK_FAILED")

        return Response({"url": login_url})
