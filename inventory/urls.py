from django.urls import path
from . import views

urlpatterns = [
    path('', views.item_list, name='item_list'),
    path('add/', views.item_add, name='item_add'),
    path('edit/<int:id>/', views.item_edit, name='item_edit'),
    path('delete/<int:id>/', views.item_delete, name='item_delete'),
    path('detail/<int:id>/', views.item_detail, name='item_detail'),
    path('bulk-edit/', views.bulk_edit, name='bulk_edit'),

    # Quick add URLs
    path('quick-add/category/', views.quick_add_category, name='quick_add_category'),
    path('quick-add/location/', views.quick_add_location, name='quick_add_location'),
    path('quick-add/person/', views.quick_add_person, name='quick_add_person'),
]