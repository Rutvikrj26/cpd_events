"""
Accounts app models - User, UserSession, UserInvitation.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from common.fields import EncryptedTextField, LowercaseEmailField
from common.models import BaseModel, SoftDeleteModel
from common.utils import generate_verification_code


class UserManager(BaseUserManager):
    """
    Custom user manager with email as the unique identifier.
    """

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        """Allow authentication with email (case-insensitive)."""
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    """
    Custom user model for the CPD Events platform.

    Roles are managed via Django Groups (learner, educator, course_manager, instructor, admin).
    Users can belong to multiple groups simultaneously.

    Key Features:
    - Email-based authentication (no username)
    - Django Groups for role management
    - Soft delete with data anonymization
    - Email verification flow
    - Notification preferences

    Soft Delete Behavior:
    - Email anonymized to prevent reuse issues
    - Personal data cleared for GDPR compliance
    - Related data (registrations, certificates) preserved
    """

    # =========================================
    # Authentication Fields
    # =========================================
    email = LowercaseEmailField(unique=True, db_index=True, help_text="Primary email address (used for login)")

    # OAuth integration fields
    google_user_id = models.CharField(
        max_length=255, blank=True, null=True, unique=True, db_index=True, help_text="Google user ID for OAuth"
    )
    auth_provider = models.CharField(
        max_length=20,
        choices=[("local", "Local"), ("google", "Google")],
        default="local",
        help_text="Original authentication method used for account creation",
    )

    # =========================================
    # Profile Fields
    # =========================================
    full_name = models.CharField(max_length=255, validators=[MinLengthValidator(2)], help_text="Full name")
    professional_title = models.CharField(max_length=255, blank=True, help_text="Professional title (e.g., MD, PhD)")
    organization_name = models.CharField(max_length=255, blank=True, help_text="Organization/company name")
    timezone = models.CharField(max_length=50, default="UTC", help_text="User's preferred timezone")
    profile_photo_url = models.URLField(blank=True, help_text="URL to profile photo")
    profile_image = models.ImageField(upload_to="profile_images/", blank=True, null=True, help_text="Profile image file")
    bio = models.TextField(blank=True, max_length=1000, help_text="User bio/description")

    # =========================================
    # Account Status
    # =========================================
    is_active = models.BooleanField(default=True, help_text="Whether user can log in")
    is_staff = models.BooleanField(default=False, help_text="Can access admin site")
    onboarding_completed = models.BooleanField(default=False, help_text="Whether user completed initial onboarding")

    # =========================================
    # Email Verification
    # =========================================
    email_verified = models.BooleanField(default=False, help_text="Whether email has been verified")
    email_verified_at = models.DateTimeField(null=True, blank=True, help_text="When email was verified")
    email_verification_token = models.CharField(max_length=100, blank=True, help_text="Token for email verification")
    email_verification_sent_at = models.DateTimeField(null=True, blank=True, help_text="When verification email was sent")

    # =========================================
    # Password Reset
    # =========================================
    password_reset_token = models.CharField(max_length=100, blank=True, help_text="Token for password reset")
    password_reset_sent_at = models.DateTimeField(null=True, blank=True, help_text="When password reset was requested")

    # =========================================
    # Email Change (self-service)
    # =========================================
    pending_email = LowercaseEmailField(blank=True, help_text="New email awaiting confirmation")
    email_change_token = models.CharField(max_length=100, blank=True, help_text="Token for confirming email change")
    email_change_requested_at = models.DateTimeField(null=True, blank=True, help_text="When the email change was requested")

    # =========================================
    # Notification Preferences
    # =========================================
    notify_event_reminders = models.BooleanField(default=True, help_text="Receive event reminders")
    notify_certificate_issued = models.BooleanField(default=True, help_text="Receive certificate notifications")
    notify_event_updates = models.BooleanField(default=True, help_text="Receive event change notifications")

    # =========================================
    # Engagement Stats (denormalized)
    # =========================================
    events_attended_count = models.PositiveIntegerField(default=0, help_text="Number of events attended")
    certificates_earned_count = models.PositiveIntegerField(default=0, help_text="Number of certificates earned")
    total_cpd_credits = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Total CPD credits earned")
    events_hosted_count = models.PositiveIntegerField(default=0, help_text="Number of events hosted")

    # =========================================
    # Timestamps
    # =========================================
    last_login_at = models.DateTimeField(null=True, blank=True, help_text="Last successful login")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        permissions = [
            ("can_manage_users", "Can manage users (admin)"),
            ("can_invite_users", "Can invite users"),
        ]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["uuid"]),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    # =========================================
    # Role Properties (via Django Groups)
    # =========================================
    #
    # `is_staff` is NOT considered here. Django's own admin site continues to
    # gate on `is_staff` (it checks in `django.contrib.admin`, which we do not
    # override), but our application authorization is driven exclusively by
    # Group membership. Use `is_institution_admin` below as the single source
    # of truth for "can administer the institution".

    @property
    def is_institution_admin(self):
        """True iff the user belongs to the `admin` group.

        This is the authoritative check for institution administrator power
        inside our application. Django's own `/admin/` UI continues to gate
        on `is_staff`, which is tracked separately.
        """
        return self.groups.filter(name="admin").exists()

    @property
    def is_educator(self):
        """Check if user is in the educator or admin group."""
        return self.groups.filter(name__in=["educator", "admin"]).exists()

    @property
    def is_learner(self):
        """Check if user is in the learner group."""
        return self.groups.filter(name="learner").exists()

    @property
    def is_course_manager(self):
        """Check if user is in the course_manager or admin group."""
        return self.groups.filter(name__in=["course_manager", "admin"]).exists()

    @property
    def is_admin(self):
        """Alias for institution admin (kept for call-site compatibility)."""
        return self.is_institution_admin

    @property
    def role_names(self):
        """Get list of group names the user belongs to."""
        return list(self.groups.values_list("name", flat=True))

    @property
    def primary_role(self):
        """Get the highest-priority role for display purposes."""
        roles = set(self.role_names)
        if "admin" in roles:
            return "admin"
        if "educator" in roles:
            return "educator"
        if "course_manager" in roles:
            return "course_manager"
        if "instructor" in roles:
            return "instructor"
        return "learner"

    @property
    def display_name(self):
        """Best name for display."""
        if self.professional_title:
            return f"{self.full_name}, {self.professional_title}"
        return self.full_name

    @property
    def email_verification_expires_at(self):
        """Calculate when email verification token expires (24 hours)."""
        if not self.email_verification_sent_at:
            return None
        return self.email_verification_sent_at + timezone.timedelta(hours=24)

    # =========================================
    # Methods
    # =========================================
    def assign_role(self, role_name: str):
        """Add a role (Django Group) to this user."""
        from django.contrib.auth.models import Group

        group, _ = Group.objects.get_or_create(name=role_name)
        self.groups.add(group)

    def remove_role(self, role_name: str):
        """Remove a role (Django Group) from this user."""
        from django.contrib.auth.models import Group

        try:
            group = Group.objects.get(name=role_name)
            self.groups.remove(group)
        except Group.DoesNotExist:
            pass

    def set_roles(self, role_names: list[str], *, changed_by=None, reason: str = ""):
        """Replace all roles with the given list and record an audit row.

        Pass `changed_by` (a User) and optional `reason` when the change
        originates from an admin action, so the audit trail has attribution.
        """
        from django.contrib.auth.models import Group

        before = self.role_names
        # get_or_create so callers can pass role names that haven't yet been
        # materialised as Group rows (parity with assign_role).
        groups = []
        for name in role_names:
            group, _ = Group.objects.get_or_create(name=name)
            groups.append(group)
        self.groups.set(groups)
        after = self.role_names

        if set(before) != set(after):
            UserRoleChange.objects.create(
                user=self,
                changed_by=changed_by,
                from_roles=list(before),
                to_roles=list(after),
                reason=reason,
            )

    def generate_email_verification_token(self):
        """Generate and save email verification token."""
        self.email_verification_token = generate_verification_code(32)
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=["email_verification_token", "email_verification_sent_at", "updated_at"])
        return self.email_verification_token

    def verify_email(self, token):
        """Verify email with token."""
        if self.email_verification_token and self.email_verification_token == token:
            self.email_verified = True
            self.email_verified_at = timezone.now()
            self.email_verification_token = ""
            self.save(update_fields=["email_verified", "email_verified_at", "email_verification_token", "updated_at"])
            return True
        return False

    def generate_password_reset_token(self):
        """Generate and save password reset token."""
        self.password_reset_token = generate_verification_code(32)
        self.password_reset_sent_at = timezone.now()
        self.save(update_fields=["password_reset_token", "password_reset_sent_at", "updated_at"])
        return self.password_reset_token

    def reset_password(self, token, new_password):
        """Reset password with token."""
        if not self.password_reset_token or self.password_reset_token != token:
            return False

        # Check token expiry (24 hours)
        if self.password_reset_sent_at:
            expiry = self.password_reset_sent_at + timezone.timedelta(hours=24)
            if timezone.now() > expiry:
                return False

        self.set_password(new_password)
        self.password_reset_token = ""
        self.save(update_fields=["password", "password_reset_token", "updated_at"])
        return True

    def anonymize(self):
        """
        Anonymize user data for GDPR compliance.
        Clears personal details and marks as inactive.
        """
        import uuid

        self.full_name = "Deleted User"
        self.email = f"deleted-{uuid.uuid4()}@example.com"
        self.professional_title = ""
        self.organization_name = ""
        self.bio = ""
        self.profile_photo_url = ""
        self.is_active = False
        self.email_verified = False
        self.password_reset_token = ""
        self.password_reset_sent_at = None

        # Save all changes and then soft delete
        self.save()

        if hasattr(self, "soft_delete"):
            self.soft_delete()
        else:
            self.delete()

        return True

    def soft_delete(self):
        """Soft delete with anonymization."""
        import uuid as uuid_lib

        anon_suffix = str(uuid_lib.uuid4())[:8]
        self.email = f"deleted_{anon_suffix}@deleted.local"
        self.full_name = "Deleted User"
        self.professional_title = ""
        self.organization_name = ""
        self.profile_photo_url = ""
        self.is_active = False

        # Call parent soft_delete
        super().soft_delete()

    def record_login(self):
        """Record successful login."""
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at", "updated_at"])


class UserInvitation(BaseModel):
    """
    Invitation for a new user to join the institution.

    Admin creates an invitation, user receives email with activation link,
    clicks link to set password and complete account setup.
    """

    ROLE_CHOICES = [
        ("learner", "Learner"),
        ("educator", "Educator"),
        ("course_manager", "Course Manager"),
        ("instructor", "Instructor"),
        ("admin", "Admin"),
    ]

    email = LowercaseEmailField(db_index=True, help_text="Email to invite")
    full_name = models.CharField(max_length=255, help_text="Invitee's full name")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="learner", help_text="Role to assign on acceptance")
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sent_invitations")
    token = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique invitation token")
    accepted_at = models.DateTimeField(null=True, blank=True, help_text="When the invitation was accepted")
    expires_at = models.DateTimeField(help_text="When the invitation expires")
    is_used = models.BooleanField(default=False, help_text="Whether the invitation has been used")
    message = models.TextField(blank=True, help_text="Optional personal message from admin")
    resent_count = models.PositiveIntegerField(default=0, help_text="How many times this invitation has been resent")
    last_sent_at = models.DateTimeField(default=timezone.now, help_text="When the invitation was last sent")
    revoked_at = models.DateTimeField(null=True, blank=True, help_text="When the invitation was revoked by an admin")

    class Meta:
        db_table = "user_invitations"
        ordering = ["-created_at"]
        verbose_name = "User Invitation"
        verbose_name_plural = "User Invitations"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["token"]),
            models.Index(fields=["is_used", "-created_at"]),
        ]

    def __str__(self):
        return f"Invitation for {self.email} ({self.role})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and not self.is_revoked

    @property
    def status(self):
        """Derived status: pending / accepted / expired / revoked."""
        if self.is_used:
            return "accepted"
        if self.is_revoked:
            return "revoked"
        if self.is_expired:
            return "expired"
        return "pending"

    def accept(self, user):
        """Mark invitation as accepted."""
        self.is_used = True
        self.accepted_at = timezone.now()
        self.save(update_fields=["is_used", "accepted_at", "updated_at"])

    def revoke(self):
        """Mark invitation as revoked. Idempotent."""
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at", "updated_at"])

    @classmethod
    def create_invitation(cls, email, full_name, role, invited_by, message="", expires_days=None):
        """Create a new invitation with a unique token."""
        from django.conf import settings

        if expires_days is None:
            expires_days = getattr(settings, "INVITATION_EXPIRY_DAYS", 30)

        now = timezone.now()
        return cls.objects.create(
            email=email,
            full_name=full_name,
            role=role,
            invited_by=invited_by,
            token=generate_verification_code(48),
            expires_at=now + timezone.timedelta(days=expires_days),
            last_sent_at=now,
            message=message,
        )


class UserSession(BaseModel):
    """
    Active user session for tracking logins.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")

    session_key = models.CharField(max_length=100, unique=True, db_index=True, help_text="Django session key")

    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP address")
    user_agent = models.TextField(blank=True, help_text="Browser user agent")
    device_type = models.CharField(max_length=50, blank=True, help_text="Detected device type")

    last_activity_at = models.DateTimeField(auto_now=True, help_text="Last activity timestamp")
    expires_at = models.DateTimeField(help_text="When session expires")

    is_active = models.BooleanField(default=True, help_text="Whether session is active")

    class Meta:
        db_table = "user_sessions"
        ordering = ["-last_activity_at"]
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self):
        return f"Session: {self.user.email}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    @classmethod
    def deactivate_all_for_user(cls, user):
        return cls.objects.filter(user=user, is_active=True).update(is_active=False)


