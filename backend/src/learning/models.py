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
from common.models import BaseModel, SoftDeleteModel


def validate_module_content_data(content_type: str, content_data):
    """
    Shape-check ``ModuleContent.content_data`` for a given content_type.

    Canonical shapes:
      text:     {"body": "<html>"}
      lesson:   {"video"?: {"url": str}, "text"?: {"body": "<html>"}}
      video:    {"url": str, "provider"?: str, "thumbnail"?: str}
      document: {}                  # binary lives on the `file` field
      quiz:     {"questions": [...], "passing_score": int}
      external: {"url": str, "open_in_new_tab"?: bool}
    """
    if content_data is None or content_data == {}:
        return
    if not isinstance(content_data, dict):
        raise ValidationError({'content_data': 'content_data must be a JSON object.'})

    def _text_block(value, field):
        if not isinstance(value, dict) or not isinstance(value.get('body'), str):
            raise ValidationError(
                {'content_data': f'{field} must be an object with a "body" string.'}
            )

    if content_type == 'text':
        if not isinstance(content_data.get('body'), str):
            raise ValidationError(
                {'content_data': 'text content requires {"body": "<html>"}.'}
            )
    elif content_type == 'lesson':
        if 'video' in content_data and content_data['video'] is not None:
            video = content_data['video']
            if not isinstance(video, dict) or not isinstance(video.get('url'), str):
                raise ValidationError(
                    {'content_data': 'lesson.video must be {"url": "..."}.'}
                )
        if 'text' in content_data and content_data['text'] is not None:
            _text_block(content_data['text'], 'lesson.text')
    elif content_type == 'video':
        if not isinstance(content_data.get('url'), str):
            raise ValidationError(
                {'content_data': 'video content requires {"url": "..."}.'}
            )
    elif content_type == 'quiz':
        if not isinstance(content_data.get('questions'), list):
            raise ValidationError(
                {'content_data': 'quiz content requires a "questions" list.'}
            )
    elif content_type == 'external':
        if not isinstance(content_data.get('url'), str):
            raise ValidationError(
                {'content_data': 'external content requires {"url": "..."}.'}
            )
    elif content_type == 'document':
        pass


class EventModule(BaseModel):
    """
    Learning module within an event.

    Modules can contain videos, documents, quizzes, and assignments.
    They can be released on schedule or based on prerequisites.
    """

    class ReleaseType(models.TextChoices):
        IMMEDIATE = "immediate", "Immediate"
        SCHEDULED = "scheduled", "Scheduled Date"
        DAYS_AFTER_REG = "days_after_registration", "Days After Registration"
        PREREQUISITE = "prerequisite", "After Prerequisite"

    # Relationships
    # Relationships
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="modules", null=True, blank=True)
    prerequisite_module = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="dependent_modules"
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
        db_table = "event_modules"
        verbose_name = "Event Module"
        verbose_name_plural = "Event Modules"
        ordering = ["event", "order"]
        unique_together = [["event", "order"]]
        indexes = [
            models.Index(fields=["event", "order"]),
            models.Index(fields=["is_published"]),
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

        # Course sequential gating: previous module (by order) must be completed
        if course_enrollment:
            course_modules = list(
                CourseModule.objects.filter(course=course_enrollment.course)
                .select_related('module')
                .order_by('order')
            )
            for i, cm in enumerate(course_modules):
                if cm.module_id == self.id and i > 0:
                    prev_module = course_modules[i - 1].module
                    try:
                        prev_progress = ModuleProgress.objects.get(
                            course_enrollment=course_enrollment, module=prev_module
                        )
                        if prev_progress.status != ModuleProgress.Status.COMPLETED:
                            return False
                    except ModuleProgress.DoesNotExist:
                        return False
                    break

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

                return prereq_progress.status == "completed"
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
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"
        TEXT = "text", "Text/HTML"
        QUIZ = "quiz", "Quiz"
        EXTERNAL = "external", "External Link"
        LESSON = "lesson", "Mixed Lesson"

    # Relationships
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name="contents")

    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=ContentType.choices)
    order = models.PositiveIntegerField(default=0)

    # Duration in minutes (for tracking)
    duration_minutes = models.PositiveIntegerField(default=0)

    # Content data (JSON) — shape depends on content_type (enforced by
    # validate_module_content_data below):
    #   text:     {"body": "<html>"}
    #   lesson:   {"video"?: {"url": "..."}, "text"?: {"body": "<html>"}}
    #   video:    {"url": "...", "provider"?: "...", "thumbnail"?: "..."}
    #   document: {} (the binary lives on the `file` field)
    #   quiz:     {"questions": [...], "passing_score": int}
    #   external: {"url": "...", "open_in_new_tab"?: bool}
    content_data = models.JSONField(default=dict, blank=True)
    file = models.FileField(
        upload_to="learning/modules/", blank=True, null=True, help_text="Uploaded file (for document/video)"
    )

    # Requirements
    is_required = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "module_contents"
        verbose_name = "Module Content"
        verbose_name_plural = "Module Contents"
        ordering = ["module", "order"]
        unique_together = [["module", "order"]]

    def clean(self):
        super().clean()
        validate_module_content_data(self.content_type, self.content_data)

    def save(self, *args, **kwargs):
        # Normalize legacy content_data shapes on write so we never persist
        # drift even if a caller bypasses the serializer validator.
        self.content_data = _normalize_module_content_data(
            self.content_type, self.content_data
        )
        validate_module_content_data(self.content_type, self.content_data)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.module.title} - {self.title}"


