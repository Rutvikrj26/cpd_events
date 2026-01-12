"""
Learning models for course modules and assignments.

Models:
- EventModule: Learning modules within an event
- ModuleContent: Content items within a module
- Assignment: Graded assignments
- AssignmentSubmission: Student submissions
- SubmissionReview: Review/grading records
- ContentProgress: Progress tracking for content
- ModuleProgress: Progress tracking for modules
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from common.config import AssignmentDefaults, ModuleDefaults
from common.models import BaseModel


class EventModule(BaseModel):
    """
    Learning module within an event.

    Modules can contain videos, documents, quizzes, and assignments.
    They can be released on schedule or based on prerequisites.
    """

    class ReleaseType(models.TextChoices):
        IMMEDIATE = 'immediate', 'Immediate'
        SCHEDULED = 'scheduled', 'Scheduled Date'
        DAYS_AFTER_REG = 'days_after_registration', 'Days After Registration'
        PREREQUISITE = 'prerequisite', 'After Prerequisite'

    # Relationships
    # Relationships
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='modules', null=True, blank=True)
    prerequisite_module = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependent_modules'
    )

    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    # Release settings
    release_type = models.CharField(max_length=30, choices=ReleaseType.choices, default=ReleaseType.IMMEDIATE)
    release_at = models.DateTimeField(null=True, blank=True)
    release_days_after_registration = models.PositiveIntegerField(default=0)

    # Scoring
    passing_score = models.PositiveIntegerField(
        default=ModuleDefaults.PASSING_SCORE, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # CPD credits for this module
    cpd_credits = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cpd_type = models.CharField(max_length=50, blank=True)

    # Status
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = 'event_modules'
        verbose_name = 'Event Module'
        verbose_name_plural = 'Event Modules'
        ordering = ['event', 'order']
        unique_together = [['event', 'order']]
        indexes = [
            models.Index(fields=['event', 'order']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return f"{self.event.title} - {self.title}"

    def is_available_for(self, user, registration=None, course_enrollment=None):
        """
        Check if module is available for a user context.
        Must provide either registration OR course_enrollment.
        """
        now = timezone.now()

        if not self.is_published:
            return False

        if self.release_type == self.ReleaseType.IMMEDIATE:
            return True

        if self.release_type == self.ReleaseType.SCHEDULED:
            return self.release_at and now >= self.release_at

        # Context-aware availability checks
        created_at = None
        if registration:
            created_at = registration.created_at
        elif course_enrollment:
            created_at = course_enrollment.enrolled_at

        if self.release_type == self.ReleaseType.DAYS_AFTER_REG:
            if not created_at:
                return False
            release_date = created_at + timezone.timedelta(days=self.release_days_after_registration)
            return now >= release_date

        if self.release_type == self.ReleaseType.PREREQUISITE:
            if not self.prerequisite_module:
                return True
            # Check if prerequisite is completed
            try:
                # Polymorphic lookup
                if registration:
                    prereq_progress = ModuleProgress.objects.get(registration=registration, module=self.prerequisite_module)
                elif course_enrollment:
                    prereq_progress = ModuleProgress.objects.get(
                        course_enrollment=course_enrollment, module=self.prerequisite_module
                    )
                else:
                    return False

                return prereq_progress.status == 'completed'
            except ModuleProgress.DoesNotExist:
                return False

        return False

    def is_available_for_registration(self, registration):
        """Legacy helper for events."""
        return self.is_available_for(registration.user, registration=registration)


class ModuleContent(BaseModel):
    """
    Content item within a module.

    Types: video, document, text, quiz, external link.
    """

    class ContentType(models.TextChoices):
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'
        TEXT = 'text', 'Text/HTML'
        QUIZ = 'quiz', 'Quiz'
        EXTERNAL = 'external', 'External Link'
        LESSON = 'lesson', 'Mixed Lesson'

    # Relationships
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name='contents')

    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    order = models.PositiveIntegerField(default=0)

    # Duration in minutes (for tracking)
    duration_minutes = models.PositiveIntegerField(default=0)

    # Content data (JSON) - structure depends on content_type
    # video: {url, provider, video_id, thumbnail}
    # document: {url, filename, file_type, size}
    # text: {html_content}
    # quiz: {questions: [...], passing_score}
    # external: {url, open_in_new_tab}
    content_data = models.JSONField(default=dict)
    file = models.FileField(
        upload_to='learning/modules/', blank=True, null=True, help_text="Uploaded file (for document/video)"
    )

    # Requirements
    is_required = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = 'module_contents'
        verbose_name = 'Module Content'
        verbose_name_plural = 'Module Contents'
        ordering = ['module', 'order']
        unique_together = [['module', 'order']]

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class Assignment(BaseModel):
    """
    Graded assignment within a module.

    Assignments can have rubrics and support multiple submission types.
    """

    class SubmissionType(models.TextChoices):
        TEXT = 'text', 'Text Response'
        FILE = 'file', 'File Upload'
        URL = 'url', 'URL/Link'
        MIXED = 'mixed', 'Mixed (Text + File)'

    # Relationships
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name='assignments')

    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField()

    # Due date (relative to module release)
    due_days_after_release = models.PositiveIntegerField(default=AssignmentDefaults.DUE_DAYS_AFTER_RELEASE)

    # Scoring
    max_score = models.PositiveIntegerField(default=AssignmentDefaults.MAX_SCORE)
    passing_score = models.PositiveIntegerField(default=AssignmentDefaults.PASSING_SCORE)

    # Submission settings
    allow_resubmission = models.BooleanField(default=True)
    max_attempts = models.PositiveIntegerField(default=AssignmentDefaults.MAX_ATTEMPTS)
    submission_type = models.CharField(max_length=20, choices=SubmissionType.choices, default=SubmissionType.TEXT)

    # Rubric (JSON)
    # {criteria: [{name, description, max_points, levels: [{points, description}]}]}
    rubric = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'assignments'
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'
        ordering = ['module', 'created_at']

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    @property
    def passing_percentage(self):
        """Calculate passing percentage."""
        if self.max_score == 0:
            return 0
        return (self.passing_score / self.max_score) * 100


class AssignmentSubmission(BaseModel):
    """
    Student submission for an assignment.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        IN_REVIEW = 'in_review', 'In Review'
        NEEDS_REVISION = 'needs_revision', 'Needs Revision'
        GRADED = 'graded', 'Graded'
        APPROVED = 'approved', 'Approved'

    # Relationships
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    registration = models.ForeignKey(
        'registrations.Registration', on_delete=models.CASCADE, related_name='assignment_submissions', null=True, blank=True
    )
    course_enrollment = models.ForeignKey(
        'learning.CourseEnrollment', on_delete=models.CASCADE, related_name='assignment_submissions', null=True, blank=True
    )
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_submissions'
    )

    # Submission details
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    attempt_number = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Content
    content = models.JSONField(default=dict)  # {text, notes, etc.}
    file_url = models.URLField(max_length=500, blank=True)

    # Grading
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'assignment_submissions'
        verbose_name = 'Assignment Submission'
        verbose_name_plural = 'Assignment Submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['assignment', 'registration']),
            models.Index(fields=['assignment', 'course_enrollment']),
            models.Index(fields=['status']),
        ]

    def clean(self):
        super().clean()
        if self.registration and self.course_enrollment:
            raise ValidationError("Submission cannot belong to both Registration and Course Enrollment.")
        if not self.registration and not self.course_enrollment:
            raise ValidationError("Submission must belong to either Registration or Course Enrollment.")

    def __str__(self):
        user = self.registration.user if self.registration else self.course_enrollment.user
        return f"{user.email} - {self.assignment.title}"

    def __str__(self):
        return f"{self.registration.user.email} - {self.assignment.title}"

    @property
    def is_passing(self):
        """Check if submission passed."""
        if self.score is None:
            return None
        return self.score >= self.assignment.passing_score

    def submit(self):
        """Submit the assignment."""
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.save()

    def grade(self, score, feedback='', graded_by=None):
        """Grade the submission."""
        self.score = score
        self.feedback = feedback
        self.graded_by = graded_by
        self.graded_at = timezone.now()
        self.status = self.Status.GRADED if self.is_passing else self.Status.NEEDS_REVISION
        self.save()


