from django.contrib.auth import logout


class AuthorizationVersionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_version = request.session.get("authz_version")
            if session_version is not None and session_version != request.user.authz_version:
                logout(request)
        return self.get_response(request)
