from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


ROLE_ADMIN = 'Admin'
ROLE_SUPPLY_MANAGER = 'Supply Manager'
ROLE_MIS = 'MIS'
ROLE_PERSON_ACCOUNTABLE = 'Person Accountable'


def ensure_default_roles(**kwargs):
    from inventory.models import Category, CustomField, Department, Item, Location, Person
    from repairs.models import RepairTicket

    inventory_models = [Category, CustomField, Department, Item, Location, Person]
    repair_models = [RepairTicket]

    # Admin: Full permissions
    admin_group = Group.objects.get_or_create(name=ROLE_ADMIN)[0]
    admin_group.permissions.set(Permission.objects.all())

    # Supply Manager: Full inventory CRUD + request/view repair tickets (cannot process tickets)
    supply_group = Group.objects.get_or_create(name=ROLE_SUPPLY_MANAGER)[0]
    supply_group.permissions.set(
        _model_permissions(inventory_models) |
        _model_permissions([RepairTicket], actions=('view', 'add'))
    )

    # MIS: Process repair tickets + view inventory (view-only on inventory, cannot edit/add)
    mis_group = Group.objects.get_or_create(name=ROLE_MIS)[0]
    mis_group.permissions.set(
        _model_permissions(repair_models) |
        _model_permissions([Item, Location, Person], actions=('view',))
    )

    # Accountable Person: View + edit items, create/request repair tickets (cannot add/delete items or process tickets)
    accountable_group = Group.objects.get_or_create(name=ROLE_PERSON_ACCOUNTABLE)[0]
    accountable_group.permissions.set(
        _model_permissions([Item, Location, Person], actions=('view', 'change')) |
        _model_permissions([RepairTicket], actions=('view', 'add'))
    )


def _model_permissions(models, actions=('add', 'change', 'delete', 'view')):
    permissions = Permission.objects.none()
    for model in models:
        content_type = ContentType.objects.get_for_model(model)
        codenames = [f'{action}_{model._meta.model_name}' for action in actions]
        permissions = permissions | Permission.objects.filter(content_type=content_type, codename__in=codenames)
    return permissions


def get_role_permission_codenames():
    """Return codename mapping for each role for template syncing."""
    from inventory.models import Category, CustomField, Department, Item, Location, Person
    from repairs.models import RepairTicket
    
    def codenames_for(models, actions):
        result = []
        for model in models:
            for action in actions:
                result.append(f'{action}_{model._meta.model_name}')
        return result
    
    return {
        ROLE_ADMIN: codenames_for(
            [Category, CustomField, Department, Item, Location, Person, RepairTicket],
            ['add', 'change', 'delete', 'view']
        ),
        ROLE_SUPPLY_MANAGER: codenames_for(
            [Category, CustomField, Department, Item, Location, Person],
            ['add', 'change', 'delete', 'view']
        ) + codenames_for([RepairTicket], ['view', 'add']),
        ROLE_MIS: codenames_for(
            [RepairTicket],
            ['add', 'change', 'delete', 'view']
        ) + codenames_for([Item, Location, Person], ['view']),
        ROLE_PERSON_ACCOUNTABLE: codenames_for(
            [Item, Location, Person],
            ['view', 'change']
        ) + codenames_for([RepairTicket], ['view', 'add']),
    }
