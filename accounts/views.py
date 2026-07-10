from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegisterForm, UserRoleForm
from .roles import ROLE_ADMIN


def is_role_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=ROLE_ADMIN).exists())


@login_required
def pending_approval(request):
    return render(request, 'accounts/pending_approval.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created. An admin will grant access shortly.')
            return redirect('pending_approval')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def user_list(request):
    if not is_role_admin(request.user):
        raise PermissionDenied
    users = User.objects.prefetch_related('groups', 'user_permissions').order_by('username')
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
            messages.success(request, f'Roles updated for {user.username}.')
            return redirect('account_user_list')
    else:
        form = UserRoleForm(instance=user)

    return render(request, 'accounts/user_roles_form.html', {
        'form': form,
        'target_user': user,
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
