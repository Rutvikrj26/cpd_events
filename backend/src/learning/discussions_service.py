"""Side effects for discussion board events — notifications and emails."""

from __future__ import annotations

import logging
import os

from accounts.models import Notification
from accounts.notifications import create_notification

logger = logging.getLogger(__name__)


def _emails_enabled() -> bool:
    return os.getenv('DISCUSSION_EMAILS_ENABLED', 'True').lower() in ('1', 'true', 'yes')


def _course_url(course) -> str:
    return f"/learn/{course.uuid}?tab=discussion"


def _thread_url(thread) -> str:
    return f"/learn/{thread.course.uuid}?tab=discussion&thread={thread.uuid}"


def _send_email(template: str, recipient, context: dict) -> None:
    if not _emails_enabled() or not recipient or not getattr(recipient, 'email', None):
        return
    try:
        from integrations.services import email_service

        email_service.send_email(template, recipient.email, context)
    except Exception as e:
        logger.warning('discussion email send failed: %s', e)


def notify_new_reply(reply) -> None:
    """Notify thread author + prior reply authors when a new reply lands."""
    from .models import DiscussionReply

    thread = reply.thread
    recipients: dict[int, object] = {}
    if thread.author_id and thread.author_id != reply.author_id:
        recipients[thread.author_id] = thread.author
    prior_authors = (
        DiscussionReply.objects.filter(thread=thread)
        .exclude(pk=reply.pk)
        .exclude(author__isnull=True)
        .exclude(author_id=reply.author_id)
        .select_related('author')
    )
    for prior in prior_authors:
        recipients.setdefault(prior.author_id, prior.author)

    context = {
        'course_title': thread.course.title,
        'thread_title': thread.title,
        'reply_author': (reply.author.full_name if reply.author else 'Someone'),
        'reply_excerpt': (reply.body_plain or '')[:240],
        'thread_url': _thread_url(thread),
    }

    for user in recipients.values():
        create_notification(
            user=user,
            title=f"New reply in “{thread.title}”",
            message=context['reply_excerpt'],
            notification_type=Notification.Type.DISCUSSION_REPLY,
            action_url=context['thread_url'],
            metadata={
                'course_uuid': str(thread.course.uuid),
                'thread_uuid': str(thread.uuid),
                'reply_uuid': str(reply.uuid),
            },
        )
        ctx = dict(context, user_name=user.full_name)
        _send_email('discussion_reply', user, ctx)


def notify_mentions(post, mentioned_users) -> None:
    """Notify users @-mentioned in a thread body or reply body."""
    if not mentioned_users:
        return
    from .models import DiscussionReply

    if isinstance(post, DiscussionReply):
        thread = post.thread
        body_plain = post.body_plain
    else:
        thread = post
        body_plain = post.body_plain

    context = {
        'course_title': thread.course.title,
        'thread_title': thread.title,
        'mentioned_by': (post.author.full_name if post.author else 'Someone'),
        'excerpt': (body_plain or '')[:240],
        'thread_url': _thread_url(thread),
    }

    author_id = post.author_id
    for user in mentioned_users:
        if user.id == author_id:
            continue
        create_notification(
            user=user,
            title=f"You were mentioned in “{thread.title}”",
            message=context['excerpt'],
            notification_type=Notification.Type.DISCUSSION_MENTION,
            action_url=context['thread_url'],
            metadata={
                'course_uuid': str(thread.course.uuid),
                'thread_uuid': str(thread.uuid),
                'post_uuid': str(post.uuid),
            },
        )
        ctx = dict(context, user_name=user.full_name)
        _send_email('discussion_mention', user, ctx)


def notify_flag_resolved(flag) -> None:
    """Notify the flag reporter + the content author when a flag is resolved."""
    from .models import DiscussionReply

    target = flag.thread if flag.thread_id else flag.reply
    if not target:
        return
    thread = target if not isinstance(target, DiscussionReply) else target.thread
    outcome = 'hidden' if flag.status == flag.Status.RESOLVED_HIDDEN else 'kept'
    context = {
        'course_title': thread.course.title,
        'thread_title': thread.title,
        'outcome': outcome,
        'thread_url': _thread_url(thread),
    }
    recipients: dict[int, object] = {}
    if flag.reporter_id and flag.reporter:
        recipients[flag.reporter_id] = flag.reporter
    if target.author_id and target.author:
        recipients.setdefault(target.author_id, target.author)

    for user in recipients.values():
        create_notification(
            user=user,
            title=f"Flag resolved in “{thread.title}”",
            message=f"Content was {outcome} by staff.",
            notification_type=Notification.Type.DISCUSSION_FLAG_RESOLVED,
            action_url=context['thread_url'],
            metadata={
                'course_uuid': str(thread.course.uuid),
                'thread_uuid': str(thread.uuid),
                'flag_uuid': str(flag.uuid),
                'outcome': outcome,
            },
        )
