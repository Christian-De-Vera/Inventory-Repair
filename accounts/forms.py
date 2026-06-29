from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission, User

from .roles import ROLE_ADMIN, ROLE_MIS, ROLE_PERSON_ACCOUNTABLE, ROLE_SUPPLY_MANAGER


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class UserRoleForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(
            name__in=[ROLE_ADMIN, ROLE_SUPPLY_MANAGER, ROLE_MIS, ROLE_PERSON_ACCOUNTABLE]
        ).order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    is_active = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active', 'groups')


class PermissionSelectionForm(forms.Form):
    """Form for selecting individual permissions with collapsible groups."""
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Get all permissions for inventory and repairs models
        from inventory.models import Category, CustomField, Department, Item, Location, Person
        from repairs.models import RepairTicket
        
        inventory_models = [Category, CustomField, Department, Item, Location, Person]
        
        # Group permissions by model
        permission_groups = {}
        for model in inventory_models:
            app_label = model._meta.app_label
            model_name = model._meta.model_name
            perms = Permission.objects.filter(content_type__app_label=app_label, content_type__model=model_name)
            if perms:
                group_key = f"{app_label}.{model_name}"
                permission_groups[group_key] = perms
        
        perms = Permission.objects.filter(content_type__app_label='repairs', content_type__model='repairticket')
        if perms:
            permission_groups['repairs.repairticket'] = perms
        
        # Create checkboxes for each permission
        user_perms = set(user.user_permissions.values_list('id', flat=True)) if user else set()
        for group_key, perms in sorted(permission_groups.items()):
            group_name = group_key.replace('.', '_')
            self.fields[group_name] = forms.BooleanField(
                required=False,
                label=f'{group_key.split(".")[0].title()} - {group_key.split(".")[1].replace("_", " ").title()}',
                initial=True,
            )
            for perm in perms:
                field_name = f"perm_{perm.id}"
                self.fields[field_name] = forms.BooleanField(
                    required=False,
                    label=self._format_perm_label(perm),
                    initial=perm.id in user_perms,
                )
    
    def _format_perm_label(self, perm):
        """Format permission codename to readable label."""
        labels = {
            'add': 'Add',
            'change': 'Edit',
            'delete': 'Delete',
            'view': 'View',
        }
        parts = perm.codename.split('_')
        action = labels.get(parts[0], parts[0]) if parts else ''
        model_name = parts[1].replace('_', ' ').title() if len(parts) > 1 else ''
        return f"{action} {model_name}".strip() if model_name else action
