"""
Notification helpers for creating in-app notifications.
"""

from __future__ import annotations

from typing import Any

from accounts.models import Notification


def create_notification(
    *,
    user,
    title: str,
    message: str = '',
    notification_type: str = Notification.Type.SYSTEM,
    action_url: str = '',
    metadata: dict[str, Any] | None = None,
) -> Notification | None:
    if not user:
        return None

    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        metadata=metadata or {},
    )
