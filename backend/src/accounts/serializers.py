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

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'password_confirm',
            'full_name',
            'professional_title',
            'organization_name',
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

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Assign default learner role
        user.assign_role("learner")

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
            'roles': self.user.role_names,
            'primary_role': self.user.primary_role,
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

    roles = serializers.SerializerMethodField()
    primary_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'uuid',
            'email',
            'full_name',
            'professional_title',
            'organization_name',
            'profile_photo_url',
            'bio',
            'roles',
            'primary_role',
            'email_verified',
            'onboarding_completed',
            'timezone',
            # Notification preferences
            'notify_event_reminders',
            'notify_certificate_issued',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'email',
            'roles',
            'primary_role',
            'email_verified',
            'onboarding_completed',
            'created_at',
            'updated_at',
        ]

    def get_roles(self, obj):
        return obj.role_names

    def get_primary_role(self, obj):
        return obj.primary_role


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            'full_name',
            'professional_title',
            'organization_name',
            'profile_photo_url',
            'bio',
            'timezone',
        ]


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences only."""

    class Meta:
        model = User
        fields = [
            'notify_event_reminders',
            'notify_certificate_issued',
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


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user data for embedding."""

    class Meta:
        model = User
        fields = ['uuid', 'full_name', 'email']


# =============================================================================
# Admin User Management Serializers
# =============================================================================


class AdminUserListSerializer(serializers.ModelSerializer):
    """User data for admin user management list."""

    roles = serializers.SerializerMethodField()
    primary_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'uuid', 'email', 'full_name', 'professional_title',
            'organization_name', 'roles', 'primary_role',
            'is_active', 'is_staff', 'email_verified',
            'last_login_at', 'created_at',
        ]
        read_only_fields = fields

    def get_roles(self, obj):
        return obj.role_names

    def get_primary_role(self, obj):
        return obj.primary_role


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Create a user directly (admin action)."""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    roles = serializers.ListField(child=serializers.CharField(), required=False, default=["learner"])

    class Meta:
        model = User
        fields = ['email', 'full_name', 'professional_title', 'organization_name', 'password', 'roles']

    def validate_roles(self, value):
        valid_roles = {"learner", "educator", "course_manager", "admin"}
        for role in value:
            if role not in valid_roles:
                raise serializers.ValidationError(f"Invalid role: {role}. Valid roles: {valid_roles}")
        return value

    def create(self, validated_data):
        roles = validated_data.pop('roles', ['learner'])
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.email_verified = True  # Admin-created users are auto-verified
        user.save()

        # Assign roles
        for role_name in roles:
            user.assign_role(role_name)

        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Update user details (admin action)."""

    roles = serializers.ListField(child=serializers.CharField(), required=False)

    class Meta:
        model = User
        fields = ['full_name', 'professional_title', 'organization_name', 'is_active', 'roles']

    def validate_roles(self, value):
        valid_roles = {"learner", "educator", "course_manager", "admin"}
        for role in value:
            if role not in valid_roles:
                raise serializers.ValidationError(f"Invalid role: {role}. Valid roles: {valid_roles}")
        return value

    def update(self, instance, validated_data):
        roles = validated_data.pop('roles', None)
        instance = super().update(instance, validated_data)

        if roles is not None:
            instance.set_roles(roles)

        return instance


class InviteUserSerializer(serializers.Serializer):
    """Send invitation to a new user."""

    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(required=True, max_length=255)
    role = serializers.ChoiceField(
        choices=["learner", "educator", "course_manager", "admin"],
        default="learner",
    )
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000, default="")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()


class BulkInviteSerializer(serializers.Serializer):
    """Bulk invite users via list of invitations."""

    invitations = serializers.ListField(
        child=InviteUserSerializer(),
        min_length=1,
        max_length=100,
    )


class AcceptInvitationSerializer(serializers.Serializer):
    """Accept an invitation and set password."""

    token = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': "Passwords don't match."})
        return attrs


class UserInvitationSerializer(serializers.ModelSerializer):
    """Serializer for UserInvitation list/detail."""

    from accounts.models import UserInvitation

    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        from accounts.models import UserInvitation
        model = UserInvitation
        fields = [
            'uuid', 'email', 'full_name', 'role', 'invited_by_name',
            'is_used', 'is_expired', 'expires_at', 'accepted_at', 'created_at',
        ]
        read_only_fields = fields

    def get_invited_by_name(self, obj):
        return obj.invited_by.full_name if obj.invited_by else None


# =============================================================================
# Account Deletion Serializer
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
# GDPR Data Export Serializer
# =============================================================================


class DataExportSerializer(serializers.Serializer):
    """GDPR data export request."""

    include_registrations = serializers.BooleanField(default=True)
    include_certificates = serializers.BooleanField(default=True)
    include_attendance = serializers.BooleanField(default=True)
    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
