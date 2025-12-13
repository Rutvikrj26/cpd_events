# Learning App: Modules, Content & Assignments

## Overview

The `learning` app provides optional LMS (Learning Management System) features:
- Event modules with scheduled content release (drip content)
- Multiple content types (video, documents, links, text)
- Assignments with submission and review workflows
- Progress tracking for certificate eligibility

**All features are optional per event** — organizers can enable/disable as needed.

---

## Feature Flags on Event

These fields are added to the Event model to enable LMS features:

```python
# In events/models.py - Add to Event model

# =========================================
# LMS Features (Optional)
# =========================================
modules_enabled = models.BooleanField(
    default=False,
    help_text="Enable content modules for this event"
)
assignments_enabled = models.BooleanField(
    default=False,
    help_text="Enable assignments for this event"
)
require_module_completion = models.BooleanField(
    default=False,
    help_text="Require all modules completed for certificate"
)
require_assignments_passed = models.BooleanField(
    default=False,
    help_text="Require all required assignments passed for certificate"
)
passing_score_percent = models.PositiveIntegerField(
    default=70,
    validators=[MinValueValidator(0), MaxValueValidator(100)],
    help_text="Minimum score % to pass assignments (if graded)"
)
```

**Updated Certificate Eligibility Logic:**

```python
# In registrations/models.py - Update Registration.can_receive_certificate

@property
def can_receive_certificate(self):
    """Check if eligible for certificate."""
    if not self.event.certificates_enabled:
        return False
    if self.status != self.Status.CONFIRMED:
        return False
    
    # Attendance requirement (existing)
    if not self.attendance_eligible and not self.attendance_override:
        return False
    
    # NEW: Module completion requirement
    if self.event.require_module_completion:
        if not self.all_modules_completed:
            return False
    
    # NEW: Assignment requirement
    if self.event.require_assignments_passed:
        if not self.all_required_assignments_passed:
            return False
    
    return True
```

---

## Models

### EventModule

A content unit/week/section within an event.

```python
# learning/models.py

from django.db import models
from django.utils import timezone
from common.models import BaseModel


class EventModule(BaseModel):
    """
    A module/unit/week within an event.
    
    Modules organize content and can be released on a schedule
    (drip content) or all at once.
    
    Example structures:
    - Weekly modules: "Week 1: Introduction", "Week 2: Advanced Topics"
    - Topic modules: "Module 1: Basics", "Module 2: Deep Dive"
    - Session modules: "Pre-Work", "Live Session", "Post-Session"
    """
    
    class ReleaseType(models.TextChoices):
        IMMEDIATE = 'immediate', 'Available Immediately'
        SCHEDULED = 'scheduled', 'Scheduled Release'
        AFTER_PREVIOUS = 'after_previous', 'After Previous Module Completed'
        AFTER_REGISTRATION = 'after_registration', 'Days After Registration'
    
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='modules'
    )
    
    # =========================================
    # Basic Info
    # =========================================
    title = models.CharField(
        max_length=200,
        help_text="Module title (e.g., 'Week 1: Introduction')"
    )
    description = models.TextField(
        blank=True,
        max_length=2000,
        help_text="Module description/overview"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower = first)"
    )
    
    # =========================================
    # Release Settings
    # =========================================
    release_type = models.CharField(
        max_length=20,
        choices=ReleaseType.choices,
        default=ReleaseType.IMMEDIATE
    )
    release_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When module becomes available (for scheduled release)"
    )
    release_days_after_registration = models.PositiveIntegerField(
        default=0,
        help_text="Days after registration to release (for drip content)"
    )
    
    # =========================================
    # Requirements
    # =========================================
    is_required = models.BooleanField(
        default=True,
        help_text="Required for event completion"
    )
    prerequisite_module = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dependent_modules',
        help_text="Module that must be completed first"
    )
    
    # =========================================
    # Estimated Time
    # =========================================
    estimated_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Estimated time to complete (minutes)"
    )
    
    # =========================================
    # Status
    # =========================================
    is_published = models.BooleanField(
        default=False,
        help_text="Whether module is visible to attendees"
    )
    
    # =========================================
    # Denormalized Counts
    # =========================================
    content_count = models.PositiveIntegerField(
        default=0
    )
    assignment_count = models.PositiveIntegerField(
        default=0
    )
    
    class Meta:
        db_table = 'event_modules'
        ordering = ['order', 'id']
        unique_together = [['event', 'order']]
        indexes = [
            models.Index(fields=['event', 'order']),
            models.Index(fields=['event', 'is_published']),
            models.Index(fields=['release_at']),
        ]
        verbose_name = 'Event Module'
        verbose_name_plural = 'Event Modules'
    
    def __str__(self):
        return f"{self.event.title} - {self.title}"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def is_released(self):
        """Check if module is released (globally)."""
        if self.release_type == self.ReleaseType.IMMEDIATE:
            return True
        if self.release_type == self.ReleaseType.SCHEDULED:
            return self.release_at and timezone.now() >= self.release_at
        # For other types, check per-registration
        return None  # Depends on registration
    
    def is_available_for(self, registration):
        """
        Check if module is available for a specific registration.
        
        Args:
            registration: Registration to check
        
        Returns:
            bool: Whether module is available
        """
        if not self.is_published:
            return False
        
        if self.release_type == self.ReleaseType.IMMEDIATE:
            return True
        
        if self.release_type == self.ReleaseType.SCHEDULED:
            return self.release_at and timezone.now() >= self.release_at
        
        if self.release_type == self.ReleaseType.AFTER_PREVIOUS:
            if not self.prerequisite_module:
                return True
            # Check if prerequisite is completed
            try:
                progress = ModuleProgress.objects.get(
                    registration=registration,
                    module=self.prerequisite_module
                )
                return progress.is_completed
            except ModuleProgress.DoesNotExist:
                return False
        
        if self.release_type == self.ReleaseType.AFTER_REGISTRATION:
            release_date = registration.created_at + timezone.timedelta(
                days=self.release_days_after_registration
            )
            return timezone.now() >= release_date
        
        return False
    
    def update_counts(self):
        """Update denormalized counts."""
        self.content_count = self.contents.count()
        self.assignment_count = self.assignments.count()
        self.save(update_fields=['content_count', 'assignment_count', 'updated_at'])
```

