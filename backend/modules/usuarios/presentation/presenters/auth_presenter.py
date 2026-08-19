"""
AuthPresenter — transforma LoginTokenResult a esquema HTTP LoginTokenOut.
"""
from modules.usuarios.presentation.schemas.auth_schemas import LoginTokenOut, AuthUserOut


class AuthPresenter:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP.
    Desacopla el formateo de respuesta de los controladores.
    """

    @staticmethod
    def present_login(result) -> LoginTokenOut:
        """
        Transforma un LoginTokenResult a LoginTokenOut.

        Args:
            result: LoginTokenResult del servicio de dominio

        Returns:
            Esquema LoginTokenOut listo para respuesta HTTP
        """
        return LoginTokenOut(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_at=result.expires_at,
            user=AuthUserOut(
                id=result.user.id,
                username=result.user.username,
                dni=result.user.dni,
                email=result.user.email,
                nombres=result.user.nombres,
                apellidos=result.user.apellidos,
                is_staff=result.user.is_staff,
                is_superuser=result.user.is_superuser,
            ),
        )
