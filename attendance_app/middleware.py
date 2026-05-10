from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.timezone import now
from datetime import timedelta


class AutoLogoutMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:

            current_time = now()

            last_activity = request.session.get('last_activity')

            if last_activity:
                last_activity = now().fromisoformat(last_activity)

                if current_time - last_activity > timedelta(seconds=settings.SESSION_COOKIE_AGE):
                    logout(request)
                    return redirect('login')

            request.session['last_activity'] = current_time.isoformat()

        response = self.get_response(request)

        return response