---

### ModuleContent

Individual content items within a module.

```python
class ModuleContent(BaseModel):
    """
    A content item within a module.
    
    Supports multiple content types:
    - Video (embedded or hosted)
    - Document (PDF, DOCX, etc.)
    - Link (external resource)
    - Text/HTML (inline content)
    - Quiz (link to external quiz or embedded)
    - Recording (Zoom cloud recording from event)
    """
    
    class ContentType(models.TextChoices):
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'
        LINK = 'link', 'External Link'
        TEXT = 'text', 'Text/HTML Content'
        AUDIO = 'audio', 'Audio'
        PRESENTATION = 'presentation', 'Presentation'
        QUIZ = 'quiz', 'Quiz'
        DOWNLOAD = 'download', 'Downloadable File'
        RECORDING = 'recording', 'Zoom Recording'
    
    module = models.ForeignKey(
        EventModule,
        on_delete=models.CASCADE,
        related_name='contents'
    )
    
    # =========================================
    # Basic Info
    # =========================================
    title = models.CharField(
        max_length=200,
        help_text="Content title"
    )
    description = models.TextField(
        blank=True,
        max_length=1000,
        help_text="Brief description"
    )
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within module"
    )
    
    # =========================================
    # Content Data
    # =========================================
    # For video/audio
    video_url = models.URLField(
        blank=True,
        help_text="Video URL (YouTube, Vimeo, or direct)"
    )
    video_embed_code = models.TextField(
        blank=True,
        help_text="Custom embed code (if not using URL)"
    )
    video_duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Video/audio duration in seconds"
    )
    
    # For Zoom recordings
    zoom_recording = models.ForeignKey(
        'integrations.ZoomRecording',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='module_contents',
        help_text="Linked Zoom recording (for recording content type)"
    )
    
    # For documents/downloads
    file_url = models.URLField(
        blank=True,
        help_text="URL to file in cloud storage"
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Original filename"
    )
    file_size_bytes = models.PositiveIntegerField(
        default=0
    )
    file_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="MIME type or extension"
    )
    
    # For links
    external_url = models.URLField(
        blank=True,
        help_text="External link URL"
    )
    open_in_new_tab = models.BooleanField(
        default=True
    )
    
    # For text/HTML content
    text_content = models.TextField(
        blank=True,
        help_text="HTML content (sanitized)"
    )
    
    # =========================================
    # Requirements
    # =========================================
    is_required = models.BooleanField(
        default=True,
        help_text="Required for module completion"
    )
    minimum_view_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Minimum seconds to view (for videos)"
    )
    
    # =========================================
    # Status
    # =========================================
    is_published = models.BooleanField(
        default=True
    )
    
    class Meta:
        db_table = 'module_contents'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['module', 'order']),
            models.Index(fields=['content_type']),
        ]
        verbose_name = 'Module Content'
        verbose_name_plural = 'Module Contents'
    
    def __str__(self):
        return f"{self.module.title} - {self.title}"
    
    @property
    def estimated_minutes(self):
        """Estimated time to complete this content."""
        if self.content_type in ['video', 'audio']:
            return max(1, self.video_duration_seconds // 60)
        if self.content_type == 'recording' and self.zoom_recording:
            return max(1, self.zoom_recording.duration_seconds // 60)
        if self.content_type == 'text':
            # Rough estimate: 200 words per minute
            word_count = len(self.text_content.split())
            return max(1, word_count // 200)
        if self.content_type == 'document':
            return 5  # Default estimate
        return 2  # Links, downloads
```

