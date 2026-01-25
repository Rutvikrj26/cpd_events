
import json
import uuid
import os
from datetime import datetime, timedelta, timezone

# Constants
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')

def get_uuid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(seed)))

def get_date(days_offset=0):
    return (datetime.now(timezone.utc) + timedelta(days=days_offset)).isoformat()

def write_fixture(app, filename, data):
    directory = os.path.join(SRC_DIR, app, 'fixtures')
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(data)} items to {filepath}")

# Data Storage
users = []
billing = []
assets_certs = []
assets_badges = []
assets_contacts = []
assets_promos = []
events_data = []
learning_data = []
registrations_data = []
feedback_data = []

# 1. Accounts
# Password hash for 'demo123'
PASSWORD_HASH = "pbkdf2_sha256$1200000$oluUd8pakoVBuUVJdxQf72$/H2PRGoIh8w/F7+8mD35yIP6C7U83nTWIa9KLPI3Ly8="

user_list = [
    (1, 'admin@cpdevents.com', 'Super', 'Admin', True, True, None),
    (2, 'organizer.pro@example.com', 'Sarah', 'Chen', False, False, 'HealthTech Solutions'),
    (3, 'organizer.basic@example.com', 'John', 'Doe', False, False, 'Local Meetups'),
    (4, 'attendee.engaged@example.com', 'Alice', 'Active', False, False, 'General Hospital'),
    (5, 'attendee.casual@example.com', 'Bob', 'Basic', False, False, None),
    (6, 'speaker.guest@example.com', 'Alan', 'Grant', False, False, 'Paleontology Dept')
]

for pk, email, first, last, is_staff, is_superuser, org in user_list:
    users.append({
        "model": "accounts.user",
        "pk": pk,
        "fields": {
            "uuid": get_uuid(f"user_{pk}"),
            "password": PASSWORD_HASH,
            "last_login": get_date(),
            "is_superuser": is_superuser,
            "email": email,
            "first_name": first,
            "last_name": last,
            "is_staff": is_staff,
            "is_active": True,
            "email_verified": True,
            "organization_name": org or "",
            "professional_title": "Dr." if pk in [2, 4, 6] else "",
            "stripe_charges_enabled": pk == 2,
            "created_at": get_date(-365),
            "updated_at": get_date()
        }
    })

# Zoom Connection for Pro Org
users.append({
    "model": "accounts.zoomconnection",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("zoom_1"),
        "user": 2,
        "access_token": "encrypted_fake_token",
        "refresh_token": "encrypted_fake_refresh",
        "token_expires_at": get_date(30),
        "zoom_user_id": "zoom_user_pro",
        "zoom_email": "organizer.pro@example.com",
        "is_active": True,
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})

# 2. Billing
# Stripe Products
products = [
    (1, "attendee", "Basic", 1),
    (2, "pro", "Pro", None)
]
for pk, plan, name, limit in products:
    billing.append({
        "model": "billing.stripeproduct",
        "pk": pk,
        "fields": {
            "uuid": get_uuid(f"prod_{pk}"),
            "name": name,
            "plan": plan,
            "is_active": True,
            "events_per_month": limit,
            "stripe_product_id": f"prod_fake_{pk}",
            "created_at": get_date(-365),
            "updated_at": get_date()
        }
    })

# Stripe Prices
billing.append({
    "model": "billing.stripeprice",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("price_1"),
        "product": 1,
        "amount_cents": 0,
        "billing_interval": "month",
        "stripe_price_id": "price_free",
        "created_at": get_date(-365),
        "updated_at": get_date()
    }
})
billing.append({
    "model": "billing.stripeprice",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("price_2"),
        "product": 2,
        "amount_cents": 9900,
        "billing_interval": "month",
        "stripe_price_id": "price_pro_month",
        "created_at": get_date(-365),
        "updated_at": get_date()
    }
})

# Subscriptions
# Pro Org
billing.append({
    "model": "billing.subscription",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("sub_1"),
        "user": 2,
        "plan": "pro",
        "status": "active",
        "current_period_start": get_date(-15),
        "current_period_end": get_date(15),
        "stripe_subscription_id": "sub_fake_pro",
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})
# Basic Org - Fixed: should be "organizer" plan
billing.append({
    "model": "billing.subscription",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("sub_2"),
        "user": 3,
        "plan": "organizer",  # Fixed: was "attendee"
        "status": "active",
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})

