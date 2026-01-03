"""
Accounts app models - User, ZoomConnection, UserSession.
"""

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
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        """Allow authentication with email (case-insensitive)."""
        return self.get(email__iexact=email)


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    """
    Custom user model for the CPD Events platform.

    Key Features:
    - Email-based authentication (no username)
    - Account types: Attendee (default) and Organizer
    - Soft delete with data anonymization
    - Email verification flow
    - Notification preferences
    - Organizer profile fields

    Soft Delete Behavior:
    - Email anonymized to prevent reuse issues
    - Personal data cleared for GDPR compliance
    - Related data (registrations, certificates) preserved
    """

    class AccountType(models.TextChoices):
        ATTENDEE = 'attendee', 'Attendee'
        ORGANIZER = 'organizer', 'Organizer'

    # =========================================
    # Authentication Fields
    # =========================================
    email = LowercaseEmailField(unique=True, db_index=True, help_text="Primary email address (used for login)")

    # =========================================
    # Profile Fields
    # =========================================
    full_name = models.CharField(max_length=255, validators=[MinLengthValidator(2)], help_text="Full name")
    professional_title = models.CharField(max_length=255, blank=True, help_text="Professional title (e.g., MD, PhD)")
    organization_name = models.CharField(max_length=255, blank=True, help_text="Organization/company name")
    timezone = models.CharField(max_length=50, default='UTC', help_text="User's preferred timezone")
    profile_photo_url = models.URLField(blank=True, help_text="URL to profile photo")
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True, help_text="Profile image file")
    bio = models.TextField(blank=True, max_length=1000, help_text="User bio/description")

    # =========================================
    # Account Type & Status
    # =========================================
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.ATTENDEE,
        db_index=True,
        help_text="Account type determines available features",
    )

    is_active = models.BooleanField(default=True, help_text="Whether user can log in")
    is_staff = models.BooleanField(default=False, help_text="Can access admin site")

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
    # Notification Preferences
    # =========================================
    notify_event_reminders = models.BooleanField(default=True, help_text="Receive event reminders")
    notify_certificate_issued = models.BooleanField(default=True, help_text="Receive certificate notifications")
    notify_marketing = models.BooleanField(default=False, help_text="Receive marketing emails")
    notify_event_updates = models.BooleanField(default=True, help_text="Receive event change notifications")

    # =========================================
    # Organizer Profile Fields
    # =========================================
    organizer_bio = models.TextField(blank=True, max_length=2000, help_text="Public bio for organizer profile")
    organizer_website = models.URLField(blank=True, help_text="Website URL")
    organizer_linkedin = models.URLField(blank=True, help_text="LinkedIn profile URL")
    organizer_twitter = models.CharField(max_length=100, blank=True, help_text="Twitter/X handle")
    organizer_logo_url = models.URLField(blank=True, help_text="Organization logo URL")
    organizer_slug = models.SlugField(
        max_length=100, unique=True, null=True, blank=True, help_text="URL-friendly identifier for public profile"
    )
    is_organizer_profile_public = models.BooleanField(default=False, help_text="Make organizer profile visible to public")

    # =========================================
    # Engagement Stats (denormalized)
    # =========================================
    events_attended_count = models.PositiveIntegerField(default=0, help_text="Number of events attended")
    certificates_earned_count = models.PositiveIntegerField(default=0, help_text="Number of certificates earned")
    total_cpd_credits = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Total CPD credits earned")

    # Organizer stats
    events_hosted_count = models.PositiveIntegerField(default=0, help_text="Number of events hosted")

    # =========================================
    # Timestamps
    # =========================================
    stripe_connect_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Connect Account ID")
    stripe_account_status = models.CharField(max_length=50, default='pending', help_text="Connect account status")
    stripe_charges_enabled = models.BooleanField(default=False, help_text="Whether account can accept payments")

    # =========================================
    # Timestamps
    # =========================================
    last_login_at = models.DateTimeField(null=True, blank=True, help_text="Last successful login")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['account_type']),
            models.Index(fields=['uuid']),
            models.Index(fields=['organizer_slug']),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    # =========================================
    # Properties
    # =========================================
    @property
    def is_organizer(self):
        """Check if user is an organizer."""
        return self.account_type == self.AccountType.ORGANIZER

    @property
    def is_attendee(self):
        """Check if user is an attendee."""
        return self.account_type == self.AccountType.ATTENDEE

    @property
    def display_name(self):
        """Best name for display."""
        if self.professional_title:
            return f"{self.full_name}, {self.professional_title}"
        return self.full_name

    @property
    def has_zoom_connected(self):
        """Check if Zoom is connected."""
        return hasattr(self, 'zoom_connection') and self.zoom_connection.is_active

    @property
    def email_verification_expires_at(self):
        """Calculate when email verification token expires (24 hours)."""
        if not self.email_verification_sent_at:
            return None
        return self.email_verification_sent_at + timezone.timedelta(hours=24)

    # =========================================
    # Methods
    # =========================================
    def upgrade_to_organizer(self):
        """Upgrade account to organizer."""
        if self.account_type != self.AccountType.ORGANIZER:
            self.account_type = self.AccountType.ORGANIZER
            self.save(update_fields=['account_type', 'updated_at'])

    def downgrade_to_attendee(self):
        """Downgrade account to attendee."""
        if self.account_type != self.AccountType.ATTENDEE:
            self.account_type = self.AccountType.ATTENDEE
            self.save(update_fields=['account_type', 'updated_at'])

    def generate_email_verification_token(self):
        """Generate and save email verification token."""
        self.email_verification_token = generate_verification_code(32)
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at', 'updated_at'])
        return self.email_verification_token

    def verify_email(self, token):
        """Verify email with token."""
        if self.email_verification_token and self.email_verification_token == token:
            self.email_verified = True
            self.email_verified_at = timezone.now()
            self.email_verification_token = ''
            self.save(update_fields=['email_verified', 'email_verified_at', 'email_verification_token', 'updated_at'])
            return True
        return False

    def generate_password_reset_token(self):
        """Generate and save password reset token."""
        self.password_reset_token = generate_verification_code(32)
        self.password_reset_sent_at = timezone.now()
        self.save(update_fields=['password_reset_token', 'password_reset_sent_at', 'updated_at'])
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
        self.password_reset_token = ''
        self.save(update_fields=['password', 'password_reset_token', 'updated_at'])
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
        self.organizer_bio = ""
        self.organizer_website = ""
        self.profile_photo_url = ""
        self.is_active = False
        self.email_verified = False
        self.password_reset_token = ""
        self.password_reset_sent_at = None
        
        # Save all changes and then soft delete
        self.save()
        
        # If the model has soft_delete, use it
        if hasattr(self, 'soft_delete'):
            self.soft_delete()
        else:
            self.delete()
            
        return True

    def soft_delete(self):
        """Soft delete with anonymization."""
        import uuid as uuid_lib

        # Anonymize personal data
        anon_suffix = str(uuid_lib.uuid4())[:8]
        self.email = f"deleted_{anon_suffix}@deleted.local"
        self.full_name = "Deleted User"
        self.professional_title = ""
        self.organization_name = ""
        self.profile_photo_url = ""
        self.organizer_bio = ""
        self.organizer_website = ""
        self.organizer_linkedin = ""
        self.organizer_twitter = ""
        self.organizer_logo_url = ""
        self.organizer_slug = None
        self.is_active = False

        # Call parent soft_delete
        super().soft_delete()

    def record_login(self):
        """Record successful login."""
        self.last_login_at = timezone.now()
        self.save(update_fields=['last_login_at', 'updated_at'])