def _normalize_module_content_data(content_type: str, content_data):
    """Rewrite known legacy shapes into the canonical ones."""
    if not isinstance(content_data, dict):
        return content_data or {}
    data = dict(content_data)

    if content_type == 'text':
        # Accept legacy {"text": "html"} or {"text": {"body": "html"}} and
        # flatten to {"body": "html"}.
        if 'body' not in data:
            legacy = data.pop('text', None)
            if isinstance(legacy, str):
                data['body'] = legacy
            elif isinstance(legacy, dict) and isinstance(legacy.get('body'), str):
                data['body'] = legacy['body']
    elif content_type == 'lesson':
        # lesson.text may arrive as a plain string — wrap it.
        text_block = data.get('text')
        if isinstance(text_block, str):
            data['text'] = {'body': text_block}
        # lesson.video may arrive as a plain URL string — wrap it.
        video_block = data.get('video')
        if isinstance(video_block, str):
            data['video'] = {'url': video_block}
    return data


class Assignment(BaseModel):
    """
    Graded assignment within a module.

    Assignments can have rubrics and support multiple submission types.
    """

    class SubmissionType(models.TextChoices):
        TEXT = "text", "Text Response"
        FILE = "file", "File Upload"
        URL = "url", "URL/Link"
        MIXED = "mixed", "Mixed (Text + File)"

    # Relationships
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name="assignments")

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
        db_table = "assignments"
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"
        ordering = ["module", "created_at"]

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
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        IN_REVIEW = "in_review", "In Review"
        NEEDS_REVISION = "needs_revision", "Needs Revision"
        GRADED = "graded", "Graded"
        APPROVED = "approved", "Approved"

    # Relationships
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    registration = models.ForeignKey(
        "registrations.Registration", on_delete=models.CASCADE, related_name="assignment_submissions", null=True, blank=True
    )
    course_enrollment = models.ForeignKey(
        "learning.CourseEnrollment", on_delete=models.CASCADE, related_name="assignment_submissions", null=True, blank=True
    )
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="graded_submissions"
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
        db_table = "assignment_submissions"
        verbose_name = "Assignment Submission"
        verbose_name_plural = "Assignment Submissions"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["assignment", "registration"]),
            models.Index(fields=["assignment", "course_enrollment"]),
            models.Index(fields=["status"]),
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

    def grade(self, score, feedback="", graded_by=None):
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
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        GRADED = "graded", "Graded"
        RETURNED = "returned", "Returned for Revision"
        APPROVED = "approved", "Approved"
        RESUBMITTED = "resubmitted", "Resubmitted"

    # Relationships
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="submission_reviews"
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
        db_table = "submission_reviews"
        verbose_name = "Submission Review"
        verbose_name_plural = "Submission Reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.submission} - {self.action}"


