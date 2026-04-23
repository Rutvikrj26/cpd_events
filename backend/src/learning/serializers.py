"""
Serializers for learning API.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from badges.models import BadgeTemplate
from certificates.models import CertificateTemplate

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
    DiscussionFlag,
    DiscussionReply,
    DiscussionThread,
    EventModule,
    Program,
    ProgramCourse,
    ProgramEnrollment,
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
    assignment = serializers.UUIDField(source='assignment.uuid', read_only=True)

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
    content = serializers.UUIDField(source='content.uuid', read_only=True)

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
    user_role = serializers.SerializerMethodField()
    programs = serializers.SerializerMethodField()

    def get_programs(self, obj):
        """Public-visible programs that include this course."""
        published_programs = obj.programs.filter(
            status=Program.Status.PUBLISHED, is_public=True,
        ).only('uuid', 'title', 'slug', 'short_description', 'price_cents', 'currency')
        return [
            {
                'uuid': str(p.uuid),
                'title': p.title,
                'slug': p.slug,
                'short_description': p.short_description,
                'price_cents': p.price_cents,
                'currency': p.currency,
            }
            for p in published_programs
        ]
    certificate_template = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=CertificateTemplate.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        allow_null=True,
    )
    badge_template = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=BadgeTemplate.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        allow_null=True,
    )

    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_staff_role(request.user)
        return None

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
            'is_free',
            'price_cents',
            'currency',
            # Stripe integration
            'stripe_product_id',
            'stripe_price_id',
            # Format & Virtual settings
            'format',
            'live_session_start',
            'live_session_end',
            'live_session_timezone',
            # Enrollment settings
            'enrollment_open',
            'max_enrollments',
            'enrollment_requires_approval',
            'enrollment_opens_at',
            'enrollment_closes_at',
            'enrollment_window_state',
            'is_enrollable',
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
            'user_role',
            'programs',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'enrollment_count',
            'completion_count',
            'module_count',
            'programs',
            'created_at',
            'updated_at',
        ]


class CourseListSerializer(serializers.ModelSerializer):
    """List view for courses."""

    user_role = serializers.SerializerMethodField()

    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_staff_role(request.user)
        return None

    class Meta:
        model = Course
        fields = [
            'uuid',
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
            'user_role',
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

    certificate_template = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=CertificateTemplate.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        allow_null=True,
    )
    badge_template = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=BadgeTemplate.objects.filter(deleted_at__isnull=True, is_active=True),
        required=False,
        allow_null=True,
    )

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
            'video_settings',
            'live_session_start',
            'live_session_end',
            'live_session_timezone',

            # Other settings
            'enrollment_open',
            'max_enrollments',
            'enrollment_opens_at',
            'enrollment_closes_at',
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
        attrs = _apply_format_defaults(attrs, self.instance)
        attrs = _validate_publish_transition(attrs, self.instance)
        return attrs


def _apply_format_defaults(attrs, instance=None):
    """Set sensible default completion criteria per format on create."""
    if instance is not None:
        return attrs
    fmt = attrs.get('format', Course.CourseFormat.ONLINE)
    if 'hybrid_completion_criteria' in attrs:
        return attrs
    if fmt == Course.CourseFormat.ONLINE:
        attrs['hybrid_completion_criteria'] = Course.HybridCompletionCriteria.MODULES_ONLY
    elif fmt == Course.CourseFormat.LIVE:
        attrs['hybrid_completion_criteria'] = Course.HybridCompletionCriteria.SESSIONS_ONLY
    return attrs


def _validate_publish_transition(attrs, instance=None):
    """If transitioning to PUBLISHED, enforce structural validation."""
    new_status = attrs.get('status')
    if new_status != Course.Status.PUBLISHED:
        return attrs
    if instance is None:
        # Cannot evaluate sessions/modules on a yet-to-be-created course.
        # Force draft on initial create; explicit publish goes through CourseViewSet.publish action.
        attrs['status'] = Course.Status.DRAFT
        return attrs
    if instance.status == Course.Status.PUBLISHED:
        return attrs
    # Apply pending changes before validation
    fmt = attrs.get('format', instance.format)
    instance.format = fmt
    try:
        instance.validate_for_publish()
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages})
    return attrs


class CourseStaffSerializer(serializers.ModelSerializer):
    """Course staff member details."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.display_name', read_only=True)

    class Meta:
        from .models import CourseStaff
        model = CourseStaff
        fields = ['uuid', 'user_email', 'user_name', 'role', 'created_at']
        read_only_fields = fields


