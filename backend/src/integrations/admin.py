from django.contrib import admin

from .models import EmailLog, ScheduledEmail


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'email_type', 'status', 'sent_at')
    list_filter = ('email_type', 'status')
    search_fields = ('recipient_email', 'subject')
    ordering = ('-created_at',)


@admin.register(ScheduledEmail)
class ScheduledEmailAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'template_key', 'send_at', 'status', 'batch_key')
    list_filter = ('status', 'template_key')
    search_fields = ('recipient_email', 'subject', 'batch_key')
    ordering = ('send_at',)
    raw_id_fields = ('recipient_user', 'event', 'registration', 'email_log')