class ContentProgress(BaseModel):
    """
    Progress tracking for module content.
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    # Relationships
    # Relationships
    registration = models.ForeignKey(
        "registrations.Registration", on_delete=models.CASCADE, related_name="content_progress", null=True, blank=True
    )
    course_enrollment = models.ForeignKey(
        "learning.CourseEnrollment", on_delete=models.CASCADE, related_name="content_progress", null=True, blank=True
    )
    content = models.ForeignKey(ModuleContent, on_delete=models.CASCADE, related_name="progress_records")

    # Progress
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    time_spent_seconds = models.PositiveIntegerField(default=0)

    # Position tracking (for videos, documents)
    last_position = models.JSONField(default=dict)  # {time, page, etc.}

    class Meta:
        db_table = "content_progress"
        verbose_name = "Content Progress"
        verbose_name_plural = "Content Progress"
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "content"],
                name="unique_registration_content",
                condition=models.Q(registration__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["course_enrollment", "content"],
                name="unique_enrollment_content",
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
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    # Relationships
    # Relationships
    registration = models.ForeignKey(
        "registrations.Registration", on_delete=models.CASCADE, related_name="module_progress", null=True, blank=True
    )
    course_enrollment = models.ForeignKey(
        "learning.CourseEnrollment", on_delete=models.CASCADE, related_name="module_progress", null=True, blank=True
    )
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name="progress_records")

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
        db_table = "module_progress"
        verbose_name = "Module Progress"
        verbose_name_plural = "Module Progress"
        constraints = [
            models.UniqueConstraint(
                fields=["registration", "module"],
                name="unique_registration_module",
                condition=models.Q(registration__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["course_enrollment", "module"],
                name="unique_enrollment_module",
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
    Self-paced learning course.

    Courses are standalone learning experiences with modules, content,
    and assignments. Unlike events, courses don't have scheduled times -
    learners can complete them at their own pace.

    Key Features:
    - Self-paced modules and content
    - Enrollment management
    - Progress tracking
    - Certificate issuance on completion
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    # =========================================
    # Ownership
    # =========================================
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_courses",
        help_text="User who created this course",
    )

    # =========================================
    # Basic Info
    # =========================================
    class CourseFormat(models.TextChoices):
        ONLINE = "online", "Online (Self-Paced)"
        LIVE = "live", "Live (Lectures)"
        HYBRID = "hybrid", "Hybrid (Modules + Live Sessions)"

    title = models.CharField(max_length=255, help_text="Course title")
    format = models.CharField(
        max_length=20, choices=CourseFormat.choices, default=CourseFormat.ONLINE, help_text="Delivery format"
    )
    slug = models.SlugField(max_length=100, help_text="URL-friendly identifier")
    description = models.TextField(blank=True, max_length=5000, help_text="Course description")
    short_description = models.CharField(max_length=300, blank=True, help_text="Brief description for listings")
    featured_image = models.ImageField(upload_to="courses/images/", null=True, blank=True, help_text="Featured image")
    featured_image_url = models.URLField(blank=True, help_text="External featured image URL")

    # =========================================
    # Virtual/Live Session Settings (for Hybrid courses)
    # =========================================
    video_settings = models.JSONField(default=dict, blank=True, help_text="Video conferencing settings")

    # Live session scheduling (for Hybrid format)
    live_session_start = models.DateTimeField(null=True, blank=True, help_text="Start time for live session")
    live_session_end = models.DateTimeField(null=True, blank=True, help_text="End time for live session")
    live_session_timezone = models.CharField(max_length=64, default="UTC", help_text="Timezone for live sessions")

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
    thumbnail = models.ImageField(upload_to="courses/thumbnails/", blank=True, null=True)

    # =========================================
    # Pricing & Payments
    # =========================================
    price_cents = models.PositiveIntegerField(default=0, help_text="Price in cents (0 for free)")
    currency = models.CharField(max_length=3, default="USD", help_text="Currency code (ISO 4217)")
    stripe_product_id = models.CharField(max_length=255, blank=True, help_text="Stripe Product ID")
    stripe_price_id = models.CharField(max_length=255, blank=True, help_text="Stripe Price ID")

    # =========================================
    # Enrollment Settings
    # =========================================
    enrollment_open = models.BooleanField(default=True, help_text="Accept new enrollments")
    max_enrollments = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum enrollments (null = unlimited)")
    enrollment_requires_approval = models.BooleanField(default=False, help_text="Require approval for enrollment")
    enrollment_opens_at = models.DateTimeField(null=True, blank=True, help_text="Enrollments accepted from this time")
    enrollment_closes_at = models.DateTimeField(null=True, blank=True, help_text="Enrollments close at this time")

    # =========================================
    # Duration & Completion
    # =========================================
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0, help_text="Estimated hours to complete")
    passing_score = models.PositiveIntegerField(
        default=70, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Minimum score to pass (0-100)"
    )

    # =========================================
    # Hybrid Completion Criteria
    # =========================================
    class HybridCompletionCriteria(models.TextChoices):
        MODULES_ONLY = "modules_only", "Complete All Required Modules"
        SESSIONS_ONLY = "sessions_only", "Attend All Required Sessions"
        BOTH = "both", "Complete Modules AND Attend Sessions"
        EITHER = "either", "Complete Modules OR Attend Sessions"
        MIN_SESSIONS = "min_sessions", "Complete Modules + Minimum Sessions"

    hybrid_completion_criteria = models.CharField(
        max_length=20,
        choices=HybridCompletionCriteria.choices,
        default=HybridCompletionCriteria.BOTH,
        help_text="How to determine completion for hybrid courses",
    )
    min_sessions_required = models.PositiveIntegerField(
        default=1, help_text="Minimum sessions to attend (when using MIN_SESSIONS criteria)"
    )

    # =========================================
    # Certificate Settings
    # =========================================

    certificates_enabled = models.BooleanField(default=True, help_text="Issue certificates on completion")
    certificate_template = models.ForeignKey(
        "certificates.CertificateTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        help_text="Template for certificates",
    )
    auto_issue_certificates = models.BooleanField(default=True, help_text="Auto-issue when course is completed")

    # =========================================
    # Badge Settings
    # =========================================
    badges_enabled = models.BooleanField(default=False, help_text="Issue badges on completion")
    badge_template = models.ForeignKey(
        "badges.BadgeTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        help_text="Template for badges",
    )
    auto_issue_badges = models.BooleanField(default=True, help_text="Auto-issue badges when course is completed")

    # =========================================
    # Stats (denormalized)
    # =========================================
    enrollment_count = models.PositiveIntegerField(default=0, help_text="Total enrollments")
    completion_count = models.PositiveIntegerField(default=0, help_text="Completed enrollments")
    module_count = models.PositiveIntegerField(default=0, help_text="Number of modules")

    class Meta:
        db_table = "courses"
        ordering = ["-created_at"]
        permissions = [
            ("can_create_course", "Can create courses"),
            ("can_manage_course", "Can manage courses"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "slug"],
                name="unique_course_slug_per_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["is_public", "status"]),
        ]
        verbose_name = "Course"
        verbose_name_plural = "Courses"

    def __str__(self):
        return self.title

    def can_manage(self, user) -> bool:
        """Check if user has full course-management access."""
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if user.groups.filter(name="admin").exists():
            return True
        if self.created_by_id == user.id:
            return True
        return self.staff_assignments.filter(user=user).exists()

    def can_instruct(self, user) -> bool:
        """Check if user has instructional access for this course.

        Course staff are all instructors under the unified role model;
        the per-course role distinction was retired with `course_manager`.
        """
        return self.can_manage(user)

    def get_staff_role(self, user) -> str | None:
        """Return the effective course role for the given user."""
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        if user.groups.filter(name="admin").exists() or self.created_by_id == user.id:
            return 'admin'
        assignment = self.staff_assignments.filter(user=user).first()
        return assignment.role if assignment else None

    @property
    def is_free(self):
        return self.price_cents == 0

    @property
    def effective_image_url(self):
        """Get image URL, preferring uploaded file."""
        if self.featured_image:
            return self.featured_image.url
        return self.featured_image_url or ""

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

    @property
    def enrollment_window_state(self):
        """Return 'upcoming' | 'open' | 'closed' | 'unbounded' based on the window fields only."""
        from django.utils import timezone as _tz
        now = _tz.now()
        if self.enrollment_opens_at and now < self.enrollment_opens_at:
            return 'upcoming'
        if self.enrollment_closes_at and now > self.enrollment_closes_at:
            return 'closed'
        if not self.enrollment_opens_at and not self.enrollment_closes_at:
            return 'unbounded'
        return 'open'

    @property
    def is_enrollable(self):
        """Fully-qualified check: toggle + window + capacity."""
        return self.check_enrollable()[0]

    def check_enrollable(self):
        """
        Return (ok, code, message). Used by every enrollment entry point so
        clients see a consistent error. Codes: ENROLLMENT_CLOSED,
        ENROLLMENT_UPCOMING, COURSE_FULL.
        """
        if not self.enrollment_open:
            return False, 'ENROLLMENT_CLOSED', 'Enrollments are closed for this course.'
        state = self.enrollment_window_state
        if state == 'upcoming':
            return False, 'ENROLLMENT_UPCOMING', f'Enrollment opens on {self.enrollment_opens_at.isoformat()}.'
        if state == 'closed':
            return False, 'ENROLLMENT_CLOSED', f'Enrollment closed on {self.enrollment_closes_at.isoformat()}.'
        if self.is_full:
            return False, 'COURSE_FULL', 'Course enrollment is full.'
        return True, '', ''

    def validate_for_publish(self):
        """
        Check that the course is structurally valid for publication.

        Raises ValidationError if:
        - hybrid: must have at least one module AND at least one published session
        - live:   must have at least one published session
        - online: must have at least one module
        """
        from django.core.exceptions import ValidationError

        errors = {}
        has_modules = self.modules.exists()
        has_published_sessions = self.sessions.filter(is_published=True).exists()

        if self.format == self.CourseFormat.ONLINE:
            if not has_modules:
                errors['modules'] = 'A self-paced course must have at least one module.'
        elif self.format == self.CourseFormat.LIVE:
            if not has_published_sessions:
                errors['sessions'] = 'A live course must have at least one published session.'
            if self.hybrid_completion_criteria == self.HybridCompletionCriteria.MIN_SESSIONS:
                published_count = self.sessions.filter(is_published=True).count()
                if self.min_sessions_required > published_count:
                    errors['min_sessions_required'] = (
                        f'Required sessions ({self.min_sessions_required}) exceeds '
                        f'available published sessions ({published_count}).'
                    )
        elif self.format == self.CourseFormat.HYBRID:
            if not has_modules:
                errors['modules'] = 'A hybrid course must have at least one module.'
            if not has_published_sessions:
                errors['sessions'] = 'A hybrid course must have at least one published session.'

        if errors:
            raise ValidationError(errors)

    def publish(self):
        """Publish the course (after structural validation)."""
        self.validate_for_publish()
        self.status = self.Status.PUBLISHED
        self.save(update_fields=["status", "updated_at"])

    def archive(self):
        """Archive the course."""
        self.status = self.Status.ARCHIVED
        self.save(update_fields=["status", "updated_at"])

    def update_counts(self):
        """Update denormalized counts."""
        self.enrollment_count = self.enrollments.filter(
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED]
        ).count()
        self.completion_count = self.enrollments.filter(status=CourseEnrollment.Status.COMPLETED).count()
        self.module_count = self.modules.count()
        self.save(update_fields=["enrollment_count", "completion_count", "module_count", "updated_at"])


class CourseAnnouncement(BaseModel):
    """
    Announcements for a course.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_announcements",
    )

    class Meta:
        db_table = "course_announcements"
        ordering = ["-created_at"]
        verbose_name = "Course Announcement"
        verbose_name_plural = "Course Announcements"

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class CourseModule(BaseModel):
    """
    Links modules to courses (through table for Course-EventModule relationship).

    This allows EventModule to be reused for both event-based and course-based learning.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    module = models.ForeignKey(EventModule, on_delete=models.CASCADE, related_name="course_links")
    order = models.PositiveIntegerField(default=0, help_text="Display order in course")
    is_required = models.BooleanField(default=True, help_text="Required for course completion")

    class Meta:
        db_table = "course_modules"
        ordering = ["order"]
        unique_together = ["course", "module"]
        verbose_name = "Course Module"
        verbose_name_plural = "Course Modules"

    def __str__(self):
        return f"{self.course.title} - {self.module.title}"


class CourseStaff(BaseModel):
    """
    Assigns users as staff on a course.

    All course staff are instructors under the unified role model; staff
    assignment grants both management and instructional access for the
    assigned course.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='staff_assignments')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_staff_assignments'
    )
    role = models.CharField(max_length=30, default='instructor')

    class Meta:
        db_table = 'course_staff'
        unique_together = ['course', 'user']
        verbose_name = 'Course Staff'
        verbose_name_plural = 'Course Staff'

    def __str__(self):
        return f"{self.user.email} - {self.course.title} ({self.role})"


