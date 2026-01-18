# Accounts App: User Management

## Overview

The `accounts` app handles all user-related functionality:
- User authentication and authorization
- Profile management
- Zoom OAuth integration
- Session management
- Password reset flow

---

## Models

### User

The core user model. All users start as attendees and can upgrade to organizers.

```python
# accounts/models.py

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from common.models import SoftDeleteModel
from common.fields import LowercaseEmailField


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    """
    Custom user model with email-based authentication.
    
    Account Types:
    - Attendee: Can register for events, receive certificates, track CPD
    - Organizer: Everything attendee can do + create events, issue certificates
    
    Upgrade Path:
    - Attendee → Organizer (via upgrade_to_organizer())
    - Organizer → Attendee (via downgrade_to_attendee(), loses organizer features)
    
    Soft Delete Behavior:
    - User is anonymized, not deleted (GDPR compliance)
    - Events owned by user: PROTECTED (cannot delete user with events)
    - Registrations: User FK set to NULL (registration preserved)
    - Certificates: Preserved (historical record)
    """
    
    class AccountType(models.TextChoices):
        ATTENDEE = 'attendee', 'Attendee'
        ORGANIZER = 'organizer', 'Organizer'
    
    # =========================================
    # Authentication
    # =========================================
    email = LowercaseEmailField(
        unique=True,
        db_index=True,
        error_messages={
            'unique': 'An account with this email already exists.'
        }
    )
    
    # Email verification
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether user has verified their email"
    )
    email_verification_token = models.CharField(
        max_length=64,
        blank=True,
        help_text="Token for email verification link"
    )
    email_verification_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the verification token expires"
    )
    email_verification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When verification email was last sent"
    )
    
    # Password reset
    password_reset_token = models.CharField(
        max_length=64,
        blank=True,
        help_text="Token for password reset link"
    )
    password_reset_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reset token expires"
    )
    password_reset_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When reset email was last sent"
    )
    
    # =========================================
    # Account Type & Status
    # =========================================
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.ATTENDEE,
        db_index=True
    )
    upgraded_to_organizer_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user upgraded to organizer"
    )
    
    # =========================================
    # Profile
    # =========================================
    full_name = models.CharField(
        max_length=255,
        help_text="Full name as it appears on certificates"
    )
    professional_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Job title or role (e.g., 'Senior Consultant')"
    )
    credentials = models.CharField(
        max_length=255,
        blank=True,
        help_text="Professional credentials (e.g., 'MD, PhD, FACP')"
    )
    organization_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Organization/company name (free text, for display)"
    )
    profile_photo_url = models.URLField(
        blank=True,
        help_text="URL to profile photo in cloud storage"
    )
    bio = models.TextField(
        blank=True,
        max_length=2000,
        help_text="Short biography (for public profile)"
    )
    
    # =========================================
    # Organizer Profile (organizers only)
    # =========================================
    organizer_display_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Display name as organizer (defaults to full_name)"
    )
    organizer_logo_url = models.URLField(
        blank=True,
        help_text="Logo URL for branding on events and certificates"
    )
    organizer_website = models.URLField(
        blank=True,
        help_text="Organizer's website URL"
    )
    organizer_bio = models.TextField(
        blank=True,
        max_length=2000,
        help_text="Organizer description (shown on public profile)"
    )
    organizer_social_linkedin = models.URLField(
        blank=True,
        help_text="LinkedIn profile URL"
    )
    organizer_social_twitter = models.URLField(
        blank=True,
        help_text="Twitter/X profile URL"
    )
    is_organizer_profile_public = models.BooleanField(
        default=True,
        help_text="Show organizer profile publicly"
    )
    
    # =========================================
    # Preferences
    # =========================================
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="User's preferred timezone (IANA format)"
    )
    
    # Notification preferences (all users)
    notify_event_reminders = models.BooleanField(
        default=True,
        help_text="Receive event reminder emails"
    )
    notify_certificate_issued = models.BooleanField(
        default=True,
        help_text="Receive email when certificate is issued"
    )
    notify_marketing = models.BooleanField(
        default=False,
        help_text="Receive marketing and product updates"
    )
    
    # Notification preferences (organizers only)
    notify_new_registration = models.BooleanField(
        default=True,
        help_text="Receive email on new event registration"
    )
    notify_event_summary = models.BooleanField(
        default=True,
        help_text="Receive post-event summary email"
    )
    
    # =========================================
    # Admin & System
    # =========================================
    is_staff = models.BooleanField(
        default=False,
        help_text="Can access admin site"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Account is active (False = disabled)"
    )
    
    # Onboarding
    onboarding_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user completed onboarding"
    )
    
    # Tracking
    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful login"
    )
    last_active_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last activity timestamp"
    )
    
    # =========================================
    # Phase 2: Organization (nullable FK, add later)
    # =========================================
    # organization = models.ForeignKey(
    #     'organizations.Organization',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='members'
    # )
    # organization_role = models.CharField(max_length=20, blank=True)
    
    # =========================================
    # Manager & Auth Config
    # =========================================
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['uuid']),
            models.Index(fields=['account_type']),
            models.Index(fields=['account_type', 'is_active']),
        ]
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email
    
    # =========================================
    # Properties
    # =========================================
    @property
    def is_organizer(self):
        return self.account_type == self.AccountType.ORGANIZER
    
    @property
    def is_attendee(self):
        return self.account_type == self.AccountType.ATTENDEE
    
    @property
    def display_name(self):
        """Full name with credentials if available."""
        if self.credentials:
            return f"{self.full_name}, {self.credentials}"
        return self.full_name
    
    @property
    def initials(self):
        """Return initials for avatar placeholder."""
        parts = self.full_name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.full_name[:2].upper() if self.full_name else "?"
    
    @property
    def has_completed_onboarding(self):
        return self.onboarding_completed_at is not None
    
    @property
    def has_zoom_connected(self):
        return hasattr(self, 'zoom_connection') and self.zoom_connection.is_active
    
    # =========================================
    # Methods
    # =========================================
    def upgrade_to_organizer(self):
        """Upgrade attendee account to organizer."""
        if self.account_type != self.AccountType.ORGANIZER:
            self.account_type = self.AccountType.ORGANIZER
            self.upgraded_to_organizer_at = timezone.now()
            self.save(update_fields=[
                'account_type', 
                'upgraded_to_organizer_at', 
                'updated_at'
            ])
    
    def downgrade_to_attendee(self):
        """
        Downgrade organizer to attendee.
        
        Note: Events created by user remain owned by them but they
        lose access to organizer features.
        """
        if self.account_type == self.AccountType.ORGANIZER:
            self.account_type = self.AccountType.ATTENDEE
            self.save(update_fields=['account_type', 'updated_at'])
    
    def complete_onboarding(self):
        """Mark onboarding as completed."""
        if self.onboarding_completed_at is None:
            self.onboarding_completed_at = timezone.now()
            self.save(update_fields=['onboarding_completed_at', 'updated_at'])
    
    def generate_email_verification_token(self):
        """Generate new email verification token."""
        from common.utils import generate_verification_code
        
        self.email_verification_token = generate_verification_code(64)
        self.email_verification_token_expires_at = timezone.now() + timezone.timedelta(hours=24)
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=[
            'email_verification_token',
            'email_verification_token_expires_at',
            'email_verification_sent_at',
            'updated_at'
        ])
        return self.email_verification_token
    
    def verify_email(self, token):
        """
        Verify email with token.
        
        Returns:
            bool: True if verification successful
        """
        if not self.email_verification_token:
            return False
        
        if self.email_verification_token != token:
            return False
        
        if timezone.now() > self.email_verification_token_expires_at:
            return False
        
        self.email_verified = True
        self.email_verification_token = ''
        self.email_verification_token_expires_at = None
        self.save(update_fields=[
            'email_verified',
            'email_verification_token',
            'email_verification_token_expires_at',
            'updated_at'
        ])
        return True
    
    def generate_password_reset_token(self):
        """Generate new password reset token."""
        from common.utils import generate_verification_code
        
        self.password_reset_token = generate_verification_code(64)
        self.password_reset_token_expires_at = timezone.now() + timezone.timedelta(hours=1)
        self.password_reset_sent_at = timezone.now()
        self.save(update_fields=[
            'password_reset_token',
            'password_reset_token_expires_at',
            'password_reset_sent_at',
            'updated_at'
        ])
        return self.password_reset_token
    
    def reset_password(self, token, new_password):
        """
        Reset password with token.
        
        Returns:
            bool: True if reset successful
        """
        if not self.password_reset_token:
            return False
        
        if self.password_reset_token != token:
            return False
        
        if timezone.now() > self.password_reset_token_expires_at:
            return False
        
        self.set_password(new_password)
        self.password_reset_token = ''
        self.password_reset_token_expires_at = None
        self.save(update_fields=[
            'password',
            'password_reset_token',
            'password_reset_token_expires_at',
            'updated_at'
        ])
        return True
    
    def anonymize(self):
        """
        Anonymize user data for GDPR deletion requests.
        
        Preserves: certificates, attendance records (anonymized)
        Deletes: sessions, personal data
        """
        self.email = f"deleted-{self.uuid}@anonymized.local"
        self.full_name = "Deleted User"
        self.professional_title = ''
        self.credentials = ''
        self.organization_name = ''
        self.bio = ''
        self.profile_photo_url = ''
        self.email_verified = False
        self.email_verification_token = ''
        self.password_reset_token = ''
        self.soft_delete()
        
        # Delete sessions
        self.sessions.all().delete()
    
    def clean(self):
        """Model validation."""
        super().clean()
        from django.core.exceptions import ValidationError
        from common.validators import validate_timezone
        
        errors = {}
        
        try:
            validate_timezone(self.timezone)
        except ValidationError as e:
            errors['timezone'] = str(e)
        
        if errors:
            raise ValidationError(errors)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('accounts:profile', kwargs={'uuid': self.uuid})
```

