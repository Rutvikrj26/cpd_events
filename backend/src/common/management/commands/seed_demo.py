"""Populate the database with a rich demo data set anchored to ``now()``.

Run via ``accredit local seed --reset`` (which flushes, migrates, loads
``00_groups``, runs ``setup_groups``, and then invokes this command).

All dates are computed relative to ``timezone.now()`` at seed time so the
demo stays evergreen. The command is idempotent on ``--reset`` and skips
work it detects already ran on a plain invocation.

Personas produced:

* Learner ``Dr. Emily Park`` — heavy engagement, many certs/badges, active
  subscription, course completed, assignment graded pass, promo applied.
* Learner ``Dr. Michael Torres`` — blocked/edge paths: payment_failed,
  pending_payment, feedback-gated cert, resubmission flow, refunded course
  purchase, cancelled subscription.
* Learner ``Dr. Aisha Khan`` — early-journey empties, one waitlisted
  registration, one live-now registration, on-demand replay, flagged a
  thread, no badges.
* Organizer ``Dr. James Wilson`` — owns every event/course.
* Instructor ``Dr. Priya Shah`` — grading queue populated; staff on courses.
* Admin ``Dr. Sarah Chen`` — superuser, sees all.

Plus a ``Dr. Alex Rivera`` pending invitation (not loginable).
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


DEMO_PASSWORD_HASH = make_password("demo12345")


class Command(BaseCommand):
    help = "Populate the database with a rich, time-anchored demo data set."

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(self.style.MIGRATE_HEADING(f"Seeding demo data anchored to {now:%Y-%m-%d %H:%M %Z}"))

        with transaction.atomic():
            users = self._build_users(now)
            templates = self._build_templates(now, users)
            speakers = self._build_speakers(users)
            events = self._build_events(now, users, templates, speakers)
            sessions = self._build_event_sessions(now, events)
            registrations = self._build_registrations(now, users, events, sessions)
            courses, programs = self._build_courses_and_programs(now, users, templates)
            enrollments = self._build_course_enrollments(now, users, courses)
            self._build_program_enrollments(now, users, programs)
            self._build_event_modules_and_progress(now, users, events, courses, registrations, enrollments)
            self._build_certificates(now, users, registrations, enrollments, templates)
            self._build_badges(now, users, registrations, enrollments, templates)
            self._build_feedback(now, events, registrations)
            self._build_discussions(now, users, courses)
            self._build_billing(now, users, events, courses)
            self._build_promo_codes(now, users, events, registrations)
            self._build_stripe_events_and_disputes(now, users, events, registrations)
            self._build_notifications(now, users, events, courses)
            self._build_audit_log(now, users)
            self._build_invitations(now, users)
            self._build_cpd_requirements(users)
            self._build_course_announcements(now, users, courses)
            self._build_submission_reviews(now, users)
            self._backfill_attendance_records(now, events, registrations)
            self._build_video_rooms_and_recordings(now, events)
            self._refresh_denormalized_counts(events, courses, programs)
            self._reassert_event_statuses(events, now)

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write("")
        self.stdout.write("Personas (password: demo12345):")
        for tag, email in [
            ("Admin", "admin@utoronto.ca"),
            ("Organizer", "organizer@utoronto.ca"),
            ("Instructor", "priya.shah@utoronto.ca"),
            ("Learner (heavy)", "emily.park@hospital.com"),
            ("Learner (blocked)", "m.torres@clinic.com"),
            ("Learner (empty/live)", "aisha.khan@university.edu"),
        ]:
            self.stdout.write(f"  {tag:<22} {email}")

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def _build_users(self, now):
        from accounts.models import User

        def upsert(email, **fields):
            defaults = {"password": DEMO_PASSWORD_HASH, **fields}
            defaults.setdefault("email_verified", True)
            defaults.setdefault("email_verified_at", now - timedelta(days=90))
            defaults.setdefault("onboarding_completed", True)
            defaults.setdefault("is_active", True)
            user, created = User.objects.update_or_create(email=email, defaults=defaults)
            return user

        admin = upsert(
            "admin@utoronto.ca",
            full_name="Dr. Sarah Chen",
            professional_title="MD, PhD",
            organization_name="University of Toronto",
            timezone="America/Toronto",
            bio="Institution administrator overseeing CPD programs.",
            is_staff=True,
            is_superuser=True,
            last_login_at=now - timedelta(hours=2),
        )
        organizer = upsert(
            "organizer@utoronto.ca",
            full_name="Dr. James Wilson",
            professional_title="MD, FRCPC",
            organization_name="University of Toronto",
            timezone="America/Toronto",
            bio="Emergency medicine physician and medical educator with 15 years of experience.",
            last_login_at=now - timedelta(hours=6),
        )
        instructor = upsert(
            "priya.shah@utoronto.ca",
            full_name="Dr. Priya Shah",
            professional_title="PhD, Clinical Education",
            organization_name="University of Toronto",
            timezone="America/Toronto",
            bio="Faculty lead for course assessments and grading.",
            last_login_at=now - timedelta(hours=4),
        )
        emily = upsert(
            "emily.park@hospital.com",
            full_name="Dr. Emily Park",
            professional_title="MD",
            organization_name="Toronto General Hospital",
            timezone="America/Toronto",
            bio="Internal medicine resident interested in clinical ethics and cardiac care.",
            last_login_at=now - timedelta(hours=1),
        )
        michael = upsert(
            "m.torres@clinic.com",
            full_name="Dr. Michael Torres",
            professional_title="DO",
            organization_name="Lakeside Family Clinic",
            timezone="America/Los_Angeles",
            auth_provider="google",
            google_user_id="google_demo_michael",
            bio="Family medicine physician focused on primary care quality improvement.",
            last_login_at=now - timedelta(days=2),
        )
        aisha = upsert(
            "aisha.khan@university.edu",
            full_name="Dr. Aisha Khan",
            professional_title="PhD",
            organization_name="University of Ottawa",
            timezone="Europe/London",
            # Verified so the demo presenter can actually log in; keep onboarding
            # incomplete so the onboarding/empty-state UI still renders.
            email_verified=True,
            onboarding_completed=False,
            bio="",
            last_login_at=now - timedelta(days=14),
        )

        # Assign groups
        group_names = {
            admin: ["admin"],
            organizer: ["organizer", "instructor"],
            instructor: ["instructor"],
            emily: ["learner"],
            michael: ["learner"],
            aisha: ["learner"],
        }
        for user, names in group_names.items():
            user.groups.clear()
            for name in names:
                group, _ = Group.objects.get_or_create(name=name)
                user.groups.add(group)

        return {
            "admin": admin,
            "organizer": organizer,
            "instructor": instructor,
            "emily": emily,
            "michael": michael,
            "aisha": aisha,
        }

    # ------------------------------------------------------------------
    # Templates (certificates, badges)
    # ------------------------------------------------------------------
    def _build_templates(self, now, users):
        from badges.models import BadgeTemplate
        from certificates.models import CertificateTemplate

        cert_template, _ = CertificateTemplate.objects.update_or_create(
            name="Standard CPD Certificate",
            defaults=dict(
                owner=users["organizer"],
                description="Official CPD completion certificate for medical professionals.",
                file_type="pdf",
                width_px=1056,
                height_px=816,
                orientation="landscape",
                field_positions={
                    "recipient_name": {"x": 528, "y": 350, "fontSize": 28, "fontWeight": "bold", "textAlign": "center"},
                    "event_title": {"x": 528, "y": 420, "fontSize": 18, "textAlign": "center"},
                    "date": {"x": 528, "y": 480, "fontSize": 14, "textAlign": "center"},
                    "cpd_credits": {"x": 528, "y": 520, "fontSize": 14, "textAlign": "center"},
                    "verification_code": {"x": 528, "y": 750, "fontSize": 10, "textAlign": "center"},
                },
                is_default=True,
                is_active=True,
            ),
        )

        badge_template, _ = BadgeTemplate.objects.update_or_create(
            name="Ethics Certified",
            defaults=dict(
                owner=users["organizer"],
                description="Awarded to healthcare professionals who complete the Clinical Ethics program.",
                width_px=500,
                height_px=500,
                field_positions={
                    "recipient_name": {"x": 250, "y": 380, "fontSize": 16, "textAlign": "center"},
                    "date": {"x": 250, "y": 420, "fontSize": 12, "textAlign": "center"},
                },
                is_active=True,
            ),
        )
        badge_template_cpd, _ = BadgeTemplate.objects.update_or_create(
            name="CPD Champion",
            defaults=dict(
                owner=users["organizer"],
                description="Recognising sustained engagement with continuing professional development.",
                width_px=500,
                height_px=500,
                field_positions={
                    "recipient_name": {"x": 250, "y": 380, "fontSize": 16, "textAlign": "center"},
                },
                is_active=True,
            ),
        )

        return {
            "cert_standard": cert_template,
            "badge_ethics": badge_template,
            "badge_cpd": badge_template_cpd,
        }

    # ------------------------------------------------------------------
    # Speakers
    # ------------------------------------------------------------------
    def _build_speakers(self, users):
        from events.models import Speaker

        singh, _ = Speaker.objects.update_or_create(
            name="Prof. Robert Singh",
            defaults=dict(
                owner=users["organizer"],
                bio="Professor of Bioethics at the University of Toronto with over 20 years of experience.",
                qualifications="PhD Bioethics, MA Philosophy",
                email="r.singh@utoronto.ca",
                linkedin_url="https://linkedin.com/in/robertsingh",
                is_active=True,
            ),
        )
        chang, _ = Speaker.objects.update_or_create(
            name="Dr. Lisa Chang",
            defaults=dict(
                owner=users["organizer"],
                bio="Emergency medicine specialist and certified ACLS instructor.",
                qualifications="MD, FRCPC Emergency Medicine, ACLS Instructor",
                email="l.chang@tgh.ca",
                is_active=True,
            ),
        )
        ortiz, _ = Speaker.objects.update_or_create(
            name="Dr. Ana Ortiz",
            defaults=dict(
                owner=users["organizer"],
                bio="Surgeon-educator specialising in minimally invasive technique training.",
                qualifications="MD, FACS",
                email="a.ortiz@tgh.ca",
                is_active=True,
            ),
        )
        # Additional roster members so the Speakers page looks like a real
        # pool, not a placeholder. These five aren't login personas — they're
        # speaker-profile rows attached to events as needed elsewhere.
        extras = [
            ("Dr. Helen Yamamoto", "Pediatric ICU lead with a focus on respiratory therapy.",
             "MD, FRCPC Pediatric Critical Care", "h.yamamoto@sickkids.ca",
             "https://linkedin.com/in/helenyamamoto"),
            ("Dr. Pierre Beaumont", "Health policy researcher and former CMO.",
             "MD, MPH, FRCPC", "p.beaumont@toh.ca", ""),
            ("Dr. Naomi Adeyemi", "Internal medicine consultant and faculty preceptor.",
             "MD, FRCPC Internal Medicine", "n.adeyemi@sunnybrook.ca",
             "https://linkedin.com/in/naomiadeyemi"),
            ("Dr. Wei-Lin Chen", "Anesthesiologist and CPD curriculum designer.",
             "MD, FRCPC Anesthesia", "w.chen@uhn.ca", ""),
            ("Aria Patel, RN, MN", "Critical-care nurse educator and simulation lead.",
             "RN, MN, CNCC(C)", "a.patel@vch.ca", "https://linkedin.com/in/ariapatel"),
        ]
        for name, bio, quals, email, linkedin in extras:
            Speaker.objects.update_or_create(
                name=name,
                defaults=dict(
                    owner=users["organizer"],
                    bio=bio,
                    qualifications=quals,
                    email=email,
                    linkedin_url=linkedin,
                    is_active=True,
                ),
            )
        return {"singh": singh, "chang": chang, "ortiz": ortiz}

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def _build_events(self, now, users, templates, speakers):
        from events.models import Event

        owner = users["organizer"]
        cert_tpl = templates["cert_standard"]
        badge_tpl = templates["badge_ethics"]

        def mk_event(slug, title, starts_at, *, duration=120, status="published", event_type="webinar",
                     fmt="online", price="0.00", currency="USD", max_attendees=None, waitlist_enabled=False,
                     waitlist_max=None, waitlist_auto_promote=False, cpd_type="general", cpd_value="1.00",
                     require_feedback=False, auto_issue_certs=True, auto_issue_badges=False,
                     badge_template=None, is_multi_session=False, reg_opens=None, reg_closes=None,
                     short_description="", description="", location="", recording_enabled=False,
                     actual_start_at=None, actual_end_at=None, video_enabled=False):
            defaults = dict(
                owner=owner,
                title=title,
                description=description or f"Demo description for {title}.",
                short_description=short_description or title,
                event_type=event_type,
                format=fmt,
                status=status,
                timezone="America/Toronto",
                starts_at=starts_at,
                duration_minutes=duration,
                actual_start_at=actual_start_at,
                actual_end_at=actual_end_at,
                currency=currency,
                price=Decimal(price),
                registration_enabled=True,
                max_attendees=max_attendees,
                waitlist_enabled=waitlist_enabled,
                waitlist_max=waitlist_max,
                waitlist_auto_promote=waitlist_auto_promote,
                allow_guest_registration=True,
                cpd_enabled=True,
                cpd_credit_type=cpd_type,
                cpd_credit_value=Decimal(cpd_value),
                cpd_accreditation_note="Accredited by the Royal College of Physicians and Surgeons of Canada",
                certificates_enabled=True,
                certificate_template=cert_tpl,
                auto_issue_certificates=auto_issue_certs,
                require_feedback_for_certificate=require_feedback,
                badges_enabled=bool(badge_template),
                badge_template=badge_template,
                auto_issue_badges=auto_issue_badges,
                is_public=True,
                is_multi_session=is_multi_session,
                registration_opens_at=reg_opens,
                registration_closes_at=reg_closes,
                location=location,
                recording_enabled=recording_enabled,
                video_settings=(
                    {"enabled": True, "recording_enabled": recording_enabled, "screen_share": True}
                    if video_enabled else {}
                ),
            )
            obj, _ = Event.objects.update_or_create(slug=slug, defaults=defaults)
            return obj

        events = {}
        events["ethics"] = mk_event(
            "clinical-ethics-modern-practice",
            "Clinical Ethics in Modern Practice",
            starts_at=now - timedelta(days=33, hours=4),
            duration=120,
            status=Event.Status.COMPLETED,
            event_type=Event.EventType.WEBINAR,
            price="49.99", currency="USD",
            max_attendees=50, waitlist_enabled=True, waitlist_max=10, waitlist_auto_promote=True,
            cpd_type="ethics", cpd_value="3.00",
            auto_issue_certs=True, badge_template=badge_tpl, auto_issue_badges=True,
            is_multi_session=True,
            reg_opens=now - timedelta(days=75), reg_closes=now - timedelta(days=34),
            short_description="Explore critical ethical challenges in modern healthcare practice.",
            actual_start_at=now - timedelta(days=33, hours=4),
            actual_end_at=now - timedelta(days=33, hours=2),
        )
        events["ethics"].speakers.set([speakers["singh"], speakers["chang"]])

        events["acls"] = mk_event(
            "acls-workshop",
            "Advanced Cardiac Life Support Workshop",
            starts_at=now - timedelta(days=66),
            duration=180,
            status=Event.Status.COMPLETED,
            event_type=Event.EventType.WORKSHOP,
            price="0.00",
            max_attendees=30,
            cpd_type="clinical", cpd_value="4.00",
            auto_issue_certs=True, require_feedback=True,
            short_description="Hands-on ACLS certification workshop.",
            actual_start_at=now - timedelta(days=66),
            actual_end_at=now - timedelta(days=66, hours=-3, minutes=-5),
        )
        events["acls"].speakers.set([speakers["chang"]])

        events["telemed"] = mk_event(
            "telemedicine-best-practices",
            "Telemedicine Best Practices",
            starts_at=now + timedelta(days=18),
            duration=90,
            status=Event.Status.PUBLISHED,
            event_type=Event.EventType.WORKSHOP,
            price="29.99", currency="CAD",
            max_attendees=40,
            cpd_type="clinical", cpd_value="1.50",
            auto_issue_certs=False,
            reg_opens=now - timedelta(days=10), reg_closes=now + timedelta(days=17),
            short_description="Standards and pitfalls of modern telemedicine delivery.",
        )
        events["telemed"].speakers.set([speakers["singh"]])

        events["live_now"] = mk_event(
            "emergency-medicine-live",
            "Emergency Medicine Live Update",
            starts_at=now - timedelta(minutes=15),
            duration=120,
            status=Event.Status.LIVE,
            event_type=Event.EventType.WEBINAR,
            price="19.99", currency="USD",
            max_attendees=200,
            cpd_type="clinical", cpd_value="2.00",
            auto_issue_certs=True, badge_template=badge_tpl, auto_issue_badges=True,
            short_description="Join our live emergency medicine round-up happening right now.",
            recording_enabled=True,
            video_enabled=True,
            actual_start_at=now - timedelta(minutes=15),
        )
        events["live_now"].speakers.set([speakers["chang"]])

        # An imminent webinar — starts in ~5 min so the lobby Join button
        # activates immediately (within the 15-min gate) and reminders are
        # close to firing. Lets demos walk the lobby state transitions live.
        events["imminent"] = mk_event(
            "icu-protocols-quick-update",
            "ICU Protocols: Quick Update",
            starts_at=now + timedelta(minutes=5),
            duration=45,
            status=Event.Status.PUBLISHED,
            event_type=Event.EventType.WEBINAR,
            price="0.00",
            max_attendees=100,
            cpd_type="clinical", cpd_value="0.75",
            short_description="Bite-sized protocol changes for ICU teams. Starts in just a few minutes.",
            video_enabled=True,
            recording_enabled=True,
        )

        events["waitlist_full"] = mk_event(
            "mental-health-first-aid",
            "Mental Health First Aid",
            starts_at=now + timedelta(days=44),
            duration=240,
            status=Event.Status.PUBLISHED,
            event_type=Event.EventType.TRAINING,
            price="0.00",
            max_attendees=20, waitlist_enabled=True, waitlist_max=5, waitlist_auto_promote=False,
            cpd_type="general", cpd_value="4.00",
            short_description="Early identification of mental health crises in clinical settings.",
        )
        events["waitlist_full"].speakers.set([speakers["ortiz"]])

        events["hybrid"] = mk_event(
            "surgical-techniques-hybrid",
            "Surgical Techniques — Hybrid Workshop",
            starts_at=now + timedelta(days=28),
            duration=360,
            status=Event.Status.PUBLISHED,
            event_type=Event.EventType.WORKSHOP,
            fmt=Event.EventFormat.HYBRID,
            price="149.00", currency="CAD",
            max_attendees=30,
            cpd_type="clinical", cpd_value="6.00",
            auto_issue_certs=True, badge_template=badge_tpl, auto_issue_badges=False,
            is_multi_session=True,
            short_description="Mixed in-person + online multi-session workshop for surgical skills.",
            location="Toronto General Hospital — Simulation Lab, Rm 302",
        )
        events["hybrid"].speakers.set([speakers["ortiz"], speakers["chang"]])

        events["ondemand"] = mk_event(
            "pediatric-grand-rounds",
            "Pediatric Grand Rounds — Replay",
            starts_at=now - timedelta(days=21),
            duration=75,
            status=Event.Status.COMPLETED,
            event_type=Event.EventType.LECTURE,
            price="0.00",
            cpd_type="clinical", cpd_value="1.25",
            auto_issue_certs=True,
            short_description="On-demand replay of the pediatric grand rounds.",
            recording_enabled=True,
            actual_start_at=now - timedelta(days=21),
            actual_end_at=now - timedelta(days=21, hours=-1, minutes=-15),
        )
        events["ondemand"].speakers.set([speakers["singh"]])

        events["pre_open"] = mk_event(
            "research-ethics-symposium",
            "Research Ethics Symposium",
            starts_at=now + timedelta(days=85),
            duration=180,
            status=Event.Status.PUBLISHED,
            event_type=Event.EventType.SEMINAR,
            price="75.00", currency="CAD",
            max_attendees=80,
            cpd_type="ethics", cpd_value="3.00",
            reg_opens=now + timedelta(days=10), reg_closes=now + timedelta(days=80),
            short_description="Symposium on contemporary research ethics challenges.",
        )
        events["pre_open"].speakers.set([speakers["singh"], speakers["ortiz"]])

        events["multi_past"] = mk_event(
            "nursing-leadership-summit",
            "Nursing Leadership Summit",
            starts_at=now - timedelta(days=12),
            duration=240,
            status=Event.Status.COMPLETED,
            event_type=Event.EventType.SEMINAR,
            price="0.00",
            max_attendees=100,
            cpd_type="general", cpd_value="4.00",
            auto_issue_certs=True, require_feedback=True,
            is_multi_session=True,
            short_description="Multi-session summit on clinical leadership.",
            actual_start_at=now - timedelta(days=12),
            actual_end_at=now - timedelta(days=12, hours=-4),
        )
        events["multi_past"].speakers.set([speakers["chang"], speakers["ortiz"]])

        return events

    # ------------------------------------------------------------------
    # Event Sessions
    # ------------------------------------------------------------------
    def _build_event_sessions(self, now, events):
        from events.models import EventSession

        sessions = {}

        def mk_session(event, title, starts_at, duration=60, order=0, session_type="live",
                        cpd="0.00", mandatory=True):
            defaults = dict(
                title=title,
                description=f"Session: {title}",
                starts_at=starts_at,
                duration_minutes=duration,
                order=order,
                session_type=session_type,
                cpd_credits=Decimal(cpd),
                is_mandatory=mandatory,
                is_published=True,
            )
            obj, _ = EventSession.objects.update_or_create(event=event, title=title, defaults=defaults)
            return obj

        e = events["ethics"]
        sessions["ethics_s1"] = mk_session(e, "Ethics Foundations", e.starts_at, duration=60, order=0, cpd="1.50")
        sessions["ethics_s2"] = mk_session(e, "Case Studies & Discussion", e.starts_at + timedelta(minutes=60), duration=60, order=1, cpd="1.50")

        h = events["hybrid"]
        sessions["hybrid_s1"] = mk_session(h, "Day 1 — Technique Didactics", h.starts_at, duration=180, order=0, cpd="3.00")
        sessions["hybrid_s2"] = mk_session(h, "Day 2 — Hands-on Lab", h.starts_at + timedelta(days=1), duration=180, order=1, cpd="3.00")

        m = events["multi_past"]
        sessions["multi_s1"] = mk_session(m, "Session 1: Vision-setting", m.starts_at, duration=120, order=0, cpd="2.00")
        sessions["multi_s2"] = mk_session(m, "Session 2: Difficult Conversations", m.starts_at + timedelta(minutes=120), duration=120, order=1, cpd="2.00")

        return sessions

    # ------------------------------------------------------------------
    # Registrations + attendance
    # ------------------------------------------------------------------
    def _build_registrations(self, now, users, events, sessions):
        from events.models import SessionAttendance
        from registrations.models import AttendanceRecord, Registration

        regs = {}

        def mk_reg(event, user, *, status=Registration.Status.CONFIRMED, payment_status=None,
                   attended=False, attendance_eligible=False, total_minutes=0,
                   waitlist_position=None, amount_paid=None, email=None, full_name=None,
                   professional_title="", organization_name="",
                   created_at=None, cancelled_at=None):
            if payment_status is None:
                payment_status = Registration.PaymentStatus.PAID if event.price and event.price > 0 else Registration.PaymentStatus.NA
            defaults = dict(
                email=(email or (user.email if user else "guest@demo.test")),
                full_name=(full_name or (user.full_name if user else "Guest Attendee")),
                professional_title=professional_title or (user.professional_title if user else ""),
                organization_name=organization_name or (user.organization_name if user else ""),
                status=status,
                payment_status=payment_status,
                waitlist_position=waitlist_position,
                attended=attended,
                attendance_eligible=attendance_eligible,
                total_attendance_minutes=total_minutes,
                amount_paid=Decimal(str(amount_paid)) if amount_paid is not None else Decimal("0"),
                total_amount=Decimal(str(amount_paid)) if amount_paid is not None else Decimal("0"),
                cancelled_at=cancelled_at,
            )
            if status == Registration.Status.CANCELLED and not cancelled_at:
                defaults["cancelled_at"] = now - timedelta(days=5)
                defaults["cancellation_reason"] = "Schedule conflict"
            obj, _ = Registration.objects.update_or_create(event=event, email=defaults["email"], defaults=dict(defaults, user=user))
            if created_at:
                Registration.objects.filter(pk=obj.pk).update(created_at=created_at)
            return obj

        # Past ethics event
        e = events["ethics"]
        regs["emily_ethics"] = mk_reg(e, users["emily"], attended=True, attendance_eligible=True, total_minutes=113, amount_paid="58.24", created_at=now - timedelta(days=45))
        regs["michael_ethics"] = mk_reg(e, users["michael"], attended=True, attendance_eligible=True, total_minutes=100, amount_paid="56.74", created_at=now - timedelta(days=44))
        regs["aisha_ethics_waitlist"] = mk_reg(e, users["aisha"], status=Registration.Status.WAITLISTED, payment_status=Registration.PaymentStatus.REFUNDED, waitlist_position=1, amount_paid="49.99", created_at=now - timedelta(days=40))
        regs["guest_ethics"] = mk_reg(e, None, email="jordan.lee@example.com", full_name="Dr. Jordan Lee", attended=False, amount_paid="58.24", created_at=now - timedelta(days=42))

        # ACLS
        a = events["acls"]
        regs["emily_acls"] = mk_reg(a, users["emily"], attended=True, attendance_eligible=True, total_minutes=185, created_at=now - timedelta(days=75))
        regs["michael_acls"] = mk_reg(a, users["michael"], attended=True, attendance_eligible=True, total_minutes=179, created_at=now - timedelta(days=74))
        regs["aisha_acls_cancelled"] = mk_reg(a, users["aisha"], status=Registration.Status.CANCELLED, created_at=now - timedelta(days=72))

        # Telemedicine (future, paid)
        t = events["telemed"]
        regs["emily_telemed"] = mk_reg(t, users["emily"], created_at=now - timedelta(days=2), amount_paid="29.99")
        regs["michael_telemed_failed"] = mk_reg(t, users["michael"], status=Registration.Status.PENDING, payment_status=Registration.PaymentStatus.FAILED, amount_paid="29.99", created_at=now - timedelta(days=1))

        # Live now
        ln = events["live_now"]
        regs["aisha_live"] = mk_reg(ln, users["aisha"], attended=False, amount_paid="19.99", created_at=now - timedelta(days=3))
        regs["emily_live"] = mk_reg(ln, users["emily"], attended=True, total_minutes=14, amount_paid="19.99", created_at=now - timedelta(days=3))
        regs["michael_live_pending"] = mk_reg(ln, users["michael"], status=Registration.Status.PENDING, payment_status=Registration.PaymentStatus.PENDING, amount_paid="19.99", created_at=now - timedelta(hours=1))

        # Imminent event — confirmed registrations for Emily and Aisha so the
        # lobby Join button activates immediately and reminders are visible
        # in admin near their fire window. A guest registration too — exercises
        # the public /r/<uuid>/lobby route.
        imm = events["imminent"]
        regs["emily_imminent"] = mk_reg(imm, users["emily"], created_at=now - timedelta(hours=2))
        regs["aisha_imminent"] = mk_reg(imm, users["aisha"], created_at=now - timedelta(hours=1))
        regs["guest_imminent"] = mk_reg(
            imm, None,
            email="guest_imminent_demo@example.com",
            full_name="Guest Demo Attendee",
            created_at=now - timedelta(minutes=30),
        )

        # Waitlist-full event
        wf = events["waitlist_full"]
        # Fill up to capacity with realistic guest attendees (simulate all seats
        # taken). These names also drive the Contacts page via the
        # registration→contact post_save signal, so spread them across
        # plausible orgs/titles instead of "Attendee N".
        _MHFA_GUESTS = [
            ("Dr. Hannah Park", "MD, FRCPC", "Toronto General Hospital", "h.park@tgh.ca"),
            ("Dr. Marcus Williams", "MD", "Sunnybrook Health Sciences", "m.williams@sunnybrook.ca"),
            ("Dr. Priya Patel", "MD, MPH", "St. Michael's Hospital", "p.patel@smh.ca"),
            ("Dr. Sofia Nakamura", "DO", "Mount Sinai Hospital", "s.nakamura@msh.ca"),
            ("Nurse Practitioner Jamie Reed", "NP, MN", "Women's College Hospital", "j.reed@wch.ca"),
            ("Dr. Andre Dubois", "MD, FRCSC", "Sainte-Justine Hospital", "a.dubois@chusj.org"),
            ("Dr. Olivia Tran", "MD", "Vancouver General Hospital", "o.tran@vgh.ca"),
            ("Dr. Benjamin Cohen", "MD, MSc", "Jewish General Hospital", "b.cohen@jgh.mcgill.ca"),
            ("Dr. Yuki Tanaka", "MD, PhD", "Princess Margaret Cancer Centre", "y.tanaka@uhn.ca"),
            ("Dr. Rachel Goldberg", "MD, FAAP", "Hospital for Sick Children", "r.goldberg@sickkids.ca"),
            ("Dr. Carlos Mendoza", "DO", "Lakeridge Health", "c.mendoza@lh.ca"),
            ("Dr. Aisling O'Brien", "MD, FRCPC", "London Health Sciences Centre", "a.obrien@lhsc.on.ca"),
            ("Dr. David Klein", "MD", "Hamilton Health Sciences", "d.klein@hhsc.ca"),
            ("Dr. Fatima Hassan", "MD, MPH", "The Ottawa Hospital", "f.hassan@toh.ca"),
            ("Dr. Liam Murphy", "MD, FRCPC", "Kingston Health Sciences", "l.murphy@kingstonhsc.ca"),
            ("Dr. Evelyn Chu", "MD, FRCPC", "Trillium Health Partners", "e.chu@thp.ca"),
            ("Dr. Nathan Brooks", "DO", "Queensway Carleton Hospital", "n.brooks@qch.on.ca"),
            ("Dr. Maya Subramanian", "MD, FACP", "Markham Stouffville Hospital", "m.subramanian@msh.on.ca"),
            ("Dr. Tomás Rivera", "MD", "Humber River Hospital", "t.rivera@hrh.ca"),
            ("Dr. Charlotte Wells", "MD, FRCPC", "Michael Garron Hospital", "c.wells@mgh.ca"),
        ]
        for i in range(wf.max_attendees or 20):
            name, title, org, email = _MHFA_GUESTS[i % len(_MHFA_GUESTS)]
            mk_reg(wf, None, email=email, full_name=name,
                   professional_title=title, organization_name=org,
                   created_at=now - timedelta(days=10 + i % 7))
        regs["aisha_waitlist_full"] = mk_reg(wf, users["aisha"], status=Registration.Status.WAITLISTED, waitlist_position=1, created_at=now - timedelta(days=7))
        regs["michael_waitlist_full"] = mk_reg(wf, users["michael"], status=Registration.Status.WAITLISTED, waitlist_position=2, created_at=now - timedelta(days=6))

        # Hybrid (future)
        h = events["hybrid"]
        regs["emily_hybrid"] = mk_reg(h, users["emily"], amount_paid="149.00", created_at=now - timedelta(days=5))

        # On-demand past
        od = events["ondemand"]
        regs["aisha_ondemand"] = mk_reg(od, users["aisha"], attended=False, created_at=now - timedelta(days=20))
        regs["michael_ondemand_noshow"] = mk_reg(od, users["michael"], attended=False, created_at=now - timedelta(days=25))
        regs["emily_ondemand"] = mk_reg(od, users["emily"], attended=True, attendance_eligible=True, total_minutes=75, created_at=now - timedelta(days=25))

        # Multi-session past (partial attendance)
        m = events["multi_past"]
        regs["emily_multi"] = mk_reg(m, users["emily"], attended=True, attendance_eligible=True, total_minutes=240, created_at=now - timedelta(days=20))
        regs["michael_multi_partial"] = mk_reg(m, users["michael"], attended=True, attendance_eligible=False, total_minutes=110, created_at=now - timedelta(days=20))

        # Session attendance for partial case
        SessionAttendance.objects.update_or_create(
            session=sessions["multi_s1"], registration=regs["michael_multi_partial"],
            defaults=dict(duration_minutes=110, is_eligible=True),
        )
        # Michael did NOT attend session 2 — no record created
        SessionAttendance.objects.update_or_create(
            session=sessions["multi_s1"], registration=regs["emily_multi"],
            defaults=dict(duration_minutes=120, is_eligible=True),
        )
        SessionAttendance.objects.update_or_create(
            session=sessions["multi_s2"], registration=regs["emily_multi"],
            defaults=dict(duration_minutes=120, is_eligible=True),
        )

        # Attendance records for the live event (emily joined, aisha waiting)
        AttendanceRecord.objects.update_or_create(
            event=ln, registration=regs["emily_live"], participant_email=users["emily"].email,
            defaults=dict(
                participant_name=users["emily"].full_name,
                join_time=ln.starts_at,
                duration_minutes=14,
                is_matched=True,
                matched_at=now,
                join_method="web",
            ),
        )
        # Emily past attendance records
        AttendanceRecord.objects.update_or_create(
            event=e, registration=regs["emily_ethics"], participant_email=users["emily"].email,
            defaults=dict(
                participant_name=users["emily"].full_name,
                join_time=e.starts_at,
                leave_time=e.starts_at + timedelta(minutes=113),
                duration_minutes=113,
                is_matched=True,
                matched_at=now - timedelta(days=33),
                join_method="web",
            ),
        )

        return regs

    # ------------------------------------------------------------------
    # Courses & programs
    # ------------------------------------------------------------------
    def _build_courses_and_programs(self, now, users, templates):
        from learning.models import Course, CourseStaff, Program, ProgramCourse

        cert_tpl = templates["cert_standard"]

        def mk_course(slug, title, *, status="published", price_cents=0, currency="USD",
                      fmt="online", max_enrollments=None, short_description="", description="",
                      cpd_credits="1.00", cpd_type="general", is_public=True,
                      enrollment_open=True, enrollment_opens_at=None, enrollment_closes_at=None,
                      enrollment_count=0, hybrid_completion_criteria=None,
                      min_sessions_required=1):
            defaults = dict(
                created_by=users["organizer"],
                title=title,
                format=fmt,
                description=description or f"Demo description for {title}.",
                short_description=short_description or title,
                cpd_credits=Decimal(cpd_credits),
                cpd_type=cpd_type,
                status=status,
                is_public=is_public,
                price_cents=price_cents,
                currency=currency,
                enrollment_open=enrollment_open,
                max_enrollments=max_enrollments,
                enrollment_opens_at=enrollment_opens_at,
                enrollment_closes_at=enrollment_closes_at,
                estimated_hours=Decimal("6.0"),
                passing_score=70,
                certificates_enabled=True,
                certificate_template=cert_tpl,
                auto_issue_certificates=True,
                enrollment_count=enrollment_count,
            )
            if hybrid_completion_criteria is not None:
                defaults["hybrid_completion_criteria"] = hybrid_completion_criteria
                defaults["min_sessions_required"] = min_sessions_required
            obj, _ = Course.objects.update_or_create(
                created_by=users["organizer"], slug=slug,
                defaults=defaults,
            )
            return obj

        courses = {}
        courses["ethics"] = mk_course(
            "intro-to-clinical-ethics",
            "Introduction to Clinical Ethics",
            status="published",
            price_cents=4900, currency="CAD",
            cpd_credits="5.00", cpd_type="ethics",
            short_description="Foundations of ethical reasoning in clinical practice.",
        )
        courses["comms"] = mk_course(
            "patient-communication-essentials",
            "Patient Communication Essentials",
            status="published",
            price_cents=0,
            cpd_credits="3.00", cpd_type="general",
            short_description="Core communication skills for patient interactions.",
        )
        courses["records"] = mk_course(
            "digital-health-records",
            "Digital Health Records Mastery",
            status="published",
            price_cents=9900, currency="CAD",
            cpd_credits="4.00", cpd_type="clinical",
            max_enrollments=50,
            short_description="Advanced EHR workflows for modern clinicians.",
        )
        courses["pharma"] = mk_course(
            "pharmacology-refresher",
            "Pharmacology Refresher",
            status="archived",
            price_cents=0,
            cpd_credits="2.00", cpd_type="clinical",
            short_description="Archived course retained for alumni access.",
        )
        courses["surgical_draft"] = mk_course(
            "advanced-surgical-skills",
            "Advanced Surgical Skills (Draft)",
            status="draft",
            price_cents=19900, currency="CAD",
            cpd_credits="6.00", cpd_type="clinical",
            is_public=False,
            short_description="Upcoming advanced surgical skills course.",
        )
        # A free, published course intentionally NOT pre-enrolled for any
        # persona — so the demo can showcase the enroll-via-Discover flow
        # (P5 enrollment confirmation email + Notification + signal triggers).
        courses["qi"] = mk_course(
            "quality-improvement-foundations",
            "Quality Improvement Foundations",
            status="published",
            price_cents=0,
            cpd_credits="2.50", cpd_type="general",
            short_description="Free intro course. Open to all — try the enrollment flow end-to-end.",
            description=(
                "A free, self-paced intro to QI in healthcare. Reserved as a sandbox so "
                "demo users can walk through the enrollment confirmation, notification, "
                "and progress flows without affecting other learners' state."
            ),
        )
        # Hybrid course — pre-work modules plus two scheduled live sessions.
        # Exercises hybrid_completion_criteria=BOTH (modules AND sessions),
        # CourseSession rendering, attendance tracking, and the live/replay
        # surfaces inside the course player.
        courses["bootcamp"] = mk_course(
            "procedural-skills-bootcamp",
            "Procedural Skills Bootcamp",
            status="published",
            fmt=Course.CourseFormat.HYBRID,
            price_cents=12900, currency="CAD",
            cpd_credits="6.00", cpd_type="clinical",
            hybrid_completion_criteria=Course.HybridCompletionCriteria.BOTH,
            short_description="Self-paced anatomy + equipment pre-work, then two live skills sessions.",
            description=(
                "Mastery-track hybrid course. Complete the three pre-work modules at "
                "your own pace, then attend two live sessions: a didactic Q&A and a "
                "hands-on lab. Both modules and live attendance are required to "
                "earn the certificate."
            ),
        )

        # Pure-live cohort course — no self-paced modules, completion is
        # driven entirely by session attendance. Exercises the LIVE branch of
        # _progress_snapshot() that the bootcamp's HYBRID flow doesn't.
        courses["cohort"] = mk_course(
            "cohort-workshop-difficult-conversations",
            "Cohort Workshop: Difficult Conversations",
            status="published",
            fmt=Course.CourseFormat.LIVE,
            price_cents=4900, currency="CAD",
            cpd_credits="2.50", cpd_type="general",
            short_description="Two-session live cohort on having difficult patient conversations.",
            description=(
                "A live, instructor-led cohort. Two 60-minute sessions over two "
                "weeks. No self-paced material — completion is earned by "
                "attending both sessions."
            ),
        )

        # Assign instructor as staff on two courses
        for course in [courses["ethics"], courses["comms"]]:
            CourseStaff.objects.update_or_create(course=course, user=users["instructor"], defaults={"role": "instructor"})

        # Program bundling Ethics + Comms
        program, _ = Program.objects.update_or_create(
            created_by=users["organizer"], slug="primary-care-excellence",
            defaults=dict(
                title="Primary Care Excellence Track",
                description="A bundled program combining ethics and communication essentials.",
                short_description="Save when you buy both together.",
                status=Program.Status.PUBLISHED,
                is_public=True,
                price_cents=6900, currency="CAD",
            ),
        )
        for i, course in enumerate([courses["ethics"], courses["comms"]]):
            ProgramCourse.objects.update_or_create(
                program=program, course=course,
                defaults=dict(order=i, is_required=True),
            )

        return courses, {"primary_care": program}

    # ------------------------------------------------------------------
    # Course enrollments
    # ------------------------------------------------------------------
    def _build_course_enrollments(self, now, users, courses):
        from learning.models import CourseEnrollment

        enrollments = {}

        def mk_enroll(course, user, *, status=CourseEnrollment.Status.ACTIVE, progress=0,
                      modules_completed=0, current_score=None, completed_at=None,
                      certificate_issued=False, certificate_issued_at=None,
                      enrolled_days_ago=10, started_days_ago=None):
            # Default started_at for any non-PENDING enrollment; cards otherwise
            # show "Started: Not started" alongside completion timestamps even
            # when progress is recomputed > 0 by _refresh_denormalized_counts.
            # PENDING (e.g., awaiting payment / instructor approval) is the one
            # status where "not started yet" is correct.
            if started_days_ago is None and status != CourseEnrollment.Status.PENDING:
                started_days_ago = max(0, enrolled_days_ago - 1)
            defaults = dict(
                status=status,
                progress_percent=progress,
                modules_completed=modules_completed,
                current_score=current_score,
                completed_at=completed_at,
                certificate_issued=certificate_issued,
                certificate_issued_at=certificate_issued_at,
                started_at=(now - timedelta(days=started_days_ago)) if started_days_ago is not None else None,
            )
            obj, _ = CourseEnrollment.objects.update_or_create(course=course, user=user, defaults=defaults)
            CourseEnrollment.objects.filter(pk=obj.pk).update(enrolled_at=now - timedelta(days=enrolled_days_ago))
            obj.refresh_from_db()
            return obj

        # Emily: completed ethics course, in-progress comms
        enrollments["emily_ethics"] = mk_enroll(
            courses["ethics"], users["emily"],
            status=CourseEnrollment.Status.COMPLETED,
            progress=100, modules_completed=3, current_score=90,
            completed_at=now - timedelta(days=5),
            certificate_issued=True, certificate_issued_at=now - timedelta(days=5),
            enrolled_days_ago=45,
        )
        enrollments["emily_comms"] = mk_enroll(
            courses["comms"], users["emily"],
            progress=60, modules_completed=3, current_score=88,
            enrolled_days_ago=14,
        )
        # Pure-live cohort: Emily attends both sessions → COMPLETED via
        # session attendance only (LIVE format, no modules to complete).
        # Final progress + completed_at are set by _refresh_denormalized_counts
        # once the attendance rows exist.
        enrollments["emily_cohort"] = mk_enroll(
            courses["cohort"], users["emily"],
            progress=0, modules_completed=0,
            enrolled_days_ago=21,
        )
        # Michael: active on ethics (low progress), active on comms (prereq-locked area)
        enrollments["michael_ethics"] = mk_enroll(
            courses["ethics"], users["michael"],
            progress=15, modules_completed=0, current_score=None,
            enrolled_days_ago=20,
        )
        enrollments["michael_comms"] = mk_enroll(
            courses["comms"], users["michael"],
            progress=40, modules_completed=2,
            enrolled_days_ago=15,
        )
        # Archive-remnant: Emily historical enrollment
        enrollments["emily_pharma"] = mk_enroll(
            courses["pharma"], users["emily"],
            status=CourseEnrollment.Status.COMPLETED,
            progress=100, modules_completed=2,
            completed_at=now - timedelta(days=180),
            certificate_issued=True, certificate_issued_at=now - timedelta(days=180),
            enrolled_days_ago=200,
        )
        # Digital Health Records — three live enrollments so the
        # Enrollments tab matches the dashboard count instead of relying on
        # a denormalised override with no backing rows.
        enrollments["emily_records"] = mk_enroll(
            courses["records"], users["emily"],
            progress=35, modules_completed=1, current_score=82,
            enrolled_days_ago=18,
        )
        enrollments["michael_records"] = mk_enroll(
            courses["records"], users["michael"],
            progress=10, modules_completed=0,
            enrolled_days_ago=8,
        )
        enrollments["aisha_records"] = mk_enroll(
            courses["records"], users["aisha"],
            status=CourseEnrollment.Status.PENDING,
            progress=0, modules_completed=0,
            enrolled_days_ago=2,
        )
        # Dropped — Michael started Patient Communication Essentials and
        # decided it wasn't for him. Surfaces the "Dropped" status badge.
        enrollments["michael_qi_dropped"] = mk_enroll(
            courses["qi"], users["michael"],
            status=CourseEnrollment.Status.DROPPED,
            progress=22, modules_completed=0,
            enrolled_days_ago=40,
        )
        # Manually completed — Aisha was marked complete by an instructor
        # despite low underlying activity (e.g., transfer credit, equivalency).
        # Tests that mark_complete_manually + the COMPLETED-lock invariant
        # cooperate: status COMPLETED + progress 100 is preserved even
        # though leaf progress would say otherwise.
        enrollments["aisha_qi_manual"] = mk_enroll(
            courses["qi"], users["aisha"],
            status=CourseEnrollment.Status.COMPLETED,
            progress=100, modules_completed=0,
            completed_at=now - timedelta(days=12),
            certificate_issued=False,
            enrolled_days_ago=30,
        )
        # Hybrid bootcamp — Emily enrolled mid-journey: pre-work modules done,
        # attended session 1 (past), session 2 still upcoming.
        enrollments["emily_bootcamp"] = mk_enroll(
            courses["bootcamp"], users["emily"],
            progress=0, modules_completed=0,  # recomputed by the snapshot path
            enrolled_days_ago=14,
        )
        return enrollments

    def _build_program_enrollments(self, now, users, programs):
        from learning.models import ProgramEnrollment

        ProgramEnrollment.objects.update_or_create(
            user=users["emily"], program=programs["primary_care"],
            defaults=dict(
                status=ProgramEnrollment.Status.ACTIVE,
                enrolled_at=now - timedelta(days=45),
                started_at=now - timedelta(days=45),
                course_enrollments_seeded=True,
            ),
        )

    # ------------------------------------------------------------------
    # Event modules, content, assignments, progress
    # ------------------------------------------------------------------
    def _build_event_modules_and_progress(self, now, users, events, courses, registrations, enrollments):
        from learning.models import (
            Assignment, AssignmentSubmission, ContentProgress, CourseModule, EventModule,
            ModuleContent, ModuleProgress,
        )

        def mk_module(course, title, order, *, description="", is_published=True, prereq=None,
                       release_type="immediate", cpd="0.50", passing_score=70):
            mod, _ = EventModule.objects.update_or_create(
                event=None, title=title,
                defaults=dict(
                    description=description or f"Module — {title}",
                    order=order,
                    is_published=is_published,
                    prerequisite_module=prereq,
                    release_type=release_type,
                    cpd_credits=Decimal(cpd),
                    passing_score=passing_score,
                ),
            )
            CourseModule.objects.update_or_create(
                course=course, module=mod,
                defaults=dict(order=order, is_required=True),
            )
            return mod

        def mk_content(module, title, content_type, order, *, duration=10, content_data=None, is_required=True):
            obj, _ = ModuleContent.objects.update_or_create(
                module=module, title=title,
                defaults=dict(
                    content_type=content_type,
                    order=order,
                    duration_minutes=duration,
                    content_data=content_data or {"body": f"<p>{title}</p>"} if content_type == "text" else (content_data or {}),
                    is_required=is_required,
                    is_published=True,
                ),
            )
            return obj

        # ---- Ethics course modules ----
        ethics = courses["ethics"]
        m_eth_1 = mk_module(ethics, "Foundations of Clinical Ethics", order=0, cpd="1.00")
        m_eth_2 = mk_module(ethics, "Case Analysis Workshop", order=1, cpd="2.00")
        m_eth_3 = mk_module(ethics, "Advanced Ethics Applications", order=2, prereq=m_eth_2, release_type="prerequisite", cpd="2.00")

        c_eth_1_welcome = mk_content(m_eth_1, "Welcome & Orientation", "text", 0, duration=5, content_data={"body": "<p>Welcome to clinical ethics.</p>"})
        c_eth_1_video = mk_content(m_eth_1, "Intro Video", "video", 1, duration=15, content_data={"url": "https://demo.example/intro-ethics.mp4", "provider": "demo"})
        c_eth_2_text = mk_content(m_eth_2, "Case Study Guide", "text", 0, duration=20, content_data={"body": "<p>Read the scenario carefully.</p>"})
        c_eth_2_quiz = mk_content(m_eth_2, "Module 2 Quiz", "quiz", 1, duration=20, content_data={"questions": [{"q": "Beneficence means?", "choices": ["a", "b"], "answer": 0}], "passing_score": 70})
        c_eth_3_video = mk_content(m_eth_3, "Advanced Case Video", "video", 0, duration=30, content_data={"url": "https://demo.example/adv-ethics.mp4"})
        c_eth_3_primer = mk_content(m_eth_3, "Telemedicine Ethics Primer", "text", 1, duration=15, content_data={"body": "<p>Emerging considerations.</p>"})

        # ---- Comms course modules (5 modules covering all content types) ----
        comms = courses["comms"]
        m_c_1 = mk_module(comms, "Foundations of Patient Communication", 0, cpd="0.50")
        m_c_2 = mk_module(comms, "Active Listening Techniques", 1, cpd="0.50")
        m_c_3 = mk_module(comms, "Difficult Conversations", 2, cpd="0.75")
        m_c_4 = mk_module(comms, "Cultural Competence", 3, cpd="0.75", prereq=m_c_3, release_type="prerequisite")
        m_c_5 = mk_module(comms, "Capstone Assignment", 4, cpd="0.50")

        c_c_1_welcome = mk_content(m_c_1, "Welcome Text", "text", 0, duration=5, content_data={"body": "<p>Welcome.</p>"})
        c_c_2_video = mk_content(m_c_2, "Listening Video", "video", 0, duration=15, content_data={"url": "https://demo.example/listening.mp4"})
        c_c_3_pdf = mk_content(m_c_3, "Reading PDF", "document", 0, duration=20, content_data={})
        c_c_3_reflection = mk_content(m_c_3, "Demo Reflection", "text", 1, duration=10, content_data={"body": "<p>Reflect.</p>"})
        mk_content(m_c_4, "External Reference", "external", 0, duration=15, content_data={"url": "https://example.com/cultural-competence", "open_in_new_tab": True})
        mk_content(m_c_4, "Lesson Bundle", "lesson", 1, duration=20, content_data={"video": {"url": "https://demo.example/cc.mp4"}, "text": {"body": "<p>Context.</p>"}})
        mk_content(m_c_5, "Capstone Brief", "text", 0, duration=5, content_data={"body": "<p>Submit the capstone.</p>"})

        # ---- Digital Health Records course (published+priced, looked empty) ----
        records = courses["records"]
        m_dhr_1 = mk_module(records, "EHR Workflow Foundations", 0, cpd="1.00")
        m_dhr_2 = mk_module(records, "Documentation & Coding Best Practices", 1, cpd="1.00")
        m_dhr_3 = mk_module(records, "Privacy, Security & PHIPA", 2, cpd="1.00")
        m_dhr_4 = mk_module(records, "Optimising Day-to-Day EHR Use", 3, prereq=m_dhr_3,
                             release_type="prerequisite", cpd="1.00")

        c_dhr_1_text = mk_content(m_dhr_1, "Module Overview", "text", 0, duration=8,
                   content_data={"body": "<p>How modern EHRs reshape clinical workflows.</p>"})
        c_dhr_1_video = mk_content(m_dhr_1, "EHR Tour Video", "video", 1, duration=18,
                   content_data={"url": "https://demo.example/ehr-tour.mp4", "provider": "demo"})
        c_dhr_2_doc = mk_content(m_dhr_2, "Coding Reference Guide", "document", 0, duration=25,
                   content_data={})
        c_dhr_2_quiz = mk_content(m_dhr_2, "Documentation Quiz", "quiz", 1, duration=15,
                   content_data={"questions": [
                       {"q": "Which note type best supports billing review?",
                        "choices": ["SOAP", "Free text", "Telephone encounter"], "answer": 0},
                   ], "passing_score": 70})
        mk_content(m_dhr_3, "Privacy & PHIPA Reading", "text", 0, duration=20,
                   content_data={"body": "<p>Patient privacy obligations under PHIPA.</p>"})
        mk_content(m_dhr_3, "External Reference: PHIPA Toolkit", "external", 1, duration=10,
                   content_data={"url": "https://www.ipc.on.ca/", "open_in_new_tab": True})
        mk_content(m_dhr_4, "EHR Power-User Tips", "video", 0, duration=22,
                   content_data={"url": "https://demo.example/power-user.mp4"})
        mk_content(m_dhr_4, "Wrap-up & Reflection", "text", 1, duration=10,
                   content_data={"body": "<p>Reflect on three workflow improvements you'll try this month.</p>"})

        # ---- Pharmacology Refresher (archived but listed) ----
        pharma = courses["pharma"]
        m_ph_1 = mk_module(pharma, "Refresher Highlights", 0, cpd="1.00")
        m_ph_2 = mk_module(pharma, "Common Drug Interactions", 1, cpd="1.00")
        mk_content(m_ph_1, "Refresher Reading", "text", 0, duration=15,
                   content_data={"body": "<p>Archived course retained for alumni access.</p>"})
        mk_content(m_ph_2, "Interaction Tables", "document", 0, duration=20,
                   content_data={})

        # ---- Procedural Skills Bootcamp (HYBRID) ----
        bootcamp = courses["bootcamp"]
        m_bc_1 = mk_module(bootcamp, "Pre-work: Anatomy Review", 0, cpd="1.00")
        m_bc_2 = mk_module(bootcamp, "Equipment & Sterile Setup", 1, cpd="1.00")
        m_bc_3 = mk_module(bootcamp, "Post-procedure Care", 2, cpd="1.00")

        c_bc_1_text = mk_content(m_bc_1, "Anatomy Reading", "text", 0, duration=15,
                                  content_data={"body": "<p>Review the regional anatomy notes before Session 1.</p>"})
        c_bc_1_video = mk_content(m_bc_1, "Anatomy Walkthrough Video", "video", 1, duration=20,
                                   content_data={"url": "https://demo.example/anatomy.mp4"})
        c_bc_2_doc = mk_content(m_bc_2, "Equipment Checklist (PDF)", "document", 0, duration=10,
                                 content_data={})
        c_bc_2_quiz = mk_content(m_bc_2, "Sterile Setup Quiz", "quiz", 1, duration=10,
                                  content_data={
                                      "questions": [
                                          {"q": "Which step comes first?",
                                           "choices": ["Hand hygiene", "Glove on", "Drape patient"],
                                           "answer": 0},
                                      ],
                                      "passing_score": 70,
                                  })
        c_bc_3_text = mk_content(m_bc_3, "Post-procedure Care Notes", "text", 0, duration=12,
                                  content_data={"body": "<p>Discharge instructions and red-flag follow-up triggers.</p>"})
        c_bc_3_external = mk_content(m_bc_3, "Reference: National Practice Guidelines", "external", 1, duration=8,
                                      content_data={"url": "https://example.com/national-guidelines",
                                                    "open_in_new_tab": True})

        # ---- Assignments ----
        a_eth = Assignment.objects.update_or_create(
            module=m_eth_2, title="Ethics Case Study Analysis",
            defaults=dict(
                description="Analyse the provided case using a named ethical framework.",
                instructions="Write 500-750 words addressing the rubric criteria.",
                due_days_after_release=14,
                max_score=100, passing_score=70,
                allow_resubmission=True, max_attempts=3,
                submission_type="text",
                rubric={"criteria": [
                    {"name": "Issue Identification", "max_points": 25},
                    {"name": "Framework", "max_points": 30},
                    {"name": "Stakeholder Analysis", "max_points": 20},
                    {"name": "Recommendation", "max_points": 25},
                ]},
            ),
        )[0]
        a_cap = Assignment.objects.update_or_create(
            module=m_c_5, title="Capstone Reflection",
            defaults=dict(
                description="Reflect on a communication scenario.",
                instructions="Describe and analyse a real-world scenario.",
                due_days_after_release=21,
                max_score=100, passing_score=60,
                allow_resubmission=True, max_attempts=3,
                submission_type="text",
                rubric={"criteria": [
                    {"name": "Depth", "max_points": 50},
                    {"name": "Clarity", "max_points": 50},
                ]},
            ),
        )[0]

        # Submissions covering each state
        # Emily: graded pass on ethics assignment
        AssignmentSubmission.objects.update_or_create(
            assignment=a_eth, course_enrollment=enrollments["emily_ethics"], attempt_number=1,
            defaults=dict(
                status=AssignmentSubmission.Status.GRADED,
                submitted_at=now - timedelta(days=30),
                content={"text": "Thorough analysis with strong framework application..."},
                score=85, graded_by=users["instructor"], graded_at=now - timedelta(days=28),
                feedback="Excellent analysis — strong on framework, consider deeper stakeholder treatment.",
            ),
        )
        # Michael: graded fail + resubmission allowed
        AssignmentSubmission.objects.update_or_create(
            assignment=a_eth, course_enrollment=enrollments["michael_ethics"], attempt_number=1,
            defaults=dict(
                status=AssignmentSubmission.Status.NEEDS_REVISION,
                submitted_at=now - timedelta(days=10),
                content={"text": "First draft, needs depth."},
                score=55, graded_by=users["instructor"], graded_at=now - timedelta(days=8),
                feedback="Needs greater framework depth. Please resubmit.",
            ),
        )
        # Michael: submitted awaiting grade (instructor's queue)
        AssignmentSubmission.objects.update_or_create(
            assignment=a_cap, course_enrollment=enrollments["michael_comms"], attempt_number=1,
            defaults=dict(
                status=AssignmentSubmission.Status.SUBMITTED,
                submitted_at=now - timedelta(days=1),
                content={"text": "Capstone draft submitted for review."},
            ),
        )
        # Aisha: draft (not started state — draft entry)
        # (intentionally no submission to represent "Not started")
        # Emily: resubmitted & re-graded pass on capstone
        AssignmentSubmission.objects.update_or_create(
            assignment=a_cap, course_enrollment=enrollments["emily_comms"], attempt_number=2,
            defaults=dict(
                status=AssignmentSubmission.Status.GRADED,
                submitted_at=now - timedelta(days=3),
                content={"text": "Revised capstone reflecting feedback."},
                score=82, graded_by=users["instructor"], graded_at=now - timedelta(days=1),
                feedback="Significant improvement — well done.",
            ),
        )

        # Content progress (sampling — covers 0%, partial, 100%)
        def progress(enroll, content, *, status=ContentProgress.Status.COMPLETED, percent=100, started_days_ago=5, completed_days_ago=4):
            defaults = dict(
                status=status,
                progress_percent=percent,
                started_at=now - timedelta(days=started_days_ago) if started_days_ago else None,
                completed_at=now - timedelta(days=completed_days_ago) if status == ContentProgress.Status.COMPLETED else None,
                time_spent_seconds=600,
            )
            ContentProgress.objects.update_or_create(
                course_enrollment=enroll, content=content, defaults=defaults,
            )

        progress(enrollments["emily_ethics"], c_eth_1_welcome, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_ethics"], c_eth_1_video, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_ethics"], c_eth_2_text, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_ethics"], c_eth_2_quiz, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_ethics"], c_eth_3_video, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_ethics"], c_eth_3_primer, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["michael_ethics"], c_eth_2_text, status=ContentProgress.Status.IN_PROGRESS, percent=60, completed_days_ago=None)

        # Hybrid bootcamp leaf data for Emily — pre-work modules 1+2 done,
        # m3 untouched, session 1 attended, session 2 upcoming.
        from learning.models import CourseSession, CourseSessionAttendance
        bc = courses["bootcamp"]

        bc_session_1, _ = CourseSession.objects.update_or_create(
            course=bc, title="Session 1: Live Q&A on Anatomy",
            defaults=dict(
                description="Didactic Q&A — review the anatomy walkthrough before joining.",
                order=0,
                session_type=CourseSession.SessionType.LIVE,
                starts_at=now - timedelta(days=4, hours=2),
                duration_minutes=90,
                timezone="America/Toronto",
                actual_start_at=now - timedelta(days=4, hours=2),
                actual_end_at=now - timedelta(days=4, hours=2) + timedelta(minutes=92),
                cpd_credits=Decimal("1.50"),
                is_mandatory=True,
                minimum_attendance_percent=80,
                status=CourseSession.Status.COMPLETED,
                is_published=True,
                recording_enabled=True,
                recording_auto_publish=True,
            ),
        )
        bc_session_2, _ = CourseSession.objects.update_or_create(
            course=bc, title="Session 2: Hands-on Skills Lab",
            defaults=dict(
                description="In-person lab — bring your scrubs and printed checklist.",
                order=1,
                session_type=CourseSession.SessionType.LIVE,
                # In-person — exercises D4 (no VideoRoom provisioned for this
                # session; learner-facing UI shows venue rather than Join button).
                delivery_mode=CourseSession.DeliveryMode.IN_PERSON,
                starts_at=now + timedelta(days=7, hours=2),
                duration_minutes=180,
                timezone="America/Toronto",
                cpd_credits=Decimal("3.00"),
                is_mandatory=True,
                minimum_attendance_percent=80,
                status=CourseSession.Status.SCHEDULED,
                is_published=True,
                recording_enabled=False,
            ),
        )
        # Cancelled supplementary session — exercises D2 (cancellation auto-
        # recompute path). The session pre-existed before being scrubbed; its
        # CANCELLED status removes it from the completion denominator. The
        # cancellation email task fires for every active enrollee on save.
        CourseSession.objects.update_or_create(
            course=bc, title="Optional: Pre-Lab Equipment Walk-through",
            defaults=dict(
                description="Cancelled — equipment walk-through merged into Session 2.",
                order=2,
                session_type=CourseSession.SessionType.LIVE,
                delivery_mode=CourseSession.DeliveryMode.ONLINE,
                starts_at=now - timedelta(days=1, hours=3),
                duration_minutes=45,
                timezone="America/Toronto",
                cpd_credits=Decimal("0.50"),
                is_mandatory=False,
                minimum_attendance_percent=80,
                status=CourseSession.Status.CANCELLED,
                cancelled_reason="Folded into Session 2 to keep the cohort focused.",
                cancelled_at=now - timedelta(days=2),
                is_published=True,
                recording_enabled=False,
            ),
        )
        # Emily attended Session 1 fully → eligible.
        CourseSessionAttendance.objects.update_or_create(
            session=bc_session_1, enrollment=enrollments["emily_bootcamp"],
            defaults=dict(
                attendance_minutes=88,
                is_eligible=True,
                participant_email=users["emily"].email,
                join_time=bc_session_1.starts_at,
                leave_time=bc_session_1.starts_at + timedelta(minutes=88),
            ),
        )
        # Pre-work content progress: m1 + m2 fully done, m3 not started.
        progress(enrollments["emily_bootcamp"], c_bc_1_text, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_bootcamp"], c_bc_1_video, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_bootcamp"], c_bc_2_doc, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_bootcamp"], c_bc_2_quiz, status=ContentProgress.Status.COMPLETED)

        # Pure-live cohort sessions — Emily attended both, so the LIVE branch
        # of _progress_snapshot() will land at 100% during the refresh pass.
        cohort = courses["cohort"]
        cohort_session_1, _ = CourseSession.objects.update_or_create(
            course=cohort, title="Session 1: Framing Difficult Conversations",
            defaults=dict(
                description="Introducing the SPIKES protocol with role-play.",
                order=0,
                session_type=CourseSession.SessionType.LIVE,
                starts_at=now - timedelta(days=14, hours=3),
                duration_minutes=60,
                timezone="America/Toronto",
                actual_start_at=now - timedelta(days=14, hours=3),
                actual_end_at=now - timedelta(days=14, hours=3) + timedelta(minutes=62),
                cpd_credits=Decimal("1.25"),
                is_mandatory=True,
                minimum_attendance_percent=80,
                status=CourseSession.Status.COMPLETED,
                is_published=True,
                recording_enabled=True,
                recording_auto_publish=True,
            ),
        )
        cohort_session_2, _ = CourseSession.objects.update_or_create(
            course=cohort, title="Session 2: De-escalation & Family Meetings",
            defaults=dict(
                description="Applying the framework to family-meeting scenarios.",
                order=1,
                session_type=CourseSession.SessionType.LIVE,
                starts_at=now - timedelta(days=7, hours=3),
                duration_minutes=60,
                timezone="America/Toronto",
                actual_start_at=now - timedelta(days=7, hours=3),
                actual_end_at=now - timedelta(days=7, hours=3) + timedelta(minutes=58),
                cpd_credits=Decimal("1.25"),
                is_mandatory=True,
                minimum_attendance_percent=80,
                status=CourseSession.Status.COMPLETED,
                is_published=True,
                recording_enabled=True,
                recording_auto_publish=True,
            ),
        )
        for s in (cohort_session_1, cohort_session_2):
            CourseSessionAttendance.objects.update_or_create(
                session=s, enrollment=enrollments["emily_cohort"],
                defaults=dict(
                    attendance_minutes=int(s.duration_minutes * 0.95),
                    is_eligible=True,
                    participant_email=users["emily"].email,
                    join_time=s.starts_at,
                    leave_time=s.starts_at + timedelta(minutes=int(s.duration_minutes * 0.95)),
                ),
            )

        # Comms course leaf-level progress for Emily — backs the 60% display.
        # Without ContentProgress rows the recompute path inside
        # _progress_snapshot() would land at ~12% even though three modules
        # are flagged COMPLETED, because the snapshot reads ContentProgress
        # directly (single source of truth).
        progress(enrollments["emily_comms"], c_c_1_welcome, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_comms"], c_c_2_video, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_comms"], c_c_3_pdf, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_comms"], c_c_3_reflection, status=ContentProgress.Status.COMPLETED)
        # Michael barely started Comms — m1 done, mid-watch on the m2 video.
        progress(enrollments["michael_comms"], c_c_1_welcome, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["michael_comms"], c_c_2_video, status=ContentProgress.Status.IN_PROGRESS, percent=40, completed_days_ago=None)

        # DHR leaf data — Emily 35% (m1 fully done = 2/8 ≈ 25% + 1 of m2 = 37.5%),
        # Michael 12% (just one content of m1 watched).
        progress(enrollments["emily_records"], c_dhr_1_text, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_records"], c_dhr_1_video, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["emily_records"], c_dhr_2_doc, status=ContentProgress.Status.COMPLETED)
        progress(enrollments["michael_records"], c_dhr_1_text, status=ContentProgress.Status.COMPLETED)

        # Module progress to make the UI happy
        def mp(enroll, module, status, completed_contents, total_contents, *, score=None):
            defaults = dict(
                status=status,
                contents_completed=completed_contents,
                contents_total=total_contents,
                score=score,
                started_at=now - timedelta(days=7),
                completed_at=now - timedelta(days=3) if status == ModuleProgress.Status.COMPLETED else None,
            )
            ModuleProgress.objects.update_or_create(
                course_enrollment=enroll, module=module, defaults=defaults,
            )

        mp(enrollments["emily_ethics"], m_eth_1, ModuleProgress.Status.COMPLETED, 2, 2, score=95)
        mp(enrollments["emily_ethics"], m_eth_2, ModuleProgress.Status.COMPLETED, 2, 2, score=85)
        mp(enrollments["emily_ethics"], m_eth_3, ModuleProgress.Status.COMPLETED, 2, 2, score=92)
        # Michael completed m1 so the m2 case-study assignment is reachable
        # (he has a needs_revision submission there); m2 itself is in_progress.
        mp(enrollments["michael_ethics"], m_eth_1, ModuleProgress.Status.COMPLETED, 2, 2, score=78)
        mp(enrollments["michael_ethics"], m_eth_2, ModuleProgress.Status.IN_PROGRESS, 0, 2)

        # Comms course — Emily is at 60% (modules_completed=3). Mark the first
        # three modules COMPLETED so the player's sequential-unlock gate
        # actually opens m4 (Cultural Competence) for her. Without these rows
        # ``Module.is_available_for`` blocks every module past m1.
        mp(enrollments["emily_comms"], m_c_1, ModuleProgress.Status.COMPLETED, 1, 1, score=90)
        mp(enrollments["emily_comms"], m_c_2, ModuleProgress.Status.COMPLETED, 1, 1, score=88)
        mp(enrollments["emily_comms"], m_c_3, ModuleProgress.Status.COMPLETED, 2, 2, score=85)
        mp(enrollments["michael_comms"], m_c_1, ModuleProgress.Status.COMPLETED, 1, 1, score=80)
        mp(enrollments["michael_comms"], m_c_2, ModuleProgress.Status.IN_PROGRESS, 0, 1)

    # ------------------------------------------------------------------
    # Certificates
    # ------------------------------------------------------------------
    def _build_certificates(self, now, users, registrations, enrollments, templates):
        from certificates.models import Certificate

        tpl = templates["cert_standard"]
        organizer = users["organizer"]

        def mk_cert(*, registration=None, course_enrollment=None, status=Certificate.Status.ACTIVE,
                    issued_days_ago=30, revoke_reason="", view_count=0, download_count=0,
                    cpd_type="general", cpd_credits="1.00", data_extra=None):
            owner_name = (registration.full_name if registration else course_enrollment.user.full_name)
            event_title = registration.event.title if registration else course_enrollment.course.title
            certificate_data = {
                "recipient_name": owner_name,
                "event_title": event_title,
                "cpd_type": cpd_type,
                "cpd_credits": cpd_credits,
            }
            if data_extra:
                certificate_data.update(data_extra)
            defaults = dict(
                template=tpl,
                issued_by=organizer,
                status=status,
                certificate_data=certificate_data,
                email_sent=True,
                email_sent_at=now - timedelta(days=issued_days_ago),
                view_count=view_count,
                download_count=download_count,
                first_viewed_at=(now - timedelta(days=issued_days_ago - 1)) if view_count else None,
                first_downloaded_at=(now - timedelta(days=issued_days_ago - 2)) if download_count else None,
                revoked_at=(now - timedelta(days=2) if status == Certificate.Status.REVOKED else None),
                revoked_by=(users["admin"] if status == Certificate.Status.REVOKED else None),
                revocation_reason=revoke_reason,
            )
            lookup = {}
            if registration:
                lookup["registration"] = registration
            else:
                lookup["course_enrollment"] = course_enrollment
            cert, _ = Certificate.objects.update_or_create(**lookup, defaults=defaults)
            Certificate.objects.filter(pk=cert.pk).update(
                created_at=now - timedelta(days=issued_days_ago),
                file_generated_at=now - timedelta(days=issued_days_ago),
            )
            # Mirror the production cert-issuance service: flip the
            # ``certificate_issued`` flag on the source row so denormalised
            # counts (Event.certificate_count, Course.completion_count etc.)
            # stay consistent for active certs. Revoked certs do not count.
            if status == Certificate.Status.ACTIVE:
                issued_at = now - timedelta(days=issued_days_ago)
                if registration:
                    from registrations.models import Registration
                    Registration.objects.filter(pk=registration.pk).update(
                        certificate_issued=True,
                        certificate_issued_at=issued_at,
                    )
                else:
                    from learning.models import CourseEnrollment
                    CourseEnrollment.objects.filter(pk=course_enrollment.pk).update(
                        certificate_issued=True,
                        certificate_issued_at=issued_at,
                    )
            return cert

        mk_cert(registration=registrations["emily_ethics"], issued_days_ago=33, view_count=3, download_count=1, cpd_type="ethics", cpd_credits="3.00")
        mk_cert(registration=registrations["emily_acls"], issued_days_ago=65, view_count=2, download_count=1, cpd_type="clinical", cpd_credits="4.00")
        mk_cert(registration=registrations["emily_multi"], issued_days_ago=10, view_count=1, download_count=0, cpd_type="general", cpd_credits="4.00")
        mk_cert(registration=registrations["emily_ondemand"], issued_days_ago=20, view_count=1, cpd_type="clinical", cpd_credits="1.25")
        # Revoked (Emily, an older one)
        mk_cert(course_enrollment=enrollments["emily_pharma"], issued_days_ago=180, status=Certificate.Status.REVOKED, revoke_reason="Content superseded; reissued later.", view_count=1, cpd_type="clinical", cpd_credits="2.00")
        # Certificate for completed course
        mk_cert(course_enrollment=enrollments["emily_ethics"], issued_days_ago=5, view_count=2, download_count=1, cpd_type="ethics", cpd_credits="5.00")

        # Michael acls: no cert issued (feedback gate) — intentional absence
        # Michael ethics event: cert issued since feedback wasn't required
        mk_cert(registration=registrations["michael_ethics"], issued_days_ago=33, view_count=0, cpd_type="ethics", cpd_credits="3.00")

    # ------------------------------------------------------------------
    # Badges
    # ------------------------------------------------------------------
    def _build_badges(self, now, users, registrations, enrollments, templates):
        from badges.models import IssuedBadge

        tpl_ethics = templates["badge_ethics"]
        tpl_cpd = templates["badge_cpd"]
        organizer = users["organizer"]

        def mk_badge(template, registration, recipient, *, issued_days_ago=30):
            defaults = dict(
                template=template,
                recipient=recipient,
                issued_by=organizer,
                status=IssuedBadge.Status.ACTIVE,
                issued_at=now - timedelta(days=issued_days_ago),
                badge_data={
                    "recipient_name": recipient.full_name,
                    "event_title": registration.event.title if registration else "",
                    "badge_name": template.name,
                },
            )
            obj, _ = IssuedBadge.objects.update_or_create(
                registration=registration, template=template, recipient=recipient,
                defaults=defaults,
            )
            return obj

        # Emily: three badges — renders a populated grid
        mk_badge(tpl_ethics, registrations["emily_ethics"], users["emily"], issued_days_ago=33)
        mk_badge(tpl_cpd, registrations["emily_acls"], users["emily"], issued_days_ago=65)
        mk_badge(tpl_cpd, registrations["emily_multi"], users["emily"], issued_days_ago=10)
        # Michael/Aisha: no badges → empty state

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------
    def _build_feedback(self, now, events, registrations):
        from feedback.models import EventFeedback, FeedbackField, FeedbackFieldResponse

        def ensure_template(event):
            """Create standard feedback fields for an event (idempotent)."""
            fields = {}
            specs = [
                ("overall_rating", "Overall Rating", FeedbackField.FieldType.RATING, True, 1, 5),
                ("content_rating", "Content Quality", FeedbackField.FieldType.RATING, True, 1, 5),
                ("speaker_rating", "Speaker Effectiveness", FeedbackField.FieldType.RATING, True, 1, 5),
                ("comments", "Comments", FeedbackField.FieldType.TEXTAREA, False, None, None),
            ]
            for i, (key, label, ftype, required, mn, mx) in enumerate(specs):
                fields[key], _ = FeedbackField.objects.update_or_create(
                    event=event, label=label,
                    defaults=dict(field_type=ftype, required=required, order=i, min_value=mn, max_value=mx),
                )
            return fields

        def submit(event, registration, responses, *, created_days_ago=20):
            fb, _ = EventFeedback.objects.update_or_create(
                event=event, session=None, registration=registration,
                defaults=dict(is_anonymous=False),
            )
            EventFeedback.objects.filter(pk=fb.pk).update(created_at=now - timedelta(days=created_days_ago))
            for key, value in responses.items():
                field = FeedbackField.objects.get(event=event, label=_feedback_label_for(key))
                FeedbackFieldResponse.objects.update_or_create(
                    feedback=fb, field=field, defaults=dict(value=value),
                )
            return fb

        # ACLS (feedback required for certs)
        ensure_template(events["acls"])
        submit(events["acls"], registrations["emily_acls"], {
            "overall_rating": 5, "content_rating": 5, "speaker_rating": 5,
            "comments": "Excellent workshop! Simulation realistic and thorough ACLS review.",
        }, created_days_ago=65)
        # Michael did NOT submit for ACLS → certificate blocked

        # Multi-session past (feedback required) — Emily submitted, Michael did not
        ensure_template(events["multi_past"])
        submit(events["multi_past"], registrations["emily_multi"], {
            "overall_rating": 4, "content_rating": 4, "speaker_rating": 5,
            "comments": "Strong leadership sessions — would attend again.",
        }, created_days_ago=10)

        # On-demand past
        ensure_template(events["ondemand"])
        submit(events["ondemand"], registrations["aisha_ondemand"], {
            "overall_rating": 4, "content_rating": 4, "speaker_rating": 4,
            "comments": "Great replay — hoping for more pediatric content.",
        }, created_days_ago=15)

    # ------------------------------------------------------------------
    # Discussions
    # ------------------------------------------------------------------
    def _build_discussions(self, now, users, courses):
        from learning.models import DiscussionFlag, DiscussionReply, DiscussionThread

        def thread(course, author, title, body, *, pinned=False, locked=False, hidden=False,
                   days_ago=5):
            t, _ = DiscussionThread.objects.update_or_create(
                course=course, title=title,
                defaults=dict(
                    author=author,
                    body_html=f"<p>{body}</p>",
                    body_plain=body,
                    is_pinned=pinned, is_locked=locked, is_hidden=hidden,
                    last_activity_at=now - timedelta(days=days_ago),
                ),
            )
            DiscussionThread.objects.filter(pk=t.pk).update(created_at=now - timedelta(days=days_ago))
            return t

        def reply(t, author, body, *, days_ago=3, hidden=False):
            r, _ = DiscussionReply.objects.update_or_create(
                thread=t, author=author, body_plain=body,
                defaults=dict(body_html=f"<p>{body}</p>", is_hidden=hidden),
            )
            DiscussionReply.objects.filter(pk=r.pk).update(created_at=now - timedelta(days=days_ago))
            return r

        ethics = courses["ethics"]
        comms = courses["comms"]
        # course "records" intentionally left without discussions (empty forum state)

        # Ethics course threads
        t_pinned = thread(ethics, users["organizer"], "Welcome and rules",
                          "Read these before posting.", pinned=True, days_ago=30)
        reply(t_pinned, users["emily"], "Thanks for setting the tone!", days_ago=29)
        reply(t_pinned, users["michael"], "Looking forward to the discussions.", days_ago=28)

        t_many = thread(ethics, users["emily"], "Thoughts on Module 2 case study",
                         "Curious what others thought about the consent scenario.", days_ago=10)
        for i, (who, txt) in enumerate([
            (users["michael"], "I found the framing tough."),
            (users["instructor"], "Instructor note — consider the stakeholder map."),
            (users["emily"], "Revised after that — thanks."),
            (users["aisha"], "Jumping in late but agree."),
            (users["michael"], "Follow-up question about precedent?"),
        ]):
            reply(t_many, who, txt, days_ago=10 - i)

        t_zero = thread(ethics, users["michael"], "Quiet thread — any takers?",
                        "Anyone working on the reflection yet?", days_ago=6)

        t_locked = thread(ethics, users["organizer"], "FAQ — please read",
                           "Housekeeping information.", locked=True, days_ago=45)

        t_hidden = thread(ethics, users["aisha"], "Removed by moderator",
                           "This post was hidden after a flag.", hidden=True, days_ago=12)
        reply(t_hidden, users["instructor"], "This thread was hidden by moderators.", days_ago=11)

        # Flag on a thread (Aisha flagged)
        DiscussionFlag.objects.update_or_create(
            thread=t_many, reply=None, reporter=users["aisha"],
            defaults=dict(reason=DiscussionFlag.Reason.OFF_TOPIC, status=DiscussionFlag.Status.OPEN,
                          note="Drifted away from the original topic."),
        )

        # Comms course — lighter
        t_comms = thread(comms, users["emily"], "Active listening tips",
                         "What techniques work best in busy clinics?", days_ago=4)
        reply(t_comms, users["instructor"], "A short pause + reflective summary helps most.", days_ago=3)

    # ------------------------------------------------------------------
    # Billing
    # ------------------------------------------------------------------
    def _build_billing(self, now, users, events, courses):
        from billing.models import CoursePurchase, PaymentMethod, RefundRecord

        # Payment methods
        PaymentMethod.objects.update_or_create(
            stripe_payment_method_id="pm_demo_emily_1",
            defaults=dict(
                user=users["emily"], card_brand="visa", card_last4="4242",
                card_exp_month=12, card_exp_year=now.year + 2, is_default=True,
                billing_email=users["emily"].email,
            ),
        )
        PaymentMethod.objects.update_or_create(
            stripe_payment_method_id="pm_demo_michael_1",
            defaults=dict(
                user=users["michael"], card_brand="mastercard", card_last4="0004",
                card_exp_month=1, card_exp_year=now.year - 1, is_default=True,
                billing_email=users["michael"].email,
            ),
        )

        # Course purchases — Michael refund + completed
        CoursePurchase.objects.update_or_create(
            stripe_payment_intent_id="pi_demo_michael_ethics",
            defaults=dict(
                user=users["michael"], course=courses["ethics"],
                amount_cents=4900, currency="cad",
                status=CoursePurchase.Status.COMPLETED,
            ),
        )
        purchase_refunded, _ = CoursePurchase.objects.update_or_create(
            stripe_payment_intent_id="pi_demo_michael_records_refunded",
            defaults=dict(
                user=users["michael"], course=courses["records"],
                amount_cents=9900, currency="cad",
                status=CoursePurchase.Status.REFUNDED,
            ),
        )
        RefundRecord.objects.update_or_create(
            stripe_refund_id="re_demo_michael_records",
            defaults=dict(
                purchase=purchase_refunded, processed_by=users["admin"],
                stripe_payment_intent_id="pi_demo_michael_records_refunded",
                amount_cents=9900, currency="cad",
                status=RefundRecord.Status.SUCCEEDED,
                reason=RefundRecord.Reason.REQUESTED_BY_CUSTOMER,
                description="Learner changed tracks.",
            ),
        )

    # ------------------------------------------------------------------
    # Promo codes
    # ------------------------------------------------------------------
    def _build_promo_codes(self, now, users, events, registrations):
        from promo_codes.models import PromoCode, PromoCodeUsage

        active, _ = PromoCode.objects.update_or_create(
            owner=users["organizer"], code="SPRING25",
            defaults=dict(
                description="25% off spring CPD events.",
                currency="CAD",
                discount_type=PromoCode.DiscountType.PERCENTAGE,
                discount_value=Decimal("25.00"),
                is_active=True,
                valid_from=now - timedelta(days=30),
                valid_until=now + timedelta(days=60),
                max_uses=100,
                max_uses_per_user=1,
                current_uses=1,
            ),
        )
        active.events.add(events["hybrid"], events["telemed"])

        PromoCode.objects.update_or_create(
            owner=users["organizer"], code="WINTER24",
            defaults=dict(
                description="Expired winter promo.",
                currency="CAD",
                discount_type=PromoCode.DiscountType.FIXED_AMOUNT,
                discount_value=Decimal("15.00"),
                is_active=False,
                valid_from=now - timedelta(days=180),
                valid_until=now - timedelta(days=60),
                max_uses=50,
                current_uses=12,
            ),
        )

        reg_hybrid = registrations["emily_hybrid"]
        PromoCodeUsage.objects.update_or_create(
            promo_code=active, registration=reg_hybrid,
            defaults=dict(
                user_email=reg_hybrid.email, user=users["emily"],
                original_price=Decimal("149.00"),
                discount_amount=Decimal("37.25"),
                final_price=Decimal("111.75"),
            ),
        )

        # Additional codes covering the variants the Promo Codes page filters
        # by: a fully-redeemed code (hits the cap), a max-uses-per-user code,
        # an org-wide percentage code with no event scope, an upcoming code
        # not yet active, and a one-shot VIP code.
        capped, _ = PromoCode.objects.update_or_create(
            owner=users["organizer"], code="ETHICS50",
            defaults=dict(
                description="Half off the Ethics symposium — redeemed in full.",
                currency="CAD",
                discount_type=PromoCode.DiscountType.PERCENTAGE,
                discount_value=Decimal("50.00"),
                is_active=False,
                valid_from=now - timedelta(days=120),
                valid_until=now - timedelta(days=10),
                max_uses=20,
                max_uses_per_user=1,
                current_uses=20,
            ),
        )
        capped.events.add(events["pre_open"], events["ethics"])

        org_wide, _ = PromoCode.objects.update_or_create(
            owner=users["organizer"], code="ALUMNI10",
            defaults=dict(
                description="10% off any event for alumni — applies org-wide.",
                currency="CAD",
                discount_type=PromoCode.DiscountType.PERCENTAGE,
                discount_value=Decimal("10.00"),
                is_active=True,
                valid_from=now - timedelta(days=14),
                valid_until=now + timedelta(days=180),
                max_uses=None,
                max_uses_per_user=2,
                current_uses=4,
            ),
        )
        # No event linkage = applies to all owner's events.

        PromoCode.objects.update_or_create(
            owner=users["organizer"], code="EARLYFALL",
            defaults=dict(
                description="Early-fall preview promo. Activates next week.",
                currency="CAD",
                discount_type=PromoCode.DiscountType.FIXED_AMOUNT,
                discount_value=Decimal("20.00"),
                is_active=True,
                valid_from=now + timedelta(days=7),
                valid_until=now + timedelta(days=90),
                max_uses=200,
                max_uses_per_user=1,
                current_uses=0,
            ),
        )

        vip, _ = PromoCode.objects.update_or_create(
            owner=users["organizer"], code="VIPGUEST",
            defaults=dict(
                description="Single-use VIP code — comp seat at the surgical workshop.",
                currency="CAD",
                discount_type=PromoCode.DiscountType.PERCENTAGE,
                discount_value=Decimal("100.00"),
                is_active=True,
                valid_from=now - timedelta(days=30),
                valid_until=now + timedelta(days=14),
                max_uses=1,
                max_uses_per_user=1,
                current_uses=0,
            ),
        )
        vip.events.add(events["hybrid"])

        # A handful of redemptions on ALUMNI10 so the usage-history view has
        # variety. Tied to existing past registrations.
        for reg_key, original, discount, final in [
            ("emily_telemed", "29.99", "3.00", "26.99"),
            ("michael_telemed_failed", "29.99", "3.00", "26.99"),
            ("emily_acls", "0.00", "0.00", "0.00"),
            ("emily_ondemand", "0.00", "0.00", "0.00"),
        ]:
            reg = registrations.get(reg_key)
            if reg is None:
                continue
            PromoCodeUsage.objects.update_or_create(
                promo_code=org_wide, registration=reg,
                defaults=dict(
                    user_email=reg.email, user=reg.user,
                    original_price=Decimal(original),
                    discount_amount=Decimal(discount),
                    final_price=Decimal(final),
                ),
            )

    # ------------------------------------------------------------------
    # Stripe webhook events + disputes (BillingAdminPage)
    # ------------------------------------------------------------------
    def _build_stripe_events_and_disputes(self, now, users, events, registrations):
        """Populate StripeEvent rows + a couple of Disputes so the admin
        Billing page has plausible Stripe webhook history, an open dispute,
        and a closed (won) dispute. Reconcile drift remains zero by design —
        every webhook here is marked processed.
        """
        from billing.models import CoursePurchase, Dispute, StripeEvent

        def stripe_event(event_id, event_type, *, data, processed=True, error="", days_ago=1):
            obj, _ = StripeEvent.objects.update_or_create(
                event_id=event_id,
                defaults=dict(
                    event_type=event_type,
                    payload={
                        "id": event_id,
                        "type": event_type,
                        "api_version": "2024-04-10",
                        "data": {"object": data},
                        "livemode": False,
                    },
                    processed_at=(now - timedelta(days=days_ago, hours=-1)) if processed else None,
                    error=error,
                ),
            )
            StripeEvent.objects.filter(event_id=event_id).update(
                received_at=now - timedelta(days=days_ago),
            )
            return obj

        # checkout.session.completed for Emily's hybrid registration
        reg_hybrid = registrations["emily_hybrid"]
        stripe_event(
            "evt_demo_checkout_emily_hybrid",
            "checkout.session.completed",
            data={
                "id": "cs_demo_emily_hybrid",
                "amount_total": 14900,
                "currency": "cad",
                "customer_email": reg_hybrid.email,
                "metadata": {"registration_uuid": str(reg_hybrid.uuid), "kind": "event"},
                "payment_intent": "pi_demo_emily_hybrid",
                "payment_status": "paid",
            },
            days_ago=5,
        )
        stripe_event(
            "evt_demo_charge_emily_hybrid",
            "charge.succeeded",
            data={
                "id": "ch_demo_emily_hybrid",
                "amount": 14900, "currency": "cad",
                "payment_intent": "pi_demo_emily_hybrid",
                "status": "succeeded",
            },
            days_ago=5,
        )
        # Michael's refunded course purchase — succeeded → refund.created
        stripe_event(
            "evt_demo_charge_michael_records",
            "charge.succeeded",
            data={
                "id": "ch_demo_michael_records",
                "amount": 9900, "currency": "cad",
                "payment_intent": "pi_demo_michael_records_refunded",
                "status": "succeeded",
            },
            days_ago=15,
        )
        stripe_event(
            "evt_demo_refund_michael_records",
            "charge.refunded",
            data={
                "id": "ch_demo_michael_records",
                "amount_refunded": 9900,
                "currency": "cad",
                "payment_intent": "pi_demo_michael_records_refunded",
                "refunded": True,
            },
            days_ago=10,
        )
        # A failed payment — Telemedicine attempt by Michael
        stripe_event(
            "evt_demo_pi_failed_michael_telemed",
            "payment_intent.payment_failed",
            data={
                "id": "pi_demo_michael_telemed_failed",
                "amount": 2999, "currency": "cad",
                "last_payment_error": {"code": "card_declined", "message": "Your card was declined."},
                "status": "requires_payment_method",
            },
            days_ago=1,
        )
        # An unprocessed event so the "unprocessed" filter has a hit
        stripe_event(
            "evt_demo_unprocessed_invoice",
            "invoice.payment_succeeded",
            data={
                "id": "in_demo_unrelated",
                "amount_paid": 19900, "currency": "cad",
            },
            processed=False,
            days_ago=0,
        )
        # An errored event so the "errored" filter has a hit
        stripe_event(
            "evt_demo_errored_session",
            "checkout.session.completed",
            data={
                "id": "cs_demo_errored",
                "amount_total": 0, "currency": "cad",
                "metadata": {"registration_uuid": "00000000-0000-0000-0000-000000000000"},
            },
            processed=True,
            error="Registration not found for metadata.registration_uuid",
            days_ago=2,
        )
        # Dispute lifecycle pair
        stripe_event(
            "evt_demo_dispute_created",
            "charge.dispute.created",
            data={"id": "dp_demo_open", "charge": "ch_demo_emily_hybrid", "amount": 14900, "currency": "cad"},
            days_ago=3,
        )
        stripe_event(
            "evt_demo_dispute_closed_won",
            "charge.dispute.closed",
            data={"id": "dp_demo_closed", "charge": "ch_demo_michael_ethics", "amount": 4900, "currency": "cad", "status": "won"},
            days_ago=20,
        )

        # Disputes — one open (needs response), one closed-won.
        michael_purchase = CoursePurchase.objects.filter(
            stripe_payment_intent_id="pi_demo_michael_ethics",
        ).first()
        Dispute.objects.update_or_create(
            stripe_dispute_id="dp_demo_open",
            defaults=dict(
                stripe_charge_id="ch_demo_emily_hybrid",
                stripe_payment_intent_id="pi_demo_emily_hybrid",
                registration=reg_hybrid,
                course_purchase=None,
                amount_cents=14900, currency="cad",
                reason=Dispute.Reason.PRODUCT_NOT_RECEIVED,
                status=Dispute.Status.NEEDS_RESPONSE,
                evidence_due_by=now + timedelta(days=4),
                raw_payload={"created_via": "demo seed"},
            ),
        )
        Dispute.objects.update_or_create(
            stripe_dispute_id="dp_demo_closed",
            defaults=dict(
                stripe_charge_id="ch_demo_michael_ethics",
                stripe_payment_intent_id="pi_demo_michael_ethics",
                registration=None,
                course_purchase=michael_purchase,
                amount_cents=4900, currency="cad",
                reason=Dispute.Reason.GENERAL,
                status=Dispute.Status.WON,
                submitted_at=now - timedelta(days=25),
                closed_at=now - timedelta(days=20),
                outcome="won",
                raw_payload={"created_via": "demo seed"},
            ),
        )

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _build_notifications(self, now, users, events, courses):
        from accounts.models import Notification

        def notify(user, ntype, title, *, message="", read=False, days_ago=1, action_url="", metadata=None):
            defaults = dict(
                notification_type=ntype,
                title=title, message=message, action_url=action_url, metadata=metadata or {},
                read_at=(now - timedelta(days=days_ago - 1)) if read else None,
            )
            obj, _ = Notification.objects.update_or_create(
                user=user, title=title, notification_type=ntype, defaults=defaults,
            )
            Notification.objects.filter(pk=obj.pk).update(created_at=now - timedelta(days=days_ago))

        # Emily
        notify(users["emily"], Notification.Type.SYSTEM,
               f"Registration confirmed: {events['ethics'].title}",
               message="You're all set. We'll email a reminder closer to the date.",
               read=True, days_ago=45)
        notify(users["emily"], Notification.Type.SYSTEM,
               "Certificate issued",
               message=f"Your certificate for {events['ethics'].title} is ready.",
               action_url="/certificates", days_ago=33)
        notify(users["emily"], Notification.Type.DISCUSSION_REPLY,
               "New reply on 'Thoughts on Module 2 case study'",
               message="Dr. Torres replied to your thread.",
               days_ago=5)
        # Michael
        notify(users["michael"], Notification.Type.PAYMENT_FAILED,
               "Payment failed for Telemedicine Best Practices",
               message="Please update your payment method and try again.",
               action_url="/registrations", days_ago=1)
        notify(users["michael"], Notification.Type.REFUND_PROCESSED,
               "Refund processed: Digital Health Records",
               message="CA$99.00 has been refunded to your card.",
               read=True, days_ago=10)
        notify(users["michael"], Notification.Type.DISCUSSION_FLAG_RESOLVED,
               "Your post was reviewed",
               message="A moderator reviewed a flagged post in your course.",
               days_ago=4)
        # Aisha
        notify(users["aisha"], Notification.Type.SYSTEM,
               "Added to waitlist: Mental Health First Aid",
               message="You're #1 on the waitlist. We'll email when a spot opens.",
               days_ago=7)
        notify(users["aisha"], Notification.Type.ACCOUNT_ACTIVATED,
               "Welcome to CPD Events",
               message="Finish onboarding to get personalised recommendations.",
               action_url="/onboarding", days_ago=14)

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------
    def _build_audit_log(self, now, users):
        from accounts.models import AuditLog

        def log(actor, action, *, days_ago=1, object_type="", metadata=None):
            AuditLog.objects.create(
                actor=actor, action=action,
                object_type=object_type,
                metadata=metadata or {},
            )
            AuditLog.objects.filter(actor=actor, action=action).update(
                created_at=now - timedelta(days=days_ago),
            )

        entries = [
            (users["admin"], "user.invited", 14, "accounts.User", {"email": "newlearner@example.com"}),
            (users["admin"], "user.role_changed", 10, "accounts.User", {"user_email": users["instructor"].email, "to_roles": ["instructor"]}),
            (users["admin"], "certificate.revoked", 2, "certificates.Certificate", {"reason": "Content superseded"}),
            (users["admin"], "login", 0, "accounts.User", {}),
            (users["organizer"], "event.published", 12, "events.Event", {"title": "Nursing Leadership Summit"}),
            (users["organizer"], "event.completed", 10, "events.Event", {"title": "Nursing Leadership Summit"}),
            (users["organizer"], "course.created", 45, "learning.Course", {"title": "Patient Communication Essentials"}),
            (users["instructor"], "submission.graded", 1, "learning.AssignmentSubmission", {}),
            (users["emily"], "login", 0, "accounts.User", {}),
            (users["michael"], "payment.failed", 1, "registrations.Registration", {}),
        ]
        for actor, action, days_ago, otype, meta in entries:
            log(actor, action, days_ago=days_ago, object_type=otype, metadata=meta)

    # ------------------------------------------------------------------
    # Invitations
    # ------------------------------------------------------------------
    def _build_invitations(self, now, users):
        from accounts.models import UserInvitation

        # Pending invitation (alex rivera)
        UserInvitation.objects.update_or_create(
            email="newlearner@example.com",
            defaults=dict(
                full_name="Dr. Alex Rivera",
                role="learner",
                invited_by=users["admin"],
                token="demo_invite_token_alex",
                expires_at=now + timedelta(days=14),
                is_used=False,
                message="Welcome aboard — click to finish setup.",
                last_sent_at=now - timedelta(days=1),
            ),
        )
        # Expired invitation
        UserInvitation.objects.update_or_create(
            email="expired.invite@example.com",
            defaults=dict(
                full_name="Dr. Sam Rivera",
                role="learner",
                invited_by=users["admin"],
                token="demo_invite_token_expired",
                expires_at=now - timedelta(days=3),
                is_used=False,
                message="",
                last_sent_at=now - timedelta(days=40),
            ),
        )

    # ------------------------------------------------------------------
    # CPD requirements
    # ------------------------------------------------------------------
    def _build_cpd_requirements(self, users):
        from accounts.models import CPDRequirement

        CPDRequirement.objects.update_or_create(
            user=users["emily"], cpd_type="general",
            defaults=dict(
                cpd_type_display="General CPD",
                annual_requirement=Decimal("50.00"),
                period_type=CPDRequirement.PeriodType.CALENDAR_YEAR,
                licensing_body="CPSO", license_number="CPSO-78234",
            ),
        )
        CPDRequirement.objects.update_or_create(
            user=users["emily"], cpd_type="ethics",
            defaults=dict(
                cpd_type_display="Ethics CPD",
                annual_requirement=Decimal("8.00"),
                period_type=CPDRequirement.PeriodType.CALENDAR_YEAR,
                licensing_body="CPSO", license_number="CPSO-78234",
            ),
        )
        CPDRequirement.objects.update_or_create(
            user=users["michael"], cpd_type="general",
            defaults=dict(
                cpd_type_display="General CPD",
                annual_requirement=Decimal("40.00"),
                period_type=CPDRequirement.PeriodType.CALENDAR_YEAR,
                licensing_body="ABFM", license_number="ABFM-44521",
            ),
        )

    # ------------------------------------------------------------------
    # Course announcements
    # ------------------------------------------------------------------
    def _build_course_announcements(self, now, users, courses):
        from learning.models import CourseAnnouncement

        entries = [
            (courses["ethics"], "Welcome to Intro to Clinical Ethics",
             "New cohort kick-off — syllabus and reading list attached.", 20),
            (courses["ethics"], "Module 3 now available",
             "Advanced applications module has been released for all learners.", 6),
            (courses["comms"], "Live Q&A scheduled",
             "Join the optional live Q&A with your instructor next week.", 2),
        ]
        for course, title, body, days_ago in entries:
            obj, _ = CourseAnnouncement.objects.update_or_create(
                course=course, title=title,
                defaults=dict(body=body, is_published=True, created_by=users["organizer"]),
            )
            CourseAnnouncement.objects.filter(pk=obj.pk).update(created_at=now - timedelta(days=days_ago))

    # ------------------------------------------------------------------
    # Submission reviews (activity timeline)
    # ------------------------------------------------------------------
    def _build_submission_reviews(self, now, users):
        from learning.models import AssignmentSubmission, SubmissionReview

        # For each graded/needs-revision submission, write a short history so
        # submission-detail views with an activity timeline are populated.
        for sub in AssignmentSubmission.objects.all():
            SubmissionReview.objects.get_or_create(
                submission=sub, action=SubmissionReview.Action.SUBMITTED,
                defaults=dict(reviewer=None, from_status="", to_status=sub.Status.SUBMITTED,
                              feedback="Submitted by learner."),
            )
            if sub.status in (sub.Status.GRADED, sub.Status.NEEDS_REVISION):
                SubmissionReview.objects.get_or_create(
                    submission=sub, action=SubmissionReview.Action.GRADED,
                    defaults=dict(
                        reviewer=users["instructor"],
                        from_status=sub.Status.SUBMITTED, to_status=sub.status,
                        score=sub.score, feedback=sub.feedback or "",
                    ),
                )

    # ------------------------------------------------------------------
    # Attendance records (ensure timeline has entries for every attended reg)
    # ------------------------------------------------------------------
    def _backfill_attendance_records(self, now, events, registrations):
        from registrations.models import AttendanceRecord, Registration

        attended_regs = Registration.objects.filter(attended=True).exclude(total_attendance_minutes=0)
        for reg in attended_regs:
            if reg.attendance_records.exists():
                continue
            join = reg.event.actual_start_at or reg.event.starts_at
            duration = reg.total_attendance_minutes or 0
            AttendanceRecord.objects.create(
                event=reg.event, registration=reg,
                participant_email=reg.email, participant_name=reg.full_name,
                join_time=join,
                leave_time=join + timedelta(minutes=duration) if duration else None,
                duration_minutes=duration,
                is_matched=True, matched_at=reg.created_at,
                join_method="web",
            )

    # ------------------------------------------------------------------
    # Video rooms + published recordings
    # ------------------------------------------------------------------
    def _build_video_rooms_and_recordings(self, now, events):
        """Stand up VideoRoom rows for video-enabled events and a single
        published VideoRecording (with a sample MP4) for the on-demand replay.

        The room rows are recorded with status=ACTIVE for the live event,
        SCHEDULED for upcoming events, and ENDED for past ones — so the join
        flow has plausible state in admin even when the LiveKit provider
        isn't running locally. The published recording lets the
        ``/events/<uuid>/recording`` page render a real ``<video>`` element
        end-to-end.
        """
        from django.contrib.contenttypes.models import ContentType

        from conferencing.models import VideoRecording, VideoRecordingFile, VideoRoom
        from events.models import Event

        ct = ContentType.objects.get_for_model(Event)

        def upsert_room(event, *, status, started_at=None, ended_at=None):
            room_name = f"event-{event.uuid}"
            obj, _ = VideoRoom.objects.update_or_create(
                content_type=ct, object_id=event.id,
                defaults=dict(
                    room_id=f"demo-{event.uuid}",
                    room_name=room_name,
                    provider='livekit',
                    status=status,
                    started_at=started_at,
                    ended_at=ended_at,
                    settings={"enabled": True, "screen_share": True},
                    max_participants=event.max_attendees or 0,
                ),
            )
            return obj

        # Live event — currently active
        live_room = upsert_room(
            events["live_now"], status=VideoRoom.Status.ACTIVE,
            started_at=now - timedelta(minutes=15),
        )
        # Imminent event — scheduled, not yet started
        upsert_room(events["imminent"], status=VideoRoom.Status.SCHEDULED)
        # Hybrid (upcoming) — scheduled
        upsert_room(events["hybrid"], status=VideoRoom.Status.SCHEDULED)
        # On-demand replay — ended, recording was captured
        ondemand_room = upsert_room(
            events["ondemand"], status=VideoRoom.Status.ENDED,
            started_at=events["ondemand"].starts_at,
            ended_at=events["ondemand"].starts_at + timedelta(minutes=events["ondemand"].duration_minutes),
        )

        # Published recording on the on-demand replay event so the recording
        # playback page renders a real <video> tag.
        recording, _ = VideoRecording.objects.update_or_create(
            event=events["ondemand"], video_room=ondemand_room,
            defaults=dict(
                egress_id=f"demo-egress-{events['ondemand'].uuid}",
                provider='livekit',
                recording_start=events["ondemand"].starts_at,
                recording_end=events["ondemand"].starts_at + timedelta(minutes=75),
                duration_seconds=75 * 60,
                total_size_bytes=42_000_000,
                status=VideoRecording.Status.AVAILABLE,
                storage_path=f"recordings/event-{events['ondemand'].uuid}.mp4",
                access_level=VideoRecording.AccessLevel.REGISTRANTS,
                title=f"{events['ondemand'].title} — Recording",
                description='Auto-published replay of the live session.',
                is_published=True,
                published_at=events["ondemand"].starts_at + timedelta(hours=2),
                view_count=18,
                unique_viewers=12,
            ),
        )
        # A small public-domain MP4 we can point the demo recording at.
        # BigBuckBunny is the canonical sample video used everywhere for tests.
        VideoRecordingFile.objects.update_or_create(
            recording=recording, file_type=VideoRecordingFile.FileType.VIDEO,
            defaults=dict(
                file_name=f"event-{events['ondemand'].uuid}.mp4",
                file_extension='mp4',
                file_size_bytes=42_000_000,
                storage_url='https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
                is_visible=True,
            ),
        )

        # Optional: also surface the live room as having an in-progress
        # recording (no file yet) so the UI shows the "recording" status badge
        # mid-event. Useful for showcasing the recording-active indicator.
        if events["live_now"].recording_enabled:
            VideoRecording.objects.update_or_create(
                video_room=live_room, event=events["live_now"],
                defaults=dict(
                    egress_id=f"demo-egress-live-{events['live_now'].uuid}",
                    provider='livekit',
                    recording_start=events["live_now"].starts_at,
                    status=VideoRecording.Status.RECORDING,
                    access_level=VideoRecording.AccessLevel.REGISTRANTS,
                    title=f"{events['live_now'].title} — Live Recording",
                    is_published=False,
                ),
            )

    # ------------------------------------------------------------------
    # Denormalized counts
    # ------------------------------------------------------------------
    def _refresh_denormalized_counts(self, events, courses, programs):
        from learning.models import CourseEnrollment

        for event in events.values():
            event.update_counts()
        for course in courses.values():
            course.update_counts()
        for program in programs.values():
            program.update_counts()
        # Recompute progress_percent for every ACTIVE enrollment from its
        # leaf data (ContentProgress / submissions / session attendance).
        # The seed inserts those leaves directly via update_or_create, which
        # bypasses the signal cascade — without this pass, dashboards and
        # the My Learning Courses tab would show the seed's literal `progress`
        # arg even when the leaves disagree. COMPLETED enrollments are
        # short-circuited by update_progress() and stay at 100.
        for enrollment in CourseEnrollment.objects.filter(
            status=CourseEnrollment.Status.ACTIVE
        ):
            try:
                enrollment.update_progress()
            except Exception:
                # Don't fail the whole seed if a single enrollment trips on
                # missing related rows — log and move on.
                self.stdout.write(self.style.WARNING(
                    f"  warn: update_progress failed for enrollment {enrollment.id}"
                ))

    # ------------------------------------------------------------------
    # Re-assert event statuses after LiveKit / signal side-effects
    # ------------------------------------------------------------------
    def _reassert_event_statuses(self, events, now):
        """Creating VideoRooms through the real LiveKit provider fires
        room_started webhooks that flip events to ``live``. We undo that for
        every event except the one we intentionally want live-now.
        """
        from events.models import Event

        desired = {
            "ethics": Event.Status.COMPLETED,
            "acls": Event.Status.COMPLETED,
            "telemed": Event.Status.PUBLISHED,
            "live_now": Event.Status.LIVE,
            "waitlist_full": Event.Status.PUBLISHED,
            "hybrid": Event.Status.PUBLISHED,
            "ondemand": Event.Status.COMPLETED,
            "pre_open": Event.Status.PUBLISHED,
            "multi_past": Event.Status.COMPLETED,
        }
        for key, status in desired.items():
            event = events[key]
            Event.objects.filter(pk=event.pk).update(status=status)

# Module-level helper to avoid referencing nested state in closures
def _feedback_label_for(key):
    mapping = {
        "overall_rating": "Overall Rating",
        "content_rating": "Content Quality",
        "speaker_rating": "Speaker Effectiveness",
        "comments": "Comments",
    }
    return mapping[key]
