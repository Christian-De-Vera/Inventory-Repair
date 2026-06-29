from django.urls import path
from . import views

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('add/', views.item_add, name='item_add'),
    path('edit/<int:id>/', views.item_edit, name='item_edit'),
    path('delete/<int:id>/', views.item_delete, name='item_delete'),
    path('detail/<int:id>/', views.item_detail, name='item_detail'),
    path('break-kit/<int:id>/', views.break_kit, name='break_kit'),
    path('bulk-edit/', views.bulk_edit, name='bulk_edit'),
    path('bulk-delete/', views.bulk_delete, name='bulk_delete'),
    
    # Quick add URLs
    path('quick-add/category/', views.quick_add_category, name='quick_add_category'),
    path('quick-add/department/', views.quick_add_department, name='quick_add_department'),
    path('quick-add/location/', views.quick_add_location, name='quick_add_location'),
    path('quick-add/person/', views.quick_add_person, name='quick_add_person'),
    path('quick-add/custom-field/', views.quick_add_custom_field, name='quick_add_custom_field'), 
    path('add-to-kit/<int:parent_id>/', views.add_existing_to_kit, name='add_existing_to_kit'),
    path('remove-from-kit/<int:id>/', views.remove_from_kit, name='remove_from_kit'),
    
    # Custom Field Management URLs
    path('custom-fields/', views.custom_fields_list, name='custom_fields_list'),
    path('custom-fields/add/', views.custom_field_add, name='custom_field_add'),
    path('custom-fields/edit/<int:id>/', views.custom_field_edit, name='custom_field_edit'),
    path('custom-fields/delete/<int:id>/', views.custom_field_delete, name='custom_field_delete'),

    path('download-qr/<int:id>/', views.download_item_qr, name='download_item_qr'),

    path('find-by-code/', views.find_item_by_code, name='find_item_by_code'),
    path('export/csv/', views.export_items_csv, name='export_items_csv'),
    path('mark-in-repair/<int:id>/', views.mark_item_in_repair, name='mark_item_in_repair'),

    path('dashboard/', views.dashboard, name='inventory_dashboard'),
]