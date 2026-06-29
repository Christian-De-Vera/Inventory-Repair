from django.db import models
from django.contrib.auth.models import User


class NotificationType(models.Model):
    code = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, default='bi-bell')

    def __str__(self):
        return self.label


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_item = models.ForeignKey('inventory.Item', on_delete=models.SET_NULL, null=True, blank=True)
    related_ticket = models.ForeignKey('repairs.RepairTicket', on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type.label}: {self.title}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    email_repair_ticket = models.BooleanField(default=True)
    email_item_status = models.BooleanField(default=True)
    email_item_moved = models.BooleanField(default=True)
    email_eol_warning = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Preferences for {self.user.username}"