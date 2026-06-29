from django.db import IntegrityError
from .models import Notification, NotificationType, NotificationPreference


def create_notification(recipient, type_code, title, message, related_item=None, related_ticket=None):
    """Create a notification for a recipient."""
    try:
        notification_type, _ = NotificationType.objects.get_or_create(
            code=type_code,
            defaults={'label': type_code.replace('_', ' ').title()}
        )
    except IntegrityError:
        notification_type = NotificationType.objects.get(code=type_code)
    return Notification.objects.create(
        recipient=recipient,
        type=notification_type,
        title=title,
        message=message,
        related_item=related_item,
        related_ticket=related_ticket
    )


def get_unread_count(user):
    """Get count of unread notifications for user."""
    return Notification.objects.filter(recipient=user, is_read=False).count()


def mark_as_read(user, notification_ids):
    """Mark notifications as read."""
    Notification.objects.filter(recipient=user, id__in=notification_ids).update(is_read=True)


def get_recent_notifications(user, limit=10):
    """Get recent notifications for user."""
    return Notification.objects.filter(recipient=user).select_related('type', 'related_item', 'related_ticket')[:limit]


def get_or_create_preferences(user):
    """Get or create notification preferences for user."""
    preferences, _ = NotificationPreference.objects.get_or_create(user=user)
    return preferences