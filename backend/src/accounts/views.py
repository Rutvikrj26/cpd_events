"""
Accounts app views and viewsets.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from common.permissions import IsOrganizer
from common.rbac import roles
from common.utils import error_response

from . import cpd_serializers, serializers
from .models import CPDRequirement
from drf_yasg.utils import swagger_auto_schema

User = get_user_model()


# =============================================================================
# Throttle Classes
# =============================================================================


class AuthThrottle(AnonRateThrottle):
    """Stricter throttle for auth endpoints."""

    scope = 'auth'


# =============================================================================
# Authentication Views
# =============================================================================


@roles('public', route_name='signup')
class SignupView(generics.CreateAPIView):
    """POST /api/v1/auth/signup/ - Create new user account."""

    serializer_class = serializers.SignupSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        # Link any guest registrations to this new user account
        from registrations.models import Registration

        Registration.link_registrations_for_user(user)

        return Response(
            {
                'message': 'Account created successfully.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'uuid': str(user.uuid),
                    'email': user.email,
                    'full_name': user.full_name,
                    'account_type': user.account_type,
                },
            },
            status=status.HTTP_201_CREATED,
        )


@roles('public', route_name='token_obtain')
class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/token/ - Obtain JWT token pair."""

    serializer_class = serializers.CustomTokenObtainPairSerializer
    throttle_classes = [AuthThrottle]


@roles('public', route_name='email_verification')
class EmailVerificationView(generics.GenericAPIView):
    """POST /api/v1/auth/verify-email/ - Verify email with token."""

    serializer_class = serializers.EmailVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']

        try:
            user = User.objects.get(email_verification_token=token, email_verified=False)
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired token.'}}, status=status.HTTP_400_BAD_REQUEST
            )

        if user.email_verification_expires_at and user.email_verification_expires_at < timezone.now():
            return Response(
                {'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired.'}}, status=status.HTTP_400_BAD_REQUEST
            )

        user.email_verified = True
        user.email_verification_token = ''
        user.save(update_fields=['email_verified', 'email_verification_token', 'updated_at'])

        # Link any guest registrations
        from registrations.models import Registration

        Registration.link_registrations_for_user(user)

        return Response({'message': 'Email verified successfully.'})


@roles('public', route_name='password_reset_request')
class PasswordResetRequestView(generics.GenericAPIView):
    """POST /api/v1/auth/password-reset/ - Request password reset."""

    serializer_class = serializers.PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email__iexact=email)
            user.generate_password_reset_token()
            # In production: send_password_reset_email.delay(user.id)
        except User.DoesNotExist:
            pass  # Don't reveal if email exists

        return Response({'message': 'If an account exists, a password reset email has been sent.'})


@roles('public', route_name='password_reset_confirm')
class PasswordResetConfirmView(generics.GenericAPIView):
    """POST /api/v1/auth/password-reset/confirm/ - Confirm password reset."""

    serializer_class = serializers.PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(password_reset_token=token)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return error_response('Invalid or expired token.', code='INVALID_TOKEN')
        except jwt.ExpiredSignatureError:
            return error_response('Token has expired.', code='TOKEN_EXPIRED')

        user.set_password(password)
        user.password_reset_token = ''
        user.save(update_fields=['password', 'password_reset_token', 'updated_at'])

        return Response({'message': 'Password reset successfully.'})


@roles('attendee', 'organizer', 'admin', route_name='password_change')
class PasswordChangeView(generics.GenericAPIView):
    """POST /api/v1/auth/password-change/ - Change password."""

    serializer_class = serializers.PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password', 'updated_at'])

        return Response({'message': 'Password changed successfully.'})


# =============================================================================
# User Profile Views
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='current_user')
class CurrentUserView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/ - Current user profile."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return serializers.UserProfileUpdateSerializer
        return serializers.UserSerializer

    def get_object(self):
        return self.request.user


@roles('organizer', 'admin', route_name='organizer_profile')
class OrganizerProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/organizer-profile/ - Organizer profile."""

    serializer_class = serializers.OrganizerProfileUpdateSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_object(self):
        return self.request.user


@roles('attendee', 'organizer', 'admin', route_name='notification_preferences')
class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/notifications/ - Notification preferences."""

    serializer_class = serializers.NotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@roles('public', route_name='public_organizer')
class PublicOrganizerView(generics.RetrieveAPIView):
    """GET /api/v1/organizers/{uuid}/ - Public organizer profile."""

    serializer_class = serializers.PublicOrganizerSerializer
    permission_classes = [AllowAny]
    lookup_field = 'uuid'

    def get_queryset(self):
        return User.objects.filter(account_type='organizer', is_organizer_profile_public=True, deleted_at__isnull=True)


