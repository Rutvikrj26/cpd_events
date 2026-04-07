from django.contrib import admin

from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'email_type', 'status', 'sent_at')
    list_filter = ('email_type', 'status')
    search_fields = ('recipient_email', 'subject')
    ordering = ('-created_at',)
