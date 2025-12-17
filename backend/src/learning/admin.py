"""
Admin configuration for learning app.
"""

from django.contrib import admin

from .models import (
    Assignment,
    AssignmentSubmission,
    ContentProgress,
    EventModule,
    ModuleContent,
    ModuleProgress,
    SubmissionReview,
)


class ModuleContentInline(admin.TabularInline):
    """Inline for module contents."""

    model = ModuleContent
    extra = 0
    fields = ['title', 'content_type', 'order', 'is_required', 'is_published']


class AssignmentInline(admin.TabularInline):
    """Inline for module assignments."""

    model = Assignment
    extra = 0
    fields = ['title', 'max_score', 'passing_score', 'submission_type']


@admin.register(EventModule)
class EventModuleAdmin(admin.ModelAdmin):
    """Admin for EventModule model."""

    list_display = ['title', 'event', 'order', 'release_type', 'is_published', 'cpd_credits']
    list_filter = ['is_published', 'release_type', 'event']
    search_fields = ['title', 'event__title']
    ordering = ['event', 'order']
    inlines = [ModuleContentInline, AssignmentInline]

    fieldsets = (
        ('Basic Info', {'fields': ('event', 'title', 'description', 'order')}),
        (
            'Release Settings',
            {'fields': ('release_type', 'release_at', 'release_days_after_registration', 'prerequisite_module')},
        ),
        ('Scoring & Credits', {'fields': ('passing_score', 'cpd_credits', 'cpd_type')}),
        ('Status', {'fields': ('is_published',)}),
    )


@admin.register(ModuleContent)
class ModuleContentAdmin(admin.ModelAdmin):
    """Admin for ModuleContent model."""

    list_display = ['title', 'module', 'content_type', 'order', 'is_required', 'is_published']
    list_filter = ['content_type', 'is_required', 'is_published']
    search_fields = ['title', 'module__title']


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """Admin for Assignment model."""

    list_display = ['title', 'module', 'max_score', 'passing_score', 'submission_type']
    list_filter = ['submission_type', 'allow_resubmission']
    search_fields = ['title', 'module__title']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    """Admin for AssignmentSubmission model."""

    list_display = ['assignment', 'get_user', 'status', 'attempt_number', 'score', 'submitted_at']
    list_filter = ['status', 'attempt_number']
    search_fields = ['registration__user__email', 'assignment__title']
    readonly_fields = ['uuid', 'created_at', 'updated_at']

    def get_user(self, obj):
        return obj.registration.user.email

    get_user.short_description = 'User'


@admin.register(SubmissionReview)
class SubmissionReviewAdmin(admin.ModelAdmin):
    """Admin for SubmissionReview model."""

    list_display = ['submission', 'reviewer', 'action', 'score', 'created_at']
    list_filter = ['action']
    search_fields = ['submission__assignment__title']


@admin.register(ContentProgress)
class ContentProgressAdmin(admin.ModelAdmin):
    """Admin for ContentProgress model."""

    list_display = ['content', 'get_user', 'status', 'progress_percent', 'completed_at']
    list_filter = ['status']
    search_fields = ['registration__user__email', 'content__title']

    def get_user(self, obj):
        return obj.registration.user.email

    get_user.short_description = 'User'


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    """Admin for ModuleProgress model."""

    list_display = ['module', 'get_user', 'status', 'contents_completed', 'contents_total', 'score']
    list_filter = ['status']
    search_fields = ['registration__user__email', 'module__title']

    def get_user(self, obj):
        return obj.registration.user.email

    get_user.short_description = 'User'
