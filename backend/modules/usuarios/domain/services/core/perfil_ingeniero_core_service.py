"""
PerfilIngenieroCoreService — operaciones sync para perfil de ingeniero.

NO usa transaction.atomic() internamente — el llamador (flujo) provee la transacción si es necesaria.
"""
import logging
import time
from datetime import datetime
from typing import Optional

from django.utils import timezone
from ninja.errors import HttpError

from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero, Capitulo
from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData

logger = logging.getLogger(__name__)


class PerfilIngenieroCoreService:
    """
    Servicio core sync para operaciones de PerfilIngeniero.
    """

    def _normalizar_cip(self, cip: str) -> str:
        """Normaliza CIP a 6 dígitos con ceros iniciales."""
        if not cip:
            return ""
        cip = str(cip).strip().replace('-', '').replace(' ', '')
        if not cip.isdigit():
            return ""
        return cip.zfill(6)[:6]

    def _obtener_perfil_por_cip(self, cip: str) -> Optional[PerfilIngeniero]:
        """Obtiene PerfilIngeniero por CIP."""
        normalized = self._normalizar_cip(cip)
        if not normalized:
            return None
        try:
            return PerfilIngeniero.objects.get(cip=normalized)
        except PerfilIngeniero.DoesNotExist:
            return None

    def obtener_o_crear_perfil_por_cip(self, cip: str) -> PerfilIngeniero:
        """
        Obtiene o crea un PerfilIngeniero por CIP normalizado.

        Args:
            cip: Número de CIP (se normaliza a 6 dígitos)

        Returns:
            Instancia de PerfilIngeniero (existente o recién creada)

        Raises:
            HttpError (400): Si el CIP no puede normalizarse.
            NOTE: La validación de entrada pertenece idealmente al Orquestador/Flujo;
            aquí se mantiene por compatibilidad con los flujos existentes.
        """
        normalized = self._normalizar_cip(cip)
        if not normalized:
            raise HttpError(400, f"CIP inválido: {cip}")
        perfil, _ = PerfilIngeniero.objects.get_or_create(cip=normalized)
        return perfil

    def _obtener_o_crear_especialidad(
        self,
        codigo_especialidad: Optional[str],
        capitulo: Optional[Capitulo],
    ) -> Optional["EspecialidadIngeniero"]:
        """
        Obtiene o crea una EspecialidadIngeniero desde código + capítulo.

        Args:
            codigo_especialidad: Código de especialidad del CIP (e.g., "01", "03")
            capitulo: Instancia de Capitulo ya resuelta (from _obtener_o_crear_capitulo)

        Returns:
            Instancia de EspecialidadIngeniero o None si no hay datos
        """
        if not codigo_especialidad or not capitulo:
            return None

        from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadIngeniero

        try:
            especialidad, _ = EspecialidadIngeniero.objects.get_or_create(
                codigo=codigo_especialidad,
                capitulo=capitulo,
                defaults={"nombre": f"Especialidad {codigo_especialidad}"},
            )
            return especialidad
        except Exception:
            return None

    def _obtener_o_crear_capitulo(self, capitulo_data: dict) -> Optional[Capitulo]:
        """
        Obtiene o crea un Capítulo desde datos del endpoint CIP.

        Args:
            capitulo_data: Dict con campos 'id' (codCapitulo), 'descripcion', 'abreviatura', 'grupoEnviosInst'

        Returns:
            Instancia de Capitulo o None si no hay datos
        """
        if not capitulo_data:
            return None

        registro_id = capitulo_data.get('id') or capitulo_data.get('codCapitulo')
        if not registro_id:
            return None

        capitulo, created = Capitulo.objects.update_or_create(
            registro_id=registro_id,
            defaults={
                'nombre': capitulo_data.get('descripcion') or f'Capítulo {registro_id}',
                'abreviacion': capitulo_data.get('abreviatura') or f'CAP{registro_id}',
                'grupo_envio_intitucional': capitulo_data.get('grupoEnviosInst') or None,
            }
        )
        return capitulo

    def _map_cip_data_to_perfil_fields(
        self,
        cip_data: CipColegiadoData,
    ) -> dict:
        """
        Mapea datos del endpoint CIP a campos de PerfilIngeniero.

        Args:
            cip_data: DTO con datos crudos del CIP

        Returns:
            Dict con campos para crear/actualizar PerfilIngeniero
        """
        # Construir nombre completo
        nombres = cip_data.nombres_completo

        # Obtener o crear capítulo (needed for especialidad FK resolution)
        capitulo = None
        if cip_data.capitulo:
            capitulo = self._obtener_o_crear_capitulo(cip_data.capitulo.model_dump())

        # Resolver especialidad FK: necesita (codigo, capitulo) para unique constraint
        especialidad = self._obtener_o_crear_especialidad(
            cip_data.codEspecialidad, capitulo
        )

        # Parse fecha_nacimiento from "YYYY-MM-DD" string to date
        fecha_nacimiento = None
        if cip_data.fechaNacimiento:
            try:
                fecha_nacimiento = datetime.strptime(
                    cip_data.fechaNacimiento, "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                pass

        return {
            'dni': cip_data.dni,
            'nombres': nombres,
            'apellido_paterno': cip_data.paterno,
            'apellido_materno': cip_data.materno,
            'fecha_nacimiento': fecha_nacimiento,
            'genero': cip_data.codGenero,
            'correo_personal': cip_data.correoPers,
            'correo_institucional': cip_data.correoInst,
            'direccion': cip_data.direccion,
            'ubigeo': cip_data.distritoId,
            'celular': cip_data.celular,
            'especialidad': especialidad,
            'capitulo': capitulo,
        }

    def _upsert_perfil_from_cip(
        self,
        cip: str,
        cip_data: CipColegiadoData,
    ) -> tuple[PerfilIngeniero, bool]:
        """
        Obtiene o crea/actualiza un PerfilIngeniero con datos del CIP.

        Args:
            cip: Número de CIP normalizado
            cip_data: DTO con datos del endpoint CIP

        Returns:
            Tuple (perfil, created_or_updated) donde created_or_updated es True si fue creado,
            False si fue actualizado
        """
        normalized_cip = self._normalizar_cip(cip)
        if not normalized_cip:
            raise HttpError(400, f"CIP inválido: {cip}")

        fields = self._map_cip_data_to_perfil_fields(cip_data)

        try:
            perfil = PerfilIngeniero.objects.get(cip=normalized_cip)
            # Actualizar campos existentes
            for field, value in fields.items():
                setattr(perfil, field, value)
            perfil.save()
            return perfil, False
        except PerfilIngeniero.DoesNotExist:
            # Crear nuevo
            fields['cip'] = normalized_cip
            perfil = PerfilIngeniero.objects.create(**fields)
            return perfil, True

    def _es_habilitado(self, cip: str) -> bool:
        """
        Verifica si un ingeniero está habilitado según sus campos CIP locales.

        NOTE: Esto usa el último estado conocido, NO valida en vivo.
        Para validación en vivo usar el flujo correspondiente.
        """
        perfil = self._obtener_perfil_por_cip(cip)
        if not perfil:
            return False
        return perfil.habilitado_cip and perfil.condicion_cip == "1"

    def hydrate_perfil_from_cip(
        self,
        cip: str,
        dry_run: bool = False,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> tuple[PerfilIngeniero | None, str]:
        """
        Get or create a PerfilIngeniero by normalized CIP, hydrating from CIP endpoint.

        This is the canonical reusable sync method for CIP-based profile hydration in
        legacy import flows. It reuses existing profiles when found locally, calls
        the CIP endpoint only when no local profile exists, and returns clear statuses
        so callers can skip downstream operations when CIP data is unavailable.

        Args:
            cip: Integer or string CIP number.
            dry_run: If True, do not write to DB; report what would happen.
            max_retries: Number of retry attempts on CIP service failure.
            base_delay: Base delay in seconds for exponential backoff.

        Returns:
            (perfil, status) where status is one of:
                "YA_EXISTE"          - found existing local profile, reused as-is
                "CREADO_DESDE_CIP"   - created new profile from CIP endpoint data
                "ACTUALIZADO_DESDE_CIP" - updated existing profile from CIP endpoint data
                "SIN_COLEGIADO"      - CIP endpoint returned no data (404 or null)
                "ERROR_CIP"          - CIP service unavailable after retries
                "ERROR"              - unexpected failure (invalid data, DB error, etc.)
        """
        normalized = self._normalizar_cip(str(cip))
        if not normalized:
            return None, "ERROR"

        # Step 1: Check local profile first — always reuse if present
        existing = self._obtener_perfil_por_cip(normalized)
        if existing is not None:
            return existing, "YA_EXISTE"

        # Step 2: No local profile — call CIP endpoint with retry
        # Import here to avoid circular imports at module load time
        from modules.usuarios.infrastructure.services import (
            CipServiceUnavailableError,
            get_cip_client,
        )

        cip_data_raw = None
        for attempt in range(max_retries):
            try:
                client = get_cip_client()
                cip_data_raw = client.get_colegiado(normalized)
                break
            except CipServiceUnavailableError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "CIP service unavailable for CIP %s (attempt %d/%d): %s. "
                        "Retrying in %.1fs...",
                        normalized, attempt + 1, max_retries, e, delay
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "CIP service unavailable for CIP %s after %d attempts: %s",
                        normalized, max_retries, e
                    )
                    return None, "ERROR_CIP"

        # Step 3: No data from endpoint
        if cip_data_raw is None:
            logger.info("CIP %s not found in CIP service (SIN_COLEGIADO)", normalized)
            return None, "SIN_COLEGIADO"

        # Step 4: Validate essential identity fields are present
        # The endpoint response always includes complete identity; if key fields are
        # empty/absent, treat as error rather than creating a blank profile.
        if not cip_data_raw.get("dni"):
            logger.warning(
                "CIP %s endpoint response missing dni — proceeding without DNI (SIN_DNI)", normalized
            )
            # Continue without DNI — profile can be created with dni=null for foreign engineers

        nombres = cip_data_raw.get("nombre1", "") or ""
        paterno = cip_data_raw.get("paterno", "") or ""
        materno = cip_data_raw.get("materno", "") or ""
        if not paterno and not materno and not nombres:
            logger.warning(
                "CIP %s endpoint response has no identity fields (paterno/materno/nombre1) "
                "— treating as ERROR", normalized
            )
            return None, "ERROR"

        # Step 5: Map to CipColegiadoData and upsert
        try:
            cip_data = CipColegiadoData(**cip_data_raw)
        except Exception as e:
            logger.warning(
                "CIP %s failed to parse CipColegiadoData: %s — treating as ERROR",
                normalized, e
            )
            return None, "ERROR"

        if dry_run:
            # In dry-run, just report what would be created
            return None, "CREADO_DESDE_CIP"

        try:
            perfil, created = self._upsert_perfil_from_cip(normalized, cip_data)
            return perfil, "CREADO_DESDE_CIP" if created else "ACTUALIZADO_DESDE_CIP"
        except Exception as e:
            logger.error("Failed to upsert profile for CIP %s: %s", normalized, e)
            return None, "ERROR"
