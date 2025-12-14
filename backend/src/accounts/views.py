"""
Accounts app views and viewsets.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from django.utils import timezone

from common.permissions import IsOrganizer
from . import serializers

User = get_user_model()


# =============================================================================
# Throttle Classes
# =============================================================================

class AuthThrottle(AnonRateThrottle):
    """Stricter throttle for auth endpoints."""
    rate = '20/hour'


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
        
        return Response({
            'message': 'Account created successfully.',
            'user': {
                'uuid': str(user.uuid),
                'email': user.email,
                'full_name': user.full_name,
            }
        }, status=status.HTTP_201_CREATED)


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
        
        token = serializer.validated_data['token']
        
        try:
            user = User.objects.get(
                email_verification_token=token,
                email_verified=False
            )
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired token.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.email_verification_expires_at and user.email_verification_expires_at < timezone.now():
            return Response(
                {'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.email_verified = True
        user.email_verification_token = ''
        user.save(update_fields=['email_verified', 'email_verification_token', 'updated_at'])
        
        # Link any guest registrations
        from registrations.models import Registration
        Registration.link_registrations_for_user(user)
        
        return Response({'message': 'Email verified successfully.'})


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
        
        return Response({
            'message': 'If an account exists, a password reset email has been sent.'
        })


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
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired token.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.password_reset_expires_at and user.password_reset_expires_at < timezone.now():
            return Response(
                {'error': {'code': 'TOKEN_EXPIRED', 'message': 'Token has expired.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(password)
        user.password_reset_token = ''
        user.save(update_fields=['password', 'password_reset_token', 'updated_at'])
        
        return Response({'message': 'Password reset successfully.'})


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

class CurrentUserView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/ - Current user profile."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return serializers.UserProfileUpdateSerializer
        return serializers.UserSerializer
    
    def get_object(self):
        return self.request.user


class OrganizerProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/organizer-profile/ - Organizer profile."""
    serializer_class = serializers.OrganizerProfileUpdateSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def get_object(self):
        return self.request.user


class NotificationPreferencesView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/users/me/notifications/ - Notification preferences."""
    serializer_class = serializers.NotificationPreferencesSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class PublicOrganizerView(generics.RetrieveAPIView):
    """GET /api/v1/organizers/{uuid}/ - Public organizer profile."""
    serializer_class = serializers.PublicOrganizerSerializer
    permission_classes = [AllowAny]
    lookup_field = 'uuid'
    
    def get_queryset(self):
        return User.objects.filter(
            account_type='organizer',
            is_organizer_profile_public=True,
            deleted_at__isnull=True
        )


class UpgradeToOrganizerView(generics.GenericAPIView):
    """POST /api/v1/users/me/upgrade/ - Upgrade to organizer."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.account_type == 'organizer':
            return Response(
                {'error': {'code': 'ALREADY_ORGANIZER', 'message': 'Already an organizer.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.upgrade_to_organizer()
        
        return Response({
            'message': 'Successfully upgraded to organizer.',
            'user': serializers.UserSerializer(user).data
        })


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
        reason = serializer.validated_data.get('reason', '')
        
        # Anonymize user data (GDPR compliant)
        user.anonymize()
        
        return Response({'message': 'Account has been deleted.'})