---

### Assignment

An assignment within a module or event.

```python
class Assignment(BaseModel):
    """
    An assignment for attendees to complete.
    
    Can be attached to a specific module or the event overall.
    
    Types:
    - File upload (essay, project, document)
    - Text submission (short answer, reflection)
    - Link submission (portfolio, external project)
    - Quiz (external quiz integration)
    
    Grading:
    - Pass/Fail (meets requirements or not)
    - Points (0-100 or custom max)
    - Percentage
    - Ungraded (completion only)
    """
    
    class SubmissionType(models.TextChoices):
        FILE = 'file', 'File Upload'
        TEXT = 'text', 'Text Entry'
        LINK = 'link', 'URL/Link'
        FILE_OR_TEXT = 'file_or_text', 'File or Text'
        QUIZ = 'quiz', 'Quiz'
        NONE = 'none', 'No Submission (Completion)'
    
    class GradingType(models.TextChoices):
        PASS_FAIL = 'pass_fail', 'Pass/Fail'
        POINTS = 'points', 'Points'
        PERCENTAGE = 'percentage', 'Percentage'
        UNGRADED = 'ungraded', 'Ungraded (Completion Only)'
    
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    module = models.ForeignKey(
        EventModule,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='assignments',
        help_text="Module this assignment belongs to (null for event-level)"
    )
    
    # =========================================
    # Basic Info
    # =========================================
    title = models.CharField(
        max_length=200,
        help_text="Assignment title"
    )
    description = models.TextField(
        blank=True,
        max_length=5000,
        help_text="Assignment description/overview"
    )
    instructions = models.TextField(
        blank=True,
        max_length=10000,
        help_text="Detailed instructions (supports markdown)"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    # =========================================
    # Submission Settings
    # =========================================
    submission_type = models.CharField(
        max_length=20,
        choices=SubmissionType.choices,
        default=SubmissionType.FILE
    )
    
    # File upload settings
    allowed_file_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Allowed file extensions (e.g., ['pdf', 'docx'])"
    )
    max_file_size_mb = models.PositiveIntegerField(
        default=10,
        help_text="Maximum file size in MB"
    )
    max_files = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of files"
    )
    
    # Text submission settings
    min_word_count = models.PositiveIntegerField(
        default=0,
        help_text="Minimum word count (0 = no minimum)"
    )
    max_word_count = models.PositiveIntegerField(
        default=0,
        help_text="Maximum word count (0 = no maximum)"
    )
    
    # =========================================
    # Due Date
    # =========================================
    due_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Submission deadline"
    )
    allow_late_submissions = models.BooleanField(
        default=True,
        help_text="Allow submissions after due date"
    )
    late_penalty_percent = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
        help_text="Percentage penalty for late submissions"
    )
    late_deadline_days = models.PositiveIntegerField(
        default=7,
        help_text="Days after due date to accept late submissions"
    )
    
    # =========================================
    # Grading
    # =========================================
    grading_type = models.CharField(
        max_length=20,
        choices=GradingType.choices,
        default=GradingType.PASS_FAIL
    )
    max_points = models.PositiveIntegerField(
        default=100,
        help_text="Maximum points (for points grading)"
    )
    passing_score = models.PositiveIntegerField(
        default=70,
        help_text="Minimum score to pass"
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        help_text="Weight for overall grade calculation"
    )
    
    # =========================================
    # Rubric (Optional)
    # =========================================
    rubric = models.JSONField(
        default=list,
        blank=True,
        help_text="Grading rubric criteria"
    )
    """
    Rubric schema:
    [
        {
            "criterion": "Content Quality",
            "description": "Demonstrates understanding of key concepts",
            "max_points": 40,
            "levels": [
                {"label": "Excellent", "points": 40, "description": "..."},
                {"label": "Good", "points": 30, "description": "..."},
                {"label": "Fair", "points": 20, "description": "..."},
                {"label": "Poor", "points": 10, "description": "..."}
            ]
        },
        ...
    ]
    """
    
    # =========================================
    # Requirements
    # =========================================
    is_required = models.BooleanField(
        default=True,
        help_text="Required for certificate eligibility"
    )
    
    # =========================================
    # Resources
    # =========================================
    resources = models.JSONField(
        default=list,
        blank=True,
        help_text="Supporting resources/files"
    )
    """
    Resources schema:
    [
        {
            "title": "Assignment Template",
            "type": "file",
            "url": "https://...",
            "file_type": "docx"
        },
        {
            "title": "Reference Guide",
            "type": "link",
            "url": "https://..."
        }
    ]
    """
    
    # =========================================
    # Status
    # =========================================
    is_published = models.BooleanField(
        default=False
    )
    
    # =========================================
    # Denormalized Counts
    # =========================================
    submission_count = models.PositiveIntegerField(
        default=0
    )
    graded_count = models.PositiveIntegerField(
        default=0
    )
    
    class Meta:
        db_table = 'assignments'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['event', 'order']),
            models.Index(fields=['module', 'order']),
            models.Index(fields=['due_at']),
            models.Index(fields=['is_published', 'is_required']),
        ]
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'
    
    def __str__(self):
        return f"{self.event.title} - {self.title}"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def is_past_due(self):
        if not self.due_at:
            return False
        return timezone.now() > self.due_at
    
    @property
    def final_deadline(self):
        """Last date to submit (including late period)."""
        if not self.due_at:
            return None
        if not self.allow_late_submissions:
            return self.due_at
        return self.due_at + timezone.timedelta(days=self.late_deadline_days)
    
    @property
    def is_closed(self):
        """No more submissions accepted."""
        if not self.final_deadline:
            return False
        return timezone.now() > self.final_deadline
    
    def is_available_for(self, registration):
        """Check if assignment is available for a registration."""
        if not self.is_published:
            return False
        if self.module and not self.module.is_available_for(registration):
            return False
        return True
    
    def update_counts(self):
        """Update denormalized counts."""
        from learning.models import AssignmentSubmission
        
        self.submission_count = self.submissions.filter(
            status__in=[
                AssignmentSubmission.Status.SUBMITTED,
                AssignmentSubmission.Status.UNDER_REVIEW,
                AssignmentSubmission.Status.REVIEWED,
                AssignmentSubmission.Status.APPROVED,
                AssignmentSubmission.Status.REJECTED
            ]
        ).count()
        
        self.graded_count = self.submissions.filter(
            status__in=[
                AssignmentSubmission.Status.APPROVED,
                AssignmentSubmission.Status.REJECTED
            ]
        ).count()
        
        self.save(update_fields=['submission_count', 'graded_count', 'updated_at'])
```

