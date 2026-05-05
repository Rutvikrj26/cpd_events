from django.contrib import admin, messages

from .models import AttendanceRecord, CustomFieldResponse, Registration


class CustomFieldResponseInline(admin.TabularInline):
    model = CustomFieldResponse
    extra = 0
    readonly_fields = ('field', 'value')


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    readonly_fields = ('join_time', 'leave_time', 'duration_minutes', 'participant_email')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'event', 'status', 'attended', 'certificate_issued')
    list_filter = ('status', 'attended', 'certificate_issued', 'source')
    search_fields = ('email', 'full_name', 'event__title')
    ordering = ('-created_at',)
    inlines = [CustomFieldResponseInline, AttendanceRecordInline]
    actions = ['reissue_claim_links']

    fieldsets = (
        (None, {'fields': ('event', 'user', 'email', 'full_name', 'status')}),
        ('Professional Info', {'fields': ('professional_title', 'organization_name')}),
        ('Attendance', {'fields': ('attended', 'total_attendance_minutes', 'attendance_eligible')}),
        ('Certificate', {'fields': ('certificate_issued', 'certificate_issued_at')}),
    )

    @admin.action(description='Re-issue access (claim) link by email')
    def reissue_claim_links(self, request, queryset):
        """Bulk re-issue magic-link CLAIM emails for selected registrations.

        Skips rows that are already linked to a User account — those
        users access the registration through normal sign-in. Useful when
        a registrant typo'd their email at checkout and wants the link
        re-sent to a different address (support edits ``email`` first,
        then runs this action).
        """
        from accounts.services import create_registration_claim
        from accounts.tasks import send_magic_link_email

        sent = 0
        skipped = 0
        for reg in queryset:
            if reg.user_id is not None:
                skipped += 1
                continue
            link = create_registration_claim(reg)
            send_magic_link_email(link.id)
            sent += 1

        if sent:
            self.message_user(
                request,
                f"Re-issued claim links for {sent} registration(s).",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} registration(s) already linked to a user account.",
                level=messages.WARNING,
            )


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'event', 'join_time', 'duration_minutes', 'is_matched')
    list_filter = ('is_matched', 'matched_manually')
    search_fields = ('participant_email', 'participant_name', 'event__title')
