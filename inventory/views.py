from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Sum, F, Value, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import csv
import json
import os
from datetime import date, timedelta
from .forms import ItemForm
from repairs.models import RepairTicket
from .models import Item, Category, Department, Location, Person, CustomField, CustomFieldValue

@permission_required('inventory.view_item', raise_exception=True)
def dashboard(request):
    # Total items (count of records)
    total_items = Item.objects.count()
    active_items = Item.objects.filter(status='available')
    in_repair_items = Item.objects.filter(status='in_repair')
    total_asset_value = Item.objects.aggregate(
        total=Coalesce(
            Sum(ExpressionWrapper(F('acquisition_cost') * F('quantity'), output_field=DecimalField())),
            Value(0),
            output_field=DecimalField()
        )
    )['total']

    # Items by status (for pie chart)
    status_labels = []
    status_data = []
    for code, label in Item.STATUS_CHOICES:
        count = Item.objects.filter(status=code).count()
        if count > 0:
            status_labels.append(label)
            status_data.append(count)

    # Items by category (for pie chart)
    category_labels = []
    category_data = []
    for cat in Category.objects.annotate(item_count=Count('item')).order_by('-item_count'):
        if cat.item_count > 0:
            category_labels.append(cat.name)
            category_data.append(cat.item_count)

    # Items by location
    location_labels = []
    location_data = []
    for loc in Location.objects.annotate(item_count=Count('item')).order_by('-item_count')[:6]:
        if loc.item_count > 0:
            location_labels.append(loc.name)
            location_data.append(loc.item_count)

    # Responsible custodians (top persons)
    person_labels = []
    person_data = []
    for person in Person.objects.annotate(item_count=Count('items')).order_by('-item_count')[:6]:
        if person.item_count > 0:
            person_labels.append(person.name)
            person_data.append(person.item_count)

    # Items by department
    department_labels = []
    department_data = []
    dept_counts = Item.objects.values('department__name').annotate(count=Count('id')).order_by('-count')
    for dept in dept_counts:
        label = dept['department__name'] if dept['department__name'] else "No Department"
        department_labels.append(label)
        department_data.append(dept['count'])

    # Expiring soon
    today = date.today()
    soon = today + timedelta(days=30)
    expiring_soon = Item.objects.filter(
        end_of_life_date__gte=today,
        end_of_life_date__lte=soon,
        id__isnull=False
    ).order_by('end_of_life_date')[:10]

    # Expired items
    expired = Item.objects.filter(
        end_of_life_date__lt=today,
        id__isnull=False
    ).order_by('end_of_life_date')[:10]

    # Recent items
    recent_items = Item.objects.filter(id__isnull=False).order_by('-created_at')[:5]

    def serialize_item(item):
        return {
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else None,
            'location': item.location.name if item.location else None,
            'status': item.get_status_display(),
        }

    status_items = {
        label: [serialize_item(item) for item in Item.objects.filter(status=code).select_related('category', 'location', 'person_accountable')]
        for code, label in Item.STATUS_CHOICES
    }
    category_items = {
        cat.name: [serialize_item(item) for item in Item.objects.filter(category=cat).select_related('category', 'location', 'person_accountable')]
        for cat in Category.objects.filter(name__in=category_labels)
    }
    location_items = {
        loc.name: [serialize_item(item) for item in Item.objects.filter(location=loc).select_related('category', 'location', 'person_accountable')]
        for loc in Location.objects.filter(name__in=location_labels)
    }
    person_items = {
        person.name: [serialize_item(item) for item in Item.objects.filter(person_accountable=person).select_related('category', 'location', 'person_accountable')]
        for person in Person.objects.filter(name__in=person_labels)
    }
    department_items = {
        dept: [serialize_item(item) for item in Item.objects.filter(department__name=None if dept == 'No Department' else dept).select_related('category', 'location', 'person_accountable')]
        for dept in department_labels
    }

    status_label_to_code = {label: code for code, label in Item.STATUS_CHOICES}
    category_label_to_id = {cat.name: cat.id for cat in Category.objects.filter(name__in=category_labels)}
    location_label_to_id = {loc.name: loc.id for loc in Location.objects.filter(name__in=location_labels)}
    person_label_to_id = {person.name: person.id for person in Person.objects.filter(name__in=person_labels)}

    context = {
        'total_items': total_items,
        'total_asset_value': total_asset_value,
        'active_items_count': active_items.count(),
        'in_repair_items_count': in_repair_items.count(),
        'active_items': json.dumps([{
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else None,
            'location': item.location.name if item.location else None,
            'status': item.get_status_display(),
        } for item in active_items if item.id]),
        'in_repair_items': json.dumps([{
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else None,
            'location': item.location.name if item.location else None,
            'status': item.get_status_display(),
        } for item in in_repair_items if item.id]),
        'status_labels': status_labels,
        'status_data': status_data,
        'category_labels': category_labels,
        'category_data': category_data,
        'location_labels': location_labels,
        'location_data': location_data,
        'person_labels': person_labels,
        'person_data': person_data,
        'department_labels': department_labels,
        'department_data': department_data,
        'expiring_soon_count': expiring_soon.count(),
        'expired_count': expired.count(),
        'expiring_soon_json': json.dumps([{
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else None,
            'location': item.location.name if item.location else None,
            'status': item.get_status_display(),
        } for item in expiring_soon if item.id]),
        'expired_json': json.dumps([{
            'id': item.id,
            'name': item.name,
            'category': item.category.name if item.category else None,
            'location': item.location.name if item.location else None,
            'status': item.get_status_display(),
        } for item in expired if item.id]),
        'status_items_json': json.dumps(status_items),
        'category_items_json': json.dumps(category_items),
        'location_items_json': json.dumps(location_items),
        'person_items_json': json.dumps(person_items),
        'department_items_json': json.dumps(department_items),
        'status_label_to_code': json.dumps(status_label_to_code),
        'category_label_to_id': json.dumps(category_label_to_id),
        'location_label_to_id': json.dumps(location_label_to_id),
        'person_label_to_id': json.dumps(person_label_to_id),
        'expiring_soon': expiring_soon,
        'recent_items': recent_items,
        'nav_section': 'dashboard',
    }
    return render(request, 'inventory/dashboard.html', context)

