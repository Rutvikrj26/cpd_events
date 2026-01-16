"""
Accounts app serializers.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import Notification
from common.serializers import SoftDeleteModelSerializer

User = get_user_model()


# =============================================================================
# Authentication Serializers
# =============================================================================


class SignupSerializer(serializers.ModelSerializer):
    """User registration serializer."""

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password], style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    # Optional fields for organizer signup
    account_type = serializers.ChoiceField(
        choices=['attendee', 'organizer', 'course_manager'], default='attendee', required=False
    )

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'password_confirm',
            'full_name',
            'professional_title',
            'organization_name',
            'account_type',
        ]
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': "Passwords don't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        account_type = validated_data.pop('account_type', 'attendee')

        user = User(**validated_data)
        user.set_password(password)
        user.account_type = account_type
        user.save()

        # Note: Registration linking is handled in SignupView after user creation
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data."""

    def validate(self, attrs):
        data = super().validate(attrs)

        # Block unverified users from logging in
        if not self.user.email_verified:
            raise serializers.ValidationError({
                'non_field_errors': ['Please verify your email address before logging in.']
            })

        data['user'] = {
            'uuid': str(self.user.uuid),
            'email': self.user.email,
            'full_name': self.user.full_name,
            'account_type': self.user.account_type,
            'email_verified': self.user.email_verified,
        }

        request = self.context.get('request')
        if request:
            self.user.record_login()
            self._record_session(request, data.get('refresh'))

        return data

    def _record_session(self, request, refresh_token: str | None):
        from django.conf import settings
        from rest_framework_simplejwt.tokens import RefreshToken

        from accounts.models import UserSession

        session_key = None
        expires_at = None
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                session_key = token.get('jti')
                lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', timezone.timedelta(days=1))
                expires_at = timezone.now() + lifetime
            except Exception:
                session_key = None

        if not session_key:
            return

        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        UserSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                'user': self.user,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'device_type': '',
                'expires_at': expires_at or timezone.now(),
                'is_active': True,
            },
        )


class PasswordChangeSerializer(serializers.Serializer):
    """Change password for authenticated user."""

    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': "Passwords don't match."})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Request password reset email."""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirm password reset with token."""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': "Passwords don't match."})
        return attrs


class UserSessionSerializer(serializers.Serializer):
    """Serialize active user sessions."""

    uuid = serializers.UUIDField(read_only=True)
    session_key = serializers.CharField(read_only=True)
    ip_address = serializers.CharField(read_only=True)
    user_agent = serializers.CharField(read_only=True)
    device_type = serializers.CharField(read_only=True)
    last_activity_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class EmailVerificationSerializer(serializers.Serializer):
    """Verify email with token."""

    token = serializers.CharField(required=True)


# =============================================================================
# User Serializers
# =============================================================================


class UserSerializer(SoftDeleteModelSerializer):
    """Full user serializer for profile management."""

    class Meta:
        model = User
        fields = [
            'uuid',
            'email',
            'full_name',
            'professional_title',
            'organization_name',
            'profile_photo_url',
            'account_type',
            'email_verified',
            'onboarding_completed',
            'timezone',
            # Organizer-specific
            'organizer_logo_url',
            'organizer_website',
            'organizer_bio',
            'gst_hst_number',
            # Notification preferences
            'notify_event_reminders',
            'notify_certificate_issued',
            'notify_marketing',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'email',
            'account_type',
            'email_verified',
            'onboarding_completed',
            'created_at',
            'updated_at',
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            'full_name',
            'professional_title',
            'organization_name',
            'profile_photo_url',
            'timezone',
            'gst_hst_number',
        ]


class OrganizerProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating organizer-specific profile fields."""

    class Meta:
        model = User
        fields = [
            'organizer_logo_url',
            'organizer_website',
            'organizer_bio',
            'is_organizer_profile_public',
            'gst_hst_number',
        ]


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences only."""

    class Meta:
        model = User
        fields = [
            'notify_event_reminders',
            'notify_certificate_issued',
            'notify_marketing',
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for in-app notifications."""

    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'uuid',
            'notification_type',
            'title',
            'message',
            'action_url',
            'metadata',
            'read_at',
            'is_read',
            'created_at',
        ]
        read_only_fields = fields


class PublicOrganizerSerializer(serializers.ModelSerializer):
    """Public-facing organizer profile."""

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'uuid',
            'display_name',
            'organizer_logo_url',
            'organizer_website',
            'organizer_bio',
        ]

    def get_display_name(self, obj):
        return obj.display_name


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user data for embedding."""

    class Meta:
        model = User
        fields = ['uuid', 'full_name', 'email']


# =============================================================================
# Account Deletion Serializer (H7)
# =============================================================================


class DeleteAccountSerializer(serializers.Serializer):
    """Confirm account deletion."""

    password = serializers.CharField(required=True, write_only=True)
    confirm = serializers.BooleanField(required=True)
    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('confirm'):
            raise serializers.ValidationError({"confirm": "You must confirm account deletion."})
        return attrs

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value


# =============================================================================
# GDPR Data Export Serializer (H6)
# =============================================================================


class DataExportSerializer(serializers.Serializer):
    """GDPR data export request."""

    include_registrations = serializers.BooleanField(default=True)
    include_certificates = serializers.BooleanField(default=True)
    include_attendance = serializers.BooleanField(default=True)
    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