class CourseEnrollment(BaseModel):
    """
    User enrollment in a self-paced course.

    Tracks enrollment status and progress through the course.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        DROPPED = "dropped", "Dropped"
        EXPIRED = "expired", "Expired"

    class AccessType(models.TextChoices):
        LIFETIME = "lifetime", "Lifetime Access"
        LIMITED = "limited", "Limited Access"
        SUBSCRIPTION = "subscription", "Subscription Access"

    # Relationships
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_enrollments")

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    access_type = models.CharField(max_length=20, choices=AccessType.choices, default=AccessType.LIFETIME)

    # Billing
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Checkout Session ID")

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
        related_name="manual_course_completions",
        help_text="User who manually marked this enrollment complete",
    )

    class Meta:
        db_table = "course_enrollments"
        ordering = ["-enrolled_at"]
        unique_together = ["course", "user"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["course", "status"]),
            models.Index(fields=["user", "status"]),
        ]
        verbose_name = "Course Enrollment"
        verbose_name_plural = "Course Enrollments"

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
            self.save(update_fields=["started_at", "updated_at"])

    def complete(self):
        """Mark enrollment as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.progress_percent = 100

        # Issue certificate via the service so we get PDF generation, snapshot,
        # subscription counters, and the unique-active-cert constraint.
        if (
            not self.certificate_issued
            and self.course.certificates_enabled
            and self.course.auto_issue_certificates
            and self.course.certificate_template
        ):
            from certificates.services import certificate_service

            result = certificate_service.issue_certificate(
                course_enrollment=self,
                issued_by=self.course.created_by or self.user,
            )
            if result.get('success'):
                # Service already set certificate_issued / certificate_issued_at on self.
                self.refresh_from_db(fields=['certificate_issued', 'certificate_issued_at'])

        # Issue badge if enabled
        if self.course.badges_enabled and self.course.auto_issue_badges and self.course.badge_template:
            from badges.models import IssuedBadge
            from badges.services import badge_service

            # Check for existing badge first (avoid duplicates)
            if not IssuedBadge.objects.filter(course_enrollment=self, template=self.course.badge_template).exists():
                badge_service.issue_badge(
                    course_enrollment=self,
                    template=self.course.badge_template,
                    issued_by=self.course.created_by or self.user,
                )

        self.save(
            update_fields=[
                "status",
                "completed_at",
                "progress_percent",
                "certificate_issued",
                "certificate_issued_at",
                "updated_at",
            ]
        )
        self.course.update_counts()

        # If this user has any active program enrollments that include this
        # course, re-evaluate program completion.
        for prog_enrollment in ProgramEnrollment.objects.filter(
            user=self.user,
            program__program_courses__course=self.course,
            status=ProgramEnrollment.Status.ACTIVE,
        ).distinct():
            prog_enrollment.check_completion()

    def drop(self):
        """Drop the enrollment."""
        self.status = self.Status.DROPPED
        self.save(update_fields=["status", "updated_at"])
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
        if getattr(self, "manually_completed", False):
            self.complete()
            return True

        # Check if all quizzes/assignments are passed
        if self._are_all_requirements_passed():
            self.complete()
            return True

        # Not complete yet, just save progress
        self.save(update_fields=["modules_completed", "progress_percent", "updated_at"])
        return False

    def _are_all_requirements_passed(self) -> bool:
        """
        Check if all required quizzes/assignments are passed.

        For hybrid courses, also checks session attendance based on
        hybrid_completion_criteria.

        Returns True if:
        - All required assignments have at least one submission with passing score
        - OR there are no required assignments (pure content course)
        - For hybrid courses: session attendance requirements are met
        """
        course = self.course

        # Pure self-paced: only modules matter
        if course.format == Course.CourseFormat.ONLINE:
            return self._check_module_requirements()

        # Pure live: only sessions matter
        if course.format == Course.CourseFormat.LIVE:
            return self._check_session_requirements()

        # Hybrid: criteria decides
        modules_passed = self._check_module_requirements()
        sessions_passed = self._check_session_requirements()

        criteria = course.hybrid_completion_criteria
        if criteria == Course.HybridCompletionCriteria.MODULES_ONLY:
            return modules_passed
        elif criteria == Course.HybridCompletionCriteria.SESSIONS_ONLY:
            return sessions_passed
        elif criteria == Course.HybridCompletionCriteria.BOTH:
            return modules_passed and sessions_passed
        elif criteria == Course.HybridCompletionCriteria.EITHER:
            return modules_passed or sessions_passed
        elif criteria == Course.HybridCompletionCriteria.MIN_SESSIONS:
            return modules_passed and sessions_passed
        else:
            return modules_passed

    def _check_module_requirements(self) -> bool:
        """Check if module/assignment requirements are passed."""
        # Get all required modules for this course
        required_modules = self.course.modules.filter(is_required=True).values_list("module_id", flat=True)

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

    def _check_session_requirements(self) -> bool:
        """Check if session attendance requirements are met."""
        course = self.course
        criteria = course.hybrid_completion_criteria

        # If strict session count is required, use that logic regardless of "mandatory" flags
        if criteria == Course.HybridCompletionCriteria.MIN_SESSIONS:
            published_count = course.sessions.filter(is_published=True).count()
            if published_count < course.min_sessions_required:
                return False
            eligible_count = CourseSessionAttendance.objects.filter(
                enrollment=self, is_eligible=True, session__course=course
            ).count()
            return eligible_count >= course.min_sessions_required

        # Otherwise (SESSIONS_ONLY, BOTH, EITHER): use mandatory-session attendance.
        mandatory_sessions = course.sessions.filter(is_mandatory=True, is_published=True)

        if not mandatory_sessions.exists():
            # For session-driven courses (live, or hybrid with SESSIONS_ONLY/BOTH/EITHER)
            # we can't auto-pass when there are no mandatory sessions to attend —
            # that would mark every brand-new enrollment complete.
            session_driven = course.format == Course.CourseFormat.LIVE or criteria in (
                Course.HybridCompletionCriteria.SESSIONS_ONLY,
                Course.HybridCompletionCriteria.BOTH,
                Course.HybridCompletionCriteria.EITHER,
            )
            return not session_driven

        count_passed = CourseSessionAttendance.objects.filter(
            session__in=mandatory_sessions, enrollment=self, is_eligible=True
        ).count()

        return count_passed >= mandatory_sessions.count()

    def mark_complete_manually(self, completed_by):
        """
        Manually mark course as complete (instructor/manager override).

        Args:
            completed_by: User who marked completion (instructor or course manager)
        """
        self.manually_completed = True
        self.manually_completed_by = completed_by
        self.save(update_fields=["manually_completed", "manually_completed_by", "updated_at"])
        self.complete()