class SubmissionReview(BaseModel):
    """
    Review/action record for a submission.

    Tracks the history of actions taken on a submission.
    """

    class Action(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        REVIEWED = 'reviewed', 'Reviewed'
        GRADED = 'graded', 'Graded'
        RETURNED = 'returned', 'Returned for Revision'
        APPROVED = 'approved', 'Approved'
        RESUBMITTED = 'resubmitted', 'Resubmitted'

    # Relationships
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submission_reviews'
    )

    # Action details
    action = models.CharField(max_length=20, choices=Action.choices)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)

    # Grading
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    rubric_scores = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'submission_reviews'
        verbose_name = 'Submission Review'
        verbose_name_plural = 'Submission Reviews'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.submission} - {self.action}"


class ContentProgress(BaseModel):
    """
    Progress tracking for module content.
    """

    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    # Relationships
    # Relationships
    registration = models.ForeignKey(
        'registrations.Registration', on_delete=models.CASCADE, related_name='content_progress', null=True, blank=True
    )
    course_enrollment = models.ForeignKey(
        'learning.CourseEnrollment', on_delete=models.CASCADE, related_name='content_progress', null=True, blank=True
    )
    content = models.ForeignKey(ModuleContent, on_delete=models.CASCADE, related_name='progress_records')

    # Progress
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    time_spent_seconds = models.PositiveIntegerField(default=0)

    # Position tracking (for videos, documents)
    last_position = models.JSONField(default=dict)  # {time, page, etc.}

    class Meta:
        db_table = 'content_progress'
        verbose_name = 'Content Progress'
        verbose_name_plural = 'Content Progress'
        constraints = [
            models.UniqueConstraint(
                fields=['registration', 'content'],
                name='unique_registration_content',
                condition=models.Q(registration__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['course_enrollment', 'content'],
                name='unique_enrollment_content',
                condition=models.Q(course_enrollment__isnull=False),
            ),
        ]

    def clean(self):
        super().clean()
        if self.registration and self.course_enrollment:
            raise ValidationError("Progress cannot belong to both Registration and Course Enrollment.")
        if not self.registration and not self.course_enrollment:
            raise ValidationError("Progress must belong to either Registration or Course Enrollment.")

    def __str__(self):
        user = self.registration.user if self.registration else self.course_enrollment.user
        return f"{user.email} - {self.content.title}"

    def start(self):
        """Mark content as started."""
        if self.status == self.Status.NOT_STARTED:
            self.status = self.Status.IN_PROGRESS
            self.started_at = timezone.now()
            self.save()

    def complete(self):
        """Mark content as completed."""
        self.status = self.Status.COMPLETED
        self.progress_percent = 100
        self.completed_at = timezone.now()
        self.save()

    def update_progress(self, percent, time_spent=0, position=None):
        """Update progress."""
        self.progress_percent = min(percent, 100)
        self.time_spent_seconds += time_spent
        if position:
            self.last_position = position

        if percent >= 100:
            self.complete()
        else:
            self.save()


class ModuleProgress(BaseModel):
    """
    Progress tracking for entire module.
    """

    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'

    # Relationships
    # Relationships
    registration = models.ForeignKey(
        'registrations.Registration', on_delete=models.CASCADE, related_name='module_progress', null=True, blank=True
    )
    course_enrollment = models.ForeignKey(
        'learning.CourseEnrollment', on_delete=models.CASCADE, related_name='module_progress', null=True, blank=True
    )
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name='progress_records')

    # Progress
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Content tracking
    contents_completed = models.PositiveIntegerField(default=0)
    contents_total = models.PositiveIntegerField(default=0)

    # Score (from assignments/quizzes)
    score = models.PositiveIntegerField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'module_progress'
        verbose_name = 'Module Progress'
        verbose_name_plural = 'Module Progress'
        constraints = [
            models.UniqueConstraint(
                fields=['registration', 'module'],
                name='unique_registration_module',
                condition=models.Q(registration__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['course_enrollment', 'module'],
                name='unique_enrollment_module',
                condition=models.Q(course_enrollment__isnull=False),
            ),
        ]

    def clean(self):
        super().clean()
        if self.registration and self.course_enrollment:
            raise ValidationError("Progress cannot belong to both Registration and Course Enrollment.")
        if not self.registration and not self.course_enrollment:
            raise ValidationError("Progress must belong to either Registration or Course Enrollment.")

    def __str__(self):
        user = self.registration.user if self.registration else self.course_enrollment.user
        return f"{user.email} - {self.module.title}"

    @property
    def progress_percent(self):
        """Calculate overall progress percent."""
        if self.contents_total == 0:
            return 0
        return int((self.contents_completed / self.contents_total) * 100)

    def update_from_content(self):
        """Update progress based on content progress."""
        required_contents = self.module.contents.filter(is_required=True)
        self.contents_total = required_contents.count()

        # Context-aware lookup
        query = models.Q(content__in=required_contents, status=ContentProgress.Status.COMPLETED)
        if self.registration:
            query &= models.Q(registration=self.registration)
        else:
            query &= models.Q(course_enrollment=self.course_enrollment)

        completed = ContentProgress.objects.filter(query).count()
        self.contents_completed = completed

        if self.contents_completed >= self.contents_total and self.contents_total > 0:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
        elif self.contents_completed > 0:
            self.status = self.Status.IN_PROGRESS
            if not self.started_at:
                self.started_at = timezone.now()

        self.save()


# =============================================================================
# Self-Paced Courses (Organization-owned)
# =============================================================================


class Course(BaseModel):
    """
    Self-paced learning course, owned by an organization.

    Courses are standalone learning experiences with modules, content,
    and assignments. Unlike events, courses don't have scheduled times -
    learners can complete them at their own pace.

    Key Features:
    - Organization ownership
    - Self-paced modules and content
    - Enrollment management
    - Progress tracking
    - Certificate issuance on completion
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    # =========================================
    # Ownership
    # =========================================
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True,
        help_text="Organization that owns this course (null for personal LMS plans)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_courses',
        help_text="User who created this course",
    )

    # =========================================
    # Basic Info
    # =========================================
    class CourseFormat(models.TextChoices):
        ONLINE = 'online', 'Online (Self-Paced)'
        HYBRID = 'hybrid', 'Hybrid (Includes Live Sessions)'

    title = models.CharField(max_length=255, help_text="Course title")
    format = models.CharField(
        max_length=20, choices=CourseFormat.choices, default=CourseFormat.ONLINE, help_text="Delivery format"
    )
    slug = models.SlugField(max_length=100, help_text="URL-friendly identifier")
    description = models.TextField(blank=True, max_length=5000, help_text="Course description")
    short_description = models.CharField(max_length=300, blank=True, help_text="Brief description for listings")
    featured_image = models.ImageField(upload_to='courses/images/', null=True, blank=True, help_text="Featured image")
    featured_image_url = models.URLField(blank=True, help_text="External featured image URL")

    # =========================================
    # Virtual/Live Session Settings (for Hybrid courses)
    # =========================================
    zoom_meeting_id = models.CharField(max_length=100, blank=True, help_text="Zoom Meeting ID")
    zoom_meeting_url = models.URLField(blank=True, help_text="Zoom Join URL")
    zoom_meeting_password = models.CharField(max_length=50, blank=True, help_text="Zoom Meeting Password")
    zoom_webinar_id = models.CharField(max_length=100, blank=True, help_text="Zoom Webinar ID (if webinar)")
    zoom_registrant_id = models.CharField(max_length=255, blank=True, help_text="Zoom Registrant tracking")

    # Live session scheduling (for Hybrid format)
    live_session_start = models.DateTimeField(null=True, blank=True, help_text="Start time for live session")
    live_session_end = models.DateTimeField(null=True, blank=True, help_text="End time for live session")
    live_session_timezone = models.CharField(max_length=64, default='UTC', help_text="Timezone for live sessions")

    # =========================================
    # CPD Settings
    # =========================================
    cpd_credits = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Total CPD credits for course")
    cpd_type = models.CharField(max_length=50, blank=True, help_text="Type of CPD credits")

    # =========================================
    # Status & Visibility
    # =========================================
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_public = models.BooleanField(default=True, help_text="Visible in public listings")

    # =========================================
    # Pricing
    # =========================================
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True)

    # =========================================
    # Pricing & Payments
    # =========================================
    price_cents = models.PositiveIntegerField(default=0, help_text="Price in cents (0 for free)")
    currency = models.CharField(max_length=3, default='USD', help_text="Currency code (ISO 4217)")
    stripe_product_id = models.CharField(max_length=255, blank=True, help_text="Stripe Product ID")
    stripe_price_id = models.CharField(max_length=255, blank=True, help_text="Stripe Price ID")

    # =========================================
    # Enrollment Settings
    # =========================================
    enrollment_open = models.BooleanField(default=True, help_text="Accept new enrollments")
    max_enrollments = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum enrollments (null = unlimited)")
    enrollment_requires_approval = models.BooleanField(default=False, help_text="Require approval for enrollment")

    # =========================================
    # Duration & Completion
    # =========================================
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0, help_text="Estimated hours to complete")
    passing_score = models.PositiveIntegerField(
        default=70, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Minimum score to pass (0-100)"
    )

    # =========================================
    # Certificate Settings
    # =========================================
    certificates_enabled = models.BooleanField(default=True, help_text="Issue certificates on completion")
    certificate_template = models.ForeignKey(
        'certificates.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        help_text="Template for certificates",
    )
    auto_issue_certificates = models.BooleanField(default=True, help_text="Auto-issue when course is completed")

    # =========================================
    # Stats (denormalized)
    # =========================================
    enrollment_count = models.PositiveIntegerField(default=0, help_text="Total enrollments")
    completion_count = models.PositiveIntegerField(default=0, help_text="Completed enrollments")
    module_count = models.PositiveIntegerField(default=0, help_text="Number of modules")

    class Meta:
        db_table = 'courses'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'slug'],
                condition=models.Q(organization__isnull=False),
                name='unique_course_slug_per_organization',
            ),
            models.UniqueConstraint(
                fields=['created_by', 'slug'],
                condition=models.Q(organization__isnull=True),
                name='unique_course_slug_per_owner',
            ),
        ]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['is_public', 'status']),
        ]
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'

    def __str__(self):
        return self.title

    def can_manage(self, user) -> bool:
        """Check if user can manage this course."""
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if user.is_staff:
            return True
        if self.organization_id:
            return self.organization.memberships.filter(
                user=user,
                role__in=['admin', 'course_manager'],
                is_active=True,
            ).exists()
        return self.created_by_id == user.id

    def can_instruct(self, user) -> bool:
        """Check if user is an instructor assigned to this course."""
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if not self.organization_id:
            return False
        return self.organization.memberships.filter(
            user=user,
            role='instructor',
            assigned_course=self,
            is_active=True,
        ).exists()

    @property
    def is_free(self):
        return self.price_cents == 0

    @property
    def effective_image_url(self):
        """Get image URL, preferring uploaded file."""
        if self.featured_image:
            return self.featured_image.url
        return self.featured_image_url or ''

    @property
    def is_published(self):
        """Check if course is published."""
        return self.status == self.Status.PUBLISHED

    @property
    def is_full(self):
        """Check if enrollment is at capacity."""
        if self.max_enrollments is None:
            return False
        return self.enrollment_count >= self.max_enrollments

    @property
    def spots_remaining(self):
        """Number of spots remaining."""
        if self.max_enrollments is None:
            return None
        return max(0, self.max_enrollments - self.enrollment_count)

    def publish(self):
        """Publish the course."""
        self.status = self.Status.PUBLISHED
        self.save(update_fields=['status', 'updated_at'])

    def archive(self):
        """Archive the course."""
        self.status = self.Status.ARCHIVED
        self.save(update_fields=['status', 'updated_at'])

    def update_counts(self):
        """Update denormalized counts."""
        self.enrollment_count = self.enrollments.filter(
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED]
        ).count()
        self.completion_count = self.enrollments.filter(status=CourseEnrollment.Status.COMPLETED).count()
        self.module_count = self.modules.count()
        self.save(update_fields=['enrollment_count', 'completion_count', 'module_count', 'updated_at'])


class CourseAnnouncement(BaseModel):
    """
    Announcements for a course.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='course_announcements',
    )

    class Meta:
        db_table = 'course_announcements'
        ordering = ['-created_at']
        verbose_name = 'Course Announcement'
        verbose_name_plural = 'Course Announcements'

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class CourseModule(BaseModel):
    """
    Links modules to courses (through table for Course-EventModule relationship).

    This allows EventModule to be reused for both event-based and course-based learning.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name='course_links')
    order = models.PositiveIntegerField(default=0, help_text="Display order in course")
    is_required = models.BooleanField(default=True, help_text="Required for course completion")

    class Meta:
        db_table = 'course_modules'
        ordering = ['order']
        unique_together = ['course', 'module']
        verbose_name = 'Course Module'
        verbose_name_plural = 'Course Modules'

    def __str__(self):
        return f"{self.course.title} - {self.module.title}"


class CourseEnrollment(BaseModel):
    """
    User enrollment in a self-paced course.

    Tracks enrollment status and progress through the course.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Approval'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        DROPPED = 'dropped', 'Dropped'
        EXPIRED = 'expired', 'Expired'

    # Relationships
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_enrollments')

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    # Timestamps
    enrolled_at = models.DateTimeField(auto_now_add=True, help_text="When user enrolled")
    started_at = models.DateTimeField(null=True, blank=True, help_text="When user started learning")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When user completed course")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When enrollment expires")

    # Progress
    progress_percent = models.PositiveIntegerField(
        default=0, validators=[MaxValueValidator(100)], help_text="Overall progress percentage"
    )
    modules_completed = models.PositiveIntegerField(default=0, help_text="Modules completed")
    time_spent_minutes = models.PositiveIntegerField(default=0, help_text="Total time spent")

    # Score
    current_score = models.PositiveIntegerField(null=True, blank=True, help_text="Current aggregate score")

    # Certificate
    certificate_issued = models.BooleanField(default=False, help_text="Certificate issued")
    certificate_issued_at = models.DateTimeField(null=True, blank=True)

    # Manual completion override
    manually_completed = models.BooleanField(default=False, help_text="Manually marked complete by instructor/manager")
    manually_completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_course_completions',
        help_text="User who manually marked this enrollment complete",
    )

    class Meta:
        db_table = 'course_enrollments'
        ordering = ['-enrolled_at']
        unique_together = ['course', 'user']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['course', 'status']),
            models.Index(fields=['user', 'status']),
        ]
        verbose_name = 'Course Enrollment'
        verbose_name_plural = 'Course Enrollments'

    def __str__(self):
        return f"{self.user.email} - {self.course.title}"

    @property
    def is_active(self):
        """Check if enrollment is active."""
        return self.status == self.Status.ACTIVE

    @property
    def is_completed(self):
        """Check if enrollment is completed."""
        return self.status == self.Status.COMPLETED

    @property
    def is_passing(self):
        """Check if current score is passing."""
        if self.current_score is None:
            return None
        return self.current_score >= self.course.passing_score

    def start(self):
        """Mark enrollment as started."""
        if not self.started_at:
            self.started_at = timezone.now()
            self.save(update_fields=['started_at', 'updated_at'])

    def complete(self):
        """Mark enrollment as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.progress_percent = 100

        # Issue certificate if enabled
        if not self.certificate_issued:
            if self.course.certificates_enabled and self.course.auto_issue_certificates and self.course.certificate_template:
                from certificates.models import Certificate

                # Check for existing cert first (avoid duplicates)
                if not Certificate.objects.filter(course_enrollment=self).exists():
                    cert = Certificate.objects.create(
                        course_enrollment=self,
                        template=self.course.certificate_template,
                        status=Certificate.Status.ACTIVE,
                        issued_by=self.course.created_by or self.user,  # Fallback to user if creator deleted? Or system user?
                    )
                    cert.build_certificate_data()
                    cert.save()

                    self.certificate_issued = True
                    self.certificate_issued_at = timezone.now()

        self.save(
            update_fields=[
                'status',
                'completed_at',
                'progress_percent',
                'certificate_issued',
                'certificate_issued_at',
                'updated_at',
            ]
        )
        self.course.update_counts()

    def drop(self):
        """Drop the enrollment."""
        self.status = self.Status.DROPPED
        self.save(update_fields=['status', 'updated_at'])
        self.course.update_counts()

    def update_progress(self):
        """Update progress from module progress."""
        total_modules = self.course.modules.filter(is_required=True).count()
        if total_modules == 0:
            return

        # Count completed modules
        completed = 0
        for course_module in self.course.modules.filter(is_required=True):
            try:
                progress = ModuleProgress.objects.get(
                    course_enrollment=self,
                    module=course_module.module,
                )
                if progress.status == ModuleProgress.Status.COMPLETED:
                    completed += 1
            except ModuleProgress.DoesNotExist:
                pass

        self.modules_completed = completed
        self.progress_percent = int((completed / total_modules) * 100)

        # Check completion after updating progress
        self.check_completion()

    def check_completion(self):
        """
        Check if course should be marked complete.

        Business Rule: Course completion requires:
        - All required quizzes/assignments passed (score >= passing_score)
        - OR instructor/manager has manually marked complete

        If either condition is met and status is ACTIVE, mark as COMPLETED.
        """
        if self.status != self.Status.ACTIVE:
            return False

        # Check for manual completion override
        if getattr(self, 'manually_completed', False):
            self.complete()
            return True

        # Check if all quizzes/assignments are passed
        if self._are_all_requirements_passed():
            self.complete()
            return True

        # Not complete yet, just save progress
        self.save(update_fields=['modules_completed', 'progress_percent', 'updated_at'])
        return False

    def _are_all_requirements_passed(self) -> bool:
        """
        Check if all required quizzes/assignments are passed.

        Returns True if:
        - All required assignments have at least one submission with passing score
        - OR there are no required assignments (pure content course)
        """
        # Get all required modules for this course
        required_modules = self.course.modules.filter(is_required=True).values_list('module_id', flat=True)

        if not required_modules:
            # No required modules, check if 100% progress
            return self.progress_percent >= 100

        # Get all assignments from required modules
        required_assignments = Assignment.objects.filter(module_id__in=required_modules)

        if not required_assignments.exists():
            # No assignments, just check module progress
            return self.progress_percent >= 100

        # Check each required assignment has a passing submission
        for assignment in required_assignments:
            has_passing = (
                AssignmentSubmission.objects.filter(
                    assignment=assignment,
                    course_enrollment=self,
                    status__in=[
                        AssignmentSubmission.Status.GRADED,
                        AssignmentSubmission.Status.APPROVED,
                    ],
                )
                .filter(score__gte=assignment.passing_score)
                .exists()
            )

            if not has_passing:
                return False

        return True

    def mark_complete_manually(self, completed_by):
        """
        Manually mark course as complete (instructor/manager override).

        Args:
            completed_by: User who marked completion (instructor or course manager)
        """
        self.manually_completed = True
        self.manually_completed_by = completed_by
        self.save(update_fields=['manually_completed', 'manually_completed_by', 'updated_at'])
        self.complete()