# Attendee subscriptions (users 4, 5, 6)
for user_pk in [4, 5, 6]:
    pk = user_pk - 1  # subscription pks 3, 4, 5
    billing.append({
        "model": "billing.subscription",
        "pk": pk,
        "fields": {
            "uuid": get_uuid(f"sub_{pk}"),
            "user": user_pk,
            "plan": "attendee",
            "status": "active",
            "created_at": get_date(-30),
            "updated_at": get_date()
        }
    })

# Payment Method
billing.append({
    "model": "billing.paymentmethod",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("pm_1"),
        "user": 2,
        "stripe_payment_method_id": "pm_fake_visa",
        "card_brand": "visa",
        "card_last4": "4242",
        "is_default": True,
        "card_exp_month": 12,
        "card_exp_year": 2030,
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})

# Invoices
for i in range(3):
    date_start = get_date(-30 * (i + 1))
    date_end = get_date(-30 * i)
    billing.append({
        "model": "billing.invoice",
        "pk": i + 1,
        "fields": {
            "uuid": get_uuid(f"invoice_{i}"),
            "user": 2,
            "subscription": 1,
            "stripe_invoice_id": f"in_fake_{i}",
            "amount_cents": 9900,
            "status": "paid",
            "period_start": date_start,
            "period_end": date_end,
            "paid_at": date_start,
            "created_at": date_start,
            "updated_at": date_start
        }
    })

# 3. Assets
# Certificate Template
assets_certs.append({
    "model": "certificates.certificatetemplate",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("cert_temp_1"),
        "owner": 2,
        "name": "HealthTech Standard",
        "is_active": True,
        "is_default": True,
        "width_px": 1056,
        "height_px": 816,
        "created_at": get_date(-100),
        "updated_at": get_date()
    }
})

# Badge Template
assets_badges.append({
    "model": "badges.badgetemplate",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("badge_temp_1"),
        "owner": 2,
        "name": "Certified Expert",
        "is_active": True,
        "created_at": get_date(-100),
        "updated_at": get_date()
    }
})

# Contact List & Contacts
assets_contacts.append({
    "model": "contacts.contactlist",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("list_1"),
        "owner": 2,
        "name": "Newsletter Subscribers",
        "contact_count": 5,
        "created_at": get_date(-100),
        "updated_at": get_date()
    }
})

for i in range(5):
    assets_contacts.append({
        "model": "contacts.contact",
        "pk": i + 1,
        "fields": {
            "uuid": get_uuid(f"contact_{i}"),
            "contact_list": 1,
            "email": f"contact{i}@example.com",
            "full_name": f"Contact {i}",
            "created_at": get_date(-90),
            "updated_at": get_date()
        }
    })

# Promo Code
assets_promos.append({
    "model": "promo_codes.promocode",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("promo_1"),
        "owner": 2,
        "code": "EARLYBIRD25",
        "discount_type": "percentage",
        "discount_value": "25.00",
        "is_active": True,
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})

# 4. Events
# Event 1: Conference (Upcoming)
events_data.append({
    "model": "events.event",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("event_1"),
        "owner": 2,
        "title": "Future of Medicine 2025",
        "slug": "future-medicine-2025",
        "event_type": "conference", # Not in choices, mapped to other/workshop? TextChoices allows strings. 'webinar' is a choice.
        # Let's check choices. WEBINAR, WORKSHOP, TRAINING, LECTURE, OTHER.
        # I'll use 'workshop' or 'other'. Let's use 'workshop'.
        "event_type": "workshop",
        "status": "published",
        "starts_at": get_date(14),
        "duration_minutes": 480,
        "price": "199.00",
        "currency": "USD",
        "is_multi_session": True,
        "cpd_enabled": True,
        "cpd_credit_value": "10.00",
        "certificates_enabled": True,
        "certificate_template": 1,
        "zoom_meeting_id": "999888777",
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})