# =============================================================================
# Course Live Sessions (for Hybrid courses)
# =============================================================================


class CourseSession(BaseModel):
    """
    Individual live session within a hybrid course.

    Hybrid courses consist of self-paced content plus scheduled live sessions.
    Each session can have its own video meeting and tracks attendance independently.
    """

    class SessionType(models.TextChoices):
        LIVE = "live", "Live Session"
        RECORDED = "recorded", "Recorded/On-demand"
        HYBRID = "hybrid", "Hybrid"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        LIVE = "live", "Live"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    # Relationships
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")

    # Basic info
    title = models.CharField(max_length=255, help_text="Session title")
    description = models.TextField(blank=True, help_text="Session description")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    session_type = models.CharField(max_length=20, choices=SessionType.choices, default=SessionType.LIVE)

    # Schedule
    starts_at = models.DateTimeField(help_text="Session start time")
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    timezone = models.CharField(max_length=50, default="UTC", help_text="Session timezone")
    actual_start_at = models.DateTimeField(null=True, blank=True, help_text="When the session actually started")
    actual_end_at = models.DateTimeField(null=True, blank=True, help_text="When the session actually ended")

    # Video conferencing (per-session)
    video_settings = models.JSONField(default=dict, blank=True, help_text="Video conferencing settings")
    recording_enabled = models.BooleanField(default=False, help_text="Enable cloud recording")
    recording_auto_publish = models.BooleanField(default=False, help_text="Auto-publish recording when available")

    # CPD credits for this session
    cpd_credits = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="CPD credits for attending")

    # Attendance requirements
    is_mandatory = models.BooleanField(default=True, help_text="Required for course completion")
    minimum_attendance_percent = models.PositiveIntegerField(
        default=80, help_text="Minimum attendance percentage for eligibility"
    )

    # Status & Lifecycle
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True
    )
    cancelled_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "course_sessions"
        ordering = ["course", "order", "starts_at"]
        verbose_name = "Course Session"
        verbose_name_plural = "Course Sessions"
        indexes = [
            models.Index(fields=["course", "starts_at"]),
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def ends_at(self):
        """Calculate scheduled end time."""
        return self.starts_at + timezone.timedelta(minutes=self.duration_minutes)

    @property
    def is_upcoming(self):
        """Check if session is in the future."""
        return timezone.now() < self.starts_at

    @property
    def is_live(self):
        """Check if session is currently happening."""
        now = timezone.now()
        return self.starts_at <= now <= self.ends_at

    @property
    def is_past(self):
        """Check if session has ended."""
        return timezone.now() > self.ends_at

    def _recording_enabled(self) -> bool:
        if not self.recording_enabled:
            return False
        settings = self.video_settings if isinstance(self.video_settings, dict) else {}
        return bool(settings.get('enabled'))

    def start(self):
        """Mark the session as live."""
        if self.status == self.Status.CANCELLED:
            raise ValueError("Cannot start a cancelled session.")
        self.status = self.Status.LIVE
        self.actual_start_at = timezone.now()
        self.save(update_fields=['status', 'actual_start_at', 'updated_at'])

        if self._recording_enabled():
            from conferencing.tasks import start_course_session_recording

            start_course_session_recording.delay(self.id)

    def complete(self):
        """Mark the session as completed."""
        if self.status == self.Status.CANCELLED:
            raise ValueError("Cannot complete a cancelled session.")
        self.status = self.Status.COMPLETED
        self.actual_end_at = timezone.now()
        self.save(update_fields=['status', 'actual_end_at', 'updated_at'])

        if self._recording_enabled():
            from conferencing.tasks import stop_course_session_recording

            stop_course_session_recording.delay(self.id)

    def cancel(self, reason: str = '', user=None):
        """Cancel the session."""
        if self.status == self.Status.COMPLETED:
            raise ValueError("Cannot cancel a completed session.")
        self.status = self.Status.CANCELLED
        self.cancelled_reason = reason
        self.cancelled_at = timezone.now()
        self.save(update_fields=['status', 'cancelled_reason', 'cancelled_at', 'updated_at'])

    def reschedule(self, new_starts_at, new_duration_minutes=None):
        """Move the session to a new time."""
        if self.status in (self.Status.COMPLETED, self.Status.CANCELLED):
            raise ValueError(f"Cannot reschedule a {self.status} session.")
        self.starts_at = new_starts_at
        if new_duration_minutes is not None:
            self.duration_minutes = new_duration_minutes
        self.status = self.Status.SCHEDULED
        self.save(update_fields=['starts_at', 'duration_minutes', 'status', 'updated_at'])


class CourseSessionAttendance(BaseModel):
    """
    Attendance record for a course session.

    Tracks whether an enrolled student attended a live session
    and whether they met the minimum attendance threshold.
    """

    session = models.ForeignKey(CourseSession, on_delete=models.CASCADE, related_name="attendance_records")
    enrollment = models.ForeignKey(CourseEnrollment, on_delete=models.CASCADE, related_name="session_attendance")

    # Attendance tracking
    attendance_minutes = models.PositiveIntegerField(default=0, help_text="Minutes attended")
    is_eligible = models.BooleanField(default=False, help_text="Met minimum attendance %")

    # Video participant data (for syncing — provider-agnostic, populated from LiveKit identity)
    participant_id = models.CharField(max_length=255, blank=True)
    participant_email = models.EmailField(blank=True)
    join_time = models.DateTimeField(null=True, blank=True)
    leave_time = models.DateTimeField(null=True, blank=True)

    # Manual override
    is_manual_override = models.BooleanField(default=False)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_attendance_overrides",
    )
    override_reason = models.TextField(blank=True)

    class Meta:
        db_table = "course_session_attendance"
        unique_together = ["session", "enrollment"]
        ordering = ["-created_at"]
        verbose_name = "Course Session Attendance"
        verbose_name_plural = "Course Session Attendance"
        indexes = [
            models.Index(fields=["session", "enrollment"]),
            models.Index(fields=["participant_email"]),
        ]

    def __str__(self):
        return f"{self.enrollment.user.email} - {self.session.title}"

    @property
    def attendance_percent(self):
        """Calculate attendance percentage."""
        if self.session.duration_minutes == 0:
            return 0
        return int((self.attendance_minutes / self.session.duration_minutes) * 100)

    def calculate_eligibility(self):
        """Check if attendance meets minimum threshold."""
        self.is_eligible = self.attendance_percent >= self.session.minimum_attendance_percent
        return self.is_eligible

    def set_override(self, eligible: bool, user, reason: str = ""):
        """Set manual override for attendance eligibility."""
        self.is_eligible = eligible
        self.is_manual_override = True
        self.override_by = user
        self.override_reason = reason
        self.save()