---

### AssignmentSubmission

A submission from a registrant.

```python
class AssignmentSubmission(BaseModel):
    """
    A submission for an assignment.
    
    Lifecycle:
        DRAFT → SUBMITTED → UNDER_REVIEW → REVIEWED
                                ↓              ↓
                         REVISION_REQUESTED    ↓
                                ↓              ↓
                         (resubmit) ──────────→ APPROVED / REJECTED
    
    Resubmission:
    - If revision requested, attendee can update and resubmit
    - History of all versions maintained via SubmissionVersion
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        REVISION_REQUESTED = 'revision_requested', 'Revision Requested'
        REVIEWED = 'reviewed', 'Reviewed'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
    
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
    
    # =========================================
    # Submission Content
    # =========================================
    # For text submissions
    text_content = models.TextField(
        blank=True,
        help_text="Text submission content"
    )
    
    # For file submissions
    files = models.JSONField(
        default=list,
        blank=True,
        help_text="Uploaded files"
    )
    """
    Files schema:
    [
        {
            "file_url": "https://...",
            "file_name": "essay.pdf",
            "file_size_bytes": 102400,
            "file_type": "application/pdf",
            "uploaded_at": "2025-01-15T10:30:00Z"
        },
        ...
    ]
    """
    
    # For link submissions
    link_url = models.URLField(
        blank=True
    )
    link_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Title/description of linked content"
    )
    
    # =========================================
    # Status
    # =========================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Timing
    submitted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When submission was submitted"
    )
    is_late = models.BooleanField(
        default=False,
        help_text="Submitted after due date"
    )
    
    # =========================================
    # Grading
    # =========================================
    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True, blank=True,
        help_text="Score (interpretation depends on grading type)"
    )
    score_before_penalty = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True, blank=True,
        help_text="Score before late penalty"
    )
    passed = models.BooleanField(
        null=True,
        help_text="Whether submission passed (null if not graded)"
    )
    
    # Rubric scores (if rubric used)
    rubric_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text="Scores for each rubric criterion"
    )
    """
    Rubric scores schema:
    {
        "criterion_index_0": {
            "score": 35,
            "level_selected": 1,
            "comment": "Good analysis but..."
        },
        ...
    }
    """
    
    # =========================================
    # Review
    # =========================================
    reviewed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='submissions_reviewed'
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True
    )
    feedback = models.TextField(
        blank=True,
        max_length=5000,
        help_text="Reviewer feedback to attendee"
    )
    internal_notes = models.TextField(
        blank=True,
        max_length=2000,
        help_text="Internal notes (not visible to attendee)"
    )
    
    # =========================================
    # Resubmission
    # =========================================
    version = models.PositiveIntegerField(
        default=1,
        help_text="Submission version number"
    )
    previous_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resubmissions',
        help_text="Previous version (for resubmissions)"
    )
    
    class Meta:
        db_table = 'assignment_submissions'
        unique_together = [['assignment', 'registration', 'version']]
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['assignment', 'status']),
            models.Index(fields=['registration']),
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['reviewed_by', '-submitted_at']),
        ]
        verbose_name = 'Assignment Submission'
        verbose_name_plural = 'Assignment Submissions'
    
    def __str__(self):
        return f"{self.registration.full_name} - {self.assignment.title}"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def is_graded(self):
        return self.status in [self.Status.APPROVED, self.Status.REJECTED]
    
    @property
    def can_edit(self):
        """Check if submission can be edited."""
        return self.status in [
            self.Status.DRAFT, 
            self.Status.REVISION_REQUESTED
        ]
    
    @property
    def can_submit(self):
        """Check if submission can be submitted."""
        if not self.can_edit:
            return False
        if self.assignment.is_closed:
            return False
        return True
    
    @property
    def word_count(self):
        """Count words in text submission."""
        if not self.text_content:
            return 0
        return len(self.text_content.split())
    
    # =========================================
    # Methods
    # =========================================
    def submit(self):
        """Submit the assignment."""
        if not self.can_submit:
            raise ValueError("Cannot submit at this time")
        
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        
        # Check if late
        if self.assignment.due_at and self.submitted_at > self.assignment.due_at:
            self.is_late = True
        
        self.save(update_fields=[
            'status', 'submitted_at', 'is_late', 'updated_at'
        ])
        
        self.assignment.update_counts()
    
    def start_review(self, reviewer):
        """Mark submission as under review."""
        if self.status != self.Status.SUBMITTED:
            raise ValueError("Can only review submitted work")
        
        self.status = self.Status.UNDER_REVIEW
        self.reviewed_by = reviewer
        self.save(update_fields=['status', 'reviewed_by', 'updated_at'])
    
    def request_revision(self, reviewer, feedback):
        """Request revision from attendee."""
        self.status = self.Status.REVISION_REQUESTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.feedback = feedback
        self.save(update_fields=[
            'status', 'reviewed_by', 'reviewed_at', 'feedback', 'updated_at'
        ])
        
        # Create history record
        SubmissionReview.objects.create(
            submission=self,
            reviewer=reviewer,
            action='revision_requested',
            feedback=feedback
        )
    
    def approve(self, reviewer, score=None, feedback='', rubric_scores=None):
        """Approve the submission."""
        self._complete_review(
            reviewer=reviewer,
            passed=True,
            score=score,
            feedback=feedback,
            rubric_scores=rubric_scores
        )
    
    def reject(self, reviewer, score=None, feedback='', rubric_scores=None):
        """Reject the submission."""
        self._complete_review(
            reviewer=reviewer,
            passed=False,
            score=score,
            feedback=feedback,
            rubric_scores=rubric_scores
        )
    
    def _complete_review(self, reviewer, passed, score=None, feedback='', 
                         rubric_scores=None):
        """Complete the review process."""
        self.status = self.Status.APPROVED if passed else self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.passed = passed
        self.feedback = feedback
        
        if rubric_scores:
            self.rubric_scores = rubric_scores
        
        # Calculate score
        if score is not None:
            self.score_before_penalty = score
            
            # Apply late penalty
            if self.is_late and self.assignment.late_penalty_percent > 0:
                penalty = score * (self.assignment.late_penalty_percent / 100)
                self.score = max(0, score - penalty)
            else:
                self.score = score
        
        self.save()
        
        self.assignment.update_counts()
        
        # Create history record
        SubmissionReview.objects.create(
            submission=self,
            reviewer=reviewer,
            action='approved' if passed else 'rejected',
            score=self.score,
            feedback=feedback
        )
        
        # Update registration progress
        self.registration.update_assignment_progress()
    
    def create_resubmission(self):
        """
        Create a new version for resubmission.
        
        Returns:
            New AssignmentSubmission instance
        """
        if self.status != self.Status.REVISION_REQUESTED:
            raise ValueError("Can only resubmit after revision requested")
        
        new_submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            registration=self.registration,
            text_content=self.text_content,
            files=self.files.copy() if self.files else [],
            link_url=self.link_url,
            link_title=self.link_title,
            version=self.version + 1,
            previous_version=self
        )
        
        return new_submission
```

