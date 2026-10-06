"""
AuthCoreService — operaciones ORM síncronas y generación de tokens para auth.

NO usa transaction.atomic() internamente — el llamador (flujo) provee la transacción si es necesaria.
"""
from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate
from django.utils import timezone
from ninja_jwt.tokens import RefreshToken

from injector import inject
from modules.usuarios.domain.models import Usuario
from modules.usuarios.domain.schemas.auth_result_schemas import AuthUserResult, LoginTokenResult


class AuthCoreService:
    """
    Operaciones síncronas para auth: búsqueda de usuario, autenticación, creación de tokens.
    NO usa transaction.atomic() — el llamador lo provee si es necesario.
    """

    # -------------------------------------------------------------------------
    # Helpers síncronos — acceso ORM envuelto en sync_to_async por el llamador
    # -------------------------------------------------------------------------

    def _build_user_result(self, usuario: Usuario) -> AuthUserResult:
        """
        Construye AuthUserResult a partir de una instancia de Usuario.
        Seguro para llamar dentro de sync_to_async.
        """
        return AuthUserResult(
            id=str(usuario.id),
            username=usuario.username,
            dni=usuario.dni,
            email=usuario.email,
            nombres=usuario.nombres,
            apellidos=usuario.apellidos,
            is_staff=usuario.is_staff,
            is_superuser=usuario.is_superuser,
        )

    def _get_usuario_by_username(self, username: str) -> Usuario | None:
        """Sync: obtiene usuario por campo username."""
        try:
            return Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            return None

    def _get_usuario_by_dni(self, dni: str) -> Usuario | None:
        """Sync: obtiene usuario por campo dni."""
        try:
            return Usuario.objects.get(dni=dni)
        except Usuario.DoesNotExist:
            return None

    def _get_usuario_by_email(self, email: str) -> Usuario | None:
        """Sync: obtiene usuario por campo email."""
        try:
            return Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return None

    def _authenticate(self, username: str, password: str) -> Usuario | None:
        """
        Sync: autentica vía authenticate de Django.
        Retorna None si las credenciales son inválidas.
        """
        return authenticate(username=username, password=password)

    def _create_jwt_tokens(self, usuario: Usuario) -> tuple[str, str, timezone.datetime]:
        """
        Sync: crea tokens de acceso y refresh para el usuario.
        Retorna (access_token, refresh_token, expires_at).
        """
        refresh = RefreshToken.for_user(usuario)
        expires_at = timezone.now() + self._access_token_lifetime
        return str(refresh.access_token), str(refresh), expires_at

    # -------------------------------------------------------------------------
    # Wrappers asíncronos para uso por flujos
    # -------------------------------------------------------------------------

    async def buscar_usuario_por_username(self, username: str) -> Usuario | None:
        """Async: busca usuario por username."""
        return await sync_to_async(self._get_usuario_by_username)(username)

    async def buscar_usuario_por_dni(self, dni: str) -> Usuario | None:
        """Async: busca usuario por dni."""
        return await sync_to_async(self._get_usuario_by_dni)(dni)

    async def buscar_usuario_por_email(self, email: str) -> Usuario | None:
        """Async: busca usuario por email."""
        return await sync_to_async(self._get_usuario_by_email)(email)

    async def autenticar(self, username: str, password: str) -> Usuario | None:
        """Async: autentica usuario con username y password."""
        return await sync_to_async(self._authenticate)(username, password)

    async def crear_tokens(self, usuario: Usuario) -> tuple[str, str, timezone.datetime]:
        """
        Async: crea tokens JWT para usuario autenticado.
        Retorna (access_token, refresh_token, expires_at).
        """
        return await sync_to_async(self._create_jwt_tokens)(usuario)

    async def build_user_result(self, usuario: Usuario) -> AuthUserResult:
        """Async: construye DTO de resultado de usuario."""
        return await sync_to_async(self._build_user_result)(usuario)

    @property
    def _access_token_lifetime(self):
        """Obtiene ACCESS_TOKEN_LIFETIME de settings.NINJA_JWT."""
        from django.conf import settings
        return settings.NINJA_JWT["ACCESS_TOKEN_LIFETIME"]