# Sessions for Event 1
events_data.append({
    "model": "events.eventsession",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("session_1"),
        "event": 1,
        "title": "Keynote: AI in Healthcare",
        "starts_at": get_date(14),
        "duration_minutes": 60,
        "is_mandatory": True,
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})
events_data.append({
    "model": "events.eventsession",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("session_2"),
        "event": 1,
        "title": "Ethics Workshop",
        "starts_at": get_date(14.08), # +2 hours roughly
        "duration_minutes": 90,
        "is_mandatory": True,
        "created_at": get_date(-30),
        "updated_at": get_date()
    }
})

# Event 2: Webinar (Past)
events_data.append({
    "model": "events.event",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("event_2"),
        "owner": 2,
        "title": "Weekly Health Webinar",
        "slug": "weekly-health-webinar",
        "event_type": "webinar",
        "status": "completed",
        "starts_at": get_date(-7),
        "actual_start_at": get_date(-7),
        "actual_end_at": get_date(-6.95),
        "duration_minutes": 60,
        "price": "0.00",
        "cpd_enabled": True,
        "cpd_credit_value": "1.00",
        "certificates_enabled": True,
        "certificate_template": 1,
        "auto_issue_certificates": True,
        "zoom_meeting_id": "111222333",
        "attendance_count": 1,
        "registration_count": 2,
        "certificate_count": 1,
        "created_at": get_date(-40),
        "updated_at": get_date()
    }
})

# Speaker
events_data.append({
    "model": "events.speaker",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("speaker_1"),
        "owner": 2,
        "name": "Prof. Alan Grant",
        "bio": "Paleontologist",
        "email": "speaker.guest@example.com",
        "is_active": True,
        "created_at": get_date(-40),
        "updated_at": get_date()
    }
})
# Note: ManyToMany fields (Event.speakers) are usually handled in a separate through table or list of IDs in fixtures. 
# In Django JSON fixtures, M2M is a list of PKs on the main model.
# Adding speaker to event 2
events_data[-2]['fields']['speakers'] = [1] # Adding to Weekly Health Webinar

# 5. Learning
# Course
learning_data.append({
    "model": "learning.course",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("course_1"),
        "owner": 2,
        "title": "Medical Ethics 101",
        "slug": "medical-ethics-101",
        "status": "published",
        "price_cents": 0,
        "cpd_credits": "5.00",
        "certificates_enabled": True,
        "certificate_template": 1,
        "badges_enabled": True,
        "badge_template": 1,
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})

# Modules (EventModule)
learning_data.append({
    "model": "learning.eventmodule",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("module_1"),
        "title": "Introduction to Ethics",
        "is_published": True,
        "order": 0,
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})
learning_data.append({
    "model": "learning.eventmodule",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("module_2"),
        "title": "Assessment",
        "is_published": True,
        "order": 1,
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})

# Course Modules (Link)
learning_data.append({
    "model": "learning.coursemodule",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("cm_1"),
        "course": 1,
        "module": 1,
        "order": 0,
        "is_required": True,
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})
learning_data.append({
    "model": "learning.coursemodule",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("cm_2"),
        "course": 1,
        "module": 2,
        "order": 1,
        "is_required": True,
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})

# Content
learning_data.append({
    "model": "learning.modulecontent",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("content_1"),
        "module": 1,
        "title": "Welcome Video",
        "content_type": "video",
        "order": 0,
        "content_data": json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}),
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})
learning_data.append({
    "model": "learning.modulecontent",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("content_2"),
        "module": 2,
        "title": "Final Quiz",
        "content_type": "quiz",
        "order": 0,
        "content_data": json.dumps({
            "passingScore": 70,
            "questions": [
                {
                    "id": "q1",
                    "text": "Is ethics important?",
                    "options": [{"id": "a", "text": "Yes"}, {"id": "b", "text": "No"}],
                    "correctAnswer": "a"
                }
            ]
        }),
        "created_at": get_date(-60),
        "updated_at": get_date()
    }
})

