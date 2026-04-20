"""
Management command to create Django Groups with their permissions.

Usage: python manage.py setup_groups

This creates the five institutional roles (learner, educator, course_manager, instructor, admin)
and assigns the appropriate Django permissions to each group.

Run this after migrations to ensure groups and permissions are set up.
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


# Group -> permission codenames mapping
GROUP_PERMISSIONS = {
    "learner": [
        # Events
        "view_event",
        # Registrations
        "add_registration",
        "view_registration",
        # Certificates
        "view_certificate",
        "view_certificatetemplate",
        # Learning
        "view_course",
        "view_coursemodule",
        "view_modulecontent",
        "view_assignment",
        "add_assignmentsubmission",
        "view_assignmentsubmission",
        "view_contentprogress",
        "add_contentprogress",
        "change_contentprogress",
        "add_courseenrollment",
        "view_courseenrollment",
        # Feedback
        "add_eventfeedback",
        "view_eventfeedback",
        # Badges
        "view_issuedbadge",
    ],
    "educator": [
        # Events (full CRUD)
        "add_event",
        "change_event",
        "delete_event",
        "view_event",
        "can_create_event",
        "can_manage_event",
        # Sessions
        "add_eventsession",
        "change_eventsession",
        "delete_eventsession",
        "view_eventsession",
        "add_sessionattendance",
        "change_sessionattendance",
        "view_sessionattendance",
        # Custom fields
        "add_eventcustomfield",
        "change_eventcustomfield",
        "delete_eventcustomfield",
        "view_eventcustomfield",
        # Speakers
        "add_speaker",
        "change_speaker",
        "delete_speaker",
        "view_speaker",
        # Registrations (manage)
        "add_registration",
        "change_registration",
        "view_registration",
        # Certificates (issue)
        "add_certificate",
        "change_certificate",
        "view_certificate",
        "add_certificatetemplate",
        "change_certificatetemplate",
        "delete_certificatetemplate",
        "view_certificatetemplate",
        "can_issue_certificate",
        "can_manage_templates",
        # Contacts
        "add_contactlist",
        "change_contactlist",
        "delete_contactlist",
        "view_contactlist",
        "add_contact",
        "change_contact",
        "delete_contact",
        "view_contact",
        "can_manage_contacts",
        # Promo codes
        "add_promocode",
        "change_promocode",
        "delete_promocode",
        "view_promocode",
        # Feedback
        "add_eventfeedback",
        "change_eventfeedback",
        "view_eventfeedback",
        # Badges
        "add_badgetemplate",
        "change_badgetemplate",
        "delete_badgetemplate",
        "view_badgetemplate",
        "add_issuedbadge",
        "view_issuedbadge",
        # Learning (view for hybrid events)
        "view_course",
        "view_coursemodule",
        "view_modulecontent",
        "view_assignment",
        "view_assignmentsubmission",
        "view_contentprogress",
        "add_contentprogress",
        "change_contentprogress",
        "add_courseenrollment",
        "view_courseenrollment",
    ],
    "course_manager": [
        # Courses (full CRUD)
        "add_course",
        "change_course",
        "delete_course",
        "view_course",
        "can_create_course",
        "can_manage_course",
        # Modules
        "add_eventmodule",
        "change_eventmodule",
        "delete_eventmodule",
        "view_eventmodule",
        "add_coursemodule",
        "change_coursemodule",
        "delete_coursemodule",
        "view_coursemodule",
        # Content
        "add_modulecontent",
        "change_modulecontent",
        "delete_modulecontent",
        "view_modulecontent",
        # Assignments
        "add_assignment",
        "change_assignment",
        "delete_assignment",
        "view_assignment",
        "view_assignmentsubmission",
        "add_submissionreview",
        "change_submissionreview",
        "view_submissionreview",
        # Announcements
        "add_courseannouncement",
        "change_courseannouncement",
        "delete_courseannouncement",
        "view_courseannouncement",
        # Enrollments
        "add_courseenrollment",
        "change_courseenrollment",
        "view_courseenrollment",
        # Progress
        "view_contentprogress",
        "add_contentprogress",
        "change_contentprogress",
        "view_moduleprogress",
        # Certificates (issue from courses)
        "add_certificate",
        "change_certificate",
        "view_certificate",
        "add_certificatetemplate",
        "change_certificatetemplate",
        "view_certificatetemplate",
        "can_issue_certificate",
        "can_manage_templates",
        # Events (view for hybrid courses)
        "view_event",
        # Registrations (view)
        "view_registration",
        # Feedback
        "add_eventfeedback",
        "view_eventfeedback",
        # Badges
        "view_issuedbadge",
    ],
    "instructor": [
        # Courses (assigned-course instructional access only)
        "view_course",
        "view_coursemodule",
        "view_eventmodule",
        # Content
        "view_modulecontent",
        # Assignments and grading
        "view_assignment",
        "view_assignmentsubmission",
        "add_submissionreview",
        "change_submissionreview",
        "view_submissionreview",
        # Announcements
        "add_courseannouncement",
        "change_courseannouncement",
        "view_courseannouncement",
        # Enrollments and progress
        "view_courseenrollment",
        "view_contentprogress",
        "view_moduleprogress",
        # Related read access
        "view_event",
        "view_registration",
    ],
    # Admin group inherits the union of every other group's permissions.
    # Resolved at runtime in handle() below — the sentinel "__all__" triggers
    # the merge so new permissions added to any other group propagate.
    "admin": "__all__",
}


class Command(BaseCommand):
    help = "Create institutional role groups with permissions"

    def handle(self, *args, **options):
        # Materialise the union for the admin group before iterating, so we
        # capture the final state of every other group.
        admin_codenames: set[str] = set()
        for group_name, perm_codenames in GROUP_PERMISSIONS.items():
            if perm_codenames != "__all__":
                admin_codenames.update(perm_codenames)

        for group_name, perm_codenames in GROUP_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            action = "Created" if created else "Updated"

            if perm_codenames == "__all__":
                resolved = sorted(admin_codenames)
            else:
                resolved = perm_codenames

            perms = Permission.objects.filter(codename__in=resolved)
            found_codenames = set(perms.values_list("codename", flat=True))
            missing = set(resolved) - found_codenames

            if missing:
                self.stdout.write(
                    self.style.WARNING(f"  Missing permissions for {group_name}: {missing}")
                )

            group.permissions.set(perms)
            self.stdout.write(
                self.style.SUCCESS(f"{action} group '{group_name}' with {perms.count()} permissions")
            )

        self.stdout.write(self.style.SUCCESS("\nAll groups set up successfully."))
