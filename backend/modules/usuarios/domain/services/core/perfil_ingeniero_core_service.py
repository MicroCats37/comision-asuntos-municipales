"""
PerfilIngenieroCoreService — operaciones sync para perfil de ingeniero.

NO usa transaction.atomic() internamente — el llamador (flujo) provee la transacción si es necesaria.
"""
from datetime import datetime
from typing import Optional

from django.utils import timezone
from ninja.errors import HttpError

from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero, Capitulo
from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData


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

        # Obtener o crear capítulo
        capitulo = None
        if cip_data.capitulo:
            capitulo = self._obtener_o_crear_capitulo(cip_data.capitulo.model_dump())

        return {
            'dni': cip_data.dni,
            'nombres': nombres,
            'apellido_paterno': cip_data.paterno,
            'apellido_materno': cip_data.materno,
            'fecha_nacimiento': cip_data.fechaNacimiento,  # Ya viene como date desde from_cip_data
            'genero': cip_data.codGenero,
            'correo_personal': cip_data.correoPers,
            'correo_institucional': cip_data.correoInst,
            'direccion': cip_data.direccion,
            'ubigeo': cip_data.distritoId,
            'codigo_especialidad': cip_data.codEspecialidad,
            'capitulo': capitulo,
            # Campos de habilitación CIP
            'habilitado_cip': cip_data.habilitado,
            'condicion_cip': cip_data.condicion,
            'fecha_validacion_cip': timezone.now(),
            'ultimo_periodo_pagado_cip': cip_data.ultimoPeriodoPagado,
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
