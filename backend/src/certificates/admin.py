from django.contrib import admin
from .models import CertificateTemplate, Certificate, CertificateStatusHistory


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'version', 'is_active', 'is_default', 'usage_count')
    list_filter = ('is_active', 'is_default', 'orientation')
    search_fields = ('name', 'owner__email')
    ordering = ('-created_at',)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('registration', 'template', 'status', 'verification_code', 'created_at')
    list_filter = ('status', 'email_sent')
    search_fields = ('verification_code', 'short_code', 'registration__email')
    ordering = ('-created_at',)
    readonly_fields = ('verification_code', 'short_code', 'certificate_data')


@admin.register(CertificateStatusHistory)
class CertificateStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('certificate', 'from_status', 'to_status', 'changed_by', 'created_at')
    list_filter = ('to_status',)
