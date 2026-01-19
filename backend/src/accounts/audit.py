"""
Audit logging helpers.
"""

from __future__ import annotations

from typing import Any

from accounts.models import AuditLog


def _get_ip_address(request) -> str | None:
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit_event(
    *,
    actor,
    action: str,
    object_type: str = "",
    object_uuid: str = "",
    metadata: dict[str, Any] | None = None,
    request=None,
) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=object_type,
        object_uuid=object_uuid,
        metadata=metadata or {},
        ip_address=_get_ip_address(request),
        user_agent=getattr(request, "META", {}).get("HTTP_USER_AGENT", ""),
    )
