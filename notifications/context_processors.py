from .services import get_unread_count


def unread_count(request):
    if request.user.is_authenticated:
        return {'unread_notification_count': get_unread_count(request.user)}
    return {'unread_notification_count': 0}