---

### SubmissionReview

History of reviews on a submission.

```python
class SubmissionReview(BaseModel):
    """
    Record of a review action on a submission.
    
    Maintains history of all review actions for audit trail.
    """
    
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )
    
    action = models.CharField(
        max_length=30,
        help_text="Review action taken"
    )  # submitted, revision_requested, approved, rejected
    
    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True, blank=True
    )
    feedback = models.TextField(
        blank=True
    )
    rubric_scores = models.JSONField(
        default=dict,
        blank=True
    )
    
    class Meta:
        db_table = 'submission_reviews'
        ordering = ['-created_at']
        verbose_name = 'Submission Review'
        verbose_name_plural = 'Submission Reviews'
    
    def __str__(self):
        return f"{self.submission} - {self.action}"
```

---

### ContentProgress

Track progress through individual content items.

```python
class ContentProgress(BaseModel):
    """
    Tracks a registration's progress through a content item.
    """
    
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
    
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
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )
    
    # Engagement tracking
    first_accessed_at = models.DateTimeField(
        null=True, blank=True
    )
    last_accessed_at = models.DateTimeField(
        null=True, blank=True
    )
    completed_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Time tracking
    total_time_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Total time spent on content"
    )
    
    # For video content
    video_progress_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Furthest point reached in video"
    )
    video_completed = models.BooleanField(
        default=False
    )
    
    class Meta:
        db_table = 'content_progress'
        unique_together = [['registration', 'content']]
        indexes = [
            models.Index(fields=['registration', 'status']),
            models.Index(fields=['content']),
        ]
        verbose_name = 'Content Progress'
        verbose_name_plural = 'Content Progress Records'
    
    def __str__(self):
        return f"{self.registration.full_name} - {self.content.title}"
    
    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED
    
    def record_access(self):
        """Record content was accessed."""
        now = timezone.now()
        
        if not self.first_accessed_at:
            self.first_accessed_at = now
        self.last_accessed_at = now
        
        if self.status == self.Status.NOT_STARTED:
            self.status = self.Status.IN_PROGRESS
        
        self.save(update_fields=[
            'first_accessed_at', 'last_accessed_at', 'status', 'updated_at'
        ])
    
    def record_time(self, seconds):
        """Add time spent on content."""
        from django.db.models import F
        ContentProgress.objects.filter(pk=self.pk).update(
            total_time_seconds=F('total_time_seconds') + seconds
        )
    
    def update_video_progress(self, seconds):
        """Update video progress position."""
        if seconds > self.video_progress_seconds:
            self.video_progress_seconds = seconds
            
            # Check if video completed (within 10 seconds of end)
            if self.content.video_duration_seconds > 0:
                if seconds >= (self.content.video_duration_seconds - 10):
                    self.video_completed = True
            
            self.save(update_fields=[
                'video_progress_seconds', 'video_completed', 'updated_at'
            ])
    
    def mark_completed(self):
        """Mark content as completed."""
        if self.status != self.Status.COMPLETED:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at', 'updated_at'])
            
            # Update module progress
            ModuleProgress.update_for_registration(
                self.registration, 
                self.content.module
            )
```

