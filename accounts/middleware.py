from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class LoginRequiredMiddleware:
    """Require login for the main app while leaving auth, admin, and assets open."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated or self._is_public_path(request.path):
            return self.get_response(request)

        login_url = reverse(settings.LOGIN_URL)
        return redirect(f'{login_url}?next={request.get_full_path()}')

    def _is_public_path(self, path):
        public_prefixes = [
            reverse('login'),
            reverse('register'),
            '/admin/',
            '/create-admin/',
            settings.STATIC_URL,
            settings.MEDIA_URL,
        ]
        return any(path.startswith(prefix) for prefix in public_prefixes if prefix)
