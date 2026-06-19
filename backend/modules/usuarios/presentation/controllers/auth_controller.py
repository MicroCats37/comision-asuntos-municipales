"""
AuthController — controladores HTTP ligeros para endpoints de login.

Solo delega a AuthOrchestrator y retorna vía presenter.
"""
from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from core.responses import ApiResponse, success_response
from ..schemas.auth_schemas import (
    LoginUsernameIn,
    LoginDniIn,
    LoginEmailIn,
    LoginTokenOut,
)
from ..presenters.auth_presenter import AuthPresenter
from ...domain.services.orchestrators.auth_orchestrator import AuthOrchestrator


@api_controller("/auth/login", tags=["Autenticación"], permissions=[AllowAny])
class AuthLoginController:
    """
    Controlador para login JWT modular por username, DNI o email.

    Cada endpoint:
    1. Recibe el payload
    2. Delega a AuthOrchestrator
    3. Transforma el resultado vía AuthPresenter
    4. Retorna la respuesta HTTP
    """

    @inject
    def __init__(self, auth_orchestrator: AuthOrchestrator):
        self.auth_orchestrator = auth_orchestrator

    @route.post("/username", response={200: ApiResponse[LoginTokenOut]}, auth=None)
    async def login_username(self, payload: LoginUsernameIn):
        """
        Login con username + password.

        Retorna JWT access_token, refresh_token, expires_at y datos del usuario.
        """
        result = await self.auth_orchestrator.login_username(
            username=payload.username,
            password=payload.password,
        )
        return success_response(AuthPresenter.present_login(result))

    @route.post("/dni", response={200: ApiResponse[LoginTokenOut]}, auth=None)
    async def login_dni(self, payload: LoginDniIn):
        """
        Login con DNI + password.

        Retorna JWT access_token, refresh_token, expires_at y datos del usuario.
        """
        result = await self.auth_orchestrator.login_dni(
            dni=payload.dni,
            password=payload.password,
        )
        return success_response(AuthPresenter.present_login(result))

    @route.post("/email", response={200: ApiResponse[LoginTokenOut]}, auth=None)
    async def login_email(self, payload: LoginEmailIn):
        """
        Login con email + password.

        Retorna JWT access_token, refresh_token, expires_at y datos del usuario.
        """
        result = await self.auth_orchestrator.login_email(
            email=payload.email,
            password=payload.password,
        )
        return success_response(AuthPresenter.present_login(result))
