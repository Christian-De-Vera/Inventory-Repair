from django.urls import path
from . import views

app_name = 'repairs'

urlpatterns = [
    path('', views.repair_ticket_list, name='ticket_list'),
    path('create/', views.repair_ticket_create, name='ticket_create'),
    path('create/<int:item_id>/', views.repair_ticket_create, name='ticket_create_for_item'),
    path('<int:pk>/', views.repair_ticket_detail, name='ticket_detail'),
    path('<int:pk>/update/', views.repair_ticket_update, name='ticket_update'),
    path('<int:pk>/print/', views.repair_work_order_print, name='work_order_print'),
    path('export/csv/', views.export_repairs_csv, name='export_repairs_csv'),
    path('dashboard/', views.repair_dashboard, name='repair_dashboard'),

    path('tickets/bulk-delete/', views.bulk_delete_tickets, name='bulk_delete'),

]