# =============================================================================
# Programs (curated bundles of courses)
# =============================================================================


class Program(BaseModel):
    """
    A curated bundle of multiple courses.

    Learners can either purchase the courses individually OR buy the bundle to
    get all member courses at the program's bundle price (typically a discount
    vs. the sum of individual prices). Buying the bundle auto-enrolls the
    learner in every member course.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_programs",
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True, max_length=5000)
    short_description = models.CharField(max_length=300, blank=True)
    featured_image = models.ImageField(upload_to="programs/images/", null=True, blank=True)
    featured_image_url = models.URLField(blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    is_public = models.BooleanField(default=True)

    # Bundle pricing (separate from per-course pricing)
    price_cents = models.PositiveIntegerField(default=0, help_text="Bundle price in cents")
    currency = models.CharField(max_length=3, default="USD")
    stripe_product_id = models.CharField(max_length=255, blank=True)
    stripe_price_id = models.CharField(max_length=255, blank=True)

    # Denormalized
    course_count = models.PositiveIntegerField(default=0)
    enrollment_count = models.PositiveIntegerField(default=0)

    courses = models.ManyToManyField(
        Course,
        through="ProgramCourse",
        related_name="programs",
    )

    class Meta:
        db_table = "programs"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "slug"], name="unique_program_slug_per_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["is_public", "status"]),
        ]
        verbose_name = "Program"
        verbose_name_plural = "Programs"

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def is_free(self):
        return self.price_cents == 0

    @property
    def effective_image_url(self):
        if self.featured_image:
            return self.featured_image.url
        return self.featured_image_url or ""

    def can_manage(self, user) -> bool:
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if user.groups.filter(name="admin").exists():
            return True
        return self.created_by_id == user.id

    def validate_for_publish(self):
        from django.core.exceptions import ValidationError
        if not self.program_courses.exists():
            raise ValidationError({'courses': 'A program must contain at least one course.'})

    def publish(self):
        self.validate_for_publish()
        self.status = self.Status.PUBLISHED
        self.save(update_fields=["status", "updated_at"])

    def archive(self):
        self.status = self.Status.ARCHIVED
        self.save(update_fields=["status", "updated_at"])

    def update_counts(self):
        self.course_count = self.program_courses.count()
        self.enrollment_count = self.enrollments.filter(
            status__in=[ProgramEnrollment.Status.ACTIVE, ProgramEnrollment.Status.COMPLETED]
        ).count()
        self.save(update_fields=["course_count", "enrollment_count", "updated_at"])

    def sum_individual_price_cents(self) -> int:
        """Sum of member courses' individual prices — used to display savings."""
        return sum(
            (c.price_cents or 0)
            for c in self.courses.all()
        )


