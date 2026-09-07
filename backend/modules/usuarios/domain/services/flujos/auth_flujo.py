"""
AuthFlujo — flujos de negocio asíncronos para autenticación.

Cada método _proceso_* es un caso de uso completo.
Usa sync_to_async para envolver operaciones ORM de AuthCoreService.
"""
from ninja.errors import HttpError
from injector import inject

from modules.usuarios.domain.services.core.auth_core_service import AuthCoreService
from modules.usuarios.domain.schemas.auth_result_schemas import LoginTokenResult, AuthUserResult


class AuthFlujo:
    """
    Flujos asíncronos para auth — _proceso_login_username, _proceso_login_dni, _proceso_login_email.

    Inyecta AuthCoreService para operaciones ORM síncronas envueltas en sync_to_async.
    """

    @inject
    def __init__(self, auth_core: AuthCoreService):
        self.auth_core = auth_core

    async def _proceso_login_username(self, username: str, password: str) -> LoginTokenResult:
        """
        Flujo para login por username.

        1. Busca usuario por username.
        2. Autentica con username + password.
        3. Si está autenticado, crea tokens y retorna resultado.
        """
        # Paso 1: Buscar usuario por username
        usuario = await self.auth_core.buscar_usuario_por_username(username)
        if not usuario:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 2: Autenticar
        usuario = await self.auth_core.autenticar(username=username, password=password)
        if not usuario:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 3: Verificar si el usuario está activo
        if not usuario.is_active:
            raise HttpError(403, "Usuario inactivo")

        # Paso 4: Crear tokens
        access_token, refresh_token, expires_at = await self.auth_core.crear_tokens(usuario)

        # Paso 5: Construir resultado de usuario
        user_result = await self.auth_core.build_user_result(usuario)

        return LoginTokenResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user=user_result,
        )

    async def _proceso_login_dni(self, dni: str, password: str) -> LoginTokenResult:
        """
        Flujo para login por DNI.

        1. Busca usuario por dni.
        2. Obtiene username del usuario encontrado.
        3. Autentica con username + password.
        4. Si está autenticado, crea tokens y retorna resultado.
        """
        # Paso 0: Safety shield — reject empty DNI
        if not dni:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 1: Buscar usuario por dni
        usuario = await self.auth_core.buscar_usuario_por_dni(dni)
        if not usuario:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 2: Autenticar usando username (el campo real de auth)
        usuario = await self.auth_core.autenticar(username=usuario.username, password=password)
        if not usuario:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 3: Verificar si el usuario está activo
        if not usuario.is_active:
            raise HttpError(403, "Usuario inactivo")

        # Paso 4: Crear tokens
        access_token, refresh_token, expires_at = await self.auth_core.crear_tokens(usuario)

        # Paso 5: Construir resultado de usuario
        user_result = await self.auth_core.build_user_result(usuario)

        return LoginTokenResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user=user_result,
        )

    async def _proceso_login_email(self, email: str, password: str) -> LoginTokenResult:
        """
        Flujo para login por email.

        1. Busca usuario por email.
        2. Obtiene username del usuario encontrado.
        3. Autentica con username + password.
        4. Si está autenticado, crea tokens y retorna resultado.
        """
        # Paso 0: Safety shield — reject empty email
        if not email:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 1: Buscar usuario por email
        usuario = await self.auth_core.buscar_usuario_por_email(email)
        if not usuario:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 2: Autenticar usando username (el campo real de auth)
        usuario = await self.auth_core.autenticar(username=usuario.username, password=password)
        if not usuario:
            raise HttpError(401, "Credenciales inválidas")

        # Paso 3: Verificar si el usuario está activo
        if not usuario.is_active:
            raise HttpError(403, "Usuario inactivo")

        # Paso 4: Crear tokens
        access_token, refresh_token, expires_at = await self.auth_core.crear_tokens(usuario)

        # Paso 5: Construir resultado de usuario
        user_result = await self.auth_core.build_user_result(usuario)

        return LoginTokenResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user=user_result,
        )