@permission_required('inventory.delete_item', raise_exception=True)
def bulk_delete(request):
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids')
        if len(item_ids) == 1 and ',' in item_ids[0]:
            item_ids = item_ids[0].split(',')
        if item_ids:
            items_to_delete = Item.objects.filter(id__in=item_ids)
            for item in items_to_delete:
                item.delete()  # Triggers Model.delete() logic for each
            messages.success(request, f'Successfully deleted {len(item_ids)} item(s).')
        else:
            messages.warning(request, 'No items selected.')
        return redirect('item_list')
    return redirect('item_list')

@permission_required('inventory.view_item', raise_exception=True)
def find_item_by_code(request):
    """Redirect to item detail page using scanned item code"""
    code = request.GET.get('code', '')
    if not code:
        return JsonResponse({'success': False, 'error': 'No code provided'})
    
    try:
        item = Item.objects.get(item_code=code)
        return JsonResponse({'success': True, 'id': item.id})
    except Item.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})


@permission_required('inventory.view_item', raise_exception=True)
def export_items_csv(request):
    """Export filtered items to a CSV file"""
    # 1. Reuse the same filtering logic from item_list
    items = Item.objects.all().select_related('category', 'location', 'person_accountable')
    
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(serial_no__icontains=search_query) |
            Q(department__name__icontains=search_query) |
            Q(location__name__icontains=search_query) |
            Q(person_accountable__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Apply other filters (status, category, etc.)
    for filter_param, field in [('status', 'status'), ('category', 'category_id'), 
                               ('location', 'location_id'), ('person', 'person_accountable_id')]:
        val = request.GET.get(filter_param)
        if val:
            items = items.filter(**{field: val})

    # Filter by selected item IDs
    item_ids = request.GET.get('item_ids', '')
    if item_ids:
        id_list = [int(item_id) for item_id in item_ids.split(',') if item_id.strip().isdigit()]
        if id_list:
            items = items.filter(id__in=id_list)
        else:
            items = items.none()

    # Filter by specific item ID
    item_id_filter = request.GET.get('item_id', '')
    if item_id_filter and item_id_filter.strip():
        try:
            items = items.filter(id=int(item_id_filter))
        except (ValueError, TypeError):
            items = items.none()

    # Filter by expiring / expired items
    expiring_filter = request.GET.get('expiring', '') == '1'
    expired_filter = request.GET.get('expired', '') == '1'
    if not item_ids:
        today = date.today()
        soon = today + timedelta(days=30)
        if expiring_filter:
            items = items.filter(
                end_of_life_date__gte=today,
                end_of_life_date__lte=soon
            )
        elif expired_filter:
            items = items.filter(end_of_life_date__lt=today)

    # Apply sorting logic to match item_list
    if 'sort' not in request.GET:
        sort_by = 'created_at'
        invert = True
    else:
        sort_by = request.GET.get('sort', 'created_at')
        invert = request.GET.get('invert', '') == 'true'

    valid_sort_fields = {
        'name': 'name',
        'category': 'category__name',
        'department': 'department__name',
        'status': 'status',
        'location': 'location__name',
        'person': 'person_accountable__name',
        'serial_no': 'serial_no',
        'acquisition_date': 'acquisition_date',
        'acquisition_cost': 'acquisition_cost',
        'created_at': 'created_at',
    }
    base_field = valid_sort_fields.get(sort_by, 'created_at')
    order_by = f"-{base_field}" if invert else base_field
    items = items.order_by(order_by)

    # 2. Prepare the Response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="inventory_export_{date.today()}.csv"'
    
    # Use utf-8-sig to handle the Peso symbol correctly in Excel
    writer = csv.writer(response)
    
    # 3. Handle Dynamic Custom Fields
    custom_fields = CustomField.objects.filter(is_active=True).order_by('sort_order')
    
    # 4. Define Headers
    header = [
        'Item Code', 'Name', 'Category', 'Status', 'Location', 
        'Person Accountable', 'Department', 'Serial No', 
        'Acquisition Date', 'Acquisition Cost', 'Quantity', 'Total Value'
    ]
    # Add custom fields to headers
    for cf in custom_fields:
        header.append(cf.name)
        
    writer.writerow(header)

    # 5. Write Data Rows
    for item in items:
        row = [
            item.item_code,
            item.name,
            item.category.name if item.category else '',
            item.get_status_display(),
            item.location.name if item.location else '',
            item.person_accountable.name if item.person_accountable else '',
            item.department.name if item.department else '',
            item.serial_no or '',
            item.acquisition_date or '',
            item.acquisition_cost or 0.00,
            item.quantity,
            item.get_total_value()
        ]
        
        # Add custom field values
        custom_values = item.get_custom_fields_dict()
        for cf in custom_fields:
            row.append(custom_values.get(cf.name, ''))
            
        writer.writerow(row)

    return response

@permission_required('inventory.view_item', raise_exception=True)
def download_item_qr(request, id):
    """Download QR code image for an item"""
    item = get_object_or_404(Item, id=id)
    img_bytes = item.get_qr_code_image()
    response = HttpResponse(img_bytes, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="qr_{item.item_code}.png"'
    return response

@csrf_exempt
@require_http_methods(["POST"])
@permission_required('inventory.add_customfield', raise_exception=True)
def quick_add_custom_field(request):
    """Quick add a new custom field via AJAX"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        field_type = data.get('field_type', 'text')
        help_text = data.get('help_text', '')
        
        if not name:
            return JsonResponse({'error': 'Field name is required'}, status=400)
        
        # Check if custom field already exists
        if CustomField.objects.filter(name=name).exists():
            return JsonResponse({'error': f'Field "{name}" already exists'}, status=400)
        
        # Create the custom field
        custom_field = CustomField.objects.create(
            name=name,
            field_type=field_type,
            help_text=help_text,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'id': custom_field.id,
            'name': custom_field.name,
            'field_type': custom_field.field_type,
            'message': f'Custom field "{name}" created successfully!'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@permission_required('inventory.view_customfield', raise_exception=True)
def custom_fields_list(request):
    """List all custom fields"""
    custom_fields = CustomField.objects.all().order_by('sort_order', 'name')
    return render(request, 'inventory/custom_fields_list.html', {
        'custom_fields': custom_fields,
        'title': 'Manage Custom Fields',
        'nav_section': 'inventory'
    })


@permission_required('inventory.add_customfield', raise_exception=True)
def custom_field_add(request):
    """Add a new custom field"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        field_type = request.POST.get('field_type', 'text')
        is_required = request.POST.get('is_required') == 'on'
        placeholder = request.POST.get('placeholder', '')
        help_text = request.POST.get('help_text', '')
        sort_order = request.POST.get('sort_order', 0)
        is_active = request.POST.get('is_active') == 'on'
        
        if not name:
            messages.error(request, 'Field name is required.')
            return redirect('custom_fields_list')
        
        # Check if field name already exists
        if CustomField.objects.filter(name=name).exists():
            messages.error(request, f'Field "{name}" already exists.')
            return redirect('custom_fields_list')
        
        custom_field = CustomField.objects.create(
            name=name,
            field_type=field_type,
            is_required=is_required,
            placeholder=placeholder,
            help_text=help_text,
            sort_order=int(sort_order) if sort_order else 0,
            is_active=is_active
        )
        
        messages.success(request, f'Custom field "{name}" created successfully!')
        return redirect('custom_fields_list')
    
    return render(request, 'inventory/custom_field_form.html', {'title': 'Add Custom Field'})


@permission_required('inventory.change_customfield', raise_exception=True)
def custom_field_edit(request, id):
    """Edit an existing custom field"""
    custom_field = get_object_or_404(CustomField, id=id)
    
    if request.method == 'POST':
        custom_field.name = request.POST.get('name', '').strip()
        custom_field.field_type = request.POST.get('field_type', 'text')
        custom_field.is_required = request.POST.get('is_required') == 'on'
        custom_field.placeholder = request.POST.get('placeholder', '')
        custom_field.help_text = request.POST.get('help_text', '')
        custom_field.sort_order = int(request.POST.get('sort_order', 0))
        custom_field.is_active = request.POST.get('is_active') == 'on'
        custom_field.save()
        
        messages.success(request, f'Custom field "{custom_field.name}" updated successfully!')
        return redirect('custom_fields_list')
    
    return render(request, 'inventory/custom_field_form.html', {
        'custom_field': custom_field,
        'title': 'Edit Custom Field'
    })


@permission_required('inventory.delete_customfield', raise_exception=True)
def custom_field_delete(request, id):
    """Delete a custom field"""
    custom_field = get_object_or_404(CustomField, id=id)
    
    if request.method == 'POST':
        field_name = custom_field.name
        custom_field.delete()
        messages.success(request, f'Custom field "{field_name}" deleted successfully!')
        return redirect('custom_fields_list')
    
    return render(request, 'inventory/custom_field_confirm_delete.html', {'custom_field': custom_field})

@csrf_exempt
@require_http_methods(["POST"])
@permission_required('inventory.add_category', raise_exception=True)
def quick_add_category(request):
    """Quick add a new category via AJAX"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Category name is required'}, status=400)
        
        # Check if category already exists
        category, created = Category.objects.get_or_create(name=name)
        
        if created:
            return JsonResponse({
                'success': True,
                'id': category.id,
                'name': category.name,
                'message': f'Category "{name}" created successfully!'
            })
        else:
            return JsonResponse({
                'success': True,
                'id': category.id,
                'name': category.name,
                'message': f'Category "{name}" already exists.'
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
@permission_required('inventory.add_department', raise_exception=True)
def quick_add_department(request):
    """Quick add a new department via AJAX"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Department name is required'}, status=400)
        
        # Check if department already exists
        department, created = Department.objects.get_or_create(name=name)
        
        if created:
            return JsonResponse({
                'success': True,
                'id': department.id,
                'name': department.name,
                'message': f'Department "{name}" created successfully!'
            })
        else:
            return JsonResponse({
                'success': True,
                'id': department.id,
                'name': department.name,
                'message': f'Department "{name}" already exists.'
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
@permission_required('inventory.add_location', raise_exception=True)
def quick_add_location(request):
    """Quick add a new location via AJAX"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Location name is required'}, status=400)
        
        # Check if location already exists
        location, created = Location.objects.get_or_create(name=name, defaults={'description': description})
        
        if not created and description:
            # Update description if location exists and description provided
            if not location.description:
                location.description = description
                location.save()
        
        return JsonResponse({
            'success': True,
            'id': location.id,
            'name': location.name,
            'message': f'Location "{name}" {"created" if created else "already exists"}!'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
@permission_required('inventory.add_person', raise_exception=True)
def quick_add_person(request):
    """Quick add a new person via AJAX"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        department = data.get('department', '').strip()
        contact_number = data.get('contact_number', '').strip()
        
        if not name:
            return JsonResponse({'error': 'Person name is required'}, status=400)
        
        # Check if person already exists
        person, created = Person.objects.get_or_create(
            name=name,
            defaults={
                'email': email if email else None,
                'department': department if department else None,
                'contact_number': contact_number if contact_number else None
            }
        )
        
        if not created:
            # Update existing person with any new info
            if email and not person.email:
                person.email = email
            if department and not person.department:
                person.department = department
            if contact_number and not person.contact_number:
                person.contact_number = contact_number
            if any([email, department, contact_number]):
                person.save()
        
        return JsonResponse({
            'success': True,
            'id': person.id,
            'name': person.name,
            'message': f'Person "{name}" {"created" if created else "already exists"}!'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@permission_required('inventory.view_item', raise_exception=True)
def item_list(request):
    """Display all items with sorting, search, filtering, pagination, and nested grouping"""
    items = Item.objects.all().select_related('category', 'location', 'person_accountable', 'parent_item')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(serial_no__icontains=search_query) |
            Q(department__name__icontains=search_query) |
            Q(location__name__icontains=search_query) |
            Q(person_accountable__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter and status_filter != '':
        items = items.filter(status=status_filter)
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter and category_filter != '':
        items = items.filter(category__id=category_filter)
    
    # Filter by location
    location_filter = request.GET.get('location', '')
    if location_filter and location_filter != '':
        items = items.filter(location__id=location_filter)
    
    # Filter by person accountable
    person_filter = request.GET.get('person', '')
    if person_filter and person_filter != '':
        items = items.filter(person_accountable__id=person_filter)

    # Filter by selected item IDs
    item_ids = request.GET.get('item_ids', '')
    if item_ids:
        id_list = [int(item_id) for item_id in item_ids.split(',') if item_id.strip().isdigit()]
        if id_list:
            items = items.filter(id__in=id_list)
        else:
            items = items.none()

    # Filter by specific item ID
    item_id_filter = request.GET.get('item_id', '')
    if item_id_filter and item_id_filter.strip():
        try:
            items = items.filter(id=int(item_id_filter))
        except (ValueError, TypeError):
            items = items.none()

    # Filter by expiring / expired items
    expiring_filter = request.GET.get('expiring', '') == '1'
    expired_filter = request.GET.get('expired', '') == '1'
    if not item_ids:
        today = date.today()
        soon = today + timedelta(days=30)
        if expiring_filter:
            items = items.filter(
                end_of_life_date__gte=today,
                end_of_life_date__lte=soon
            )
        elif expired_filter:
            items = items.filter(end_of_life_date__lt=today)
    
    # Filter by Kit Type
    kit_filter = request.GET.get('kit_filter', '')
    if kit_filter == 'kits':
        items = items.annotate(c_count=Count('children')).filter(c_count__gt=0)
    elif kit_filter == 'parts':
        items = items.filter(parent_item__isnull=False)
    elif kit_filter == 'standalone':
        items = items.annotate(c_count=Count('children')).filter(parent_item__isnull=True, c_count=0)

    # Nested Grouping functionality
    primary_group = request.GET.get('primary_group', 'location')  # First level group
    secondary_group = request.GET.get('secondary_group', 'none')  # Second level group (nested)
    
    # Sorting functionality
    if 'sort' not in request.GET:
        sort_by = 'created_at'
        invert = True
    else:
        sort_by = request.GET.get('sort', 'created_at')
        invert = request.GET.get('invert', '') == 'true'
    
    # Define valid base sorting fields
    valid_sort_fields = {
        'name': 'name',
        'category': 'category__name',
        'department': 'department__name',
        'status': 'status',
        'location': 'location__name',
        'person': 'person_accountable__name',
        'serial_no': 'serial_no',
        'kit_type': 'parent_item',
        'acquisition_date': 'acquisition_date',
        'acquisition_cost': 'acquisition_cost',
        'created_at': 'created_at',
    }
    
    base_field = valid_sort_fields.get(sort_by, 'created_at')
    order_by = f"-{base_field}" if invert else base_field
    
    # Apply sorting to all items first
    items = items.order_by(order_by)
    
    # Get grouped items with nested grouping
    # Note: If no grouping is selected, we could modify this to show kits 
    # hierarchically, but we'll stick to the requested grouping logic 
    # and ensure the template handles the 'children' related_name.
    
    # Optimization: Prefetch children and active repair tickets
    from repairs.models import RepairTicket
    from django.db.models import Prefetch
    items = items.prefetch_related(
        'children', 'children__location', 'children__category',
        Prefetch('repair_tickets', queryset=RepairTicket.objects.filter(status__in=['pending', 'in_progress']), to_attr='active_tickets')
    )

    def get_group_key(item, group_type):
        if group_type == 'name':
            return item.name
        elif group_type == 'category':
            return item.category.name if item.category else 'Uncategorized'
        elif group_type == 'department':
            return item.department.name if item.department else 'No Department'
        elif group_type == 'location':
            return item.location.name if item.location else 'No Location'
        elif group_type == 'status':
            return item.get_status_display()
        elif group_type == 'person':
            return item.person_accountable.name if item.person_accountable else 'Unassigned'
        elif group_type == 'acquisition_date':
            return item.acquisition_date.strftime('%Y-%m') if item.acquisition_date else 'No Date'
        elif group_type == 'kit_type':
            if item.parent_item:
                return 'Components/Parts'
            if item.children.exists():
                return 'Kit Parents'
            return 'Standalone Items'
        else:
            return 'Other'
    
    grouped_items = {}
    if primary_group != 'none':
        for item in items:
            primary_key = get_group_key(item, primary_group)
            
            if primary_key not in grouped_items:
                grouped_items[primary_key] = {'items': [], 'subgroups': {}}
            
            if secondary_group != 'none':
                secondary_key = get_group_key(item, secondary_group)
                if secondary_key not in grouped_items[primary_key]['subgroups']:
                    grouped_items[primary_key]['subgroups'][secondary_key] = []
                grouped_items[primary_key]['subgroups'][secondary_key].append(item)
            else:
                grouped_items[primary_key]['items'].append(item)
        
        # Sort subgroups
        for primary_key in grouped_items:
            if grouped_items[primary_key]['subgroups']:
                grouped_items[primary_key]['subgroups'] = dict(sorted(grouped_items[primary_key]['subgroups'].items()))
    
    # Pagination (only when no grouping)
    paginator = Paginator(items, 10) if primary_group == 'none' else None
    page = request.GET.get('page', 1)
    
    if paginator:
        try:
            items_page = paginator.page(page)
        except PageNotAnInteger:
            items_page = paginator.page(1)
        except EmptyPage:
            items_page = paginator.page(paginator.num_pages)
    else:
        items_page = None
    
    # Get data for dropdowns
    locations = Location.objects.all().order_by('name')
    categories = Category.objects.all().order_by('name')
    departments_list = Department.objects.all().order_by('name')
    persons = Person.objects.all().order_by('name')
    nav_section = 'inventory'
    status_choices = Item.STATUS_CHOICES
    
    return render(request, 'inventory/item_list.html', {
        'items': items_page if paginator else items,
        'all_items_list': Item.objects.all().only('id', 'name', 'item_code').order_by('name'),
        'grouped_items': grouped_items if primary_group != 'none' else None,
        'primary_group': primary_group,
        'secondary_group': secondary_group,
        'total_items': items.count(),
        'current_sort': sort_by,
        'current_invert': invert,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'location_filter': location_filter,
        'person_filter': person_filter,
        'item_id_filter': item_id_filter,
        'item_ids': item_ids,
        'expiring_filter': expiring_filter,
        'expired_filter': expired_filter,
        'kit_filter': kit_filter,
        'locations': locations,
        'categories': categories,
        'departments_list': departments_list,
        'persons': persons,
        'status_choices': status_choices,
        'nav_section': nav_section,
    })

@permission_required('inventory.change_item', raise_exception=True)
def bulk_edit(request):
    """Bulk edit multiple selected items"""
    if request.method == 'POST':
        item_ids = request.POST.getlist('item_ids')
        
        # Handle case where item_ids comes as comma-separated string
        if len(item_ids) == 1 and ',' in item_ids[0]:
            item_ids = item_ids[0].split(',')
        
        if not item_ids:
            messages.warning(request, 'No items selected.')
            return redirect('item_list')
        
        items = Item.objects.filter(id__in=item_ids)
        count = items.count()
        
        # Check if delete is requested
        if request.POST.get('delete') == 'true':
            if not request.user.has_perm('inventory.delete_item'):
                raise PermissionDenied
            # Delete items (images will be handled by model's delete method)
            items.delete()
            messages.success(request, f'Successfully deleted {count} item(s).')
            return redirect('item_list')
        
        # Track which fields were actually changed
        updated_fields = []
        
        # Update status
        new_status = request.POST.get('status')
        if new_status and new_status != '':
            sync_child_status = request.POST.get('sync_child_status') == 'true'
            from repairs.models import RepairTicket
            
            # Exclude items with active repair tickets
            blocked_ids = RepairTicket.objects.filter(status__in=['pending', 'in_progress']).values_list('item_id', flat=True)
            items_to_update = items.exclude(id__in=blocked_ids)
            blocked_count = items.filter(id__in=blocked_ids).count()
            
            if items_to_update.exists():
                items_to_update.update(status=new_status)
                updated_fields.append('status')
                
                if sync_child_status:
                    child_count = 0
                    for item in items_to_update:
                        for child in item.get_all_children():
                            if child.id not in blocked_ids:
                                child.status = new_status
                                child.save()
                                child_count += 1
                    if child_count > 0:
                        updated_fields.append(f'child status ({child_count} parts)')
            
            if blocked_count > 0:
                messages.warning(request, f"Status update skipped for {blocked_count} selected item(s) because they have active repair tickets.")

        # Update parent_item (Kitting)
        new_parent_id = request.POST.get('parent_item')
        if new_parent_id and new_parent_id != '':
            if new_parent_id == 'none':
                items.update(parent_item=None)
                updated_fields.append('parent_item')
            else:
                try:
                    parent = Item.objects.get(id=new_parent_id)
                    for item in items:
                        item.parent_item = parent
                        # full_clean triggers the circularity check in models.py
                        item.full_clean()
                        item.save()
                    updated_fields.append('parent_item')
                except (Item.DoesNotExist, Exception):
                    pass

        # Update name
        new_name = request.POST.get('name')
        if new_name and new_name.strip() != '':
            items.update(name=new_name.strip())
            updated_fields.append('name')
        
        # Update category
        new_category_id = request.POST.get('category')
        if new_category_id and new_category_id != '':
            try:
                category = Category.objects.get(id=new_category_id)
                items.update(category=category)
                updated_fields.append('category')
            except Category.DoesNotExist:
                pass
        
        # Update department
        new_department_id = request.POST.get('department')
        if new_department_id and new_department_id != '':
            try:
                department = Department.objects.get(id=new_department_id)
                items.update(department=department)
                updated_fields.append('department')
            except Department.DoesNotExist:
                pass
        
        # Update location
        new_location_id = request.POST.get('location')
        if new_location_id and new_location_id != '':
            try:
                location = Location.objects.get(id=new_location_id)
                move_children = request.POST.get('move_children') == 'true'
                
                for item in items:
                    item.location = location
                    item.save() # Triggers history tracking
                    
                    if move_children:
                        for child in item.get_all_children():
                            if child.status != 'in_repair':
                                child.location = location
                                child.save()
                updated_fields.append('location')
            except Location.DoesNotExist:
                pass
        
        # Update person accountable
        new_person_id = request.POST.get('person_accountable')
        if new_person_id and new_person_id != '':
            try:
                person = Person.objects.get(id=new_person_id)
                items.update(person_accountable=person)
                updated_fields.append('person_accountable')
            except Person.DoesNotExist:
                pass
        
        # Update acquisition date
        new_acquisition_date = request.POST.get('acquisition_date')
        if new_acquisition_date and new_acquisition_date != '':
            items.update(acquisition_date=new_acquisition_date)
            updated_fields.append('acquisition_date')
        
        # Update end of life date
        new_eol_date = request.POST.get('end_of_life_date')
        if new_eol_date and new_eol_date != '':
            items.update(end_of_life_date=new_eol_date)
            updated_fields.append('end_of_life_date')
        
        # Update acquisition cost
        new_acquisition_cost = request.POST.get('acquisition_cost')
        if new_acquisition_cost and new_acquisition_cost != '':
            items.update(acquisition_cost=new_acquisition_cost)
            updated_fields.append('acquisition_cost')
        
        # Handle image upload - ONLY create ONE image file
        if request.FILES.get('image'):
            uploaded_image = request.FILES['image']
            shared_image = None
            # Loop ensures old images are cleaned up and the new file is shared correctly
            for item in items:
                if not shared_image:
                    item.image = uploaded_image
                    item.save() # Triggers cleanup of old and creates new file
                    shared_image = item.image
                else:
                    item.image = shared_image
                    item.save() # Triggers cleanup of old and links to shared file
            updated_fields.append('image')
        
        # Handle image removal
        if request.POST.get('remove_image') == 'true':
            for item in items:
                item.image = None
                item.save() # Triggers the orphan check inside Model.save()
            updated_fields.append('image_removed')
        
        # Show success message with what was updated
        if updated_fields:
            fields_text = ', '.join(updated_fields)
            messages.success(request, f'Successfully updated {count} item(s). Changed: {fields_text}')
        else:
            messages.info(request, 'No changes were made to the selected items.')
        
        return redirect('item_list')
    
    return redirect('item_list')

@permission_required('inventory.add_item', raise_exception=True)
def item_add(request):
    """Add a new item or multiple items with quantity"""
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            quantity = form.cleaned_data.get('quantity', 1)
            uploaded_image = request.FILES.get('image')
            
            if quantity == 1:
                # Save single item normally
                item = form.save()
                # Save custom fields
                for field_name, value in form.cleaned_data.items():
                    if field_name.startswith('custom_'):
                        custom_field_id = int(field_name.split('_')[1])
                        custom_field = CustomField.objects.get(id=custom_field_id)
                        custom_value, _ = CustomFieldValue.objects.get_or_create(
                            item=item,
                            field=custom_field
                        )
                        custom_value.set_value(value)
                messages.success(request, f'Item "{item.name}" added successfully!')
            else:
                # Get all the data from the form
                name = form.cleaned_data['name']
                description = form.cleaned_data.get('description', '')
                parent_item = form.cleaned_data.get('parent_item')
                category = form.cleaned_data.get('category')
                department = form.cleaned_data.get('department')
                serial_no = form.cleaned_data.get('serial_no', '')
                status = form.cleaned_data['status']
                location = form.cleaned_data.get('location')
                person_accountable = form.cleaned_data.get('person_accountable')
                acquisition_date = form.cleaned_data.get('acquisition_date')
                end_of_life_date = form.cleaned_data.get('end_of_life_date')
                acquisition_cost = form.cleaned_data.get('acquisition_cost')
                
                # Extract custom field values before creating items
                custom_field_data = {}
                for field_name, value in form.cleaned_data.items():
                    if field_name.startswith('custom_'):
                        custom_field_id = int(field_name.split('_')[1])
                        custom_field_data[custom_field_id] = value
                
                # Create the first item with the image
                first_item = Item(
                    name=name,
                    description=description,
                    parent_item=parent_item,
                    category=category,
                    department=department,
                    serial_no=serial_no,
                    status=status,
                    location=location,
                    person_accountable=person_accountable,
                    acquisition_date=acquisition_date,
                    end_of_life_date=end_of_life_date,
                    acquisition_cost=acquisition_cost,
                    quantity=1
                )
                
                if uploaded_image:
                    first_item.image = uploaded_image
                
                first_item.save()
                
                # Save custom fields for first item
                for cf_id, value in custom_field_data.items():
                    cf = CustomField.objects.get(id=cf_id)
                    cv, _ = CustomFieldValue.objects.get_or_create(item=first_item, field=cf)
                    cv.set_value(value)
                
                # Get the saved image reference (if any)
                shared_image = first_item.image
                
                # Create the remaining items sharing the same image
                for i in range(quantity - 1):
                    item = Item(
                        name=name,
                        description=description,
                        parent_item=parent_item,
                        category=category,
                        department=department,
                        serial_no=serial_no,
                        status=status,
                        location=location,
                        person_accountable=person_accountable,
                        acquisition_date=acquisition_date,
                        end_of_life_date=end_of_life_date,
                        acquisition_cost=acquisition_cost,
                        quantity=1,
                        image=shared_image  # Share the same image
                    )
                    item.save()
                    
                    # Save custom fields for subsequent items
                    for cf_id, value in custom_field_data.items():
                        cf = CustomField.objects.get(id=cf_id)
                        cv, _ = CustomFieldValue.objects.get_or_create(item=item, field=cf)
                        cv.set_value(value)
                
                messages.success(request, f'Successfully added {quantity} items of "{name}"!')
            
            return redirect('item_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ItemForm()
    
    return render(request, 'inventory/item_form.html', {
        'form': form, 
        'title': 'Add Item',
        'nav_section': 'inventory'
    })

@permission_required('inventory.change_item', raise_exception=True)
def item_edit(request, id):
    """Edit an existing item"""
    item = get_object_or_404(Item, id=id)
    has_active_tickets = RepairTicket.objects.filter(item=item, status__in=['pending', 'in_progress']).exists()
    
    if request.method == 'POST':
        # Fetch current state from DB before form potentially modifies the instance
        old_item = Item.objects.get(pk=id)
        old_location = old_item.location
        old_status = old_item.status
        
        form = ItemForm(request.POST, request.FILES, instance=item)
        if has_active_tickets:
            form.fields['status'].disabled = True
        
        if form.is_valid():
            item = form.save()
            
            if has_active_tickets and item.status != old_status:
                item.status = old_status
                item.save(update_fields=['status'])
                messages.warning(request, "Status cannot be changed while this item has an active repair ticket.")
            
            # Handle Kit Location Synchronization
            # If location changed and user confirmed move_children via prompt
            if item.location != old_location and request.POST.get('move_children') == 'true':
                for child in item.get_all_children():
                    if child.status != 'in_repair':
                        child.location = item.location
                        child.save()
                messages.info(request, f"Updated location for all items in the kit.")

            # Handle Kit Status Synchronization
            if item.status != old_status and request.POST.get('sync_child_status') == 'true':
                blocked_ids = RepairTicket.objects.filter(status__in=['pending', 'in_progress']).values_list('item_id', flat=True)
                child_count = 0
                for child in item.get_all_children():
                    if child.id not in blocked_ids:
                        child.status = item.status
                        child.save()
                        child_count += 1
                if child_count > 0:
                    messages.info(request, f"Updated status for {child_count} items in the kit.")

            # Save custom fields
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('custom_'):
                    custom_field_id = int(field_name.split('_')[1])
                    custom_field = CustomField.objects.get(id=custom_field_id)
                    custom_value, created = CustomFieldValue.objects.get_or_create(
                        item=item,
                        field=custom_field
                    )
                    custom_value.set_value(value)
            
            messages.success(request, 'Item updated successfully!')
            return redirect('item_detail', id=item.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ItemForm(instance=item)
        if has_active_tickets:
            form.fields['status'].disabled = True
    
    return render(request, 'inventory/item_form.html', {
        'form': form, 
        'title': 'Edit Item', 
        'item': item,
        'has_active_tickets': has_active_tickets,
        'nav_section': 'inventory'
    })

@permission_required('inventory.change_item', raise_exception=True)
def mark_item_in_repair(request, id):
    item = get_object_or_404(Item, id=id)
    if request.method == 'POST':
        if item.status != 'in_repair':
            item.status = 'in_repair'
            item.save()
            messages.success(request, f'Item "{item.name}" marked as In Repair.')
        return redirect('repairs:ticket_create_for_item', item_id=item.id)
    return redirect('item_detail', id=item.id)

@permission_required('inventory.change_item', raise_exception=True)
def add_existing_to_kit(request, parent_id):
    """Attach an existing standalone item to a kit"""
    parent = get_object_or_404(Item, id=parent_id)
    if request.method == 'POST':
        child_id = request.POST.get('child_item_id')
        if child_id:
            child = get_object_or_404(Item, id=child_id)
            try:
                child.parent_item = parent
                child.full_clean()  # Triggers model-level circularity checks
                child.save()
                messages.success(request, f'Item "{child.name}" successfully added to kit.')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    return redirect('item_detail', id=parent_id)

@permission_required('inventory.change_item', raise_exception=True)
def remove_from_kit(request, id):
    """Remove a single item from its parent kit"""
    item = get_object_or_404(Item, id=id)
    parent_id = item.parent_item.id if item.parent_item else None
    if request.method == 'POST':
        item.parent_item = None
        item.save()
        messages.success(request, f'Item "{item.name}" removed from kit.')
        if parent_id:
            return redirect('item_detail', id=parent_id)
    return redirect('item_list')

@permission_required('inventory.change_item', raise_exception=True)
def break_kit(request, id):
    """Orphan all children of a parent item (Ungrouping)"""
    item = get_object_or_404(Item, id=id)
    if request.method == 'POST':
        children_count = item.children.count()
        item.children.update(parent_item=None)
        messages.success(request, f'Successfully ungrouped {children_count} items from "{item.name}".')
    return redirect('item_detail', id=item.id)

@permission_required('inventory.delete_item', raise_exception=True)
def item_delete(request, id):
    """Delete an item"""
    item = get_object_or_404(Item, id=id)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, f'{item.name} deleted successfully!')
        return redirect('item_list')
    
    return render(request, 'inventory/item_confirm_delete.html', {'item': item})

@permission_required('inventory.view_item', raise_exception=True)
def item_detail(request, id):
    """Show single item details"""
    item = get_object_or_404(Item, id=id)
    # Fetch children for kitting feature
    children = item.children.all().select_related('category', 'location')
    # Fetch all ancestors for a complete hierarchy path
    ancestors = item.get_ancestors()
    # Fetch location history ordered by newest first
    history = item.location_history.all().select_related('location')
    
    # Items available to be added to this kit (standalone items)
    # Exclude ancestors to prevent circular hierarchy
    ancestor_ids = [a.id for a in ancestors]
    standalone_items = Item.objects.filter(parent_item__isnull=True).exclude(id=id).exclude(id__in=ancestor_ids).order_by('name')
    
    return render(request, 'inventory/item_detail.html', {
        'item': item,
        'location_history': history,
        'children': children,
        'ancestors': ancestors,
        'standalone_items': standalone_items,
        'nav_section': 'inventory'
    })

@permission_required('inventory.view_item', raise_exception=True)
def item_hierarchy(request, id):
    """Visualize the full kit hierarchy as a tree diagram"""
    item = get_object_or_404(Item, id=id)
    # Find the top-most parent (root of the kit)
    root = item
    while root.parent_item:
        root = root.parent_item
    
    return render(request, 'inventory/item_hierarchy.html', {
        'root': root,
        'target_item': item,
        'nav_section': 'inventory'
    })
