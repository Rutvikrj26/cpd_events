"""Pure, side-effect-free derivations of UI view-state.

Each function takes a domain entity (and optionally the viewing user) and
returns a discriminated-union dict that the frontend binds to. The kind
field is the discriminator; consumers exhaustively switch on it.

Why this lives outside the model:

- `view_state` is a *projection for a specific consumer* (the learner UI).
  The same enrollment row means different things to a learner ("pending
  approval, awaiting your instructor's review") and to staff ("4 of 12
  pending in this cohort"). Audience-conditional shape belongs in a
  serializer-method-friendly layer, not on the model.

- `status` (the model column) is the write model: invariants (status
  COMPLETED ⟺ progress=100 + completed_at), querysets index on it,
  webhooks fire on transitions. Read consumers must not reconstruct UI
  semantics from it — that's exactly the bug class this module exists
  to eliminate.

- The functions are pure (no DB writes, no I/O beyond the read of
  attributes already on the entity). Easy to unit-test with a dataclass
  stub instead of a full Django object.
"""

from __future__ import annotations

from typing import Any

from learning.models import Course, CourseEnrollment, ProgramEnrollment


# ---------------------------------------------------------------------------
# Course access — used by the player bootstrap to decide whether to render
# the player shell, the pending-approval shell, or redirect to the catalog.
# ---------------------------------------------------------------------------


def derive_course_access(course: Course, *, user, enrollment: CourseEnrollment | None) -> dict[str, Any]:
    """Decide what the user can do with this course right now.

    Returns one of three discriminated shapes:

    - ``{kind: "granted", audience: "learner"|"staff_preview", enrollment_uuid, staff_role}``
      → the player can render the full curriculum.
    - ``{kind: "pending_approval", enrollment_uuid, requested_at, course: <slim>}``
      → the player renders a "your enrollment is awaiting approval" shell.
    - ``{kind: "redirect_to_detail", slug, reason}``
      → the player navigates the user to /courses/{slug}; the catalog page
        renders the right CTA (purchase, sign in, "registration opens at
        ...", etc.).

    Reasons under ``redirect_to_detail`` are stable strings the catalog
    page can branch on for context-aware messaging.
    """
    # Staff preview takes precedence — managers and instructors get the
    # full curriculum regardless of enrollment status, so they can preview
    # what learners see.
    staff_role = course.get_staff_role(user) if user and user.is_authenticated else None
    if staff_role:
        return {
            "kind": "granted",
            "audience": "staff_preview",
            "enrollment_uuid": str(enrollment.uuid) if enrollment else None,
            "staff_role": staff_role,
        }

    # Learner path: enrollment status decides.
    if enrollment is not None:
        if enrollment.status in (
            CourseEnrollment.Status.ACTIVE,
            CourseEnrollment.Status.COMPLETED,
        ):
            return {
                "kind": "granted",
                "audience": "learner",
                "enrollment_uuid": str(enrollment.uuid),
                "staff_role": None,
            }
        if enrollment.status == CourseEnrollment.Status.PENDING:
            return {
                "kind": "pending_approval",
                "enrollment_uuid": str(enrollment.uuid),
                "requested_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
                "course": _slim_course(course),
            }
        # DROPPED / EXPIRED → fall through to redirect; catalog explains.
        return {
            "kind": "redirect_to_detail",
            "slug": course.slug,
            "reason": _enrollment_revoked_reason(enrollment.status),
        }

    # No enrollment at all. If the course is paid, route to catalog with
    # a payment hint; otherwise route with the course's enrollability
    # reason (window-closed, full, or open-but-not-yet-enrolled).
    if course.price_cents and course.price_cents > 0:
        return {
            "kind": "redirect_to_detail",
            "slug": course.slug,
            "reason": "PAYMENT_REQUIRED",
        }
    ok, code, _msg = course.check_enrollable()
    return {
        "kind": "redirect_to_detail",
        "slug": course.slug,
        "reason": code or "NOT_ENROLLED",
    }


def _slim_course(course: Course) -> dict[str, Any]:
    """Minimal course shape for non-granted shells.

    Just enough for the "you're enrolled in X, awaiting approval" banner
    to render with the course title and image. The full CourseSerializer
    is overkill for the non-player shells.
    """
    return {
        "uuid": str(course.uuid),
        "title": course.title,
        "slug": course.slug,
        "featured_image_url": course.featured_image_url or None,
    }


def _enrollment_revoked_reason(status: str) -> str:
    """Map a non-active/non-pending enrollment status to a redirect reason."""
    return {
        CourseEnrollment.Status.DROPPED: "ENROLLMENT_DROPPED",
        CourseEnrollment.Status.EXPIRED: "ENROLLMENT_EXPIRED",
    }.get(status, "NOT_ENROLLED")


# ---------------------------------------------------------------------------
# Course enrollment view-state — used inside the granted player payload and
# anywhere else a learner-facing UI needs to render an enrollment card.
# ---------------------------------------------------------------------------


