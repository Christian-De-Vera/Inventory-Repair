from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import Group

from inventory.models import Item
from repairs.models import RepairTicket
from .services import create_notification
from threading import local

_thread_locals = local()


def _set_value(key, value):
    """Set a value in thread-local storage."""
    if not hasattr(_thread_locals, 'data'):
        _thread_locals.data = {}
    _thread_locals.data[key] = value


def _get_value(key):
    """Get a value from thread-local storage."""
    if not hasattr(_thread_locals, 'data'):
        return None
    return _thread_locals.data.get(key)


@receiver(pre_save, sender=RepairTicket)
def store_ticket_before_save(sender, instance, **kwargs):
    """Store ticket's old status before save."""
    if instance.pk:
        try:
            old_ticket = RepairTicket.objects.get(pk=instance.pk)
            _set_value(f'ticket_{instance.pk}_old_status', old_ticket.status)
        except RepairTicket.DoesNotExist:
            _set_value(f'ticket_{instance.pk}_old_status', None)


@receiver(post_save, sender=RepairTicket)
def repair_ticket_created(sender, instance, created, **kwargs):
    """Create notification when repair ticket is created."""
    if created:
        mis_group = Group.objects.filter(name='MIS').first()
        if mis_group:
            for user in mis_group.user_set.all():
                create_notification(
                    recipient=user,
                    type_code='repair_ticket_new',
                    title=f'New Repair Ticket: {instance.ticket_number}',
                    message=f'Ticket created for item {instance.item.name} - {instance.issue_description[:50] if instance.issue_description else ""}...',
                    related_ticket=instance
                )
                create_notification(
                    recipient=user,
                    type_code='item_in_repair',
                    title=f'{instance.item.name} marked for repair',
                    message=f'Item {instance.item.item_code} has been marked as "In Repair"',
                    related_item=instance.item
                )


@receiver(post_save, sender=RepairTicket)
def repair_ticket_status_changed(sender, instance, created, **kwargs):
    """Create notification when repair ticket status changes."""
    if created:
        return

    old_status = _get_value(f'ticket_{instance.pk}_old_status')
    if old_status is None:
        return

    if instance.status in ['completed', 'unrepairable'] and old_status != instance.status:
        mis_group = Group.objects.filter(name='MIS').first()
        if mis_group:
            for user in mis_group.user_set.all():
                create_notification(
                    recipient=user,
                    type_code='repair_ticket_resolved',
                    title=f'Ticket {instance.ticket_number} {instance.get_status_display()}',
                    message=f'Item {instance.item.name} repair completed',
                    related_ticket=instance
                )


@receiver(pre_save, sender=Item)
def store_item_before_save(sender, instance, **kwargs):
    """Store item's old values before save to detect changes."""
    if instance.pk:
        try:
            old_item = Item.objects.get(pk=instance.pk)
            _set_value(f'item_{instance.pk}_old_status', old_item.status)
            _set_value(f'item_{instance.pk}_old_location_id', old_item.location_id)
        except Item.DoesNotExist:
            _set_value(f'item_{instance.pk}_old_status', None)
            _set_value(f'item_{instance.pk}_old_location_id', None)


@receiver(post_save, sender=Item)
def item_status_changed(sender, instance, created, **kwargs):
    """Create notifications when item status or location changes."""
    if created:
        return

    old_status = _get_value(f'item_{instance.pk}_old_status')
    old_location_id = _get_value(f'item_{instance.pk}_old_location_id')

    mis_group = Group.objects.filter(name='MIS').first()
    mis_users = set(mis_group.user_set.all()) if mis_group else set()

    # Item status changed from in_repair to something else (repair completed/cancelled)
    if old_status is not None and old_status == 'in_repair' and instance.status != 'in_repair':
        for user in mis_users:
            create_notification(
                recipient=user,
                type_code='item_status_changed',
                title=f'{instance.name} status updated',
                message=f'Item status changed from "In Repair" to {instance.get_status_display()}',
                related_item=instance
            )

    # Location change (notify MIS users if location actually changed)
    if old_location_id is not None and old_location_id != instance.location_id:
        for user in mis_users:
            new_location = instance.location.name if instance.location else 'Unknown'
            create_notification(
                recipient=user,
                type_code='item_moved',
                title=f'{instance.name} location changed',
                message=f'Item moved to {new_location}',
                related_item=instance
            )