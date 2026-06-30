from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('api/list/', views.api_notifications_list, name='api_list'),
    path('api/mark-read/', views.api_mark_read, name='api_mark_read'),
    path('api/unread-count/', views.api_unread_count, name='api_unread_count'),
    path('api/delete/', views.api_delete_notifications, name='api_delete'),
]