"""
AuthOrchestrator — fachada asíncrona ligera para controladores de auth.

Solo delega a AuthFlujo. Sin lógica de negocio aquí.
"""
from injector import inject

from modules.usuarios.domain.services.flujos.auth_flujo import AuthFlujo
from modules.usuarios.domain.schemas.auth_result_schemas import LoginTokenResult


class AuthOrchestrator:
    """
    Fachada asíncrona ligera — delega toda la lógica a AuthFlujo.

    Inyecta AuthFlujo vía __init__.
    """

    @inject
    def __init__(self, flujo: AuthFlujo):
        self.flujo = flujo

    async def login_username(self, username: str, password: str) -> LoginTokenResult:
        """Login por username — delega a AuthFlujo._proceso_login_username."""
        return await self.flujo._proceso_login_username(username, password)

    async def login_dni(self, dni: str, password: str) -> LoginTokenResult:
        """Login por DNI — delega a AuthFlujo._proceso_login_dni."""
        return await self.flujo._proceso_login_dni(dni, password)

    async def login_email(self, email: str, password: str) -> LoginTokenResult:
        """Login por email — delega a AuthFlujo._proceso_login_email."""
        return await self.flujo._proceso_login_email(email, password)
