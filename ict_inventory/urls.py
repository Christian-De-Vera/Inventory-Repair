"""
URL configuration for ict_inventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.models import User
from django.http import HttpResponse
from inventory import views as inventory_views

def create_admin(request):
    if User.objects.filter(username='admin').exists():
        return HttpResponse('Admin already exists')
    User.objects.create_superuser('admin', 'admin@example.com', 'changeme123')
    return HttpResponse('Created admin: admin / changeme123 - CHANGE PASSWORD IMMEDIATELY')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', inventory_views.dashboard, name='dashboard'),
    path('inventory/', include('inventory.urls')),
    path('inventory/hierarchy/<int:id>/', inventory_views.item_hierarchy, name='item_hierarchy'),
    path('repairs/', include('repairs.urls')),
    path('notifications/', include('notifications.urls')),
    path('create-admin/', create_admin),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