# 6. Engagement (Registrations & Enrollments)
# Reg 1: Engaged -> Webinar (Attended)
registrations_data.append({
    "model": "registrations.registration",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("reg_1"),
        "event": 2,
        "user": 4,
        "email": "attendee.engaged@example.com",
        "full_name": "Alice Active",
        "status": "confirmed",
        "attended": True,
        "total_attendance_minutes": 60,
        "attendance_eligible": True,
        "certificate_issued": True,
        "certificate_issued_at": get_date(-7),
        "created_at": get_date(-10),
        "updated_at": get_date(-7)
    }
})

# Certificate for Reg 1
assets_certs.append({
    "model": "certificates.certificate",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("cert_1"),
        "registration": 1,
        "template": 1,
        "issued_by": 2,
        "status": "active",
        "certificate_data": json.dumps({"attendee_name": "Alice Active", "event_title": "Weekly Health Webinar"}),
        "created_at": get_date(-7),
        "updated_at": get_date(-7)
    }
})

# Reg 2: Casual -> Webinar (Missed)
registrations_data.append({
    "model": "registrations.registration",
    "pk": 2,
    "fields": {
        "uuid": get_uuid("reg_2"),
        "event": 2,
        "user": 5,
        "email": "attendee.casual@example.com",
        "full_name": "Bob Basic",
        "status": "confirmed",
        "attended": False,
        "created_at": get_date(-10),
        "updated_at": get_date(-10)
    }
})

# Reg 3: Engaged -> Conf (Paid)
registrations_data.append({
    "model": "registrations.registration",
    "pk": 3,
    "fields": {
        "uuid": get_uuid("reg_3"),
        "event": 1,
        "user": 4,
        "email": "attendee.engaged@example.com",
        "full_name": "Alice Active",
        "status": "confirmed",
        "payment_status": "paid",
        "amount_paid": "199.00",
        "created_at": get_date(-5),
        "updated_at": get_date(-5)
    }
})

# Reg 4: Casual -> Conf (Waitlisted)
registrations_data.append({
    "model": "registrations.registration",
    "pk": 4,
    "fields": {
        "uuid": get_uuid("reg_4"),
        "event": 1,
        "user": 5,
        "email": "attendee.casual@example.com",
        "full_name": "Bob Basic",
        "status": "waitlisted",
        "created_at": get_date(-5),
        "updated_at": get_date(-5)
    }
})

# Feedback for Reg 1
feedback_data.append({
    "model": "feedback.eventfeedback",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("feed_1"),
        "event": 2,
        "registration": 1,
        "rating": 5,
        "content_quality_rating": 5,
        "speaker_rating": 5,
        "comments": "Excellent session!",
        "created_at": get_date(-7),
        "updated_at": get_date(-7)
    }
})

# Enrollment: Engaged -> Ethics (Completed)
learning_data.append({
    "model": "learning.courseenrollment",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("enroll_1"),
        "course": 1,
        "user": 4,
        "status": "completed",
        "progress_percent": 100,
        "certificate_issued": True,
        "certificate_issued_at": get_date(-2),
        "created_at": get_date(-20),
        "updated_at": get_date(-2)
    }
})

# Badge for Enrollment 1
assets_badges.append({
    "model": "badges.issuedbadge",
    "pk": 1,
    "fields": {
        "uuid": get_uuid("badge_1"),
        "course_enrollment": 1,
        "template": 1,
        "recipient": 4,
        "issued_by": 2,
        "status": "active",
        "issued_at": get_date(-2),
        "created_at": get_date(-2),
        "updated_at": get_date(-2)
    }
})

# Write Files
write_fixture("accounts", "demo_users.json", users)
write_fixture("billing", "demo_billing.json", billing)
write_fixture("certificates", "demo_certificates.json", assets_certs)
write_fixture("badges", "demo_badges.json", assets_badges)
write_fixture("contacts", "demo_contacts.json", assets_contacts)
write_fixture("promo_codes", "demo_promos.json", assets_promos)
write_fixture("events", "demo_events.json", events_data)
write_fixture("learning", "demo_learning.json", learning_data)
write_fixture("registrations", "demo_registrations.json", registrations_data)
write_fixture("feedback", "demo_feedback.json", feedback_data)

