"""
Serializers for learning API.
"""

from rest_framework import serializers

from .models import (
    EventModule,
    ModuleContent,
    Assignment,
    AssignmentSubmission,
    SubmissionReview,
    ContentProgress,
    ModuleProgress,
)


class ModuleContentSerializer(serializers.ModelSerializer):
    """Full content details."""
    
    content_type_display = serializers.CharField(
        source='get_content_type_display', read_only=True
    )
    
    class Meta:
        model = ModuleContent
        fields = [
            'uuid', 'title', 'description',
            'content_type', 'content_type_display',
            'order', 'duration_minutes',
            'content_data', 'is_required', 'is_published',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class ModuleContentCreateSerializer(serializers.ModelSerializer):
    """Create/update content."""
    
    class Meta:
        model = ModuleContent
        fields = [
            'title', 'description', 'content_type',
            'order', 'duration_minutes', 'content_data',
            'is_required', 'is_published'
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    """Full assignment details."""
    
    submission_type_display = serializers.CharField(
        source='get_submission_type_display', read_only=True
    )
    passing_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Assignment
        fields = [
            'uuid', 'title', 'description', 'instructions',
            'due_days_after_release', 'max_score', 'passing_score',
            'passing_percentage', 'allow_resubmission', 'max_attempts',
            'submission_type', 'submission_type_display', 'rubric',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class AssignmentCreateSerializer(serializers.ModelSerializer):
    """Create/update assignment."""
    
    class Meta:
        model = Assignment
        fields = [
            'title', 'description', 'instructions',
            'due_days_after_release', 'max_score', 'passing_score',
            'allow_resubmission', 'max_attempts',
            'submission_type', 'rubric'
        ]


class EventModuleSerializer(serializers.ModelSerializer):
    """Full module details with contents."""
    
    release_type_display = serializers.CharField(
        source='get_release_type_display', read_only=True
    )
    contents = ModuleContentSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)
    content_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EventModule
        fields = [
            'uuid', 'title', 'description', 'order',
            'release_type', 'release_type_display',
            'release_at', 'release_days_after_registration',
            'prerequisite_module', 'passing_score',
            'cpd_credits', 'cpd_type', 'is_published',
            'content_count', 'assignment_count',
            'contents', 'assignments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']
    
    def get_content_count(self, obj):
        return obj.contents.count()
    
    def get_assignment_count(self, obj):
        return obj.assignments.count()


class EventModuleListSerializer(serializers.ModelSerializer):
    """Module list view - without nested items."""
    
    release_type_display = serializers.CharField(
        source='get_release_type_display', read_only=True
    )
    content_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EventModule
        fields = [
            'uuid', 'title', 'description', 'order',
            'release_type', 'release_type_display',
            'is_published', 'content_count', 'assignment_count',
            'cpd_credits'
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
            'title', 'description', 'order',
            'release_type', 'release_at', 'release_days_after_registration',
            'prerequisite_module', 'passing_score',
            'cpd_credits', 'cpd_type', 'is_published'
        ]


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """Full submission details."""
    
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    is_passing = serializers.BooleanField(read_only=True)
    assignment_title = serializers.CharField(
        source='assignment.title', read_only=True
    )
    
    class Meta:
        model = AssignmentSubmission
        fields = [
            'uuid', 'assignment', 'assignment_title',
            'status', 'status_display', 'attempt_number',
            'submitted_at', 'content', 'file_url',
            'score', 'feedback', 'graded_at', 'is_passing',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'attempt_number', 'submitted_at',
            'score', 'feedback', 'graded_at',
            'created_at', 'updated_at'
        ]


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
    action = serializers.ChoiceField(
        choices=['grade', 'return', 'approve'],
        default='grade'
    )


class SubmissionReviewSerializer(serializers.ModelSerializer):
    """Submission review history."""
    
    action_display = serializers.CharField(
        source='get_action_display', read_only=True
    )
    reviewer_name = serializers.CharField(
        source='reviewer.display_name', read_only=True
    )
    
    class Meta:
        model = SubmissionReview
        fields = [
            'uuid', 'action', 'action_display',
            'from_status', 'to_status',
            'score', 'feedback', 'rubric_scores',
            'reviewer_name', 'created_at'
        ]


class ContentProgressSerializer(serializers.ModelSerializer):
    """Content progress tracking."""
    
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    content_title = serializers.CharField(
        source='content.title', read_only=True
    )
    
    class Meta:
        model = ContentProgress
        fields = [
            'uuid', 'content', 'content_title',
            'status', 'status_display',
            'started_at', 'completed_at',
            'progress_percent', 'time_spent_seconds',
            'last_position'
        ]
        read_only_fields = [
            'uuid', 'started_at', 'completed_at'
        ]


class ContentProgressUpdateSerializer(serializers.Serializer):
    """Update content progress."""
    
    progress_percent = serializers.IntegerField(min_value=0, max_value=100)
    time_spent = serializers.IntegerField(min_value=0, required=False, default=0)
    position = serializers.DictField(required=False)
    completed = serializers.BooleanField(required=False, default=False)


class ModuleProgressSerializer(serializers.ModelSerializer):
    """Module progress tracking."""
    
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    module_title = serializers.CharField(
        source='module.title', read_only=True
    )
    progress_percent = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ModuleProgress
        fields = [
            'uuid', 'module', 'module_title',
            'status', 'status_display',
            'started_at', 'completed_at',
            'contents_completed', 'contents_total',
            'progress_percent', 'score', 'attempts'
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
