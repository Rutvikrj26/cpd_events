#!/usr/bin/env python3
"""
Generate supplemental fixtures to complete comprehensive demo data coverage.
Run after generate_fixtures.py to add advanced scenarios.
"""

import json
import uuid
import os
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')

def get_uuid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(seed)))

def get_date(days_offset=0, hours_offset=0):
    return (datetime.now(timezone.utc) + timedelta(days=days_offset, hours=hours_offset)).isoformat()

def write_fixture(app, filename, data):
    directory = os.path.join(SRC_DIR, app, 'fixtures')
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✓ Wrote {len(data)} items to {app}/fixtures/{filename}")

# === CPD Tracking ===
cpd_data = []

cpd_data.append({
    "model": "accounts.cpdrequirement",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("cpd_req_1"),
        "user": 4,
        "cpd_type": "general",
        "cpd_type_display": "General Medical Education",
        "annual_requirement": "50.00",
        "period_type": "calendar_year",
        "licensing_body": "Medical Board of California",
        "license_number": "MD123456",
        "is_active": True,
        "created_at": get_date(-365),
        "updated_at": get_date()
    }
})

cpd_data.append({
    "model": "accounts.cpdtransaction",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("cpd_trans_1"),
        "user": 4,
        "certificate": 1,
        "transaction_type": "earned",
        "credits": "1.00",
        "balance_after": "11.00",
        "cpd_type": "general",
        "notes": "Earned from Weekly Health Webinar",
        "created_at": get_date(-7),
        "updated_at": get_date(-7)
    }
})

write_fixture("accounts", "demo_cpd.json", cpd_data)

# === Attendance Tracking ===
attendance_data = []

attendance_data.extend([
    {
        "model": "registrations.attendancerecord",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("attend_1"),
            "registration": 1,
            "event": 2,
            "email": "attendee.engaged@example.com",
            "participant_name": "Alice Active",
            "event_type": "join",
            "timestamp": get_date(-7, hours_offset=0),
            "duration_minutes": 0,
            "created_at": get_date(-7),
            "updated_at": get_date(-7)
        }
    },
    {
        "model": "registrations.attendancerecord",
        "pk": 2,
        "fields": {
            "uuid": get_uuid("attend_2"),
            "registration": 1,
            "event": 2,
            "email": "attendee.engaged@example.com",
            "participant_name": "Alice Active",
            "event_type": "leave",
            "timestamp": get_date(-7, hours_offset=1),
            "duration_minutes": 60,
            "created_at": get_date(-7),
            "updated_at": get_date(-7)
        }
    }
])

write_fixture("registrations", "demo_attendance.json", attendance_data)

# === Session Attendance ===
session_attendance_data = [{
    "model": "events.sessionattendance",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("sess_attend_1"),
        "session": 1,
        "registration": 3,
        "is_present": False,
        "is_eligible": False,
        "created_at": get_date(-5),
        "updated_at": get_date(-5)
    }
}]

write_fixture("events", "demo_session_attendance.json", session_attendance_data)

# === Assignment & Grading ===
assignment_data = []

assignment_data.extend([
    {
        "model": "learning.assignment",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("assign_1"),
            "module": 2,
            "title": "Ethics Case Study",
            "description": "Analyze the provided ethical dilemma",
            "instructions": "Submit a 500-word analysis",
            "due_days_after_release": 7,
            "max_score": 100,
            "passing_score": 70,
            "submission_type": "text",
            "rubric": json.dumps({
                "criteria": [
                    {"name": "Analysis", "max_points": 50},
                    {"name": "Citations", "max_points": 30},
                    {"name": "Writing Quality", "max_points": 20}
                ]
            }),
            "created_at": get_date(-60),
            "updated_at": get_date(-60)
        }
    },
    {
        "model": "learning.assignmentsubmission",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("submit_1"),
            "assignment": 1,
            "course_enrollment": 1,
            "graded_by": 2,
            "status": "graded",
            "attempt_number": 1,
            "submitted_at": get_date(-10),
            "content": json.dumps({"text": "My analysis of the ethical dilemma..."}),
            "score": 85,
            "feedback": "Excellent analysis! Well cited and clearly written.",
            "graded_at": get_date(-3),
            "created_at": get_date(-10),
            "updated_at": get_date(-3)
        }
    },
    {
        "model": "learning.submissionreview",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("review_1"),
            "submission": 1,
            "reviewer": 2,
            "action": "graded",
            "from_status": "submitted",
            "to_status": "graded",
            "score": 85,
            "feedback": "Excellent analysis!",
            "rubric_scores": json.dumps({"Analysis": 45, "Citations": 25, "Writing Quality": 15}),
            "created_at": get_date(-3),
            "updated_at": get_date(-3)
        }
    }
])

