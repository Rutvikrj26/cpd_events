"""
Serializers for learning API.
"""

from rest_framework import serializers

from .models import (
    Assignment,
    AssignmentSubmission,
    ContentProgress,
    Course,
    CourseAnnouncement,
    CourseEnrollment,
    CourseModule,
    CourseSession,
    CourseSessionAttendance,
    EventModule,
    ModuleContent,
    ModuleProgress,
    SubmissionReview,
)


class ModuleContentSerializer(serializers.ModelSerializer):
    """Full content details."""

    content_type_display = serializers.CharField(source='get_content_type_display', read_only=True)

    class Meta:
        model = ModuleContent
        fields = [
            'uuid',
            'title',
            'description',
            'content_type',
            'content_type_display',
            'order',
            'duration_minutes',
            'content_data',
            'is_required',
            'is_published',
            'file',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class ModuleContentCreateSerializer(serializers.ModelSerializer):
    """Create/update content."""

    class Meta:
        model = ModuleContent
        fields = [
            'title',
            'description',
            'content_type',
            'order',
            'duration_minutes',
            'content_data',
            'file',
            'is_published',
            'module',
        ]
        read_only_fields = ['module']
        # We manually handle uniqueness in create/update to avoid DRF implicit lookup errors
        # triggered by unique_together when module is read-only or inferred
        validators = []


class AssignmentSerializer(serializers.ModelSerializer):
    """Full assignment details."""

    submission_type_display = serializers.CharField(source='get_submission_type_display', read_only=True)
    passing_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'uuid',
            'title',
            'description',
            'instructions',
            'due_days_after_release',
            'max_score',
            'passing_score',
            'passing_percentage',
            'allow_resubmission',
            'max_attempts',
            'submission_type',
            'submission_type_display',
            'rubric',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class AssignmentCreateSerializer(serializers.ModelSerializer):
    """Create/update assignment."""

    class Meta:
        model = Assignment
        fields = [
            'title',
            'description',
            'instructions',
            'due_days_after_release',
            'max_score',
            'passing_score',
            'allow_resubmission',
            'max_attempts',
            'submission_type',
            'rubric',
        ]


class EventModuleSerializer(serializers.ModelSerializer):
    """Full module details with contents."""

    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True)
    contents = ModuleContentSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)
    content_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()

    class Meta:
        model = EventModule
        fields = [
            'uuid',
            'title',
            'description',
            'order',
            'release_type',
            'release_type_display',
            'release_at',
            'release_days_after_registration',
            'prerequisite_module',
            'passing_score',
            'cpd_credits',
            'cpd_type',
            'is_published',
            'content_count',
            'assignment_count',
            'contents',
            'assignments',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def get_content_count(self, obj):
        return obj.contents.count()

    def get_assignment_count(self, obj):
        return obj.assignments.count()


class EventModuleListSerializer(serializers.ModelSerializer):
    """Module list view - without nested items."""

    release_type_display = serializers.CharField(source='get_release_type_display', read_only=True)
    content_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()

    class Meta:
        model = EventModule
        fields = [
            'uuid',
            'title',
            'description',
            'order',
            'release_type',
            'release_type_display',
            'is_published',
            'content_count',
            'assignment_count',
            'cpd_credits',
        ]

    def get_content_count(self, obj):
        return obj.contents.count()

    def get_assignment_count(self, obj):
        return obj.assignments.count()


class EventModuleCreateSerializer(serializers.ModelSerializer):
    """Create/update module."""

    class Meta:
        model = EventModule
        fields = [
            'title',
            'description',
            'order',
            'release_type',
            'release_at',
            'release_days_after_registration',
            'prerequisite_module',
            'passing_score',
            'cpd_credits',
            'cpd_type',
            'is_published',
        ]


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """Full submission details."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_passing = serializers.BooleanField(read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            'uuid',
            'assignment',
            'assignment_title',
            'status',
            'status_display',
            'attempt_number',
            'submitted_at',
            'content',
            'file_url',
            'score',
            'feedback',
            'graded_at',
            'is_passing',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'attempt_number',
            'submitted_at',
            'score',
            'feedback',
            'graded_at',
            'created_at',
            'updated_at',
        ]


class AssignmentSubmissionStaffSerializer(serializers.ModelSerializer):
    """Submission details for course staff."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    user_email = serializers.EmailField(source='course_enrollment.user.email', read_only=True)
    user_name = serializers.CharField(source='course_enrollment.user.full_name', read_only=True)
    user_uuid = serializers.UUIDField(source='course_enrollment.user.uuid', read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            'uuid',
            'assignment',
            'assignment_title',
            'status',
            'status_display',
            'attempt_number',
            'submitted_at',
            'content',
            'file_url',
            'score',
            'feedback',
            'graded_at',
            'user_uuid',
            'user_email',
            'user_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class AssignmentSubmissionCreateSerializer(serializers.ModelSerializer):
    """Submit assignment."""

    class Meta:
        model = AssignmentSubmission
        fields = ['content', 'file_url']


class SubmissionGradeSerializer(serializers.Serializer):
    """Grade a submission."""

    score = serializers.IntegerField(min_value=0)
    feedback = serializers.CharField(required=False, allow_blank=True)
    rubric_scores = serializers.DictField(required=False)
    action = serializers.ChoiceField(choices=['grade', 'return', 'approve'], default='grade')


class SubmissionReviewSerializer(serializers.ModelSerializer):
    """Submission review history."""

    action_display = serializers.CharField(source='get_action_display', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.display_name', read_only=True)

    class Meta:
        model = SubmissionReview
        fields = [
            'uuid',
            'action',
            'action_display',
            'from_status',
            'to_status',
            'score',
            'feedback',
            'rubric_scores',
            'reviewer_name',
            'created_at',
        ]


class ContentProgressSerializer(serializers.ModelSerializer):
    """Content progress tracking."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    content_title = serializers.CharField(source='content.title', read_only=True)

    class Meta:
        model = ContentProgress
        fields = [
            'uuid',
            'content',
            'content_title',
            'status',
            'status_display',
            'started_at',
            'completed_at',
            'progress_percent',
            'time_spent_seconds',
            'last_position',
        ]
        read_only_fields = ['uuid', 'started_at', 'completed_at']


class ContentProgressUpdateSerializer(serializers.Serializer):
    """Update content progress."""

    progress_percent = serializers.IntegerField(min_value=0, max_value=100)
    time_spent = serializers.IntegerField(min_value=0, required=False, default=0)
    position = serializers.DictField(required=False)
    completed = serializers.BooleanField(required=False, default=False)


class ModuleProgressSerializer(serializers.ModelSerializer):
    """Module progress tracking."""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    module_title = serializers.CharField(source='module.title', read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = ModuleProgress
        fields = [
            'uuid',
            'module',
            'module_title',
            'status',
            'status_display',
            'started_at',
            'completed_at',
            'contents_completed',
            'contents_total',
            'progress_percent',
            'score',
            'attempts',
        ]
        read_only_fields = fields


class AttendeeLearningDashboardSerializer(serializers.Serializer):
    """Dashboard view for attendee's learning progress."""

    event_uuid = serializers.UUIDField()
    event_title = serializers.CharField()
    modules_total = serializers.IntegerField()
    modules_completed = serializers.IntegerField()
    overall_progress = serializers.IntegerField()
    assignments_pending = serializers.IntegerField()
    cpd_credits_earned = serializers.DecimalField(max_digits=5, decimal_places=2)
    modules = ModuleProgressSerializer(many=True)


class CourseModuleSerializer(serializers.ModelSerializer):
    """Course module link with nested module details."""

    module = EventModuleSerializer(read_only=True)

    class Meta:
        model = CourseModule
        fields = ['uuid', 'module', 'order', 'is_required', 'created_at', 'updated_at']


class CourseSerializer(serializers.ModelSerializer):
    """Full course details."""

    modules = CourseModuleSerializer(many=True, read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_slug = serializers.CharField(source='organization.slug', read_only=True)
    organization_logo_url = serializers.CharField(source='organization.effective_logo_url', read_only=True)

    class Meta:
        model = Course
        fields = [
            'uuid',
            'organization',
            'organization_name',
            'organization_slug',
            'organization_logo_url',
            'title',
            'slug',
            'description',
            'short_description',
            'featured_image',
            'featured_image_url',
            'cpd_credits',
            'cpd_type',
            'status',
            'is_public',
            'is_free',
            'price_cents',
            'currency',
            # Stripe integration
            'stripe_product_id',
            'stripe_price_id',
            # Format & Virtual settings
            'format',
            'zoom_meeting_id',
            'zoom_meeting_uuid',
            'zoom_meeting_url',
            'zoom_start_url',
            'zoom_meeting_password',
            'zoom_webinar_id',
            'zoom_registrant_id',
            'zoom_settings',
            'zoom_error',
            'zoom_error_at',
            'live_session_start',
            'live_session_end',
            'live_session_timezone',
            # Enrollment settings
            'enrollment_open',
            'max_enrollments',
            'enrollment_requires_approval',
            'estimated_hours',
            'passing_score',
            'hybrid_completion_criteria',
            'min_sessions_required',
            'certificates_enabled',
            'certificate_template',
            'auto_issue_certificates',
            # Badge settings
            'badges_enabled',
            'badge_template',
            'auto_issue_badges',
            # Stats
            'enrollment_count',
            'completion_count',
            'module_count',
            'modules',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'organization',
            'enrollment_count',
            'completion_count',
            'module_count',
            'created_at',
            'updated_at',
        ]


class CourseListSerializer(serializers.ModelSerializer):
    """List view for courses."""

    organization_name = serializers.CharField(source='organization.name', read_only=True)
    organization_slug = serializers.CharField(source='organization.slug', read_only=True)
    organization_logo_url = serializers.CharField(source='organization.effective_logo_url', read_only=True)

    class Meta:
        model = Course
        fields = [
            'uuid',
            'organization',
            'organization_name',
            'organization_slug',
            'organization_logo_url',
            'title',
            'slug',
            'short_description',
            'featured_image',
            'featured_image_url',
            'cpd_credits',
            'cpd_type',
            'status',
            'is_public',
            'is_free',
            'price_cents',
            'currency',
            'format',
            'enrollment_count',
            'module_count',
            'estimated_hours',
            'created_at',
        ]


def _validate_certificate_settings(attrs, instance=None):
    certificates_enabled = attrs.get('certificates_enabled')
    certificate_template = attrs.get('certificate_template')

    if instance is not None:
        if certificates_enabled is None:
            certificates_enabled = instance.certificates_enabled
        if certificate_template is None:
            certificate_template = instance.certificate_template

    if certificates_enabled and not certificate_template:
        raise serializers.ValidationError(
            {'certificate_template': 'Select a certificate template when certificates are enabled.'}
        )

    return attrs


def _validate_badge_settings(attrs, instance=None):
    badges_enabled = attrs.get('badges_enabled')
    badge_template = attrs.get('badge_template')

    if instance is not None:
        if badges_enabled is None:
            badges_enabled = instance.badges_enabled
        if badge_template is None:
            badge_template = instance.badge_template

    if badges_enabled and not badge_template:
        raise serializers.ValidationError(
            {'badge_template': 'Select a badge template when badges are enabled.'}
        )

    return attrs


class CourseCreateSerializer(serializers.ModelSerializer):
    """Create/update course."""

    class Meta:
        model = Course
        fields = [
            'uuid',
            'title',
            'slug',
            'description',
            'short_description',
            'featured_image',
            'featured_image_url',
            'cpd_credits',
            'cpd_type',
            'status',
            'is_public',
            'price_cents',
            'currency',
            # Format & Virtual settings
            'format',
            'zoom_settings',
            'live_session_start',
            'live_session_end',
            'live_session_timezone',

            # Other settings
            'enrollment_open',
            'max_enrollments',
            'estimated_hours',
            'passing_score',
            'hybrid_completion_criteria',
            'min_sessions_required',
            'certificates_enabled',
            'certificate_template',
            'auto_issue_certificates',
            # Badge settings
            'badges_enabled',
            'badge_template',
            'auto_issue_badges',
        ]

    def validate(self, attrs):
        attrs = _validate_certificate_settings(attrs, self.instance)
        attrs = _validate_badge_settings(attrs, self.instance)
        return attrs


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """Enrollment details."""

    course = CourseListSerializer(read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = [
            'uuid',
            'course',
            'status',
            'enrolled_at',
            'started_at',
            'completed_at',
            'progress_percent',
            'modules_completed',
            'current_score',
            'certificate_issued',
            'certificate_issued_at',
        ]
        read_only_fields = fields


class CourseEnrollmentRosterSerializer(serializers.ModelSerializer):
    """Enrollment details for course staff roster views."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_uuid = serializers.UUIDField(source='user.uuid', read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = [
            'uuid',
            'user_uuid',
            'user_email',
            'user_name',
            'status',
            'enrolled_at',
            'started_at',
            'completed_at',
            'progress_percent',
            'modules_completed',
            'certificate_issued',
            'certificate_issued_at',
        ]
        read_only_fields = fields


class CourseAnnouncementSerializer(serializers.ModelSerializer):
    """Course announcement details."""

    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = CourseAnnouncement
        fields = [
            'uuid',
            'title',
            'body',
            'is_published',
            'created_by',
            'created_by_name',
            'created_by_email',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'created_by', 'created_at', 'updated_at']


# =============================================================================
# Course Session Serializers
# =============================================================================


class CourseSessionSerializer(serializers.ModelSerializer):
    """Full session details."""

    session_type_display = serializers.CharField(source='get_session_type_display', read_only=True)
    ends_at = serializers.DateTimeField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_live = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)

    class Meta:
        model = CourseSession
        fields = [
            'uuid',
            'title',
            'description',
            'order',
            'session_type',
            'session_type_display',
            'starts_at',
            'ends_at',
            'duration_minutes',
            'timezone',
            'zoom_meeting_id',
            'zoom_join_url',
            'zoom_start_url',
            'zoom_password',
            'zoom_settings',
            'zoom_error',
            'cpd_credits',
            'is_mandatory',
            'minimum_attendance_percent',
            'is_published',
            'is_upcoming',
            'is_live',
            'is_past',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'zoom_meeting_id',
            'zoom_join_url',
            'zoom_start_url',
            'zoom_password',
            'zoom_error',
            'created_at',
            'updated_at',
        ]


class CourseSessionListSerializer(serializers.ModelSerializer):
    """Brief session info for lists."""

    session_type_display = serializers.CharField(source='get_session_type_display', read_only=True)
    ends_at = serializers.DateTimeField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_live = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)

    class Meta:
        model = CourseSession
        fields = [
            'uuid',
            'title',
            'order',
            'session_type',
            'session_type_display',
            'starts_at',
            'ends_at',
            'duration_minutes',
            'zoom_join_url',
            'cpd_credits',
            'is_mandatory',
            'is_published',
            'is_upcoming',
            'is_live',
            'is_past',
            'zoom_meeting_id',
            'zoom_password',
        ]


class CourseSessionCreateSerializer(serializers.ModelSerializer):
    """Create/update session."""

    class Meta:
        model = CourseSession
        fields = [
            'title',
            'description',
            'order',
            'session_type',
            'starts_at',
            'duration_minutes',
            'timezone',
            'zoom_settings',
            'zoom_meeting_id',
            'zoom_password',
            'cpd_credits',
            'is_mandatory',
            'minimum_attendance_percent',
            'is_published',
        ]


class CourseSessionAttendanceSerializer(serializers.ModelSerializer):
    """Session attendance record."""

    user_email = serializers.EmailField(source='enrollment.user.email', read_only=True)
    user_name = serializers.CharField(source='enrollment.user.full_name', read_only=True)
    session_title = serializers.CharField(source='session.title', read_only=True)
    attendance_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = CourseSessionAttendance
        fields = [
            'uuid',
            'session',
            'session_title',
            'enrollment',
            'user_email',
            'user_name',
            'attendance_minutes',
            'attendance_percent',
            'is_eligible',
            'zoom_user_email',
            'zoom_join_time',
            'zoom_leave_time',
            'is_manual_override',
            'override_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'session',
            'enrollment',
            'zoom_user_email',
            'zoom_join_time',
            'zoom_leave_time',
            'created_at',
            'updated_at',
        ]
class UnmatchedParticipantSerializer(serializers.Serializer):
    """Zoom participant not matched to any enrollment."""
    user_id = serializers.CharField(required=False, allow_null=True)
    user_name = serializers.CharField()
    user_email = serializers.EmailField(required=False, allow_null=True)
    join_time = serializers.DateTimeField()
    leave_time = serializers.DateTimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField()


class MatchParticipantSerializer(serializers.Serializer):
    """Manual matching of participant to enrollment."""
    enrollment_uuid = serializers.UUIDField()
    participants = UnmatchedParticipantSerializer(many=True, required=False)
    # Alternatively accept just one
    zoom_user_email = serializers.EmailField(required=False)
    zoom_user_name = serializers.CharField(required=False)
    zoom_join_time = serializers.DateTimeField(required=False)
    zoom_leave_time = serializers.DateTimeField(required=False)
    attendance_minutes = serializers.IntegerField(required=False)