class CourseStaffCreateSerializer(serializers.Serializer):
    """Create a course staff assignment."""

    user_uuid = serializers.UUIDField()
    # Only instructor is valid — the per-course course_manager distinction was
    # retired with the Django group. `role` kept on the model for future
    # extensibility but has a single accepted value today.
    role = serializers.ChoiceField(choices=['instructor'], default='instructor')


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
    published_recording = serializers.SerializerMethodField()

    def get_published_recording(self, obj):
        from conferencing.models import VideoRecording

        rec = (
            VideoRecording.objects.filter(
                course_session=obj,
                is_published=True,
                status=VideoRecording.Status.AVAILABLE,
            )
            .order_by('-recording_start')
            .first()
        )
        if not rec:
            return None
        return {
            'uuid': str(rec.uuid),
            'storage_path': rec.storage_path,
            'duration_seconds': rec.duration_seconds,
            'recording_end': rec.recording_end.isoformat() if rec.recording_end else None,
        }

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
            'video_settings',
            'recording_enabled',
            'recording_auto_publish',
            'cpd_credits',
            'is_mandatory',
            'minimum_attendance_percent',
            'is_published',
            'status',
            'cancelled_reason',
            'cancelled_at',
            'actual_start_at',
            'actual_end_at',
            'is_upcoming',
            'is_live',
            'is_past',
            'published_recording',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'status',
            'cancelled_reason',
            'cancelled_at',
            'actual_start_at',
            'actual_end_at',
            'published_recording',
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
            'cpd_credits',
            'is_mandatory',
            'is_published',
            'status',
            'recording_enabled',
            'recording_auto_publish',
            'cancelled_reason',
            'cancelled_at',
            'actual_start_at',
            'actual_end_at',
            'is_upcoming',
            'is_live',
            'is_past',
            'published_recording',
        ]

    published_recording = serializers.SerializerMethodField()

    def get_published_recording(self, obj):
        from conferencing.models import VideoRecording

        rec = (
            VideoRecording.objects.filter(
                course_session=obj,
                is_published=True,
                status=VideoRecording.Status.AVAILABLE,
            )
            .order_by('-recording_start')
            .first()
        )
        if not rec:
            return None
        return {
            'uuid': str(rec.uuid),
            'storage_path': rec.storage_path,
            'duration_seconds': rec.duration_seconds,
        }


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
            'video_settings',
            'recording_enabled',
            'recording_auto_publish',
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
            'participant_email',
            'join_time',
            'leave_time',
            'is_manual_override',
            'override_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'session',
            'enrollment',
            'participant_email',
            'join_time',
            'leave_time',
            'created_at',
            'updated_at',
        ]


class UnmatchedParticipantSerializer(serializers.Serializer):
    """Video participant not matched to any enrollment."""
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
    participant_email = serializers.EmailField(required=False)
    join_time = serializers.DateTimeField(required=False)
    leave_time = serializers.DateTimeField(required=False)
    attendance_minutes = serializers.IntegerField(required=False)


# =============================================================================
# Programs
# =============================================================================


class ProgramCourseEntrySerializer(serializers.ModelSerializer):
    """A course as it appears inside a program (with order/required flags)."""

    course = CourseListSerializer(read_only=True)
    course_uuid = serializers.UUIDField(write_only=True)

    class Meta:
        model = ProgramCourse
        fields = ['uuid', 'course', 'course_uuid', 'order', 'is_required', 'created_at']
        read_only_fields = ['uuid', 'course', 'created_at']

    def create(self, validated_data):
        course_uuid = validated_data.pop('course_uuid')
        try:
            course = Course.objects.get(uuid=course_uuid)
        except Course.DoesNotExist:
            raise serializers.ValidationError({'course_uuid': 'Course not found.'})
        validated_data['course'] = course
        return super().create(validated_data)


class ProgramListSerializer(serializers.ModelSerializer):
    """Brief program info for listings."""

    effective_image_url = serializers.CharField(read_only=True)
    is_free = serializers.BooleanField(read_only=True)

    class Meta:
        model = Program
        fields = [
            'uuid',
            'title',
            'slug',
            'short_description',
            'effective_image_url',
            'status',
            'is_public',
            'price_cents',
            'currency',
            'is_free',
            'course_count',
            'enrollment_count',
            'created_at',
        ]
        read_only_fields = fields