class CPDRequirement(BaseModel):
    """
    CPD requirement tracking for a user.
    """

    class PeriodType(models.TextChoices):
        CALENDAR_YEAR = "calendar_year", "Calendar Year (Jan-Dec)"
        FISCAL_YEAR = "fiscal_year", "Fiscal Year"
        ROLLING_12 = "rolling_12", "Rolling 12 Months"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cpd_requirements")

    cpd_type = models.CharField(max_length=100, help_text="CPD type code (e.g., 'general', 'clinical', 'ethics')")
    cpd_type_display = models.CharField(max_length=255, blank=True, help_text="Human-readable CPD type name")
    annual_requirement = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)], help_text="Required credits per period"
    )

    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.CALENDAR_YEAR)
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1, help_text="Month when fiscal year starts (1-12)")
    fiscal_year_start_day = models.PositiveSmallIntegerField(default=1, help_text="Day when fiscal year starts")

    licensing_body = models.CharField(max_length=255, blank=True, help_text="Name of licensing body")
    license_number = models.CharField(max_length=100, blank=True, help_text="License number")

    notes = models.TextField(blank=True, help_text="Additional notes about this requirement")

    is_active = models.BooleanField(default=True, help_text="Whether this requirement is active")

    class Meta:
        db_table = "cpd_requirements"
        verbose_name = "CPD Requirement"
        verbose_name_plural = "CPD Requirements"
        unique_together = [["user", "cpd_type"]]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.cpd_type_display or self.cpd_type}"

    def get_current_period_bounds(self):
        from datetime import date

        today = date.today()

        if self.period_type == self.PeriodType.CALENDAR_YEAR:
            start = date(today.year, 1, 1)
            end = date(today.year, 12, 31)

        elif self.period_type == self.PeriodType.FISCAL_YEAR:
            fy_month = self.fiscal_year_start_month
            fy_day = self.fiscal_year_start_day

            if today.month < fy_month or (today.month == fy_month and today.day < fy_day):
                start = date(today.year - 1, fy_month, fy_day)
                end = date(today.year, fy_month, fy_day) - timezone.timedelta(days=1)
            else:
                start = date(today.year, fy_month, fy_day)
                end = date(today.year + 1, fy_month, fy_day) - timezone.timedelta(days=1)

        elif self.period_type == self.PeriodType.ROLLING_12:
            end = today
            start = today - timezone.timedelta(days=365)

        else:
            start = date(today.year, 1, 1)
            end = date(today.year, 12, 31)

        return (start, end)

    def get_earned_credits(self):
        from decimal import Decimal

        from certificates.models import Certificate

        start, end = self.get_current_period_bounds()

        certificates = Certificate.objects.filter(
            registration__user=self.user,
            certificate_data__cpd_type=self.cpd_type,
            status="issued",
            created_at__date__gte=start,
            created_at__date__lte=end,
        )

        total = Decimal("0")
        for cert in certificates:
            try:
                val = cert.certificate_data.get("cpd_credits", 0)
                total += Decimal(str(val))
            except (TypeError, ValueError):
                continue

        return total

    @property
    def completion_percent(self):
        if self.annual_requirement == 0:
            return 100
        earned = self.get_earned_credits()
        percent = (earned / self.annual_requirement) * 100
        return min(int(percent), 100)

    @property
    def credits_remaining(self):
        from decimal import Decimal

        earned = self.get_earned_credits()
        remaining = self.annual_requirement - earned
        return max(remaining, Decimal("0"))