class ProgramCourse(BaseModel):
    """Through-table linking a Program to a Course with ordering."""

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="program_courses")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="program_memberships")
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = "program_courses"
        ordering = ["program", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "course"], name="unique_program_course",
            ),
        ]
        verbose_name = "Program Course"
        verbose_name_plural = "Program Courses"

    def __str__(self):
        return f"{self.program.title} → {self.course.title}"


class ProgramEnrollment(BaseModel):
    """A learner's enrollment in a Program (and, transitively, its courses)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        DROPPED = "dropped", "Dropped"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="program_enrollments",
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    enrolled_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    course_enrollments_seeded = models.BooleanField(
        default=False,
        help_text="True once member-course CourseEnrollments have been auto-created.",
    )

    class Meta:
        db_table = "program_enrollments"
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "program"], name="unique_program_enrollment_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["program", "status"]),
        ]
        verbose_name = "Program Enrollment"
        verbose_name_plural = "Program Enrollments"

    def __str__(self):
        return f"{self.user.email} → {self.program.title} ({self.status})"

    def activate(self):
        """Mark active and seed per-course enrollments for every member course."""
        was_pending = self.status == self.Status.PENDING
        self.status = self.Status.ACTIVE
        if not self.started_at:
            self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])
        if was_pending or not self.course_enrollments_seeded:
            self._seed_course_enrollments()

    def _seed_course_enrollments(self):
        """Create or activate CourseEnrollments for each member course (idempotent)."""
        for member in self.program.program_courses.select_related("course"):
            course = member.course
            existing = CourseEnrollment.objects.filter(course=course, user=self.user).first()
            if existing is None:
                CourseEnrollment.objects.create(
                    course=course,
                    user=self.user,
                    status=CourseEnrollment.Status.ACTIVE,
                    enrolled_at=timezone.now(),
                    access_type=CourseEnrollment.AccessType.LIFETIME,
                )
            elif existing.status not in (
                CourseEnrollment.Status.ACTIVE,
                CourseEnrollment.Status.COMPLETED,
            ):
                existing.status = CourseEnrollment.Status.ACTIVE
                if not existing.enrolled_at:
                    existing.enrolled_at = timezone.now()
                existing.save(update_fields=["status", "enrolled_at", "updated_at"])
        self.course_enrollments_seeded = True
        self.save(update_fields=["course_enrollments_seeded", "updated_at"])

    def check_completion(self) -> bool:
        """Mark COMPLETED when every required member course is completed by the learner."""
        if self.status != self.Status.ACTIVE:
            return False

        required_courses = self.program.program_courses.filter(is_required=True).values_list(
            "course_id", flat=True
        )
        if not required_courses:
            return False

        completed_required = CourseEnrollment.objects.filter(
            user=self.user,
            course_id__in=required_courses,
            status=CourseEnrollment.Status.COMPLETED,
        ).count()

        if completed_required >= len(required_courses):
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at", "updated_at"])
            return True
        return False

    def drop(self):
        self.status = self.Status.DROPPED
        self.save(update_fields=["status", "updated_at"])


class DiscussionThread(SoftDeleteModel):
    """Top-level discussion thread on a course."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="discussion_threads")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discussion_threads",
    )
    title = models.CharField(max_length=255)
    body_html = models.TextField()
    body_plain = models.TextField(blank=True)
    is_pinned = models.BooleanField(default=False, db_index=True)
    is_locked = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False, db_index=True)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    reply_count = models.PositiveIntegerField(default=0)
    mentions = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="discussion_thread_mentions",
    )

    class Meta:
        db_table = "discussion_threads"
        ordering = ["-is_pinned", "-last_activity_at"]
        indexes = [
            models.Index(fields=["course", "-last_activity_at"]),
            models.Index(fields=["course", "is_pinned"]),
        ]
        verbose_name = "Discussion Thread"
        verbose_name_plural = "Discussion Threads"

    def __str__(self):
        return f"{self.course.title} — {self.title}"

    def touch_activity(self):
        self.last_activity_at = timezone.now()
        self.save(update_fields=["last_activity_at", "updated_at"])