---

### UserManager

Custom manager for the User model.

```python
# accounts/managers.py

from django.contrib.auth.models import BaseUserManager
from common.models import SoftDeleteManager


class UserManager(BaseUserManager, SoftDeleteManager):
    """
    Custom user manager with email normalization and soft delete support.
    """
    
    def normalize_email(self, email):
        """Normalize email to lowercase."""
        email = super().normalize_email(email)
        return email.lower().strip() if email else email
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('Email is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('account_type', 'organizer')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)
    
    def get_by_natural_key(self, email):
        """Allow lookup by email (case-insensitive)."""
        return self.get(email__iexact=email)
```

---

### ZoomConnection

Stores Zoom OAuth credentials for organizers.

```python
class ZoomConnection(BaseModel):
    """
    Zoom OAuth connection for an organizer.
    
    One-to-one relationship with User.
    Tokens are encrypted at rest.
    
    Lifecycle:
    1. User initiates Zoom OAuth flow
    2. On callback, create/update ZoomConnection
    3. Tokens are refreshed automatically when expired
    4. User can disconnect (deletes this record)
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='zoom_connection'
    )
    
    # OAuth tokens (encrypted)
    access_token = EncryptedTextField(
        help_text="Zoom OAuth access token (encrypted)"
    )
    refresh_token = EncryptedTextField(
        help_text="Zoom OAuth refresh token (encrypted)"
    )
    token_expires_at = models.DateTimeField(
        help_text="When access token expires"
    )
    
    # Token scopes
    scopes = models.JSONField(
        default=list,
        help_text="List of OAuth scopes granted"
    )
    
    # Zoom account info
    zoom_user_id = models.CharField(
        max_length=100,
        help_text="Zoom user ID"
    )
    zoom_email = LowercaseEmailField(
        help_text="Email associated with Zoom account"
    )
    zoom_account_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Zoom account ID (for account-level apps)"
    )
    
    # Connection status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether connection is active"
    )
    
    # Error tracking
    last_refresh_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When tokens were last refreshed"
    )
    last_error = models.TextField(
        blank=True,
        help_text="Last error message (for debugging)"
    )
    last_error_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When last error occurred"
    )
    consecutive_errors = models.PositiveIntegerField(
        default=0,
        help_text="Count of consecutive errors"
    )
    
    class Meta:
        db_table = 'zoom_connections'
        verbose_name = 'Zoom Connection'
        verbose_name_plural = 'Zoom Connections'
    
    def __str__(self):
        return f"Zoom: {self.zoom_email} ({self.user.email})"
    
    @property
    def is_token_expired(self):
        """Check if access token has expired."""
        return timezone.now() >= self.token_expires_at
    
    @property
    def needs_refresh(self):
        """Check if token should be refreshed (within 5 min of expiry)."""
        buffer = timezone.timedelta(minutes=5)
        return timezone.now() >= (self.token_expires_at - buffer)
    
    @property
    def is_healthy(self):
        """Check if connection is healthy (active and not erroring)."""
        return self.is_active and self.consecutive_errors < 3
    
    def update_tokens(self, access_token, refresh_token, expires_in):
        """
        Update OAuth tokens after refresh.
        
        Args:
            access_token: New access token
            refresh_token: New refresh token
            expires_in: Token lifetime in seconds
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        self.last_refresh_at = timezone.now()
        self.consecutive_errors = 0
        self.last_error = ''
        self.save(update_fields=[
            'access_token',
            'refresh_token',
            'token_expires_at',
            'last_refresh_at',
            'consecutive_errors',
            'last_error',
            'updated_at'
        ])
    
    def record_error(self, error_message):
        """Record an error during token refresh or API call."""
        self.last_error = error_message[:1000]  # Truncate
        self.last_error_at = timezone.now()
        self.consecutive_errors += 1
        
        # Deactivate after too many errors
        if self.consecutive_errors >= 5:
            self.is_active = False
        
        self.save(update_fields=[
            'last_error',
            'last_error_at',
            'consecutive_errors',
            'is_active',
            'updated_at'
        ])
    
    def deactivate(self, reason=''):
        """Deactivate the connection."""
        self.is_active = False
        self.last_error = reason
        self.last_error_at = timezone.now()
        self.save(update_fields=[
            'is_active',
            'last_error',
            'last_error_at',
            'updated_at'
        ])
```