class Notification(BaseModel):
    """
    In-app notification for a user.
    """

    class Type(models.TextChoices):
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        REFUND_PROCESSED = "refund_processed", "Refund Processed"
        INVITATION_SENT = "invitation_sent", "Invitation Sent"
        ACCOUNT_ACTIVATED = "account_activated", "Account Activated"
        DISCUSSION_REPLY = "discussion_reply", "Discussion Reply"
        DISCUSSION_MENTION = "discussion_mention", "Discussion Mention"
        DISCUSSION_FLAG_RESOLVED = "discussion_flag_resolved", "Discussion Flag Resolved"
        SYSTEM = "system", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.SYSTEM,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "notification_type"]),
            models.Index(fields=["user", "read_at"]),
            models.Index(fields=["-created_at"]),
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])


class AuditLog(BaseModel):
    """
    Audit log entry for sensitive actions.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=120, db_index=True)
    object_type = models.CharField(max_length=120, blank=True)
    object_uuid = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "action"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        actor = self.actor.email if self.actor else "system"
        return f"{actor} - {self.action}"


class UserRoleChange(BaseModel):
    """
    Audit row for a role change on a User.

    Written by `User.set_roles()` whenever the set of role names actually
    changes. `from_roles` / `to_roles` are JSON lists of group-name strings.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_changes",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_changes_made",
    )
    from_roles = models.JSONField(default=list)
    to_roles = models.JSONField(default=list)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = "user_role_changes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["changed_by", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.from_roles} -> {self.to_roles}"
