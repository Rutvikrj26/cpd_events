from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, Notification, User, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'get_roles', 'is_active', 'email_verified')
    list_filter = ('is_active', 'email_verified', 'is_staff', 'groups')
    search_fields = ('email', 'full_name')
    ordering = ('-created_at',)
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('full_name', 'professional_title', 'organization_name', 'bio', 'timezone')}),
        ('Account', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Roles', {'fields': ('groups', 'user_permissions')}),
        ('Email Verification', {'fields': ('email_verified', 'email_verified_at')}),
        ('Notifications', {'fields': ('notify_event_reminders', 'notify_certificate_issued')}),
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

    def get_roles(self, obj):
        return ", ".join(obj.role_names) or "none"
    get_roles.short_description = "Roles"


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'last_activity_at')
    list_filter = ('is_active', 'device_type')
    search_fields = ('user__email',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'read_at', 'created_at')
    list_filter = ('notification_type', 'read_at')
    search_fields = ('user__email', 'title')
    ordering = ('-created_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('actor', 'action', 'object_type', 'object_uuid', 'created_at')
    list_filter = ('action', 'object_type')
    search_fields = ('actor__email', 'object_uuid')
    ordering = ('-created_at',)
