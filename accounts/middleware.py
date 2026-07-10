from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from .roles import ROLE_ADMIN, ROLE_MIS


class LoginRequiredMiddleware:
    """Require login for the main app while leaving auth, admin, and assets open."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.pending_approval_path = reverse('pending_approval')
        self.repair_dashboard_path = reverse('repairs:repair_dashboard')

    def __call__(self, request):
        if not request.user.is_authenticated:
            if self._is_public_path(request.path):
                return self.get_response(request)
            login_url = reverse(settings.LOGIN_URL)
            return redirect(f'{login_url}?next={request.get_full_path()}')

        if self._is_public_path(request.path) or request.path == self.pending_approval_path:
            return self.get_response(request)

        request.is_mis_only = self._is_mis_only(request.user)
        request.repair_access_allowed = self._is_repair_access_allowed(request.user)

        if self._has_access(request.user):
            if self._is_inventory_app_path(request.path) and request.is_mis_only:
                return redirect(self.repair_dashboard_path)
            if self._is_repair_app_path(request.path) and not request.repair_access_allowed:
                return redirect('/')
            return self.get_response(request)

        return redirect(self.pending_approval_path)

    def _is_repair_app_path(self, path):
        return path.startswith('/repairs/')

    def _is_repair_access_allowed(self, user):
        if user.is_superuser:
            return True
        if user.groups.filter(name=ROLE_ADMIN).exists():
            return True
        return user.groups.filter(name=ROLE_MIS).exists()

    def _is_public_path(self, path):
        public_prefixes = [
            reverse('login'),
            reverse('register'),
            reverse('logout'),
            '/admin/',
            settings.STATIC_URL,
            settings.MEDIA_URL,
            '/manifest.webmanifest',
            '/sw.js',
        ]
        return any(path.startswith(prefix) for prefix in public_prefixes if prefix)

    def _is_inventory_app_path(self, path):
        if path == '/' or path.startswith('/inventory/'):
            return True
        return False

    def _is_mis_only(self, user):
        if user.is_superuser:
            return False
        if not user.groups.filter(name=ROLE_MIS).exists():
            return False
        if user.groups.exclude(name=ROLE_MIS).exists():
            return False
        return True

    def _has_access(self, user):
        if user.is_superuser:
            return True
        return user.groups.exists()
