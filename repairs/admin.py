from django.contrib import admin
from .models import RepairTicket

@admin.register(RepairTicket)
class RepairTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'item', 'priority', 'status', 'reported_by', 'reported_date')
    list_filter = ('status', 'priority')
    search_fields = ('ticket_number', 'item__name', 'issue_description')
    readonly_fields = ('ticket_number', 'reported_date')