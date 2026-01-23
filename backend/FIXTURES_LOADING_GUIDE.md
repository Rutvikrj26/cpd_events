# Demo Fixtures - Comprehensive Loading Guide

## ✅ Status: 85% Coverage (57/67 models)

We have created comprehensive demo fixtures covering all major functionality of the CPD Events platform.

## 📦 Generated Fixtures

### Core Fixtures (Base Script: `generate_fixtures.py`)
1. **accounts/demo_users.json** - 7 users (admin, organizers, attendees, speakers)
2. **billing/demo_billing.json** - Subscriptions, products, prices, invoices, payment methods  
3. **certificates/demo_certificates.json** - Certificate templates and issued certificates
4. **badges/demo_badges.json** - Badge templates and issued badges
5. **contacts/demo_contacts.json** - Contact lists and 5 contacts
6. **promo_codes/demo_promos.json** - Active promo codes
7. **events/demo_events.json** - Events (upcoming conference, past webinar) + sessions + speakers
8. **learning/demo_learning.json** - Course + modules + content + enrollment
9. **registrations/demo_registrations.json** - 4 registrations with various statuses
10. **feedback/demo_feedback.json** - Event feedback from attendees

### Supplemental Fixtures (Script: `generate_supplemental_fixtures.py`)
11. **accounts/demo_cpd.json** - CPD requirements and credit transactions
12. **accounts/demo_sessions.json** - Active user sessions
13. **registrations/demo_attendance.json** - Raw attendance records (join/leave events)
14. **registrations/demo_custom_fields.json** - Custom field responses
15. **registrations/demo_status_variations.json** - Cancelled registrations
16. **events/demo_session_attendance.json** - Session-level attendance tracking
17. **events/demo_status_variations.json** - Draft events  
18. **learning/demo_assignments.json** - Assignments, submissions, reviews
19. **learning/demo_progress.json** - Content progress, module progress, quiz attempts
20. **integrations/demo_zoom.json** - Zoom webhooks, recordings, files, views
21. **integrations/demo_emails.json** - Email delivery logs
22. **contacts/demo_tags.json** - Contact tags for segmentation
23. **promo_codes/demo_usage.json** - Promo code usage tracking
24. **certificates/demo_audit.json** - Certificate status history
25. **badges/demo_audit.json** - Badge status history

## 🚀 Loading All Fixtures

### Option 1: Load Everything at Once

```bash
cd backend/src

python manage.py loaddata \
    demo_users \
    demo_sessions \
    demo_cpd \
    demo_billing \
    demo_certificates \
    demo_audit \
    demo_badges \
    demo_contacts \
    demo_tags \
    demo_promos \
    demo_usage \
    demo_events \
    demo_session_attendance \
    demo_status_variations \
    demo_learning \
    demo_assignments \
    demo_progress \
    demo_registrations \
    demo_attendance \
    demo_custom_fields \
    demo_feedback \
    demo_zoom \
    demo_emails
```

### Option 2: Load by Category

**Users & Auth:**
```bash
python manage.py loaddata demo_users demo_sessions demo_cpd
```

**Billing:**
```bash
python manage.py loaddata demo_billing
```

**Assets (Templates, Contacts, Promos):**
```bash
python manage.py loaddata demo_certificates demo_badges demo_contacts demo_tags demo_promos
```

**Events:**
```bash
python manage.py loaddata demo_events demo_session_attendance
```

**Learning (Courses/LMS):**
```bash
python manage.py loaddata demo_learning demo_assignments demo_progress
```

**Engagement (Registrations, Attendance, Feedback):**
```bash
python manage.py loaddata demo_registrations demo_attendance demo_custom_fields demo_feedback demo_usage
```

**Integrations (Zoom, Email):**
```bash
python manage.py loaddata demo_zoom demo_emails
```

**Audit Trails:**
```bash
python manage.py loaddata certificates/demo_audit badges/demo_audit
```

**Status Variations:**
```bash
python manage.py loaddata events/demo_status_variations registrations/demo_status_variations
```

## 📊 What's Included

### Users (6 demo accounts)
| Email | Role | Password | Description |
|-------|------|----------|-------------|
| `admin@cpdevents.com` | Admin | `demo123` | Superuser |
| `organizer.pro@example.com` | Pro Organizer | `demo123` | Paid plan, Zoom connected, owns most content |
| `organizer.basic@example.com` | Basic Organizer | `demo123` | Free tier |
| `attendee.engaged@example.com` | Active Learner | `demo123` | Completed courses, earned certificates |
| `attendee.casual@example.com` | Casual Attendee | `demo123` | Some activity |
| `speaker.guest@example.com` | Guest Speaker | `demo123` | Linked to webinar |

### Events
- **Future of Medicine 2025**: Upcoming paid conference ($199), 2 sessions, CPD-enabled
- **Weekly Health Webinar**: Past free webinar, completed with certificates issued
- **Community Health Fair**: Draft event (planning stage)

### Courses
- **Medical Ethics 101**: Self-paced, free, with video + quiz modules  
- Enrollment: Alice completed it, earned certificate + badge

### Key Scenarios Demonstrated
✅ **CPD Tracking**: Alice has 50 credit annual requirement, earned 11 so far  
✅ **Attendance**: Raw join/leave logs from Zoom webhooks  
✅ **Grading**: Alice submitted assignment, received 85/100  
✅ **Progress**: Track video views, quiz attempts, module completion  
✅ **Zoom Integration**: Webhook processing, cloud recording access  
✅ **Email Tracking**: Registration confirmations, certificate delivery, open tracking  
✅ **Promo Codes**: Alice used EARLYBIRD25 for 25% off conference  
✅ **Custom Fields**: Dietary restrictions captured during registration  
✅ **Audit Trails**: Certificate/badge status history  
✅ **Status Variations**: Draft events, cancelled registrations  

## 🔄 Regenerating Fixtures

Fixtures use deterministic UUIDs and relative dates, so you can regenerate anytime:

```bash
# Regenerate all
python3 backend/scripts/generate_fixtures.py
python3 backend/scripts/generate_supplemental_fixtures.py

# Or regenerate specific categories by editing the scripts
```

## ⚠️ Missing Models (Low Priority)

Still to-do (10 models, 15% remaining):
- `RefundRecord`, `PayoutRequest` (Financial edge cases)
- `CourseSession`, `CourseSessionAttendance` (Hybrid course live sessions)
- `CourseAnnouncement` (Instructor announcements)
- Plus 5 more niche models

These are less critical for initial demos but can be added if needed.

## 🎯 Demo Use Cases

With this data, you can demonstrate:
1. **Organizer Dashboard**: Pro organizer with active events, past completions
2. **Learner Journey**: Alice's full progression through course + event
3. **CPD Compliance**: Requirements tracking and credit accumulation
4. **Certificate Issuance**: Automatic issuance based on attendance
5. **Zoom Integration**: Webhook processing and recording access
6. **Email Engagement**: Delivery, opens, clicks tracking
7. **Promo Code Usage**: Discount application and usage limits
8. **Assignment Grading**: Instructor feedback workflow
9. **Progress Tracking**: Learner dashboards with completion percentages
10. **Audit & Compliance**: Full history of credential status changes

## 📝 Notes

- All passwords are `demo123`
- UUIDs are deterministic (based on seed strings)
- Dates are relative to "now" (stay fresh on regeneration)
- Foreign keys reference existing PKs (maintain referential integrity)
- JSON fields use proper structure for nested data
