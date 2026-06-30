from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .services import get_unread_count, mark_as_read, get_recent_notifications, delete_notifications


@login_required
def api_notifications_list(request):
    """Return recent notifications for current user."""
    notifications = get_recent_notifications(request.user)
    data = []
    for n in notifications:
        item = getattr(n, 'related_item', None)
        ticket = getattr(n, 'related_ticket', None)
        data.append({
            'id': n.id,
            'type': n.type.code if n.type else 'unknown',
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'item_id': item.id if item else None,
            'item_name': item.name if item else None,
            'ticket_id': ticket.id if ticket else None,
            'ticket_number': ticket.ticket_number if ticket else None,
        })
    return JsonResponse({'notifications': data})


@require_POST
@login_required
def api_mark_read(request):
    """Mark notifications as read."""
    ids = request.POST.getlist('ids[]')
    if not ids:
        ids = request.POST.getlist('ids')
    mark_as_read(request.user, ids)
    return JsonResponse({'success': True})


@login_required
def api_unread_count(request):
    """Return unread notification count."""
    return JsonResponse({'count': get_unread_count(request.user)})


@require_POST
@login_required
def api_delete_notifications(request):
    """Delete notifications for current user."""
    ids = request.POST.getlist('ids[]')
    if not ids:
        ids = request.POST.getlist('ids')
    deleted_count = delete_notifications(request.user, ids)
    return JsonResponse({'success': True, 'deleted_count': deleted_count})