# AI Handoff Prompt

You are taking over work on a Django project at `C:\Inventory-Repair V2`.

## Project Summary

This is an ICT Inventory and Repair Service Tracker built with Django 6.0.5 and SQLite.

Apps:
- `inventory`: items, categories, departments, locations, people, custom fields, item images, QR codes, location history, parent/child kit hierarchy.
- `repairs`: repair tickets, ticket logs, repair dashboard, work order printing, CSV export.
- `accounts`: recently added authentication, registration, role groups, login-required middleware, and user role management.

Important models:
- `inventory.models.Item`: primary inventory asset model. Tracks item code, name, parent kit, category, department, serial number, quantity, status, location, accountable person, image, acquisition/EOL data, acquisition cost, QR generation, location history.
- `inventory.models.CustomField` and `CustomFieldValue`: dynamic item fields.
- `repairs.models.RepairTicket`: linked to `Item`; ticket status syncs item status.
- `repairs.models.RepairLog`: ticket audit/progress history.

## Recent Auth And Permission Work

Implemented:
- Login at `/accounts/login/`
- Register at `/accounts/register/`
- Logout via POST buttons in sidebars
- Login-required middleware for the main app
- Default groups:
  - `Admin`
  - `Supply Manager`
  - `MIS`
  - `Person Accountable`
- New registered users are assigned to `Person Accountable`.
- Role groups are bootstrapped in `accounts.roles.ensure_default_roles()` via `post_migrate`.
- Admin users can manage roles at:
  - `/accounts/users/`
  - `/accounts/users/<id>/roles/`
- Inventory and repair sidebars are shaped by permissions.
- Inventory and repair views now use server-side permission checks.
- Main page action buttons were also made permission-aware.
- Custom 403 page added at `accounts/templates/403.html`.

Key files:
- `accounts/forms.py`
- `accounts/middleware.py`
- `accounts/roles.py`
- `accounts/views.py`
- `accounts/urls.py`
- `accounts/templates/accounts/login.html`
- `accounts/templates/accounts/register.html`
- `accounts/templates/accounts/user_list.html`
- `accounts/templates/accounts/user_roles_form.html`
- `accounts/templates/403.html`
- `ict_inventory/settings.py`
- `ict_inventory/urls.py`
- `inventory/views.py`
- `repairs/views.py`
- `inventory/templates/inventory/inventory_base.html`
- `repairs/templates/repairs/repair_base.html`

## Current Role Intent

Admin:
- Full permissions through the `Admin` group.
- Can manage user roles in the app.
- Superusers still have Django admin access.

Supply Manager:
- Inventory add/change/delete/view.
- Repair ticket view only.

MIS:
- Repair ticket add/change/delete/view.
- Item/location/person view/change.

Person Accountable:
- View-only access to item/location/person/repair ticket records.

## Validation Already Done

Commands run successfully:

```powershell
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py migrate
```

Temporary permission test passed:
- Person Accountable can open dashboard.
- Person Accountable gets `403` on `/inventory/add/`.
- Person Accountable gets `403` on `/accounts/users/`.
- Admin group user can open `/accounts/users/`.
- Admin group user can open a user role edit page.

The dev server was running at:

```text
http://127.0.0.1:8000/
```

## Known Issues / Good Next Steps

1. Add automated tests for permissions and role assignment.
2. Add a proper `requirements.txt` because the project currently has no dependency manifest. `qrcode[pil]` was installed into the venv because `inventory.models` imports `qrcode`.
3. Clean up duplicated `ItemForm`: there is one in `inventory/forms.py`, but the app currently imports `ItemForm` from `inventory.models`.
4. Review template markup in `inventory/templates/inventory/custom_fields_list.html`; it appears to have mismatched closing tags from before this auth work.
5. Consider whether `Admin` group users should automatically get `is_staff=True` if they need Django admin access, or keep in-app user management separate from Django admin.
6. Consider object-level restrictions for Person Accountable users so they only see their own assigned items, if that is a real requirement.
7. Add a profile page or password-change flow.
8. Add a registration approval flow if open self-registration should not immediately grant dashboard access.

## Important Caution

The git worktree was already dirty before this auth work. Do not revert unrelated files. Work with the current state, and inspect changes before editing.
