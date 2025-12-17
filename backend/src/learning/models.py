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

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

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
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='modules'
    )
    prerequisite_module = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dependent_modules'
    )
    
    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    # Release settings
    release_type = models.CharField(
        max_length=30,
        choices=ReleaseType.choices,
        default=ReleaseType.IMMEDIATE
    )
    release_at = models.DateTimeField(null=True, blank=True)
    release_days_after_registration = models.PositiveIntegerField(default=0)
    
    # Scoring
    passing_score = models.PositiveIntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # CPD credits for this module
    cpd_credits = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
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
    
    def is_available_for_registration(self, registration):
        """Check if module is available for a registration."""
        now = timezone.now()
        
        if not self.is_published:
            return False
        
        if self.release_type == self.ReleaseType.IMMEDIATE:
            return True
        
        if self.release_type == self.ReleaseType.SCHEDULED:
            return self.release_at and now >= self.release_at
        
        if self.release_type == self.ReleaseType.DAYS_AFTER_REG:
            release_date = registration.created_at + timezone.timedelta(
                days=self.release_days_after_registration
            )
            return now >= release_date
        
        if self.release_type == self.ReleaseType.PREREQUISITE:
            if not self.prerequisite_module:
                return True
            # Check if prerequisite is completed
            try:
                prereq_progress = ModuleProgress.objects.get(
                    registration=registration,
                    module=self.prerequisite_module
                )
                return prereq_progress.status == 'completed'
            except ModuleProgress.DoesNotExist:
                return False
        
        return False


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
    
    # Relationships
    module = models.ForeignKey(
        EventModule,
        on_delete=models.CASCADE,
        related_name='contents'
    )
    
    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices
    )
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
    module = models.ForeignKey(
        EventModule,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    
    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    instructions = models.TextField()
    
    # Due date (relative to module release)
    due_days_after_release = models.PositiveIntegerField(default=7)
    
    # Scoring
    max_score = models.PositiveIntegerField(default=100)
    passing_score = models.PositiveIntegerField(default=70)
    
    # Submission settings
    allow_resubmission = models.BooleanField(default=True)
    max_attempts = models.PositiveIntegerField(default=3)
    submission_type = models.CharField(
        max_length=20,
        choices=SubmissionType.choices,
        default=SubmissionType.TEXT
    )
    
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
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='assignment_submissions'
    )
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions'
    )
    
    # Submission details
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
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
            models.Index(fields=['status']),
        ]
    
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
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submission_reviews'
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
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='content_progress'
    )
    content = models.ForeignKey(
        ModuleContent,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )
    
    # Progress
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100)]
    )
    time_spent_seconds = models.PositiveIntegerField(default=0)
    
    # Position tracking (for videos, documents)
    last_position = models.JSONField(default=dict)  # {time, page, etc.}
    
    class Meta:
        db_table = 'content_progress'
        verbose_name = 'Content Progress'
        verbose_name_plural = 'Content Progress'
        unique_together = [['registration', 'content']]
    
    def __str__(self):
        return f"{self.registration.user.email} - {self.content.title}"
    
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
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='module_progress'
    )
    module = models.ForeignKey(
        EventModule,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )
    
    # Progress
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )
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
        unique_together = [['registration', 'module']]
    
    def __str__(self):
        return f"{self.registration.user.email} - {self.module.title}"
    
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
        
        completed = ContentProgress.objects.filter(
            registration=self.registration,
            content__in=required_contents,
            status=ContentProgress.Status.COMPLETED
        ).count()
        self.contents_completed = completed
        
        if self.contents_completed >= self.contents_total and self.contents_total > 0:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
        elif self.contents_completed > 0:
            self.status = self.Status.IN_PROGRESS
            if not self.started_at:
                self.started_at = timezone.now()
        
        self.save()
