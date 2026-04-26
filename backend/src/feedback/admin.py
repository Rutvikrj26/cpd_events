from django.contrib import admin

from .models import EventFeedback, FeedbackField, FeedbackFieldResponse


class FeedbackFieldResponseInline(admin.TabularInline):
    model = FeedbackFieldResponse
    extra = 0
    readonly_fields = ('field', 'value', 'created_at')
    can_delete = False


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ('event', 'session', 'get_attendee', 'is_anonymous', 'created_at')
    list_filter = ('is_anonymous', 'created_at')
    search_fields = ('event__title',)
    inlines = [FeedbackFieldResponseInline]

    def get_attendee(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        if obj.registration and obj.registration.user:
            return obj.registration.user.get_full_name()
        return "Unknown"

    get_attendee.short_description = 'Attendee'


class FeedbackFieldInline(admin.TabularInline):
    model = FeedbackField
    extra = 0
    fields = ('label', 'field_type', 'required', 'order', 'options')


@admin.register(FeedbackField)
class FeedbackFieldAdmin(admin.ModelAdmin):
    list_display = ('event', 'label', 'field_type', 'required', 'order')
    list_filter = ('field_type', 'required')
    search_fields = ('label', 'event__title')
