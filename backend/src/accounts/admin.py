from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserSession, ZoomConnection


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'account_type', 'is_active', 'email_verified')
    list_filter = ('account_type', 'is_active', 'email_verified', 'is_staff')
    search_fields = ('email', 'full_name')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('full_name', 'professional_title', 'organization_name', 'timezone')}),
        ('Account', {'fields': ('account_type', 'is_active', 'is_staff', 'is_superuser')}),
        ('Email Verification', {'fields': ('email_verified', 'email_verified_at')}),
        ('Notifications', {'fields': ('notify_event_reminders', 'notify_certificate_issued', 'notify_marketing')}),
        ('Organizer Profile', {'fields': ('organizer_bio', 'organizer_website', 'organizer_slug')}),
    )

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'full_name', 'password1', 'password2'),
            },
        ),
    )


@admin.register(ZoomConnection)
class ZoomConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'zoom_email', 'is_active', 'last_used_at')
    list_filter = ('is_active',)
    search_fields = ('user__email', 'zoom_email')


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'last_activity_at')
    list_filter = ('is_active', 'device_type')
    search_fields = ('user__email',)
