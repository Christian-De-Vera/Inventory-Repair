from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import csv
import json
import os
from .models import Item, ItemForm, Category, Location, Person
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
@require_http_methods(["POST"])
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

def item_list(request):
    """Display all items with sorting, search, filtering, pagination, and grouping"""
    items = Item.objects.all().select_related('category', 'location', 'person_accountable')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(serial_no__icontains=search_query) |
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
    
    # Grouping functionality (independent from sorting)
    group_by = request.GET.get('group_by', 'none')
    
    # Sorting functionality (independent from grouping)
    if 'sort' not in request.GET:
        # Default: Newest First
        sort_by = 'created_at'
        invert = True
    else:
        sort_by = request.GET.get('sort', 'created_at')
        invert = request.GET.get('invert', '') == 'true'
    
    # Define valid base sorting fields
    valid_sort_fields = {
        'name': 'name',
        'category': 'category__name',
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
    
    # Apply sorting to all items first
    items = items.order_by(order_by)
    
    # Get grouped items (after sorting)
    grouped_items = {}
    if group_by != 'none':
        for item in items:
            if group_by == 'name':
                key = item.name
            elif group_by == 'category':
                key = item.category.name if item.category else 'Uncategorized'
            elif group_by == 'location':
                key = item.location.name if item.location else 'No Location'
            elif group_by == 'status':
                key = item.get_status_display()
            elif group_by == 'person':
                key = item.person_accountable.name if item.person_accountable else 'Unassigned'
            elif group_by == 'acquisition_date':
                key = item.acquisition_date.strftime('%Y-%m') if item.acquisition_date else 'No Date'
            else:
                key = 'Other'
            
            if key not in grouped_items:
                grouped_items[key] = []
            grouped_items[key].append(item)
        
        # Sort groups alphabetically (but keep items sorted within groups)
        grouped_items = dict(sorted(grouped_items.items()))
    
    # Pagination (only when not grouped)
    paginator = Paginator(items, 10) if group_by == 'none' else None
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
    persons = Person.objects.all().order_by('name')
    status_choices = Item.STATUS_CHOICES
    
    return render(request, 'inventory/item_list.html', {
        'items': items_page if paginator else items,
        'grouped_items': grouped_items if group_by != 'none' else None,
        'group_by': group_by,
        'total_items': items.count(),
        'current_sort': sort_by,
        'current_invert': invert,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'location_filter': location_filter,
        'person_filter': person_filter,
        'locations': locations,
        'categories': categories,
        'persons': persons,
        'status_choices': status_choices,
    })

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
        
        # Track which fields were actually changed
        updated_fields = []
        
        # Update status
        new_status = request.POST.get('status')
        if new_status and new_status != '':
            items.update(status=new_status)
            updated_fields.append('status')
        
        # Update category
        new_category_id = request.POST.get('category')
        if new_category_id and new_category_id != '':
            try:
                category = Category.objects.get(id=new_category_id)
                items.update(category=category)
                updated_fields.append('category')
            except Category.DoesNotExist:
                pass
        
        # Update location
        new_location_id = request.POST.get('location')
        if new_location_id and new_location_id != '':
            try:
                location = Location.objects.get(id=new_location_id)
                items.update(location=location)
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
        
        # Handle image upload
        if request.FILES.get('image'):
            uploaded_image = request.FILES['image']
            for item in items:
                # Delete old image if exists
                if item.image:
                    old_image_path = item.image.path
                    if os.path.isfile(old_image_path):
                        os.remove(old_image_path)
                item.image = uploaded_image
                item.save()
            updated_fields.append('image')
        
        # Handle image removal
        if request.POST.get('remove_image') == 'true':
            for item in items:
                if item.image:
                    if os.path.isfile(item.image.path):
                        os.remove(item.image.path)
                    item.image = None
                    item.save()
            updated_fields.append('image_removed')
        
        # Handle delete
        if request.POST.get('delete') == 'true':
            items.delete()
            messages.success(request, f'Successfully deleted {count} item(s).')
            return redirect('item_list')
        
        # Show success message with what was updated
        if updated_fields:
            fields_text = ', '.join(updated_fields)
            messages.success(request, f'Successfully updated {count} item(s). Changed: {fields_text}')
        else:
            messages.info(request, 'No changes were made to the selected items.')
        
        return redirect('item_list')
    
    return redirect('item_list')

def item_add(request):
    """Add a new item or multiple items with quantity"""
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            quantity = form.cleaned_data.get('quantity', 1)
            
            if quantity == 1:
                # Save single item normally
                item = form.save()
                messages.success(request, f'Item "{item.name}" added successfully!')
            else:
                # Create multiple items with same data but unique codes
                base_data = {
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data.get('description', ''),
                    'category': form.cleaned_data.get('category'),
                    'serial_no': form.cleaned_data.get('serial_no', ''),
                    'status': form.cleaned_data['status'],
                    'location': form.cleaned_data.get('location'),
                    'person_accountable': form.cleaned_data.get('person_accountable'),
                    'acquisition_date': form.cleaned_data.get('acquisition_date'),
                    'end_of_life_date': form.cleaned_data.get('end_of_life_date'),
                    'acquisition_cost': form.cleaned_data.get('acquisition_cost'),
                    'quantity': 1,  # Each individual item has quantity=1
                }
                
                # Handle image separately
                image = request.FILES.get('image')
                
                created_count = 0
                for i in range(quantity):
                    item = Item(**base_data)
                    if image:
                        # Create a copy of the image for each item
                        item.image = image
                    item.save()
                    created_count += 1
                
                messages.success(request, f'Successfully added {created_count} items of "{base_data["name"]}"!')
            
            return redirect('item_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ItemForm()
    
    return render(request, 'inventory/item_form.html', {'form': form, 'title': 'Add Item'})

def item_edit(request, id):
    """Edit an existing item"""
    item = get_object_or_404(Item, id=id)
    
    if request.method == 'POST':
        # ✅ CRITICAL FIX: Add request.FILES here too
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('item_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'inventory/item_form.html', {'form': form, 'title': 'Edit Item', 'item': item})

def item_delete(request, id):
    """Delete an item"""
    item = get_object_or_404(Item, id=id)
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, f'{item.name} deleted successfully!')
        return redirect('item_list')
    
    return render(request, 'inventory/item_confirm_delete.html', {'item': item})

def item_detail(request, id):
    """Show single item details"""
    item = get_object_or_404(Item, id=id)
    return render(request, 'inventory/item_detail.html', {'item': item})