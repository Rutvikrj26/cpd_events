"""
Serializers for learning API.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.text import slugify
from rest_framework import serializers

from common.utils import generate_unique_slug

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
    """Create/update content.

    ``validate`` runs the Pydantic per-content_type schema check on the
    incoming ``content_data`` and surfaces field-level errors so the
    authoring UI can attribute each error to the right input. See
    ``learning.content_schemas`` for the canonical shapes.
    """

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

    def validate(self, attrs):
        """Cross-field check: content_data shape depends on content_type.

        Done in ``validate`` (not ``validate_content_data``) because we need
        access to ``content_type`` from the same payload, which only the
        whole-attrs hook gives us.
        """
        from learning.content_schemas import (
            ContentSchemaError,
            format_schema_error,
            validate_content_data,
        )

        content_type = attrs.get('content_type') or (
            self.instance.content_type if self.instance else None
        )
        content_data = attrs.get('content_data', None)
        # ``content_data`` may be missing on partial updates that don't touch it.
        if content_type and content_data is not None:
            try:
                validate_content_data(content_type, content_data)
            except ContentSchemaError as exc:
                raise serializers.ValidationError(
                    {'content_data': format_schema_error(exc)}
                ) from None
        return attrs


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

    progress_percent = serializers.IntegerField(min_value=0, max_value=100, required=False)
    time_spent = serializers.IntegerField(min_value=0, required=False, default=0)
    position = serializers.DictField(required=False)
    completed = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs.get('completed'):
            attrs.setdefault('progress_percent', 100)
        elif 'progress_percent' not in attrs:
            raise serializers.ValidationError({'progress_percent': 'This field is required unless completed is true.'})
        return attrs


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
    is_current_user_host = serializers.SerializerMethodField()
    programs = serializers.SerializerMethodField()

    def get_is_current_user_host(self, obj):
        from conferencing.views import is_course_session_host
        request = self.context.get('request')
        return is_course_session_host(request.user, obj) if request else False

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
            'is_current_user_host',
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
            'completion_count',
            'module_count',
            'estimated_hours',
            'user_role',
            'created_at',
        ]


def _validate_certificate_settings(attrs, instance=None):
    """Drafts can have `certificates_enabled=True` without a template.

    Picking the template is part of finishing the course, not part of
    creating it — forcing it at create time blocks the very first
    "save my draft" round-trip from the wizard. The publish-time path
    (`Course.validate_for_publish`) is the authoritative gate that
    rejects publishes when a required template is missing.
    """
    certificates_enabled = attrs.get('certificates_enabled')
    certificate_template = attrs.get('certificate_template')
    new_status = attrs.get('status')

    if instance is not None:
        if certificates_enabled is None:
            certificates_enabled = instance.certificates_enabled
        if certificate_template is None:
            certificate_template = instance.certificate_template
        if new_status is None:
            new_status = instance.status

    if (
        new_status == Course.Status.PUBLISHED
        and certificates_enabled
        and not certificate_template
    ):
        raise serializers.ValidationError(
            {'certificate_template': 'Select a certificate template before publishing.'}
        )

    return attrs


def _validate_badge_settings(attrs, instance=None):
    """Same draft-vs-published policy as certificates above."""
    badges_enabled = attrs.get('badges_enabled')
    badge_template = attrs.get('badge_template')
    new_status = attrs.get('status')

    if instance is not None:
        if badges_enabled is None:
            badges_enabled = instance.badges_enabled
        if badge_template is None:
            badge_template = instance.badge_template
        if new_status is None:
            new_status = instance.status

    if (
        new_status == Course.Status.PUBLISHED
        and badges_enabled
        and not badge_template
    ):
        raise serializers.ValidationError(
            {'badge_template': 'Select a badge template before publishing.'}
        )

    return attrs


class CourseCreateSerializer(serializers.ModelSerializer):
    """Create/update course."""

    # `Course.slug` has `max_length=100` at the DB layer, but the wizard
    # auto-generates the slug from the (potentially long) title client-
    # side and a long title would hit the cap. Accept any slug here, and
    # truncate to fit in `validate_slug` below — same end result with no
    # 400. If the client omits the slug entirely, `create()` derives one
    # from the title (mirrors the events serializer).
    slug = serializers.CharField(required=False, allow_blank=True, max_length=200)

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

    def create(self, validated_data):
        # Derive a unique slug from the supplied slug (truncated) or the
        # title. Mirrors the events flow at events/serializers.py — this
        # keeps the wizard from hitting the slug max_length=100 ceiling
        # when the title is long.
        title = validated_data.get('title', '')
        raw_slug = (validated_data.pop('slug', '') or '').strip()
        base = slugify(raw_slug or title)[:80]
        validated_data['slug'] = generate_unique_slug(Course, base)
        return super().create(validated_data)


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
    """Enrollment details.

    ``status`` is the canonical write-side state (drives invariants,
    indexes, signals). ``view_state`` is the read-side projection learner
    UIs bind to — six discriminated kinds the consumer exhaustively
    switches on. See ``learning.view_states.derive_course_enrollment_view_state``
    for the kind taxonomy and ``frontend/src/features/courses/hooks/useCoursePlayerBootstrap.ts``
    for the matching TypeScript discriminated union.
    """

    course = CourseListSerializer(read_only=True)
    next_session_at = serializers.SerializerMethodField()
    session_progress = serializers.SerializerMethodField()
    view_state = serializers.SerializerMethodField()

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
            'next_session_at',
            'session_progress',
            'view_state',
        ]
        read_only_fields = fields

    def get_view_state(self, obj):
        from learning.view_states import derive_course_enrollment_view_state

        return derive_course_enrollment_view_state(obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Omit session_progress entirely (not null) for online courses so the
        # client can branch by key presence rather than by format.
        if data.get('session_progress') is None:
            data.pop('session_progress', None)
        return data

    def get_session_progress(self, obj):
        """Compact session breakdown so My Learning cards can render
        "2 of 3 modules · 1 of 2 sessions" subtitles without a second fetch.
        Only populated for live + hybrid courses; absent for online.
        """
        from learning.models import CourseSession
        if obj.course.format not in ('live', 'hybrid'):
            return None
        sessions_total = (
            CourseSession.objects
            .filter(course=obj.course, is_published=True, is_mandatory=True)
            .exclude(status=CourseSession.Status.CANCELLED)
            .count()
        )
        sessions_attended = (
            obj.session_attendance
            .filter(is_eligible=True, session__is_mandatory=True, session__is_published=True)
            .exclude(session__status=CourseSession.Status.CANCELLED)
            .count()
        )
        return {
            'sessions_attended': sessions_attended,
            'sessions_total': sessions_total,
            'criteria': obj.course.hybrid_completion_criteria,
        }

    def get_next_session_at(self, obj):
        """Earliest upcoming CourseSession the learner hasn't yet attended-
        eligibly. Drives the "Hybrid · Next session in 7d" badge with a
        single field, no per-card N+1.
        """
        from django.utils import timezone as _tz
        from learning.models import CourseSession
        if obj.course.format not in ('live', 'hybrid'):
            return None
        attended_session_ids = obj.session_attendance.filter(
            is_eligible=True,
        ).values_list('session_id', flat=True)
        nxt = (
            CourseSession.objects.filter(
                course=obj.course, is_published=True,
                starts_at__gt=_tz.now(),
            )
            .exclude(status=CourseSession.Status.CANCELLED)
            .exclude(id__in=list(attended_session_ids))
            .order_by('starts_at')
            .first()
        )
        return nxt.starts_at.isoformat() if nxt else None


class CourseEnrollmentRosterSerializer(serializers.ModelSerializer):
    """Enrollment details for course staff roster views.

    Includes payment info derived from the most-recent ``CoursePurchase``
    for the same (user, course) pair so the roster UI can show Paid /
    Refunded / Comp next to each learner.
    """

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_uuid = serializers.UUIDField(source='user.uuid', read_only=True)
    payment = serializers.SerializerMethodField()
    via_program = serializers.SerializerMethodField()

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
            'payment',
            'via_program',
        ]
        read_only_fields = fields

    def get_via_program(self, obj):
        """Expose program provenance so the UI can replace Refund with a
        'Refund on program' link for seeded enrollments."""
        if not obj.from_program_enrollment_id:
            return None
        pe = obj.from_program_enrollment
        return {
            'program_uuid': str(pe.program.uuid),
            'program_title': pe.program.title,
            'program_slug': pe.program.slug,
            'program_enrollment_uuid': str(pe.uuid),
        }

    def get_payment(self, obj):
        """Resolve the payment row for this enrollment.

        ``comp`` is inferred — a course with a non-zero price where the
        learner has no matching CoursePurchase row and no program
        provenance was enrolled by a staff member without payment. Free
        courses always report ``free``. Program-seeded rows report
        ``via_program`` so the roster shows a 'Refund on program' affordance
        instead of a broken course-level button.
        """
        course = obj.course

        # A program-seeded enrollment routes its money through the program
        # purchase, not the course. Surface that explicitly.
        if obj.from_program_enrollment_id:
            return {'status': 'via_program'}

        if course.price_cents == 0:
            return {'status': 'free'}

        from billing.models import CoursePurchase

        purchase = (
            CoursePurchase.objects
            .filter(user=obj.user, course=course)
            .order_by('-created_at')
            .first()
        )
        if purchase is None:
            return {'status': 'comp'}
        return {
            'status': purchase.status,
            'amount_cents': purchase.amount_cents,
            'currency': purchase.currency,
            'purchase_uuid': str(purchase.uuid),
            'stripe_payment_intent_id': purchase.stripe_payment_intent_id,
            'created_at': purchase.created_at.isoformat() if purchase.created_at else None,
        }


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


class LiveSessionSerializer(serializers.ModelSerializer):
    """Learner-context view of a CourseSession.

    Collapses CourseSession + the caller's CourseSessionAttendance + the
    polymorphic VideoRoom lookup into one shape (per
    docs/design/hybrid-course-experience.md §A). The same shape will host
    EventSession in a future iteration; treat it as the canonical
    "live-session UI primitive" for the frontend.

    All learner-context fields (`attendance`, `recording`, `join_url`,
    `is_within_join_window`) require `context['request']`. Without it the
    serializer falls back to the un-hydrated shape (still valid).
    """

    ends_at = serializers.DateTimeField(read_only=True)
    attendance = serializers.SerializerMethodField()
    recording = serializers.SerializerMethodField()
    join_url = serializers.SerializerMethodField()
    is_within_join_window = serializers.SerializerMethodField()
    next_action = serializers.SerializerMethodField()

    class Meta:
        model = CourseSession
        fields = [
            'uuid', 'title', 'description', 'order',
            'session_type', 'delivery_mode',
            'starts_at', 'ends_at', 'duration_minutes', 'timezone',
            'actual_start_at', 'actual_end_at',
            'is_mandatory', 'minimum_attendance_percent',
            'status', 'is_published',
            'cpd_credits',
            # Learner-context fields
            'attendance', 'recording', 'join_url', 'is_within_join_window',
            'next_action',
        ]

    def _enrollment(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        if not hasattr(self, '_enrollment_cache'):
            self._enrollment_cache = {}
        course_id = obj.course_id
        if course_id not in self._enrollment_cache:
            from learning.models import CourseEnrollment
            self._enrollment_cache[course_id] = CourseEnrollment.objects.filter(
                user=request.user, course_id=course_id,
            ).first()
        return self._enrollment_cache[course_id]

    def get_attendance(self, obj):
        from learning.models import CourseSessionAttendance
        enr = self._enrollment(obj)
        if enr is None:
            return None
        rec = CourseSessionAttendance.objects.filter(session=obj, enrollment=enr).first()
        if rec is None:
            return None
        return {
            'is_eligible': rec.is_eligible,
            'attendance_minutes': rec.attendance_minutes,
            'is_manual_override': rec.is_manual_override,
        }

    def get_recording(self, obj):
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
        if rec is None:
            return None
        return {
            'uuid': str(rec.uuid),
            'storage_path': rec.storage_path,
            'duration_seconds': rec.duration_seconds,
        }

    def get_join_url(self, obj):
        if obj.delivery_mode == obj.DeliveryMode.IN_PERSON:
            return None
        if not self.get_is_within_join_window(obj):
            return None
        from conferencing.models import VideoRoom
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(obj)
        room = VideoRoom.objects.filter(
            content_type=ct, object_id=obj.id,
        ).exclude(status=VideoRoom.Status.ERROR).first()
        if room is None:
            return None
        # Frontend resolves the actual signed join URL via /api/conferencing
        # /rooms/.../join/. Surfacing the room UUID is enough for routing.
        return f'/courses/{obj.course.slug}/sessions/{obj.uuid}/lobby'

    def get_is_within_join_window(self, obj):
        from django.utils import timezone as _tz
        if obj.status == obj.Status.CANCELLED:
            return False
        now = _tz.now()
        # 15-min lead time before scheduled start.
        window_open = obj.starts_at - _tz.timedelta(minutes=15)
        # Window closes at actual_end_at if set, else scheduled end.
        window_close = obj.actual_end_at or obj.ends_at
        return window_open <= now <= window_close

    def get_next_action(self, obj):
        attendance = self.get_attendance(obj)
        if obj.status == obj.Status.CANCELLED:
            return None
        if self.get_is_within_join_window(obj):
            return 'join_now'
        if attendance and attendance['is_eligible']:
            return 'view_recording' if self.get_recording(obj) else None
        if obj.is_past:
            return 'view_recording' if self.get_recording(obj) else 'mark_attended_manually'
        return 'add_to_calendar'


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
            'delivery_mode',
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
            'delivery_mode',
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
            'delivery_mode',
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
    already_paid_for_courses = serializers.SerializerMethodField()
    viewer_enrollment = serializers.SerializerMethodField()

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
            'already_paid_for_courses',
            'viewer_enrollment',
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
            'already_paid_for_courses',
            'viewer_enrollment',
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

    def get_already_paid_for_courses(self, obj):
        """Warn the signed-in learner if they've already paid for one or more
        member courses individually. Powers the double-charge warning on the
        public program detail page. Anonymous users get an empty list.
        """
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not getattr(user, 'is_authenticated', False):
            return []

        from billing.models import CoursePurchase

        member_course_ids = list(
            obj.program_courses.values_list('course_id', flat=True),
        )
        if not member_course_ids:
            return []

        paid = (
            CoursePurchase.objects
            .filter(user=user, course_id__in=member_course_ids, status=CoursePurchase.Status.COMPLETED)
            .select_related('course')
        )
        return [
            {
                'course_uuid': str(p.course.uuid),
                'course_title': p.course.title,
                'amount_cents': p.amount_cents,
                'currency': p.currency,
                'purchased_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in paid
        ]

    def get_viewer_enrollment(self, obj):
        """Return the requesting user's ProgramEnrollment summary, or None.

        Used by the public program detail page to swap the purchase CTA for
        a "Continue learning" / "Completed" view once the learner is enrolled,
        preventing accidental re-purchase of an owned bundle.
        """
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        enrollment = obj.enrollments.filter(user=user).first()
        if enrollment is None:
            return None
        return {
            'status': enrollment.status,
            'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
            'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None,
        }


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
    view_state = serializers.SerializerMethodField()

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
            'view_state',
        ]
        read_only_fields = fields

    def get_view_state(self, obj):
        from learning.view_states import derive_program_enrollment_view_state

        return derive_program_enrollment_view_state(obj)

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


class ProgramEnrollmentRosterSerializer(serializers.ModelSerializer):
    """Staff-facing roster row for a program's enrollments.

    Mirrors ``CourseEnrollmentRosterSerializer`` — surfaces the matching
    ``CoursePurchase`` (by ``user × program``) as a ``payment`` object so
    the UI can badge rows Paid / Refunded / Comp / Free without a second
    round-trip.
    """

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_uuid = serializers.UUIDField(source='user.uuid', read_only=True)
    payment = serializers.SerializerMethodField()

    class Meta:
        model = ProgramEnrollment
        fields = [
            'uuid',
            'user_uuid',
            'user_email',
            'user_name',
            'status',
            'enrolled_at',
            'started_at',
            'completed_at',
            'payment',
        ]
        read_only_fields = fields

    def get_payment(self, obj):
        program = obj.program
        if program.price_cents == 0:
            return {'status': 'free'}

        from billing.models import CoursePurchase

        purchase = (
            CoursePurchase.objects
            .filter(user=obj.user, program=program)
            .order_by('-created_at')
            .first()
        )
        if purchase is None:
            return {'status': 'comp'}
        return {
            'status': purchase.status,
            'amount_cents': purchase.amount_cents,
            'currency': purchase.currency,
            'purchase_uuid': str(purchase.uuid),
            'stripe_payment_intent_id': purchase.stripe_payment_intent_id,
            'created_at': purchase.created_at.isoformat() if purchase.created_at else None,
        }


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
