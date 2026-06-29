from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegisterForm, UserRoleForm
from .roles import ROLE_ADMIN, ROLE_PERSON_ACCOUNTABLE, get_role_permission_codenames


def is_role_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=ROLE_ADMIN).exists())


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            group, _ = Group.objects.get_or_create(name=ROLE_PERSON_ACCOUNTABLE)
            user.groups.add(group)
            login(request, user)
            messages.success(request, 'Account created. An admin can grant additional permissions if needed.')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def user_list(request):
    if not is_role_admin(request.user):
        raise PermissionDenied
    users = User.objects.prefetch_related('groups', 'user_permissions').order_by('username')
    
    # Calculate role permission codenames once
    role_codenames = get_role_permission_codenames()
    role_codenames_sets = {role_name: set(codenames) for role_name, codenames in role_codenames.items()}
    
    # Annotate users with their custom role status
    for user in users:
        user_perm_codenames = set(user.user_permissions.values_list('codename', flat=True))
        
        # Check if user's permissions match any role exactly
        has_matching_role = any(
            user_perm_codenames == role_codenames_set
            for role_codenames_set in role_codenames_sets.values()
        )
        
        # Custom if has individual permissions but no role matches exactly
        user.is_custom_role = bool(user_perm_codenames) and not has_matching_role
    
    return render(request, 'accounts/user_list.html', {'users': users, 'nav_section': 'admin'})


@login_required
def user_roles_edit(request, pk):
    if not is_role_admin(request.user):
        raise PermissionDenied
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            
            # Handle individual permission assignment
            selected_perms = request.POST.getlist('permissions')
            if selected_perms:
                perms = Permission.objects.filter(id__in=selected_perms)
                user.user_permissions.set(perms)
            else:
                user.user_permissions.clear()
                
            messages.success(request, f'Permissions updated for {user.username}.')
            return redirect('account_user_list')
    else:
        form = UserRoleForm(instance=user)
    
    # Get permissions grouped by app/model
    from inventory.models import Category, CustomField, Department, Item, Location, Person
    from repairs.models import RepairTicket
    from .roles import get_role_permission_codenames, ROLE_ADMIN, ROLE_SUPPLY_MANAGER, ROLE_MIS, ROLE_PERSON_ACCOUNTABLE
    import json
    
    models = [Item, Category, Department, Location, Person, CustomField, RepairTicket]
    permission_groups = {}
    for model in models:
        perms = Permission.objects.filter(content_type__app_label=model._meta.app_label, content_type__model=model._meta.model_name)
        if perms:
            key = f"{model._meta.app_label}_{model._meta.model_name}"
            permission_groups[key] = {
                'model': model,
                'label': model._meta.verbose_name_plural.title(),
                'perms': perms
            }
    
    user_perms = set(user.user_permissions.values_list('id', flat=True))
    role_permission_map = json.dumps(get_role_permission_codenames())
    
    # Create group_id -> role_name mapping for JavaScript
    group_choices = {str(g.id): g.name for g in Group.objects.filter(name__in=[ROLE_ADMIN, ROLE_SUPPLY_MANAGER, ROLE_MIS, ROLE_PERSON_ACCOUNTABLE])}

    return render(request, 'accounts/user_roles_form.html', {
        'form': form,
        'target_user': user,
        'permission_groups': permission_groups,
        'user_perms': user_perms,
        'role_permission_map': role_permission_map,
        'group_choices': json.dumps(group_choices),
        'nav_section': 'admin',
    })


@login_required
def user_delete(request, pk):
    if not is_role_admin(request.user):
        raise PermissionDenied
    
    target_user = get_object_or_404(User, pk=pk)
    
    if request.user == target_user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('account_user_list')
    
    if request.method == 'POST':
        username = target_user.username
        target_user.delete()
        messages.success(request, f'User "{username}" has been deleted successfully.')
        return redirect('account_user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {
        'target_user': target_user,
        'nav_section': 'admin',
    })
