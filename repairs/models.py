from django.db import models, transaction
from inventory.models import Item, Person

class RepairTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('unrepairable', 'Unrepairable'),
        ('cancelled', 'Cancelled'),
    ]

    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='repair_tickets')
    issue_description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reported_by = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, related_name='reported_tickets')
    reported_date = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_tickets')
    expected_completion_date = models.DateField(blank=True, null=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Allow skipping item status sync if requested (e.g., from view prompt)
        skip_item_sync = kwargs.pop('skip_item_sync', False)

        if not self.ticket_number:
            # Generate a unique ticket number: R-YYYYMMDD-XXXX
            import random
            import string
            from datetime import datetime
            prefix = f"R-{datetime.now().strftime('%Y%m%d')}"
            random_suffix = ''.join(random.choices(string.digits, k=4))
            self.ticket_number = f"{prefix}-{random_suffix}"

        with transaction.atomic():
            super().save(*args, **kwargs)

            if not skip_item_sync:
                # Sync Item Status based on ticket status
                if self.status == 'completed':
                    self.item.status = 'available'
                elif self.status == 'unrepairable':
                    self.item.status = 'decommissioned'
                elif self.status in ['pending', 'in_progress']:
                    self.item.status = 'in_repair'
                self.item.save()

    def __str__(self):
        return f"{self.ticket_number} - {self.item.name}"

class RepairLog(models.Model):
    ticket = models.ForeignKey(RepairTicket, on_delete=models.CASCADE, related_name='logs')
    note = models.TextField()
    status_at_time = models.CharField(max_length=20, choices=RepairTicket.STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log for {self.ticket.ticket_number} at {self.created_at}"