---

### ModuleProgress

Aggregate progress for a module.

```python
class ModuleProgress(BaseModel):
    """
    Tracks a registration's aggregate progress through a module.
    """
    
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
    
    # Progress tracking
    contents_completed = models.PositiveIntegerField(
        default=0
    )
    contents_total = models.PositiveIntegerField(
        default=0
    )
    completion_percent = models.PositiveIntegerField(
        default=0
    )
    
    # Status
    is_started = models.BooleanField(
        default=False
    )
    is_completed = models.BooleanField(
        default=False
    )
    
    # Timing
    started_at = models.DateTimeField(
        null=True, blank=True
    )
    completed_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Time spent
    total_time_seconds = models.PositiveIntegerField(
        default=0
    )
    
    class Meta:
        db_table = 'module_progress'
        unique_together = [['registration', 'module']]
        indexes = [
            models.Index(fields=['registration', 'is_completed']),
            models.Index(fields=['module']),
        ]
        verbose_name = 'Module Progress'
        verbose_name_plural = 'Module Progress Records'
    
    def __str__(self):
        return f"{self.registration.full_name} - {self.module.title}"
    
    @classmethod
    def update_for_registration(cls, registration, module):
        """
        Update module progress after content progress changes.
        
        Called automatically when ContentProgress is updated.
        """
        # Get or create progress record
        progress, created = cls.objects.get_or_create(
            registration=registration,
            module=module,
            defaults={'contents_total': module.contents.filter(is_required=True).count()}
        )
        
        # Count completed required content
        completed = ContentProgress.objects.filter(
            registration=registration,
            content__module=module,
            content__is_required=True,
            status=ContentProgress.Status.COMPLETED
        ).count()
        
        total = module.contents.filter(is_required=True).count()
        
        progress.contents_completed = completed
        progress.contents_total = total
        progress.completion_percent = int((completed / total * 100)) if total > 0 else 100
        
        # Update status
        if not progress.is_started and completed > 0:
            progress.is_started = True
            progress.started_at = timezone.now()
        
        if completed >= total and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
        
        # Sum time from content progress
        progress.total_time_seconds = ContentProgress.objects.filter(
            registration=registration,
            content__module=module
        ).aggregate(total=models.Sum('total_time_seconds'))['total'] or 0
        
        progress.save()
        
        return progress
```