class ProgramSerializer(serializers.ModelSerializer):
    """Full program details with member courses + bundle savings."""

    effective_image_url = serializers.CharField(read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    program_courses = ProgramCourseEntrySerializer(many=True, read_only=True)
    sum_individual_price_cents = serializers.SerializerMethodField()
    bundle_savings_cents = serializers.SerializerMethodField()

    class Meta:
        model = Program
        fields = [
            'uuid',
            'title',
            'slug',
            'description',
            'short_description',
            'featured_image_url',
            'effective_image_url',
            'status',
            'is_public',
            'price_cents',
            'currency',
            'is_free',
            'sum_individual_price_cents',
            'bundle_savings_cents',
            'stripe_price_id',
            'course_count',
            'enrollment_count',
            'program_courses',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'effective_image_url',
            'is_free',
            'sum_individual_price_cents',
            'bundle_savings_cents',
            'course_count',
            'enrollment_count',
            'program_courses',
            'created_at',
            'updated_at',
        ]

    def get_sum_individual_price_cents(self, obj):
        return obj.sum_individual_price_cents()

    def get_bundle_savings_cents(self, obj):
        sum_individual = obj.sum_individual_price_cents()
        return max(0, sum_individual - (obj.price_cents or 0))


class ProgramCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = [
            'uuid',
            'title',
            'slug',
            'description',
            'short_description',
            'featured_image',
            'featured_image_url',
            'status',
            'is_public',
            'price_cents',
            'currency',
        ]
        read_only_fields = ['uuid']

    def validate(self, attrs):
        new_status = attrs.get('status')
        if new_status == Program.Status.PUBLISHED and self.instance is not None:
            try:
                self.instance.validate_for_publish()
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages}
                )
        elif new_status == Program.Status.PUBLISHED and self.instance is None:
            attrs['status'] = Program.Status.DRAFT
        return attrs


class ProgramEnrollmentSerializer(serializers.ModelSerializer):
    program = ProgramListSerializer(read_only=True)
    courses = serializers.SerializerMethodField()

    class Meta:
        model = ProgramEnrollment
        fields = [
            'uuid',
            'program',
            'status',
            'enrolled_at',
            'started_at',
            'completed_at',
            'course_enrollments_seeded',
            'courses',
        ]
        read_only_fields = fields

    def get_courses(self, obj):
        """Per-course breakdown showing order + the learner's enrollment status."""
        from learning.models import CourseEnrollment, ProgramCourse

        members = (
            ProgramCourse.objects.filter(program=obj.program)
            .select_related('course')
            .order_by('order')
        )
        enrollments = {
            ce.course_id: ce
            for ce in CourseEnrollment.objects.filter(user=obj.user, course__in=[m.course_id for m in members])
        }
        out = []
        for m in members:
            ce = enrollments.get(m.course_id)
            out.append({
                'uuid': str(m.course.uuid),
                'title': m.course.title,
                'slug': m.course.slug,
                'order': m.order,
                'is_required': m.is_required,
                'enrollment_status': ce.status if ce else None,
                'progress_percent': float(ce.progress_percent) if ce and ce.progress_percent is not None else 0,
                'completed_at': ce.completed_at.isoformat() if ce and ce.completed_at else None,
            })
        return out


# =============================================================================
# Discussion Board Serializers
# =============================================================================


class _UserMiniSerializer(serializers.Serializer):
    """Minimal user representation used inside discussion payloads."""

    uuid = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class CourseMemberMiniSerializer(_UserMiniSerializer):
    """User mini + their role in the course (learner / instructor / admin)."""

    role = serializers.CharField(read_only=True)


