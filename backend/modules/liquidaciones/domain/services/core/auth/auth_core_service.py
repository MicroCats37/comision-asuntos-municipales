"""
AuthCoreService — Core service for authentication context extraction.

Centralizes the logic for extracting authenticated user info from HTTP requests.
This allows future integration with django-rules, django-guardian, or other
permission frameworks without modifying Controllers.
"""
from django.http import HttpRequest
from ninja.errors import HttpError


class AuthCoreService:
    """Service for extracting authenticated user context from requests."""

    def get_authenticated_user_id(self, request: HttpRequest) -> int:
        """
        Extract the authenticated user's ID from the request.

        Raises:
            HttpError: 401 if the user is not authenticated.

        Note: HttpError in Core is an exception for auth-related errors
        because they're framework-level, not business validation. Business
        validation HttpErrors live in Orchestrators. This allows future
        django-rules/guardian integration to raise similar auth errors
        without modifying Controllers (which must remain pure delegators).
        """
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            raise HttpError(401, "Usuario no autenticado")
        return user.id