class ZoomConnection(BaseModel):
    """
    OAuth connection to Zoom for an organizer.

    Stores tokens and connection metadata.
    One-to-one with User (only organizers can have this).
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='zoom_connection')

    # =========================================
    # OAuth Tokens (encrypted at rest)
    # =========================================
    access_token = EncryptedTextField(help_text="Zoom OAuth access token")
    refresh_token = EncryptedTextField(help_text="Zoom OAuth refresh token")
    token_expires_at = models.DateTimeField(help_text="When access token expires")

    # =========================================
    # Zoom Account Info
    # =========================================
    zoom_user_id = models.CharField(max_length=100, help_text="Zoom user ID")
    zoom_account_id = models.CharField(max_length=100, blank=True, help_text="Zoom account ID")
    zoom_email = LowercaseEmailField(blank=True, help_text="Email associated with Zoom account")

    # =========================================
    # Scopes
    # =========================================
    scopes = models.TextField(blank=True, help_text="OAuth scopes granted (comma-separated)")

    # =========================================
    # Status
    # =========================================
    is_active = models.BooleanField(default=True, help_text="Whether connection is active")
    last_used_at = models.DateTimeField(null=True, blank=True, help_text="Last time connection was used")
    last_error = models.TextField(blank=True, help_text="Last error message (if any)")
    last_error_at = models.DateTimeField(null=True, blank=True, help_text="When last error occurred")
    error_count = models.PositiveIntegerField(default=0, help_text="Consecutive error count")

    class Meta:
        db_table = 'zoom_connections'
        verbose_name = 'Zoom Connection'
        verbose_name_plural = 'Zoom Connections'

    def __str__(self):
        return f"Zoom: {self.user.email}"

    @property
    def is_token_expired(self):
        """Check if access token is expired."""
        return timezone.now() >= self.token_expires_at

    @property
    def needs_refresh(self):
        """Check if token needs refresh (expires in < 5 minutes)."""
        buffer = timezone.timedelta(minutes=5)
        return timezone.now() >= (self.token_expires_at - buffer)

    def update_tokens(self, access_token, refresh_token, expires_in):
        """Update OAuth tokens after refresh."""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        self.error_count = 0
        self.last_error = ''
        self.save(
            update_fields=['access_token', 'refresh_token', 'token_expires_at', 'error_count', 'last_error', 'updated_at']
        )

    def record_usage(self):
        """Record that connection was used."""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at', 'updated_at'])

    def record_error(self, error_message):
        """Record an API error."""
        self.last_error = error_message[:1000]
        self.last_error_at = timezone.now()
        self.error_count += 1

        # Deactivate after too many errors
        if self.error_count >= 5:
            self.is_active = False

        self.save(update_fields=['last_error', 'last_error_at', 'error_count', 'is_active', 'updated_at'])

    def disconnect(self):
        """Disconnect Zoom (soft delete)."""
        self.is_active = False
        self.access_token = ''
        self.refresh_token = ''
        self.save(update_fields=['is_active', 'access_token', 'refresh_token', 'updated_at'])


class UserSession(BaseModel):
    """
    Active user session for tracking logins.

    Used for:
    - Session management (logout from all devices)
    - Security monitoring
    - Analytics
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')

    # Session identification
    session_key = models.CharField(max_length=100, unique=True, db_index=True, help_text="Django session key")

    # Device info
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP address")
    user_agent = models.TextField(blank=True, help_text="Browser user agent")
    device_type = models.CharField(max_length=50, blank=True, help_text="Detected device type")

    # Timing
    last_activity_at = models.DateTimeField(auto_now=True, help_text="Last activity timestamp")
    expires_at = models.DateTimeField(help_text="When session expires")

    # Status
    is_active = models.BooleanField(default=True, help_text="Whether session is active")

    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_activity_at']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    def __str__(self):
        return f"Session: {self.user.email}"

    @property
    def is_expired(self):
        """Check if session is expired."""
        return timezone.now() >= self.expires_at

    def deactivate(self):
        """Deactivate session (logout)."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    @classmethod
    def deactivate_all_for_user(cls, user):
        """Deactivate all sessions for a user (logout everywhere)."""
        return cls.objects.filter(user=user, is_active=True).update(is_active=False)


class CPDRequirement(BaseModel):
    """
    CPD requirement tracking for a user.

    Tracks annual CPD requirements for different licensing bodies
    and calculates progress toward completion.
    """

    class PeriodType(models.TextChoices):
        CALENDAR_YEAR = 'calendar_year', 'Calendar Year (Jan-Dec)'
        FISCAL_YEAR = 'fiscal_year', 'Fiscal Year'
        ROLLING_12 = 'rolling_12', 'Rolling 12 Months'

    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cpd_requirements')

    # Requirement details
    cpd_type = models.CharField(max_length=100, help_text="CPD type code (e.g., 'general', 'clinical', 'ethics')")
    cpd_type_display = models.CharField(max_length=255, blank=True, help_text="Human-readable CPD type name")
    annual_requirement = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)], help_text="Required credits per period"
    )

    # Period settings
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.CALENDAR_YEAR)
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1, help_text="Month when fiscal year starts (1-12)")
    fiscal_year_start_day = models.PositiveSmallIntegerField(default=1, help_text="Day when fiscal year starts")

    # Licensing body
    licensing_body = models.CharField(max_length=255, blank=True, help_text="Name of licensing body")
    license_number = models.CharField(max_length=100, blank=True, help_text="License number")

    # Notes
    notes = models.TextField(blank=True, help_text="Additional notes about this requirement")

    # Status
    is_active = models.BooleanField(default=True, help_text="Whether this requirement is active")

    class Meta:
        db_table = 'cpd_requirements'
        verbose_name = 'CPD Requirement'
        verbose_name_plural = 'CPD Requirements'
        unique_together = [['user', 'cpd_type']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.cpd_type_display or self.cpd_type}"

    def get_current_period_bounds(self):
        """
        Get start and end dates for the current period.

        Returns:
            tuple: (start_date, end_date)
        """
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
        """
        Get credits earned in current period.

        Returns:
            Decimal: Total credits earned
        """
        from decimal import Decimal

        from django.db.models import Sum

        from certificates.models import Certificate

        start, end = self.get_current_period_bounds()

        certificates = Certificate.objects.filter(
            registration__user=self.user,
            certificate_data__cpd_type=self.cpd_type,
            status='issued',
            created_at__date__gte=start,
            created_at__date__lte=end,
        )

        total = Decimal('0')
        for cert in certificates:
            try:
                # Value stored as string/number in JSON
                val = cert.certificate_data.get('cpd_credits', 0)
                total += Decimal(str(val))
            except (TypeError, ValueError):
                continue
                
        return total

    @property
    def completion_percent(self):
        """Calculate completion percentage."""
        if self.annual_requirement == 0:
            return 100
        earned = self.get_earned_credits()
        percent = (earned / self.annual_requirement) * 100
        return min(int(percent), 100)

    @property
    def credits_remaining(self):
        """Calculate remaining credits needed."""
        from decimal import Decimal

        earned = self.get_earned_credits()
        remaining = self.annual_requirement - earned
        return max(remaining, Decimal('0'))
