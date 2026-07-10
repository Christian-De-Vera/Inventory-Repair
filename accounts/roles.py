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

    admin_group = Group.objects.get_or_create(name=ROLE_ADMIN)[0]
    admin_group.permissions.set(Permission.objects.all())

    supply_group = Group.objects.get_or_create(name=ROLE_SUPPLY_MANAGER)[0]
    supply_group.permissions.set(
        _model_permissions(inventory_models) |
        _model_permissions([RepairTicket], actions=('view', 'add'))
    )

    mis_group = Group.objects.get_or_create(name=ROLE_MIS)[0]
    mis_group.permissions.set(
        _model_permissions(repair_models)
    )

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
