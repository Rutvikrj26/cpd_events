from django.contrib import admin

from .models import EventFeedback


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ('event', 'get_attendee', 'rating', 'created_at')
    list_filter = ('rating', 'is_anonymous', 'created_at')
    search_fields = ('event__title', 'comments')

    def get_attendee(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        if obj.registration and obj.registration.user:
            return obj.registration.user.get_full_name()
        return "Unknown"

    get_attendee.short_description = 'Attendee'