---

### UserSession

Tracks active login sessions for the security settings page.

```python
class UserSession(BaseModel):
    """
    Tracks user login sessions.
    
    Used for:
    - "Active sessions" in security settings
    - "Log out everywhere" functionality
    - Session analytics
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    # Session info
    session_key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Django session key"
    )
    
    # Device info
    user_agent = models.TextField(
        blank=True,
        help_text="Browser/device user agent"
    )
    device_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="Parsed device type (desktop, mobile, tablet)"
    )
    browser = models.CharField(
        max_length=50,
        blank=True,
        help_text="Parsed browser name"
    )
    os = models.CharField(
        max_length=50,
        blank=True,
        help_text="Parsed operating system"
    )
    
    # Location info
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address at login"
    )
    location_city = models.CharField(
        max_length=100,
        blank=True,
        help_text="GeoIP city"
    )
    location_country = models.CharField(
        max_length=100,
        blank=True,
        help_text="GeoIP country"
    )
    
    # Timing
    last_activity_at = models.DateTimeField(
        auto_now=True,
        help_text="Last activity in this session"
    )
    expires_at = models.DateTimeField(
        help_text="When session expires"
    )
    
    # Status
    is_current = models.BooleanField(
        default=False,
        help_text="Is this the current request's session"
    )
    
    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_activity_at']
        indexes = [
            models.Index(fields=['user', '-last_activity_at']),
            models.Index(fields=['session_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.device_type or 'Unknown'}"
    
    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
    
    @property
    def display_device(self):
        """Human-readable device description."""
        parts = []
        if self.browser:
            parts.append(self.browser)
        if self.os:
            parts.append(f"on {self.os}")
        return ' '.join(parts) if parts else 'Unknown device'
    
    @property
    def display_location(self):
        """Human-readable location."""
        parts = []
        if self.location_city:
            parts.append(self.location_city)
        if self.location_country:
            parts.append(self.location_country)
        return ', '.join(parts) if parts else 'Unknown location'
    
    def terminate(self):
        """Terminate this session."""
        from django.contrib.sessions.models import Session
        try:
            Session.objects.filter(session_key=self.session_key).delete()
        except Session.DoesNotExist:
            pass
        self.delete()
    
    @classmethod
    def terminate_all_for_user(cls, user, except_session_key=None):
        """
        Terminate all sessions for a user.
        
        Args:
            user: User whose sessions to terminate
            except_session_key: Optionally keep this session
        """
        sessions = cls.objects.filter(user=user)
        if except_session_key:
            sessions = sessions.exclude(session_key=except_session_key)
        
        # Delete Django sessions
        from django.contrib.sessions.models import Session
        session_keys = list(sessions.values_list('session_key', flat=True))
        Session.objects.filter(session_key__in=session_keys).delete()
        
        # Delete our records
        sessions.delete()
    
    @classmethod
    def cleanup_expired(cls):
        """Delete expired session records."""
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
```