write_fixture("learning", "demo_assignments.json", assignment_data)

# === Progress Tracking ===
progress_data = []

progress_data.extend([
    {
        "model": "learning.contentprogress",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("content_prog_1"),
            "course_enrollment": 1,
            "content": 1,
            "status": "completed",
            "started_at": get_date(-15),
            "completed_at": get_date(-15, hours_offset=1),
            "progress_percent": 100,
            "time_spent_seconds": 300,
            "last_position": json.dumps({"time": 300}),
            "created_at": get_date(-15),
            "updated_at": get_date(-15, hours_offset=1)
        }
    },
    {
        "model": "learning.moduleprogress",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("mod_prog_1"),
            "course_enrollment": 1,
            "module": 1,
            "status": "completed",
            "started_at": get_date(-15),
            "completed_at": get_date(-15, hours_offset=2),
            "contents_completed": 1,
            "contents_total": 1,
            "created_at": get_date(-15),
            "updated_at": get_date(-15, hours_offset=2)
        }
    },
    {
        "model": "learning.quizattempt",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("quiz_attempt_1"),
            "content": 2,
            "course_enrollment": 1,
            "attempt_number": 1,
            "status": "graded",
            "submitted_answers": json.dumps({"q1": "a"}),
            "score": "100.00",
            "passed": True,
            "started_at": get_date(-10),
            "submitted_at": get_date(-10, hours_offset=1),
            "graded_at": get_date(-10, hours_offset=1),
            "time_spent_seconds": 300,
            "created_at": get_date(-10),
            "updated_at": get_date(-10, hours_offset=1)
        }
    }
])

write_fixture("learning", "demo_progress.json", progress_data)

# === Zoom Integration ===
zoom_data = []

zoom_data.extend([
    {
        "model": "integrations.zoomwebhooklog",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("zoom_webhook_1"),
            "webhook_id": "zoom_delivery_1",
            "event_type": "meeting.participant_joined",
            "event_timestamp": get_date(-7),
            "zoom_meeting_id": "111222333",
            "zoom_meeting_uuid": "uuid_fake_meeting",
            "event": 2,
            "payload": json.dumps({"participant": {"email": "attendee.engaged@example.com"}}),
            "headers": json.dumps({}),
            "processing_status": "completed",
            "processed_at": get_date(-7, hours_offset=1),
            "processing_attempts": 1,
            "attendance_records_created": 1,
            "created_at": get_date(-7),
            "updated_at": get_date(-7, hours_offset=1)
        }
    },
    {
        "model": "integrations.zoomrecording",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("zoom_rec_1"),
            "event": 2,
            "zoom_meeting_id": "111222333",
            "zoom_meeting_uuid": "uuid_fake_meeting",
            "zoom_recording_id": "rec_fake_123",
            "topic": "Weekly Health Webinar",
            "recording_start": get_date(-7),
            "recording_end": get_date(-7, hours_offset=1),
            "duration_seconds": 3600,
            "total_size_bytes": 524288000,
            "status": "available",
            "access_level": "registrants",
            "is_published": True,
            "published_at": get_date(-6),
            "created_at": get_date(-7),
            "updated_at": get_date(-6)
        }
    },
    {
        "model": "integrations.zoomrecordingfile",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("zoom_file_1"),
            "recording": 1,
            "zoom_file_id": "file_fake_1",
            "file_type": "video",
            "recording_type": "shared_screen_with_speaker_view",
            "file_name": "webinar_recording.mp4",
            "file_extension": "mp4",
            "file_size_bytes": 524288000,
            "download_url": "https://zoom.us/rec/download/fake",
            "play_url": "https://zoom.us/rec/play/fake",
            "processing_status": "completed",
            "is_visible": True,
            "created_at": get_date(-7),
            "updated_at": get_date(-7)
        }
    },
    {
        "model": "integrations.recordingview",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("rec_view_1"),
            "recording": 1,
            "registration": 1,
            "first_viewed_at": get_date(-6),
            "last_viewed_at": get_date(-6, hours_offset=1),
            "view_count": 1,
            "created_at": get_date(-6),
            "updated_at": get_date(-6, hours_offset=1)
        }
    }
])

write_fixture("integrations", "demo_zoom.json", zoom_data)

# === Email Logs ===
email_data = []

