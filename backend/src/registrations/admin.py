from django.contrib import admin
from .models import Registration, AttendanceRecord, CustomFieldResponse


class CustomFieldResponseInline(admin.TabularInline):
    model = CustomFieldResponse
    extra = 0
    readonly_fields = ('field', 'value')


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    readonly_fields = ('join_time', 'leave_time', 'duration_minutes', 'zoom_user_email')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'event', 'status', 'attended', 'certificate_issued')
    list_filter = ('status', 'attended', 'certificate_issued', 'source')
    search_fields = ('email', 'full_name', 'event__title')
    ordering = ('-created_at',)
    inlines = [CustomFieldResponseInline, AttendanceRecordInline]
    
    fieldsets = (
        (None, {'fields': ('event', 'user', 'email', 'full_name', 'status')}),
        ('Professional Info', {'fields': ('professional_title', 'organization_name')}),
        ('Attendance', {'fields': ('attended', 'total_attendance_minutes', 'attendance_eligible')}),
        ('Certificate', {'fields': ('certificate_issued', 'certificate_issued_at')}),
    )


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'event', 'join_time', 'duration_minutes', 'is_matched')
    list_filter = ('is_matched', 'matched_manually')
    search_fields = ('zoom_user_email', 'zoom_user_name', 'event__title')
