"""
Accounts app serializers.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'full_name', 'professional_title', 'organization_name']
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

        user = User(**validated_data)
        user.set_password(password)
        user.account_type = 'attendee'
        user.save()

        # Link any guest registrations
        from registrations.models import Registration

        Registration.link_registrations_for_user(user)

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data."""

    def validate(self, attrs):
        data = super().validate(attrs)

        data['user'] = {
            'uuid': str(self.user.uuid),
            'email': self.user.email,
            'full_name': self.user.full_name,
            'account_type': self.user.account_type,
            'email_verified': self.user.email_verified,
        }

        return data


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
            'timezone',
            # Organizer-specific
            'organizer_logo_url',
            'organizer_website',
            'organizer_bio',
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
    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)

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