def derive_course_enrollment_view_state(enrollment: CourseEnrollment) -> dict[str, Any]:
    """Discriminated UI state for a single CourseEnrollment.

    Six kinds covering every state the learner UI needs to handle. The
    catalog already shows non-enrolled courses, so we do not handle
    "not_enrolled" here — that's a pre-condition for this function being
    called at all.
    """
    status = enrollment.status

    if status == CourseEnrollment.Status.PENDING:
        return {
            "kind": "awaiting_approval",
            "requested_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
        }

    if status == CourseEnrollment.Status.COMPLETED:
        certificate_uuid = None
        if enrollment.certificate_issued:
            # Lazy: the wallet endpoint will surface the actual cert.
            cert = (
                enrollment.user.certificates.filter(
                    course_enrollment=enrollment, status="active", deleted_at__isnull=True,
                )
                .order_by("-created_at")
                .first()
            )
            certificate_uuid = str(cert.uuid) if cert else None
        return {
            "kind": "completed",
            "completed_at": enrollment.completed_at.isoformat() if enrollment.completed_at else None,
            "certificate_uuid": certificate_uuid,
        }

    if status == CourseEnrollment.Status.ACTIVE:
        if enrollment.progress_percent <= 0 and not enrollment.started_at:
            return {
                "kind": "ready_to_start",
                "first_module_uuid": _first_module_uuid(enrollment.course),
            }
        return {
            "kind": "in_progress",
            "percent": int(enrollment.progress_percent or 0),
            "next_content_uuid": None,  # Phase 1.5: thread through from progress snapshot.
        }

    # DROPPED / EXPIRED — collapse to a single revoked kind with the reason.
    return {
        "kind": "revoked",
        "reason": status,
    }


def derive_program_enrollment_view_state(enrollment: ProgramEnrollment) -> dict[str, Any]:
    """Discriminated UI state for a single ProgramEnrollment.

    Mirrors the course-enrollment kinds, minus the live-session-specific
    ones (programs are bundles; live sessions belong to their member
    courses, not the program itself).

    Five kinds:
      - awaiting_approval — pending; instructor hasn't approved yet
      - ready_to_start    — active, no member-course progress
      - in_progress       — active, ≥1 member course started
      - completed         — every required member course completed
      - revoked           — dropped (or any future non-active terminal)
    """
    status = enrollment.status

    if status == ProgramEnrollment.Status.PENDING:
        return {
            "kind": "awaiting_approval",
            "requested_at": enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
        }

    if status == ProgramEnrollment.Status.COMPLETED:
        return {
            "kind": "completed",
            "completed_at": enrollment.completed_at.isoformat() if enrollment.completed_at else None,
        }

    if status == ProgramEnrollment.Status.ACTIVE:
        # "Started" means at least one member-course CourseEnrollment is
        # ACTIVE/COMPLETED with progress > 0.
        any_started = (
            CourseEnrollment.objects.filter(
                from_program_enrollment=enrollment,
                status__in=(
                    CourseEnrollment.Status.ACTIVE,
                    CourseEnrollment.Status.COMPLETED,
                ),
                progress_percent__gt=0,
            ).exists()
        )
        if not any_started:
            return {"kind": "ready_to_start"}
        # Aggregate progress across required member courses; gives the UI
        # a single number to render in the badge / progress bar.
        return {
            "kind": "in_progress",
            "percent": _program_aggregate_percent(enrollment),
        }

    # DROPPED / future terminal states.
    return {"kind": "revoked", "reason": status}


def _program_aggregate_percent(enrollment: ProgramEnrollment) -> int:
    """Average of member-course progress percentages, clamped to [0, 100]."""
    rows = CourseEnrollment.objects.filter(
        from_program_enrollment=enrollment,
    ).values_list("progress_percent", flat=True)
    if not rows:
        return 0
    avg = sum(int(p or 0) for p in rows) / len(rows)
    return max(0, min(100, int(round(avg))))


# ---------------------------------------------------------------------------
# Event registration — Registration's (status × payment_status × event_is_past
# × attended) cross-product collapses to six discriminated UI kinds.
# ---------------------------------------------------------------------------


def derive_registration_view_state(registration) -> dict[str, Any]:
    """Discriminated UI state for a single ``registrations.Registration``.

    Six kinds capture every learner-facing state the My Registrations
    cards need to render:

    - ``awaiting_payment`` — pending registration; payment unsuccessful.
      Carries ``payment_failed`` so the CTA can switch between "Resume"
      and "Try again".
    - ``confirmed_upcoming`` — confirmed, event hasn't started.
      Lobby / calendar CTAs.
    - ``confirmed_attended`` — past event, attendance recorded eligible.
      Certificate / feedback CTAs.
    - ``confirmed_missed`` — past event, no eligible attendance. The
      catalog/recording page is the recovery CTA.
    - ``waitlisted`` — no CTAs other than "leave waitlist".
    - ``cancelled`` — terminal; "Re-register" if the event is still in
      the future, else a quiet "View event" link.
    """
    from registrations.models import Registration

    status = registration.status
    payment_status = registration.payment_status
    event = registration.event
    is_past = event.is_past if event else False

    if status == Registration.Status.PENDING:
        return {
            "kind": "awaiting_payment",
            "payment_failed": payment_status == Registration.PaymentStatus.FAILED,
        }

    if status == Registration.Status.WAITLISTED:
        return {
            "kind": "waitlisted",
            "position": registration.waitlist_position,
        }

    if status == Registration.Status.CANCELLED:
        return {
            "kind": "cancelled",
            "event_in_future": not is_past,
        }

    # CONFIRMED — branch on past/future + attendance.
    if not is_past:
        return {
            "kind": "confirmed_upcoming",
            "event_starts_at": event.starts_at.isoformat() if event and event.starts_at else None,
        }

    if registration.attendance_eligible:
        return {
            "kind": "confirmed_attended",
            "certificate_issued": bool(registration.certificate_issued),
        }

    return {"kind": "confirmed_missed"}


def _first_module_uuid(course: Course) -> str | None:
    """First published module by order — the natural deep-link target for
    a brand-new enrollment. Returns the module's underlying EventModule
    uuid (which is what the player uses for routing)."""
    link = (
        course.modules.select_related("module")
        .filter(module__is_published=True)
        .order_by("order")
        .first()
    )
    return str(link.module.uuid) if link and link.module else None
