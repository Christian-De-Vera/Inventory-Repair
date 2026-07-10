from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group

from notifications.services import create_notification
from .roles import ROLE_ADMIN


@receiver(post_save, sender=User)
def notify_admins_on_new_user(sender, instance, created, **kwargs):
    if not created or instance.is_superuser:
        return
    admin_group = Group.objects.filter(name=ROLE_ADMIN).first()
    if not admin_group:
        return
    for admin_user in admin_group.user_set.all():
        create_notification(
            recipient=admin_user,
            type_code='new_user_registered',
            title='New User Registration Pending',
            message=f'User "{instance.username}" has registered and is awaiting role assignment.',
        )