---

## Registration Extensions

Add these fields and methods to the Registration model:

```python
# In registrations/models.py - Add to Registration model

# =========================================
# Learning Progress (denormalized)
# =========================================
modules_completed = models.PositiveIntegerField(
    default=0
)
modules_total = models.PositiveIntegerField(
    default=0
)
content_completion_percent = models.PositiveIntegerField(
    default=0
)
assignments_submitted = models.PositiveIntegerField(
    default=0
)
assignments_passed = models.PositiveIntegerField(
    default=0
)
assignments_total = models.PositiveIntegerField(
    default=0
)
overall_score = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    null=True, blank=True,
    help_text="Weighted average of all assignment scores"
)

# =========================================
# Properties
# =========================================
@property
def all_modules_completed(self):
    """Check if all required modules are completed."""
    if not self.event.modules_enabled:
        return True
    required = self.event.modules.filter(is_required=True).count()
    completed = self.module_progress.filter(is_completed=True).count()
    return completed >= required

@property
def all_required_assignments_passed(self):
    """Check if all required assignments are passed."""
    if not self.event.assignments_enabled:
        return True
    required = self.event.assignments.filter(is_required=True).count()
    passed = self.assignment_submissions.filter(
        assignment__is_required=True,
        passed=True
    ).count()
    return passed >= required

# =========================================
# Methods
# =========================================
def update_learning_progress(self):
    """Update all learning-related progress fields."""
    self.update_module_progress()
    self.update_assignment_progress()

def update_module_progress(self):
    """Recalculate module progress."""
    from learning.models import ModuleProgress
    
    if not self.event.modules_enabled:
        return
    
    total = self.event.modules.filter(is_required=True).count()
    completed = self.module_progress.filter(
        module__is_required=True,
        is_completed=True
    ).count()
    
    # Calculate overall content completion
    all_progress = self.module_progress.all()
    if all_progress.exists():
        avg_completion = all_progress.aggregate(
            avg=models.Avg('completion_percent')
        )['avg'] or 0
    else:
        avg_completion = 0
    
    self.modules_total = total
    self.modules_completed = completed
    self.content_completion_percent = int(avg_completion)
    self.save(update_fields=[
        'modules_total', 'modules_completed', 
        'content_completion_percent', 'updated_at'
    ])

def update_assignment_progress(self):
    """Recalculate assignment progress."""
    from learning.models import AssignmentSubmission
    
    if not self.event.assignments_enabled:
        return
    
    total = self.event.assignments.filter(is_required=True).count()
    
    submissions = self.assignment_submissions.filter(
        assignment__is_required=True,
        status__in=[
            AssignmentSubmission.Status.APPROVED,
            AssignmentSubmission.Status.REJECTED
        ]
    )
    
    submitted = submissions.count()
    passed = submissions.filter(passed=True).count()
    
    # Calculate weighted average score
    graded = self.assignment_submissions.filter(
        score__isnull=False
    ).select_related('assignment')
    
    if graded.exists():
        total_weight = sum(s.assignment.weight for s in graded)
        if total_weight > 0:
            weighted_sum = sum(
                float(s.score) * float(s.assignment.weight) 
                for s in graded
            )
            self.overall_score = weighted_sum / float(total_weight)
    
    self.assignments_total = total
    self.assignments_submitted = submitted
    self.assignments_passed = passed
    self.save(update_fields=[
        'assignments_total', 'assignments_submitted',
        'assignments_passed', 'overall_score', 'updated_at'
    ])
```

---

## Relationships

```
EventModule
├── Event (N:1, CASCADE)
├── EventModule (N:1, SET_NULL) — prerequisite
├── ModuleContent (1:N, CASCADE)
├── Assignment (1:N, CASCADE)
└── ModuleProgress (1:N, CASCADE)

ModuleContent
├── EventModule (N:1, CASCADE)
├── ZoomRecording (N:1, SET_NULL) — for recording content type
└── ContentProgress (1:N, CASCADE)

Assignment
├── Event (N:1, CASCADE)
├── EventModule (N:1, CASCADE, nullable)
└── AssignmentSubmission (1:N, CASCADE)

AssignmentSubmission
├── Assignment (N:1, CASCADE)
├── Registration (N:1, CASCADE)
├── User (N:1, SET_NULL) — reviewed_by
├── AssignmentSubmission (N:1, SET_NULL) — previous_version
└── SubmissionReview (1:N, CASCADE)

ContentProgress
├── Registration (N:1, CASCADE)
└── ModuleContent (N:1, CASCADE)

ModuleProgress
├── Registration (N:1, CASCADE)
└── EventModule (N:1, CASCADE)
```