---

### CPDRequirement

Tracks user's CPD/CE annual requirements for progress tracking.

```python
class CPDRequirement(BaseModel):
    """
    A user's CPD/CE credit requirement for a specific credit type.
    
    Users can set up multiple requirements for different credit types
    (e.g., 50 CME credits/year, 20 CLE credits/year).
    
    Used for:
    - Progress tracking on CPD dashboard
    - Progress bars showing completion toward annual goals
    - Reminders when falling behind
    """
    
    class PeriodType(models.TextChoices):
        CALENDAR_YEAR = 'calendar_year', 'Calendar Year (Jan-Dec)'
        FISCAL_YEAR = 'fiscal_year', 'Fiscal Year (Custom Start)'
        ROLLING_12 = 'rolling_12', 'Rolling 12 Months'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cpd_requirements'
    )
    
    # =========================================
    # Credit Type
    # =========================================
    cpd_type = models.CharField(
        max_length=50,
        help_text="Credit type code (e.g., CME, CLE, CPE)"
    )
    cpd_type_display = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name (e.g., 'Continuing Medical Education')"
    )
    
    # =========================================
    # Requirement
    # =========================================
    annual_requirement = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Required credits per period"
    )
    
    # =========================================
    # Period Configuration
    # =========================================
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        default=PeriodType.CALENDAR_YEAR
    )
    fiscal_year_start_month = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Month when fiscal year starts (1-12)"
    )
    fiscal_year_start_day = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Day when fiscal year starts (1-31)"
    )
    
    # =========================================
    # Optional Metadata
    # =========================================
    licensing_body = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of licensing/accreditation body"
    )
    license_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's license number (for reference)"
    )
    notes = models.TextField(
        blank=True,
        max_length=500,
        help_text="User notes about this requirement"
    )
    
    # =========================================
    # Status
    # =========================================
    is_active = models.BooleanField(
        default=True,
        help_text="Whether to track this requirement"
    )
    
    class Meta:
        db_table = 'cpd_requirements'
        unique_together = [['user', 'cpd_type']]
        ordering = ['cpd_type']
    
    def __str__(self):
        return f"{self.user.email} - {self.cpd_type}: {self.annual_requirement}"
    
    def get_current_period_bounds(self):
        """
        Get start and end dates for the current tracking period.
        
        Returns:
            tuple: (start_date, end_date)
        """
        from datetime import date
        today = date.today()
        
        if self.period_type == self.PeriodType.CALENDAR_YEAR:
            return (
                date(today.year, 1, 1),
                date(today.year, 12, 31)
            )
        
        elif self.period_type == self.PeriodType.FISCAL_YEAR:
            # Determine current fiscal year
            fiscal_start_this_year = date(
                today.year, 
                self.fiscal_year_start_month, 
                min(self.fiscal_year_start_day, 28)  # Safe day
            )
            
            if today >= fiscal_start_this_year:
                start = fiscal_start_this_year
                end = date(today.year + 1, self.fiscal_year_start_month, 
                          self.fiscal_year_start_day) - timezone.timedelta(days=1)
            else:
                start = date(today.year - 1, self.fiscal_year_start_month,
                            self.fiscal_year_start_day)
                end = fiscal_start_this_year - timezone.timedelta(days=1)
            
            return (start, end)
        
        else:  # Rolling 12 months
            end = today
            start = date(today.year - 1, today.month, today.day)
            return (start, end)
    
    def get_earned_credits(self):
        """
        Calculate credits earned in the current period.
        
        Returns:
            Decimal: Total credits earned
        """
        start_date, end_date = self.get_current_period_bounds()
        
        from certificates.models import Certificate
        from django.db.models import Sum
        
        total = Certificate.objects.filter(
            registration__user=self.user,
            status=Certificate.Status.ISSUED,
            cpd_type=self.cpd_type,
            event_date__gte=start_date,
            event_date__lte=end_date
        ).aggregate(total=Sum('cpd_credits'))['total']
        
        return total or 0
    
    @property
    def completion_percent(self):
        """Percentage toward annual requirement."""
        if not self.annual_requirement:
            return 100
        earned = self.get_earned_credits()
        return min(100, int((earned / self.annual_requirement) * 100))
    
    @property
    def credits_remaining(self):
        """Credits still needed to meet requirement."""
        earned = self.get_earned_credits()
        remaining = self.annual_requirement - earned
        return max(0, remaining)
```