class DiscussionReplySerializer(serializers.ModelSerializer):
    """A reply within a discussion thread."""

    author = _UserMiniSerializer(read_only=True)
    mentions = _UserMiniSerializer(many=True, read_only=True)
    can_moderate = serializers.SerializerMethodField()

    class Meta:
        model = DiscussionReply
        fields = [
            'uuid',
            'thread',
            'author',
            'body_html',
            'is_hidden',
            'mentions',
            'can_moderate',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'thread', 'author', 'is_hidden', 'mentions', 'created_at', 'updated_at']

    def get_can_moderate(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        course = obj.thread.course
        return course.can_manage(request.user) or course.can_instruct(request.user)


class DiscussionReplyCreateSerializer(serializers.ModelSerializer):
    """Create a reply — accepts body_html (sanitized on save)."""

    class Meta:
        model = DiscussionReply
        fields = ['body_html']

    def validate_body_html(self, value):
        from .sanitize import clean_discussion_html

        cleaned, plain = clean_discussion_html(value or '')
        if not plain:
            raise serializers.ValidationError('Reply body cannot be empty.')
        self._cleaned_pair = (cleaned, plain)
        return cleaned

    def save(self, **kwargs):
        cleaned, plain = getattr(self, '_cleaned_pair', (self.validated_data['body_html'], ''))
        kwargs['body_html'] = cleaned
        kwargs['body_plain'] = plain
        return super().save(**kwargs)


class DiscussionThreadListSerializer(serializers.ModelSerializer):
    """Thread summary row for lists."""

    author = _UserMiniSerializer(read_only=True)
    open_flag_count = serializers.SerializerMethodField()

    class Meta:
        model = DiscussionThread
        fields = [
            'uuid',
            'title',
            'author',
            'is_pinned',
            'is_locked',
            'is_hidden',
            'reply_count',
            'last_activity_at',
            'open_flag_count',
            'created_at',
        ]
        read_only_fields = fields

    def get_open_flag_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        course = obj.course
        if not (course.can_manage(request.user) or course.can_instruct(request.user)):
            return 0
        return obj.flags.filter(status=DiscussionFlag.Status.OPEN).count()


class DiscussionThreadDetailSerializer(DiscussionThreadListSerializer):
    """Thread detail — includes body and first page of replies."""

    body_html = serializers.CharField(read_only=True)
    mentions = _UserMiniSerializer(many=True, read_only=True)
    replies = serializers.SerializerMethodField()
    can_moderate = serializers.SerializerMethodField()

    class Meta(DiscussionThreadListSerializer.Meta):
        fields = DiscussionThreadListSerializer.Meta.fields + [
            'body_html',
            'mentions',
            'replies',
            'can_moderate',
            'updated_at',
        ]
        read_only_fields = fields

    def get_replies(self, obj):
        request = self.context.get('request')
        qs = obj.replies.all().select_related('author').prefetch_related('mentions')
        if request and request.user.is_authenticated:
            course = obj.course
            if not (course.can_manage(request.user) or course.can_instruct(request.user)):
                qs = qs.filter(is_hidden=False)
        return DiscussionReplySerializer(qs, many=True, context=self.context).data

    def get_can_moderate(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.course.can_manage(request.user) or obj.course.can_instruct(request.user)


class DiscussionThreadCreateSerializer(serializers.ModelSerializer):
    """Create a thread."""

    class Meta:
        model = DiscussionThread
        fields = ['title', 'body_html']

    def validate_title(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Title is required.')
        return value

    def validate_body_html(self, value):
        from .sanitize import clean_discussion_html

        cleaned, plain = clean_discussion_html(value or '')
        if not plain:
            raise serializers.ValidationError('Body cannot be empty.')
        self._cleaned_pair = (cleaned, plain)
        return cleaned

    def save(self, **kwargs):
        cleaned, plain = getattr(self, '_cleaned_pair', (self.validated_data.get('body_html', ''), ''))
        kwargs['body_html'] = cleaned
        kwargs['body_plain'] = plain
        return super().save(**kwargs)


class DiscussionThreadUpdateSerializer(DiscussionThreadCreateSerializer):
    """Author edit of their own thread."""

    class Meta(DiscussionThreadCreateSerializer.Meta):
        fields = ['title', 'body_html']


class DiscussionFlagSerializer(serializers.ModelSerializer):
    """Staff-facing flag row."""

    reporter = _UserMiniSerializer(read_only=True)
    target_type = serializers.SerializerMethodField()
    target_snippet = serializers.SerializerMethodField()
    thread_uuid = serializers.SerializerMethodField()

    class Meta:
        model = DiscussionFlag
        fields = [
            'uuid',
            'reporter',
            'reason',
            'note',
            'status',
            'target_type',
            'target_snippet',
            'thread_uuid',
            'thread',
            'reply',
            'resolved_at',
            'created_at',
        ]
        read_only_fields = fields

    def get_target_type(self, obj):
        return 'thread' if obj.thread_id else 'reply'

    def get_thread_uuid(self, obj):
        thread = obj.thread if obj.thread_id else (obj.reply.thread if obj.reply_id else None)
        return str(thread.uuid) if thread else None

    def get_target_snippet(self, obj):
        target = obj.thread if obj.thread_id else obj.reply
        text = (getattr(target, 'body_plain', '') or '') if target else ''
        return text[:240]


class DiscussionFlagCreateSerializer(serializers.ModelSerializer):
    """Learner-created flag."""

    class Meta:
        model = DiscussionFlag
        fields = ['reason', 'note']

    def validate_reason(self, value):
        valid = {c for c, _ in DiscussionFlag.Reason.choices}
        if value not in valid:
            raise serializers.ValidationError('Invalid reason.')
        return value