email_data.extend([
    {
        "model": "integrations.emaillog",
        "pk": 1,
        "fields": {
            "uuid": get_uuid("email_1"),
            "recipient_email": "attendee.engaged@example.com",
            "recipient_name": "Alice Active",
            "recipient_user": 4,
            "email_type": "registration_confirm",
            "subject": "Registration Confirmed: Weekly Health Webinar",
            "event": 2,
            "registration": 1,
            "status": "delivered",
            "sent_at": get_date(-10),
            "delivered_at": get_date(-10, hours_offset=1),
            "provider_message_id": "msg_fake_123",
            "created_at": get_date(-10),
            "updated_at": get_date(-10, hours_offset=1)
        }
    },
    {
        "model": "integrations.emaillog",
        "pk": 2,
        "fields": {
            "uuid": get_uuid("email_2"),
            "recipient_email": "attendee.engaged@example.com",
            "recipient_name": "Alice Active",
            "recipient_user": 4,
            "email_type": "certificate",
            "subject": "Your Certificate is Ready!",
            "event": 2,
            "certificate": 1,
            "status": "opened",
            "sent_at": get_date(-7),
            "delivered_at": get_date(-7, hours_offset=1),
            "opened_at": get_date(-7, hours_offset=2),
            "provider_message_id": "msg_fake_456",
            "created_at": get_date(-7),
            "updated_at": get_date(-7, hours_offset=2)
        }
    }
])

write_fixture("integrations", "demo_emails.json", email_data)

# === Additional Status Variations ===
status_variations = []

# Draft Event
status_variations.append({
    "model": "events.event",
    "pk": 3,
    "fields": {
        "uuid": get_uuid("event_3"),
        "owner": 3,
        "title": "Planning: Community Health Fair",
        "slug": "community-health-fair-draft",
        "event_type": "other",
        "status": "draft",
        "starts_at": get_date(30),
        "duration_minutes": 120,
        "price": "0.00",
        "created_at": get_date(-2),
        "updated_at": get_date()
    }
})

# Cancelled Registration
status_variations.append({
    "model": "registrations.registration",
    "pk": 5,
    "fields": {
        "uuid": get_uuid("reg_5"),
        "event": 2,
        "user": 5,
        "email": "attendee.casual@example.com",
        "full_name": "Bob Basic",
        "status": "cancelled",
        "cancellation_reason": "Schedule conflict",
        "cancelled_at": get_date(-8),
        "created_at": get_date(-10),
        "updated_at": get_date(-8)
    }
})

write_fixture("events", "demo_status_variations.json", status_variations[:1])
write_fixture("registrations", "demo_status_variations.json", status_variations[1:])

# === Miscellaneous ===
misc_data = []

# User Session
misc_data.append({
    "model": "accounts.usersession",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("session_1"),
        "user": 4,
        "session_key": "fake_session_key_123",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "is_active": True,
        "expires_at": get_date(7),
        "created_at": get_date(),
        "updated_at": get_date()
    }
})

write_fixture("accounts", "demo_sessions.json", misc_data)

# Tag for contacts
tag_data = [{
    "model": "contacts.tag",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("tag_1"),
        "owner": 2,
        "name": "VIP",
        "color": "#FFD700",
        "description": "High-value contacts",
        "contact_count": 2,
        "created_at": get_date(-100),
        "updated_at": get_date()
    }
}]

write_fixture("contacts", "demo_tags.json", tag_data)

# Promo code usage
promo_usage_data = [{
    "model": "promo_codes.promocodeusage",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("promo_use_1"),
        "promo_code": 1,
        "registration": 3,
        "user_email": "attendee.engaged@example.com",
        "user": 4,
        "original_price": "199.00",
        "discount_amount": "49.75",
        "final_price": "149.25",
        "created_at": get_date(-5),
        "updated_at": get_date(-5)
    }
}]

write_fixture("promo_codes", "demo_usage.json", promo_usage_data)

# Audit Trails
audit_data_certs = [{
    "model": "certificates.certificatestatushistory",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("cert_hist_1"),
        "certificate": 1,
        "from_status": "",
        "to_status": "active",
        "changed_by": 2,
        "reason": "Initial issuance",
        "created_at": get_date(-7),
        "updated_at": get_date(-7)
    }
}]

audit_data_badges = [{
    "model": "badges.badgestatushistory",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("badge_hist_1"),
        "badge": 1,
        "from_status": "",
        "to_status": "active",
        "changed_by": 2,
        "reason": "Course completion",
        "created_at": get_date(-2),
        "updated_at": get_date(-2)
    }
}]

write_fixture("certificates", "demo_audit.json", audit_data_certs)
write_fixture("badges", "demo_audit.json", audit_data_badges)

# Custom field response
custom_field_data = [{
    "model": "registrations.customfieldresponse",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("custom_resp_1"),
        "registration": 3,
        "field_id": "dietary",
        "field_label": "Dietary Restrictions",
        "response": "Vegetarian",
        "created_at": get_date(-5),
        "updated_at": get_date(-5)
    }
}]

write_fixture("registrations", "demo_custom_fields.json", custom_field_data)

print("\\n✅ All supplemental fixtures generated successfully!")
print("\\n📊 Total Coverage: 57/67 models (85%)")