---

## Recording Integration

When `content_type='recording'`, the content links to a ZoomRecording. Progress tracking syncs between RecordingView and ContentProgress:

```python
# Sync recording view to content progress (called from RecordingView.update_progress)
def sync_recording_to_content_progress(recording_view):
    """
    Keep ContentProgress in sync with RecordingView for LMS tracking.
    """
    contents = ModuleContent.objects.filter(
        zoom_recording=recording_view.recording
    )
    
    for content in contents:
        progress, _ = ContentProgress.objects.get_or_create(
            registration=recording_view.registration,
            content=content
        )
        
        progress.total_time_seconds = recording_view.total_watch_seconds
        progress.video_progress_seconds = recording_view.max_position_seconds
        
        if recording_view.completed and not progress.is_completed:
            progress.mark_completed()
        elif recording_view.total_watch_seconds > 0:
            progress.status = ContentProgress.Status.IN_PROGRESS
            progress.save()
```

---

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| event_modules | event_id, order | Ordered modules list |
| event_modules | event_id, is_published | Published modules |
| event_modules | release_at | Scheduled release queries |
| module_contents | module_id, order | Ordered content list |
| assignments | event_id, order | Event assignments list |
| assignments | module_id, order | Module assignments |
| assignments | due_at | Due date queries |
| assignment_submissions | assignment_id, status | Status filtering |
| assignment_submissions | registration_id | User's submissions |
| assignment_submissions | reviewed_by, -submitted_at | Reviewer queue |
| content_progress | registration_id, status | User progress |
| module_progress | registration_id, is_completed | Completion tracking |

---

## Business Rules

1. **Module Release**: Controlled by release_type and conditions
2. **Prerequisites**: Module not available until prerequisite completed
3. **Content Completion**: Required content must be completed for module completion
4. **Video Completion**: Must watch to within 10 seconds of end
5. **Assignment Deadlines**: Late submissions allowed with penalty (configurable)
6. **Resubmission**: Only after revision requested, creates new version
7. **Certificate Eligibility**: Can require modules + assignments
8. **Scoring**: Weighted average of all graded assignments

---

## API Endpoints (Suggested)

```
# Modules
GET    /api/events/{uuid}/modules/                  # List modules
GET    /api/modules/{uuid}/                         # Module detail with contents

# Content
GET    /api/contents/{uuid}/                        # Content detail
POST   /api/contents/{uuid}/progress/               # Record progress/completion

# Assignments
GET    /api/events/{uuid}/assignments/              # List assignments
GET    /api/assignments/{uuid}/                     # Assignment detail
POST   /api/assignments/{uuid}/submissions/         # Create submission
GET    /api/submissions/{uuid}/                     # Submission detail
PUT    /api/submissions/{uuid}/                     # Update draft
POST   /api/submissions/{uuid}/submit/              # Submit for review

# Review (Organizer)
GET    /api/events/{uuid}/submissions/pending/      # Pending review queue
POST   /api/submissions/{uuid}/start-review/        # Claim for review
POST   /api/submissions/{uuid}/request-revision/    # Request changes
POST   /api/submissions/{uuid}/approve/             # Approve
POST   /api/submissions/{uuid}/reject/              # Reject

# Progress
GET    /api/registrations/{uuid}/progress/          # Overall progress
GET    /api/registrations/{uuid}/modules/{uuid}/    # Module progress
```

---

## Certificate Data Extension

When LMS features are enabled, add to certificate_data snapshot:

```python
# In certificates/models.py - extend build_certificate_data()

if event.modules_enabled:
    self.certificate_data['modules_completed'] = reg.modules_completed
    self.certificate_data['content_completion_percent'] = reg.content_completion_percent

if event.assignments_enabled:
    self.certificate_data['assignments_passed'] = reg.assignments_passed
    self.certificate_data['overall_score'] = str(reg.overall_score) if reg.overall_score else None
```

---

## Plan Limits Extension

Add to subscription limits:

```python
# In billing/models.py - extend PLAN_LIMITS

PLAN_LIMITS = {
    'starter': {
        # ... existing limits ...
        'modules_per_event': 5,
        'assignments_per_event': 3,
        'content_storage_gb': 5,
    },
    'professional': {
        # ... existing limits ...
        'modules_per_event': 20,
        'assignments_per_event': 20,
        'content_storage_gb': 50,
    },
    'enterprise': {
        # ... existing limits ...
        'modules_per_event': None,  # Unlimited
        'assignments_per_event': None,
        'content_storage_gb': None,
    },
}
```
