from django.contrib import admin

from .models import Event, EventCustomField, EventStatusHistory, Speaker


class EventCustomFieldInline(admin.TabularInline):
    model = EventCustomField
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'starts_at', 'registration_count')
    list_filter = ('status', 'event_type', 'cpd_enabled', 'certificates_enabled')
    search_fields = ('title', 'slug', 'owner__email')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'starts_at'
    ordering = ('-starts_at',)
    inlines = [EventCustomFieldInline]
    filter_horizontal = ('speakers',)

    fieldsets = (
        (None, {'fields': ('owner', 'title', 'slug', 'description', 'event_type', 'status')}),
        ('Schedule', {'fields': ('timezone', 'starts_at', 'duration_minutes')}),
        ('Registration', {'fields': ('registration_enabled', 'max_attendees', 'waitlist_enabled')}),
        ('CPD', {'fields': ('cpd_enabled', 'cpd_credit_type', 'cpd_credit_value', 'learning_objectives')}),
        ('Speakers', {'fields': ('speakers',)}),
        ('Certificates', {'fields': ('certificates_enabled', 'certificate_template', 'auto_issue_certificates')}),
        ('Zoom', {'fields': ('zoom_meeting_id', 'zoom_join_url'), 'classes': ('collapse',)}),
    )


@admin.register(EventStatusHistory)
class EventStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('event', 'from_status', 'to_status', 'changed_by', 'created_at')
    list_filter = ('to_status',)
    list_filter = ('to_status',)
    search_fields = ('event__title',)


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'email', 'owner__email', 'owner__first_name', 'owner__last_name')