@roles('attendee', route_name='upgrade_to_organizer')
class UpgradeToOrganizerView(generics.GenericAPIView):
    """POST /api/v1/users/me/upgrade/ - Upgrade to organizer."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.account_type == 'organizer':
            return error_response('Already an organizer.', code='ALREADY_ORGANIZER')

        user.upgrade_to_organizer()

        return Response({'message': 'Successfully upgraded to organizer.', 'user': serializers.UserSerializer(user).data})


# =============================================================================
# Account Deletion (H7)
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='delete_account')
class DeleteAccountView(generics.GenericAPIView):
    """POST /api/v1/users/me/delete-account/ - Delete/anonymize account."""

    serializer_class = serializers.DeleteAccountSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        serializer.validated_data.get('reason', '')

        # Anonymize user data (GDPR compliant)
        user.anonymize()

        return Response({'message': 'Account has been deleted.'})


# =============================================================================
# GDPR Data Export (H6)
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='data_export')
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
        export_format = options.get('format', 'json')

        # Collect user data
        export_data = {
            'user': {
                'uuid': str(user.uuid),
                'email': user.email,
                'full_name': user.full_name,
                'professional_title': user.professional_title,
                'organization_name': user.organization_name,
                'bio': user.bio,
                'account_type': user.account_type,
                'timezone': user.timezone,
                'created_at': user.created_at.isoformat() if user.created_at else None,
            },
        }

        # Include registrations
        if options.get('include_registrations', True):
            from registrations.models import Registration

            registrations = Registration.all_objects.filter(user=user)
            export_data['registrations'] = [
                {
                    'uuid': str(r.uuid),
                    'event_title': r.event.title if r.event else None,
                    'email': r.email,
                    'full_name': r.full_name,
                    'status': r.status,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                    'attended': r.attended,
                    'attendance_eligible': r.attendance_eligible,
                }
                for r in registrations
            ]

        # Include certificates
        if options.get('include_certificates', True):
            from certificates.models import Certificate

            certificates = Certificate.objects.filter(registration__user=user)
            export_data['certificates'] = [
                {
                    'uuid': str(c.uuid),
                    'event_title': c.registration.event.title if c.registration and c.registration.event else None,
                    'credential_id': c.credential_id,
                    'cpd_credits': str(c.cpd_credits) if c.cpd_credits else None,
                    'issued_at': c.issued_at.isoformat() if c.issued_at else None,
                }
                for c in certificates
            ]

        # Include attendance records
        if options.get('include_attendance', True):
            from registrations.models import AttendanceRecord

            attendance = AttendanceRecord.objects.filter(registration__user=user)
            export_data['attendance_records'] = [
                {
                    'event_title': a.event.title if a.event else None,
                    'join_time': a.join_time.isoformat() if a.join_time else None,
                    'leave_time': a.leave_time.isoformat() if a.leave_time else None,
                    'duration_minutes': a.duration_minutes,
                }
                for a in attendance
            ]

        # Return as JSON download
        if export_format == 'json':
            response = HttpResponse(
                json.dumps(export_data, indent=2, default=str),
                content_type='application/json',
            )
            response['Content-Disposition'] = f'attachment; filename="data_export_{user.uuid}.json"'
            return response

        # CSV would require more complex handling for nested data
        return Response(export_data)


# =============================================================================
# CPD Requirement Views
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='cpd_requirements')
class CPDRequirementViewSet(viewsets.ModelViewSet):
    """
    CRUD for user CPD requirements.
    GET /api/v1/cpd-requirements/
    POST /api/v1/cpd-requirements/
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
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
    @action(detail=False, methods=['get'])
    def progress(self, request):
        """Get CPD progress summary."""
        requirements = self.get_queryset()

        from decimal import Decimal

        total_credits = request.user.total_cpd_credits or Decimal('0')

        data = {
            'total_requirements': requirements.count(),
            'completed_requirements': sum(1 for r in requirements if r.completion_percent >= 100),
            'in_progress_requirements': sum(1 for r in requirements if 0 < r.completion_percent < 100),
            'total_credits_earned': total_credits,
            'requirements': cpd_serializers.CPDRequirementSerializer(requirements, many=True).data,
        }
        return Response(data)


# =============================================================================
# RBAC Manifest Views
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='manifest')
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
            'routes': get_allowed_routes_for_user(user),
            'features': get_features_for_user(user),
            'user': {
                'account_type': getattr(user, 'account_type', 'attendee'),
                'is_staff': user.is_staff,
            }
        }
        
        return Response(data)


# =============================================================================
# Zoom SSO Views
# =============================================================================


@roles('public', route_name='zoom_auth')
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
        return Response({'url': url})


