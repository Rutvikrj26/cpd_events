from django.contrib import admin
from .models import ContactList, Contact, Tag


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    fields = ('email', 'full_name', 'professional_title', 'email_opted_out')


@admin.register(ContactList)
class ContactListAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'contact_count', 'is_default')
    list_filter = ('is_default',)
    search_fields = ('name', 'owner__email')
    inlines = [ContactInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'contact_list', 'events_invited_count', 'events_attended_count')
    list_filter = ('email_opted_out', 'email_bounced')
    search_fields = ('email', 'full_name', 'contact_list__name')
    filter_horizontal = ('tags',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'color', 'contact_count')
    search_fields = ('name', 'owner__email')