---

## Relationships

```
User
├── ZoomConnection (1:1, CASCADE)
├── UserSession (1:N, CASCADE)
├── CPDRequirement (1:N, CASCADE)
├── Event (1:N, PROTECT) — see events.md
├── CertificateTemplate (1:N, PROTECT) — see certificates.md
├── ContactList (1:N, CASCADE) — see contacts.md
├── Registration (1:N, SET_NULL) — see registrations.md
├── Certificate.issued_by (1:N, PROTECT) — see certificates.md
└── Subscription (1:1, CASCADE) — see billing.md
```

---

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| users | email (unique) | Login lookup |
| users | uuid (unique) | API/URL lookup |
| users | account_type | Filter by type |
| users | account_type, is_active | Active organizers query |
| zoom_connections | user_id (unique) | One per user |
| user_sessions | session_key | Session lookup |
| user_sessions | user_id, -last_activity_at | User's sessions list |
| user_sessions | expires_at | Cleanup job |
| cpd_requirements | user_id, cpd_type (unique) | One requirement per type per user |
| cpd_requirements | user_id, is_active | User's active requirements |

---

## Business Rules

1. **Email uniqueness**: Case-insensitive, enforced at database level
2. **Email verification**: Required before certain actions (creating events)
3. **Organizer upgrade**: One-way upgrade, requires subscription
4. **Zoom connection**: One per user, can be disconnected and reconnected
5. **Session limits**: Max 10 active sessions per user (oldest terminated)
6. **Password reset**: Token valid for 1 hour, single use
7. **Email verification**: Token valid for 24 hours, can be resent (rate limited)

---

## Security Considerations

1. **Password storage**: Django's default PBKDF2 with SHA256
2. **Token storage**: Verification/reset tokens are random 64-char strings
3. **OAuth tokens**: Encrypted at rest using Fernet
4. **Session binding**: Sessions tied to user agent (optional additional check)
5. **Rate limiting**: Email verification and password reset are rate limited
6. **Anonymization**: Soft delete anonymizes PII, preserves audit trail