@roles('public', route_name='zoom_callback')
class ZoomCallbackView(generics.GenericAPIView):
    """
    GET /api/v1/auth/zoom/callback/

    Handles the OAuth callback from Zoom.
    Exchanges code for token, gets user info, logs in or creates user.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get(self, request):
        code = request.query_params.get('code')
        error = request.query_params.get('error')

        if error:
            return error_response(f"Zoom OAuth error: {error}", code='ZOOM_AUTH_ERROR')

        if not code:
            return error_response("Authorization code missing.", code='MISSING_CODE')

        from django.conf import settings
        from django.db import transaction
        from rest_framework_simplejwt.tokens import RefreshToken

        from .models import User, ZoomConnection
        from .oauth import exchange_code_for_token, get_zoom_user_info

        # 1. Exchange code for tokens
        token_data = exchange_code_for_token(code)
        if not token_data:
            return error_response("Failed to exchange code for token.", code='TOKEN_EXCHANGE_FAILED')

        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 3600)

        # 2. Get user info
        user_info = get_zoom_user_info(access_token)
        if not user_info:
            return error_response("Failed to fetch user info from Zoom.", code='USER_INFO_FAILED')

        zoom_user_id = user_info.get('id')
        email = user_info.get('email').lower()
        first_name = user_info.get('first_name', '')
        last_name = user_info.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()

        if not email:
            return error_response("Zoom account must have an email address.", code='MISSING_EMAIL')

        # 3. Find or create user
        with transaction.atomic():
            # Try to match by ZoomConnection first
            zoom_conn = ZoomConnection.objects.filter(zoom_user_id=zoom_user_id).select_related('user').first()

            if zoom_conn:
                user = zoom_conn.user
            else:
                # Try to match by email
                user = User.objects.filter(email=email).first()

                if not user:
                    # Create new user
                    user = User.objects.create_user(
                        email=email,
                        full_name=full_name or email.split('@')[0],
                        email_verified=True,  # Zoom emails are verified
                        password=None,  # Unusable password
                    )

            # 4. Update/Create ZoomConnection
            # Even for attendees, we store this to separate Zoom ID from Email
            if not hasattr(user, 'zoom_connection'):
                ZoomConnection.objects.create(
                    user=user,
                    zoom_user_id=zoom_user_id,
                    zoom_account_id=user_info.get('account_id', ''),
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
                 return error_response("Account is disabled.", code='ACCOUNT_DISABLED')

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
# Individual Organizer Payouts (Stripe Connect)
# =============================================================================


@roles('organizer', 'admin', route_name='payouts_connect')
class PayoutsConnectView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/payouts/connect/

    Initiates Stripe Connect Express onboarding for the individual organizer.
    Returns the Stripe hosted onboarding URL.
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def post(self, request):
        from django.conf import settings
        from billing.services import stripe_connect_service

        user = request.user

        # 1. Create Connect Account if not exists
        if not user.stripe_connect_id:
            account_id = stripe_connect_service.create_account(
                email=user.email,
                country='US',  # Default; can be made dynamic
            )
            if not account_id:
                return error_response('Failed to create Stripe account.', code='CONNECT_CREATE_FAILED')

            user.stripe_connect_id = account_id
            user.stripe_account_status = 'pending'
            user.save(update_fields=['stripe_connect_id', 'stripe_account_status', 'updated_at'])

        # 2. Generate Onboarding Link
        frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else 'http://localhost:5173'
        refresh_url = f"{frontend_url}/settings?tab=payouts&refresh=true"
        return_url = f"{frontend_url}/settings?tab=payouts&success=true"

        onboarding_url = stripe_connect_service.create_account_link(
            account_id=user.stripe_connect_id,
            refresh_url=refresh_url,
            return_url=return_url,
        )

        if not onboarding_url:
            return error_response('Failed to generate onboarding link.', code='CONNECT_LINK_FAILED')

        return Response({'url': onboarding_url})


@roles('organizer', 'admin', route_name='payouts_status')
class PayoutsStatusView(generics.GenericAPIView):
    """
    GET /api/v1/users/me/payouts/status/

    Checks and syncs the Stripe Connect status for the individual organizer.
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def get(self, request):
        from billing.services import stripe_connect_service

        user = request.user

        if not user.stripe_connect_id:
            return Response({
                'connected': False,
                'status': 'not_connected',
                'charges_enabled': False,
            })

        status_info = stripe_connect_service.get_account_status(user.stripe_connect_id)

        if 'error' in status_info:
            return Response(
                {'detail': 'Failed to retrieve status from Stripe.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Update local state
        user.stripe_charges_enabled = status_info.get('charges_enabled', False)
        if status_info.get('charges_enabled'):
            user.stripe_account_status = 'active'
        elif status_info.get('details_submitted'):
            user.stripe_account_status = 'pending_verification'
        else:
            user.stripe_account_status = 'restricted'

        user.save(update_fields=['stripe_charges_enabled', 'stripe_account_status', 'updated_at'])

        return Response({
            'connected': True,
            'status': user.stripe_account_status,
            'charges_enabled': user.stripe_charges_enabled,
            'stripe_id': user.stripe_connect_id,
            'details': status_info,
        })


@roles('organizer', 'admin', route_name='payouts_dashboard')
class PayoutsDashboardView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/payouts/dashboard/

    Returns a Stripe Express dashboard login link.
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def post(self, request):
        from billing.services import stripe_connect_service

        user = request.user

        if not user.stripe_connect_id:
            return error_response('Stripe account not connected.', code='NOT_CONNECTED')

        login_url = stripe_connect_service.create_login_link(user.stripe_connect_id)
        if not login_url:
            return error_response('Failed to create Stripe dashboard link.', code='DASHBOARD_LINK_FAILED')

        return Response({'url': login_url})
