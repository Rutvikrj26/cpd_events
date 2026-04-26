"""
Certificate signals — keep User.total_cpd_credits in sync.

Without this, the denormalised field stays at 0 forever and any reader has
to reach into Certificate rows live. The signal is intentionally tolerant:
it sums every active cert across the user's registrations and course
enrollments, regardless of cpd_type, so it represents lifetime credits
rather than within-period earned credits (the latter belongs to
CPDRequirement.get_earned_credits).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


def _recompute_for_user(user):
    if not user:
        return

    from certificates.models import Certificate

    qs = Certificate.objects.filter(
        Q(registration__user=user) | Q(course_enrollment__user=user),
        status=Certificate.Status.ACTIVE,
    )
    total = Decimal("0")
    for cert in qs:
        try:
            val = cert.certificate_data.get("cpd_credits", 0) if cert.certificate_data else 0
            total += Decimal(str(val))
        except (TypeError, ValueError, InvalidOperation):
            continue

    if user.total_cpd_credits != total:
        user.__class__.objects.filter(pk=user.pk).update(total_cpd_credits=total)


def _user_for(cert) -> "object | None":
    if cert.registration and cert.registration.user:
        return cert.registration.user
    if cert.course_enrollment and cert.course_enrollment.user:
        return cert.course_enrollment.user
    return None


@receiver(post_save, sender="certificates.Certificate")
def update_total_cpd_credits_on_save(sender, instance, **kwargs):
    _recompute_for_user(_user_for(instance))


@receiver(post_delete, sender="certificates.Certificate")
def update_total_cpd_credits_on_delete(sender, instance, **kwargs):
    _recompute_for_user(_user_for(instance))