class DiscussionReply(SoftDeleteModel):
    """Flat (single-level) reply to a DiscussionThread."""

    thread = models.ForeignKey(DiscussionThread, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discussion_replies",
    )
    body_html = models.TextField()
    body_plain = models.TextField(blank=True)
    is_hidden = models.BooleanField(default=False, db_index=True)
    mentions = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="discussion_reply_mentions",
    )

    class Meta:
        db_table = "discussion_replies"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["thread", "created_at"])]
        verbose_name = "Discussion Reply"
        verbose_name_plural = "Discussion Replies"

    def __str__(self):
        return f"Reply by {self.author} on {self.thread.title}"


class DiscussionFlag(BaseModel):
    """Learner-raised flag on a thread or reply; resolved by staff."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED_KEPT = "resolved_kept", "Resolved — Content Kept"
        RESOLVED_HIDDEN = "resolved_hidden", "Resolved — Content Hidden"

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        HARASSMENT = "harassment", "Harassment"
        OFF_TOPIC = "off_topic", "Off-topic"
        OTHER = "other", "Other"

    thread = models.ForeignKey(
        DiscussionThread,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="flags",
    )
    reply = models.ForeignKey(
        DiscussionReply,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="flags",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discussion_flags_raised",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discussion_flags_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "discussion_flags"
        indexes = [models.Index(fields=["status", "-created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(thread__isnull=False, reply__isnull=True)
                    | models.Q(thread__isnull=True, reply__isnull=False)
                ),
                name="discussion_flag_exactly_one_target",
            ),
        ]
        verbose_name = "Discussion Flag"
        verbose_name_plural = "Discussion Flags"

    def __str__(self):
        target = self.thread_id and f"thread {self.thread_id}" or f"reply {self.reply_id}"
        return f"Flag on {target} ({self.reason}, {self.status})"

    @property
    def course(self):
        return self.thread.course if self.thread_id else self.reply.thread.course
