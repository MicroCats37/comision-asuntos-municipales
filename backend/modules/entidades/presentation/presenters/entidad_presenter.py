"""
EntidadPresenter — transforma resultados del dominio a esquemas HTTP.

薄 — solo transforma datos, sin lógica de negocio.
"""
from typing import Optional

from modules.entidades.domain.schemas import EntidadResult
from modules.entidades.domain.models import MunicipalidadDistrital, MunicipalidadProvincial
from modules.entidades.presentation.schemas.entidad_schemas import (
    EntidadOut,
    EntidadUpsertResponseOut,
    MunicipalidadesResponseOut,
    UbigeoDistritoOut,
    UbigeoProvinciaBasicOut,
    UbigeoDepartamentoOut,
    DistritosResponseOut,
    ProvinciaBasicOut,
    DistritoBasicOut,
)


class EntidadPresenter:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP.

    Patrón: Controller → Orchestrator → Presenter → HTTP Schema
    """

    @staticmethod
    def present_upsert(result: EntidadResult, creado: bool) -> EntidadUpsertResponseOut:
        """
        Transforma el resultado de upsert a esquema HTTP.

        Args:
            result: EntidadResult del orchestrator
            creado: True si se creó, False si se actualizó

        Returns:
            EntidadUpsertResponseOut schema para respuesta HTTP
        """
        return EntidadUpsertResponseOut(
            id=result.id,
            tipo_documento=result.tipo_documento,
            numero_documento=result.numero_documento,
            razon_social=result.razon_social,
            nombre_completo=result.nombre_completo,
            direccion=result.direccion,
            creado=creado,
        )

    @staticmethod
    def present_buscar(result: Optional[EntidadResult]) -> Optional[EntidadOut]:
        """
        Transforma el resultado de búsqueda a esquema HTTP.

        Args:
            result: EntidadResult si existe, None si no existe

        Returns:
            EntidadOut schema o None
        """
        if result is None:
            return None

        return EntidadOut(
            id=result.id,
            tipo_documento=result.tipo_documento,
            numero_documento=result.numero_documento,
            razon_social=result.razon_social,
            nombre_completo=result.nombre_completo,
            direccion=result.direccion,
        )

    @staticmethod
    def present_distritos(distritos) -> DistritosResponseOut:
        """
        Transforma lista de distritos del dominio a esquema HTTP.

        Args:
            distritos: Lista de UbigeoDistrito del ORM (ya materializada)

        Returns:
            DistritosResponseOut schema para respuesta HTTP
        """
        items = []
        for d in distritos:
            # Build from dict with pre-computed values (from orchestrator)
            if isinstance(d, dict):
                departamento = UbigeoDepartamentoOut(
                    id=d["departamento_id"],
                    nombre=d["departamento_nombre"],
                )
                provincia = UbigeoProvinciaBasicOut(
                    id=d["provincia_id"],
                    nombre=d["provincia_nombre"],
                )
                items.append(UbigeoDistritoOut(
                    id=d["distrito_id"],
                    nombre=d["distrito_nombre"],
                    ubigeo=d["ubigeo"],
                    provincia=provincia,
                    departamento=departamento,
                ))
            else:
                # Legacy ORM path — kept for callers not yet updated
                departamento = UbigeoDepartamentoOut(
                    id=d.provincia.departamento.id,
                    nombre=d.provincia.departamento.nombre,
                )
                provincia = UbigeoProvinciaBasicOut(
                    id=d.provincia.id,
                    nombre=d.provincia.nombre,
                )
                items.append(UbigeoDistritoOut(
                    id=d.id,
                    nombre=d.nombre,
                    ubigeo=d.ubigeo,
                    provincia=provincia,
                    departamento=departamento,
                ))

        return DistritosResponseOut(
            items=items,
            total=len(items),
        )

    @staticmethod
    def present_municipalidades(municipalidades) -> list[MunicipalidadesResponseOut]:
        """Transforma municipalidades del dominio a esquema HTTP para selector."""
        items = []
        for municipalidad in municipalidades:
            # Build from dict with pre-computed values (from orchestrator)
            if isinstance(municipalidad, dict):
                provincia_out = None
                if municipalidad.get("provincia_id"):
                    provincia_out = ProvinciaBasicOut(
                        id=municipalidad["provincia_id"],
                        nombre=municipalidad["provincia_nombre"],
                    )
                distrito_out = None
                if municipalidad.get("distrito_id"):
                    distrito_out = DistritoBasicOut(
                        id=municipalidad["distrito_id"],
                        nombre=municipalidad["distrito_nombre"],
                    )
                items.append(MunicipalidadesResponseOut(
                    id=municipalidad["id"],
                    nombre=municipalidad["nombre"],
                    codigo=municipalidad.get("codigo"),
                    provincia=provincia_out,
                    distrito=distrito_out,
                ))
            else:
                # Legacy ORM path — kept for callers not yet updated
                provincia_out = None
                if hasattr(municipalidad, 'provincia') and municipalidad.provincia:
                    provincia_out = ProvinciaBasicOut(
                        id=municipalidad.provincia.id,
                        nombre=municipalidad.provincia.nombre,
                    )
                distrito_out = None
                if hasattr(municipalidad, 'distrito') and municipalidad.distrito:
                    distrito_out = DistritoBasicOut(
                        id=municipalidad.distrito.id,
                        nombre=municipalidad.distrito.nombre,
                    )
                items.append(MunicipalidadesResponseOut(
                    id=municipalidad.id,
                    nombre=municipalidad.nombre,
                    codigo=municipalidad.codigo,
                    provincia=provincia_out,
                    distrito=distrito_out,
                ))

        return items
