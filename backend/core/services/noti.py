import abc
import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseNotiService(abc.ABC):
    """
    Interfaz abstracta para el servicio de notificaciones.
    Permite la inyección de dependencias y el uso de mocks en tests.
    """
    @abc.abstractmethod
    async def send_email(
        self, 
        to: list[str], 
        subject: str, 
        content: str, 
        is_html: bool = True
    ) -> bool:
        pass

    @abc.abstractmethod
    async def send_sms(self, destinations: list[str], content: str) -> bool:
        pass


class HttpxNotiService(BaseNotiService):
    """
    Implementación real que consume el microservicio NOTI de forma asíncrona.
    """
    async def send_email(
        self, 
        to: list[str], 
        subject: str, 
        content: str, 
        is_html: bool = True
    ) -> bool:
        noti_url = getattr(settings, "NOTI_URL", None)
        noti_app_id = getattr(settings, "NOTI_APP_ID", None)

        if not noti_url:
            logger.warning("[NOTI] URL de NOTI no configurada. Saltando envío de Email.")
            return False

        url = f"{noti_url.rstrip('/')}/sender/send-email"
        payload = {
            "notificanteId": noti_app_id,
            "to": to,
            "cc": [],
            "bcc": [],
            "asunto": subject,
            "contenido": content,
            "html": is_html,
            "usuarioCreacion": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info(f"[NOTI] Correo enviado exitosamente a {to}")
                    return True
                logger.error(f"[NOTI] Error enviando correo: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.exception(f"[NOTI] Excepción al enviar correo: {e}")
            return False

    async def send_sms(self, destinations: list[str], content: str) -> bool:
        noti_url = getattr(settings, "NOTI_URL", None)
        noti_app_id = getattr(settings, "NOTI_APP_ID", None)

        if not noti_url:
            logger.warning("[NOTI] URL de NOTI no configurada. Saltando envío de SMS.")
            return False

        url = f"{noti_url.rstrip('/')}/sender/send-sms"
        clean_destinations = [str(d).strip() for d in destinations if d]

        if not clean_destinations:
            return False

        payload = {
            "notificanteId": noti_app_id,
            "destino": clean_destinations,
            "contenido": content,
            "flash": False,
            "usuarioCreacion": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info(f"[NOTI] SMS enviado exitosamente a {clean_destinations}")
                    return True
                return False
        except Exception as e:
            logger.exception(f"[NOTI] Excepción al enviar SMS: {e}")
            return False


class MockNotiService(BaseNotiService):
    """
    Emulador de NOTI para desarrollo local y testing.
    Evita llamadas HTTP externas y loguea la intención en consola.
    """
    async def send_email(self, to: list[str], subject: str, content: str, is_html: bool = True) -> bool:
        logger.info(f"🚀 [MOCK-NOTI] Email -> To: {to} | Subject: {subject}")
        # En desarrollo podríamos imprimir el contenido si es necesario
        return True

    async def send_sms(self, destinations: list[str], content: str) -> bool:
        logger.info(f"📱 [MOCK-NOTI] SMS -> To: {destinations} | Msg: {content}")
        return True
