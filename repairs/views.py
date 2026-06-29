from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Q, Sum, DecimalField
import csv
import json
from datetime import date, timedelta
from decimal import Decimal
from .models import RepairTicket, RepairLog
from inventory.models import Item, Person

@permission_required('repairs.view_repairticket', raise_exception=True)
def repair_ticket_list(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    ticket_status_codes = [choice[0] for choice in RepairTicket.STATUS_CHOICES]
    status_choices = list(RepairTicket.STATUS_CHOICES) + [('in_repair', 'In Repair')]

    # Optimized base querysets to prevent N+1 database hits in the templates
    tickets_qs = RepairTicket.objects.select_related('item', 'item__category', 'item__location', 'reported_by', 'assigned_to')
    items_qs = Item.objects.select_related('category', 'location').filter(status='in_repair').distinct()

    # Identify "orphaned" items: marked 'in_repair' but no active pending/in-progress ticket
    orphaned_items_qs = items_qs.exclude(repair_tickets__status__in=['pending', 'in_progress'])

    if search_query:
        tickets_qs = tickets_qs.filter(
            Q(ticket_number__icontains=search_query) |
            Q(item__name__icontains=search_query) |
            Q(issue_description__icontains=search_query) |
            Q(resolution_notes__icontains=search_query)
        )

    if status_filter in ticket_status_codes:
        tickets = tickets_qs.filter(status=status_filter).order_by('-reported_date')
    else:
        tickets = tickets_qs.all().order_by('-reported_date')

    entries = []
    if status_filter == 'in_repair':
        entries = [
            {'type': 'item', 'item': item, 'sort_date': item.updated_at}
            for item in orphaned_items_qs
        ]
    else:
        entries = [
            {'type': 'ticket', 'ticket': ticket, 'sort_date': ticket.reported_date}
            for ticket in tickets
        ]
        
        # Only include orphaned items in the general list if not filtering by a specific ticket status
        if not status_filter:
            entries += [
                {'type': 'item', 'item': item, 'sort_date': item.updated_at}
                for item in orphaned_items_qs
            ]
            
        entries.sort(key=lambda entry: entry['sort_date'], reverse=True)

    paginator = Paginator(entries, 20)
    page = request.GET.get('page', 1)
    entries_page = paginator.get_page(page)
    context = {
        'entries': entries_page,
        'status_filter': status_filter,
        'status_choices': status_choices,
        'nav_section': 'repairs',
        'search_query': search_query,
    }
    return render(request, 'repairs/ticket_list.html', context)

@permission_required('repairs.view_repairticket', raise_exception=True)
def repair_ticket_detail(request, pk):
    ticket = get_object_or_404(
        RepairTicket.objects.select_related('item', 'reported_by', 'assigned_to'),
        pk=pk
    )
    # Fetch the chronological history for this ticket
    logs = ticket.logs.all().order_by('-created_at')
    return render(request, 'repairs/ticket_detail.html', {'ticket': ticket, 'logs': logs, 'nav_section': 'repairs'})

@permission_required('repairs.add_repairticket', raise_exception=True)
def repair_ticket_create(request, item_id=None):
    item = None
    if request.method == 'POST':
        # Get item from POST or URL parameter
        effective_item_id = request.POST.get('item') or item_id
        if not effective_item_id:
            messages.error(request, "An item must be selected to create a repair ticket.")
            return redirect('repairs:ticket_list')
            
        item = get_object_or_404(Item, id=effective_item_id)

        # Ensure item is in "In Repair" status
        if item.status != 'in_repair':
            messages.error(request, f"Cannot create ticket: {item.name} is not marked as 'In Repair'.")
            return redirect('item_detail', id=item.id)

        # Prevent duplicate active tickets for the same item
        existing_ticket = RepairTicket.objects.filter(item=item, status__in=['pending', 'in_progress']).first()
        if existing_ticket:
            messages.error(request, f"Item {item.name} already has an active repair ticket ({existing_ticket.ticket_number}).")
            return redirect('repairs:ticket_detail', pk=existing_ticket.pk)

        # Handle reported_by (could be ID or Name string from legacy forms)
        reported_by_val = request.POST.get('reported_by')
        reported_by_obj = None
        if reported_by_val:
            if str(reported_by_val).isdigit():
                reported_by_obj = Person.objects.filter(id=reported_by_val).first()
            else:
                # Fallback: find person by name if the form sent a string
                reported_by_obj = Person.objects.filter(name=reported_by_val).first()

        # Handle assigned_to if provided at creation
        assigned_to_id = request.POST.get('assigned_to')
        assigned_to_obj = None
        if assigned_to_id and assigned_to_id.isdigit():
            assigned_to_obj = Person.objects.filter(id=assigned_to_id).first()

        ticket = RepairTicket(
            item=item,
            issue_description=request.POST.get('issue_description'),
            priority=request.POST.get('priority'),
            reported_by=reported_by_obj,
            assigned_to=assigned_to_obj,
            expected_completion_date=request.POST.get('expected_completion_date') or None,
            estimated_cost=request.POST.get('estimated_cost') or 0.00,
        )
        ticket.save()

        # Log the initial ticket creation event
        log_note = f"Ticket created by {ticket.reported_by.name if ticket.reported_by else 'system'}."
        if ticket.assigned_to:
            log_note += f" Assigned to {ticket.assigned_to.name}."
            
        RepairLog.objects.create(
            ticket=ticket,
            note=log_note,
            status_at_time=ticket.status
        )

        messages.success(request, f'Repair ticket {ticket.ticket_number} created successfully.')
        return redirect('repairs:ticket_detail', pk=ticket.pk)

    if item_id:
        item = get_object_or_404(Item, id=item_id)
        # Ensure item is in "In Repair" status before showing the form
        if item.status != 'in_repair':
            messages.error(request, f"Item {item.name} must be marked as 'In Repair' before creating a ticket.")
            return redirect('item_detail', id=item.id)
            
        # Redirect if a specific item is requested but it already has an active ticket
        existing_ticket = RepairTicket.objects.filter(item=item, status__in=['pending', 'in_progress']).first()
        if existing_ticket:
            messages.warning(request, f"Item {item.name} already has an active repair ticket.")
            return redirect('repairs:ticket_detail', pk=existing_ticket.pk)

    # Exclude items that already have active repair tickets and filter for 'in_repair' status
    items = Item.objects.filter(status='in_repair').exclude(
        repair_tickets__status__in=['pending', 'in_progress']
    ).order_by('name')
    # Exclude persons who are currently marked as accountable for inventory items (custodians)
    # to keep the technician and reporter lists focused on staff and maintenance personnel.
    persons = Person.objects.filter(items__isnull=True).order_by('name')
    context = {
        'item': item,
        'items': items,
        'persons': persons,
        'priority_choices': RepairTicket.PRIORITY_CHOICES,
        'nav_section': 'repairs',
    }
    return render(request, 'repairs/ticket_form.html', context)

@permission_required('repairs.change_repairticket', raise_exception=True)
def repair_ticket_update(request, pk):
    ticket = get_object_or_404(
        RepairTicket.objects.select_related('item', 'reported_by', 'assigned_to'),
        pk=pk
    )
    old_status = ticket.status
    old_priority = ticket.priority
    old_assigned_to = ticket.assigned_to
    old_actual_cost = ticket.actual_cost
    
    if request.method == 'POST':
        # Extract values for validation and state machine logic
        status = request.POST.get('status')
        priority = request.POST.get('priority')
        resolution_notes = request.POST.get('resolution_notes', '')
        actual_cost = request.POST.get('actual_cost')
        decommission_item = request.POST.get('decommission_item') == 'true'

        # Validation Logic: Enforce requirements for completing a ticket
        if status in ['completed', 'unrepairable']:
            if not resolution_notes.strip():
                messages.error(request, f"Validation Error: Resolution notes must be provided to mark a ticket as {status}.")
                return redirect('repairs:ticket_update', pk=pk)
            if not actual_cost:
                messages.error(request, "Validation Error: You must specify an actual cost (enter 0 if free) to complete this ticket.")
                return redirect('repairs:ticket_update', pk=pk)

        # Update model instance fields
        ticket.status = status
        ticket.priority = priority
        ticket.resolution_notes = resolution_notes
        ticket.actual_cost = actual_cost or 0.00
        
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id and assigned_to_id.isdigit():
            ticket.assigned_to_id = int(assigned_to_id)
        else:
            ticket.assigned_to = None

        if ticket.status in ['completed', 'unrepairable'] and not ticket.resolved_date:
            from django.utils import timezone
            ticket.resolved_date = timezone.now()
        
        # If status is unrepairable, use the prompt preference from the UI
        skip_sync = False
        if status == 'unrepairable' and not decommission_item:
            skip_sync = True

        ticket.save(skip_item_sync=skip_sync)

        # Audit trail: Priority change
        if old_priority != ticket.priority:
            RepairLog.objects.create(
                ticket=ticket,
                note=f"Priority changed from '{dict(RepairTicket.PRIORITY_CHOICES).get(old_priority)}' to '{ticket.get_priority_display()}'.",
                status_at_time=ticket.status
            )

        # Audit trail: Assignment change
        if old_assigned_to != ticket.assigned_to:
            old_name = old_assigned_to.name if old_assigned_to else "Unassigned"
            new_name = ticket.assigned_to.name if ticket.assigned_to else "Unassigned"
            RepairLog.objects.create(
                ticket=ticket,
                note=f"Assignment changed from {old_name} to {new_name}.",
                status_at_time=ticket.status
            )

        # Audit trail: Cost change
        if old_actual_cost != ticket.actual_cost:
            RepairLog.objects.create(
                ticket=ticket,
                note=f"Repair cost updated from ₱{old_actual_cost} to ₱{ticket.actual_cost}.",
                status_at_time=ticket.status
            )

        # Auto-log status transitions
        if old_status != ticket.status:
            RepairLog.objects.create(
                ticket=ticket,
                note=f"Status changed from '{dict(RepairTicket.STATUS_CHOICES).get(old_status)}' to '{ticket.get_status_display()}'.",
                status_at_time=ticket.status
            )

        # Save a manual progress note if provided in the form
        log_note = request.POST.get('log_note')
        if log_note:
            RepairLog.objects.create(
                ticket=ticket,
                note=log_note,
                status_at_time=ticket.status
            )

        messages.success(request, f'Ticket {ticket.ticket_number} updated.')
        return redirect('repairs:ticket_detail', pk=ticket.pk)

    # Filter for non-custodians, but include the persons currently linked to this ticket
    # to ensure they remain selectable even if they were assigned inventory items recently.
    base_persons = Person.objects.filter(items__isnull=True)
    current_ids = [pid for pid in [ticket.reported_by_id, ticket.assigned_to_id] if pid]
    persons = (base_persons | Person.objects.filter(id__in=current_ids)).distinct().order_by('name')

    context = {
        'ticket': ticket,
        'status_choices': RepairTicket.STATUS_CHOICES,
        'priority_choices': RepairTicket.PRIORITY_CHOICES,
        'persons': persons,
        'nav_section': 'repairs',
    }
    return render(request, 'repairs/ticket_update.html', context)

@permission_required('repairs.view_repairticket', raise_exception=True)
def repair_work_order_print(request, pk):
    ticket = get_object_or_404(
        RepairTicket.objects.select_related('reported_by', 'assigned_to', 'item', 'item__person_accountable'),
        pk=pk
    )
    return render(request, 'repairs/work_order_print.html', {'ticket': ticket, 'nav_section': 'repairs'})

@permission_required('repairs.view_repairticket', raise_exception=True)
def export_repairs_csv(request):
    """Export filtered repair tickets to a CSV file"""
    status_filter = request.GET.get('status', '')
    ticket_status_codes = [choice[0] for choice in RepairTicket.STATUS_CHOICES]

    # 1. Fetch filtered tickets with optimized queries
    tickets = RepairTicket.objects.select_related(
        'item', 'item__category', 'reported_by', 'assigned_to'
    )

    if status_filter == 'in_repair':
        tickets = tickets.none()
    elif status_filter in ticket_status_codes:
        tickets = tickets.filter(status=status_filter)
    
    tickets = tickets.order_by('-reported_date')

    # 2. Prepare the Response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="repair_export_{date.today()}.csv"'
    
    # Use utf-8-sig for Excel compatibility (handles ₱ symbol)
    writer = csv.writer(response)
    
    # 3. Define Headers
    header = [
        'Ticket No', 'Item Name', 'Item Code', 'Category', 
        'Status', 'Priority', 'Reported By', 'Assigned To',
        'Date Reported', 'Expected Completion', 'Date Resolved',
        'Estimated Cost', 'Actual Cost', 'Issue Description', 'Resolution Notes'
    ]
    writer.writerow(header)

    # 4. Write Data Rows
    for t in tickets:
        writer.writerow([
            t.ticket_number,
            t.item.name,
            t.item.item_code,
            t.item.category.name if t.item.category else 'Uncategorized',
            t.get_status_display(),
            t.get_priority_display(),
            t.reported_by.name if t.reported_by else 'Unknown',
            t.assigned_to.name if t.assigned_to else 'Unassigned',
            t.reported_date.strftime('%Y-%m-%d %H:%M') if t.reported_date else '',
            t.expected_completion_date.strftime('%Y-%m-%d') if t.expected_completion_date else '',
            t.resolved_date.strftime('%Y-%m-%d %H:%M') if t.resolved_date else '',
            t.estimated_cost or 0.00,
            t.actual_cost or 0.00,
            t.issue_description,
            t.resolution_notes or ''
        ])

    return response

@permission_required('repairs.view_repairticket', raise_exception=True)
def repair_dashboard(request):
    today = date.today()
    soon = today + timedelta(days=30) # For upcoming completion dates

    # 1. Total Tickets
    total_tickets = RepairTicket.objects.count()

    # 2. Tickets by Status (for pie chart)
    status_labels = []
    status_data = []
    for code, label in RepairTicket.STATUS_CHOICES:
        count = RepairTicket.objects.filter(status=code).count()
        if count > 0:
            status_labels.append(str(label))
            status_data.append(count)

    # 3. Tickets by Priority (for pie chart)
    priority_labels = []
    priority_data = []
    for code, label in RepairTicket.PRIORITY_CHOICES:
        count = RepairTicket.objects.filter(priority=code).count()
        if count > 0:
            priority_labels.append(str(label))
            priority_data.append(count)

    # 6. Upcoming Completion
    upcoming_tickets = RepairTicket.objects.filter(
        expected_completion_date__gte=today,
        expected_completion_date__lte=soon,
        status__in=['pending', 'in_progress']
    ).order_by('expected_completion_date').select_related('item', 'reported_by', 'assigned_to')[:10]

    # 7. Overdue Tickets
    overdue_tickets = RepairTicket.objects.filter(
        expected_completion_date__lt=today,
        status__in=['pending', 'in_progress']
    ).order_by('expected_completion_date').select_related('item', 'reported_by', 'assigned_to')[:10]

    # 10. Total Estimated and Actual Costs
    cost_summary = RepairTicket.objects.aggregate(
        total_estimated=Sum('estimated_cost', output_field=DecimalField()),
        total_actual=Sum('actual_cost', output_field=DecimalField())
    )
    total_estimated_cost = cost_summary['total_estimated'] or Decimal('0.00')
    total_actual_cost = cost_summary['total_actual'] or Decimal('0.00')

    context = {
        'total_tickets': total_tickets,
        'status_labels': json.dumps(status_labels),
        'status_data': json.dumps(status_data),
        'priority_labels': json.dumps(priority_labels),
        'priority_data': json.dumps(priority_data),
        'upcoming_tickets': upcoming_tickets,
        'overdue_tickets': overdue_tickets,
        'total_estimated_cost': total_estimated_cost,
        'total_actual_cost': total_actual_cost,
        'nav_section': 'repairs',
    }
    return render(request, 'repairs/repair_dashboard.html', context)

@permission_required('repairs.delete_repairticket', raise_exception=True)
def bulk_delete_tickets(request):
    """Delete multiple repair tickets at once"""
    if request.method == 'POST':
        ticket_ids = request.POST.getlist('ticket_ids')
        if len(ticket_ids) == 1 and ',' in ticket_ids[0]:
            ticket_ids = ticket_ids[0].split(',')
            
        if ticket_ids:
            deleted_count, _ = RepairTicket.objects.filter(id__in=ticket_ids).delete()
            messages.success(request, f'Successfully deleted {deleted_count} repair ticket(s).')
        else:
            messages.warning(request, 'No tickets were selected.')
            
    return redirect('repairs:ticket_list')
