"""
Management command to create Django Groups with their permissions.

Usage: python manage.py setup_groups

This creates the four institutional roles (learner, organizer, instructor, admin)
and assigns the appropriate Django permissions to each group.

Role model:
- organizer: manages live events (event CRUD, speakers, promo codes, event certificates/badges).
- instructor: manages courses and programs; can schedule live sessions inside courses
  (session-scheduling subset of event perms, but cannot create top-level events).
- learner: consumes content.
- admin: union of all perms.

Run this after migrations to ensure groups and permissions are set up.
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


# Legacy group names that have been retired and must be deleted on every run so
# stale group rows don't carry obsolete permission assignments forward.
RETIRED_GROUPS = ("educator", "course_manager")


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
    "organizer": [
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
        # Certificates (issue from events)
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
        # Badges (event-issued)
        "add_badgetemplate",
        "change_badgetemplate",
        "delete_badgetemplate",
        "view_badgetemplate",
        "add_issuedbadge",
        "view_issuedbadge",
    ],
    "instructor": [
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
        # Assignments + grading
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
        # Course badges
        "add_badgetemplate",
        "change_badgetemplate",
        "view_badgetemplate",
        "add_issuedbadge",
        "view_issuedbadge",
        # Session scheduling inside courses — instructors need to host live
        # sessions as part of a course, but not create top-level events.
        "add_eventsession",
        "change_eventsession",
        "view_eventsession",
        "add_sessionattendance",
        "change_sessionattendance",
        "view_sessionattendance",
        # Related read access
        "view_event",
        "view_registration",
        # Feedback (on sessions they deliver)
        "add_eventfeedback",
        "view_eventfeedback",
    ],
    # Admin group inherits the union of every other group's permissions.
    # Resolved at runtime in handle() below — the sentinel "__all__" triggers
    # the merge so new permissions added to any other group propagate.
    "admin": "__all__",
}


class Command(BaseCommand):
    help = "Create institutional role groups with permissions"

    def handle(self, *args, **options):
        # Drop retired groups so their obsolete permission rows and any stale
        # user memberships are cleared. Re-running this command is idempotent.
        retired_qs = Group.objects.filter(name__in=RETIRED_GROUPS)
        if retired_qs.exists():
            names = ", ".join(retired_qs.values_list("name", flat=True))
            retired_qs.delete()
            self.stdout.write(self.style.WARNING(f"Deleted retired groups: {names}"))

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
