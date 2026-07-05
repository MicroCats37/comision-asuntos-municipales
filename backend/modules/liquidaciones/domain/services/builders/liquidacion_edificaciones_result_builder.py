"""
Liquidaciones Edificaciones Result Builder — construye DTOs de resultado.

Este módulo construye DTOs de resultado planos (LiquidacionEdificacionesResult)
para liquidaciones de edificaciones. El resultado se mapea directamente a
LiquidacionEdificacionOut en el Presenter.

NOTE: Este builder recibe instancias ORM y produce domain DTOs/schemas.
Es un Domain Result Builder, no un HTTP Presenter. Accede a relaciones
ORM (select_related, prefetch_related) para construir las estructuras
tipadas de forma eficiente con bulk fetches.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modules.liquidaciones.models import LiquidacionGeneral, LiquidacionEdificacion


def generar_numero_liquidacion(numero_revision: int) -> str:
    """
    Genera el número de liquidación formateado desde el número de revisión.

    Args:
        numero_revision: Número de revisión (1, 2, 3, ...)

    Returns:
        String formateado como 'LIQ-EDIF-{numero_revision}'
    """
    return f"LIQ-EDIF-{numero_revision}"


class LiquidacionEdificacionesResultBuilder:
    """
    Builder stateless para construir DTOs de resultado de liquidaciones.

    Construye LiquidacionEdificacionesResult con estructura plana (Phase 2 refactor),
    mapeando directamente a los campos de LiquidacionEdificacionOut.
    """

    @staticmethod
    def build_proyectistas_data(proyectistas_orm_list: list) -> list:
        """
        Construye una lista de ProyectistaEdificacionData desde instancias ORM de Proyectista.

        Args:
            proyectistas_orm_list: Lista de instancias de Proyectista (ORM) con
                relaciones preloadadas: perfil_ingeniero y especialidad.

        Returns:
            Lista de ProyectistaEdificacionData
        """
        from modules.liquidaciones.domain.schemas import ProyectistaEdificacionData

        result = []
        for p in proyectistas_orm_list:
            perfil = p.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = (
                f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} "
                f"{getattr(perfil, 'apellido_materno', '') if perfil else ''}"
            ).strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            result.append(ProyectistaEdificacionData(
                id=p.id,
                perfil_ingeniero_id=p.perfil_ingeniero_id,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=p.especialidad_id,
                especialidad_nombre=p.especialidad.nombre if p.especialidad else None,
                descripcion=p.descripcion,
            ))
        return result

    @staticmethod
    def build_contactos_data(contactos_orm_list: list) -> list:
        """
        Construye una lista de ContactoData desde instancias ORM de LiquidacionContacto.

        Args:
            contactos_orm_list: Lista de instancias de LiquidacionContacto (ORM) con
                select_related de contacto ya preloadado.

        Returns:
            Lista de ContactoData
        """
        from modules.liquidaciones.domain.schemas import ContactoData

        result = []
        for lc in contactos_orm_list:
            contacto = lc.contacto
            result.append(ContactoData(
                id=contacto.id,
                nombres=getattr(contacto, 'nombres', None),
                apellidos=getattr(contacto, 'apellidos', None),
                dni=getattr(contacto, 'dni', None),
                cargo=getattr(contacto, 'cargo', None),
                telefono=getattr(contacto, 'telefono', None),
                celular=getattr(contacto, 'celular', None),
                email=getattr(contacto, 'email', None),
                direccion=getattr(contacto, 'direccion', None),
                principal=lc.principal if hasattr(lc, 'principal') else False,
                descripcion=lc.descripcion if hasattr(lc, 'descripcion') else None,
            ))
        return result

    @staticmethod
    def build_result(
        liquidacion: "LiquidacionGeneral",
        proyecto,
        revision_results: list,
        subtotal: Decimal,
        igv_monto: Decimal,
        total_liquidacion: Decimal,
        total_a_pagar: Decimal,
        variables,
        cobra: bool,
        liq_edif: "LiquidacionEdificacion",
        edificaciones_proyectistas: list = None,
        edificaciones_delegados: list = None,
        contactos_orm: list = None,
        valor_proyecto: Decimal = None,
    ):
        """
        Construye LiquidacionEdificacionesResult plano (Phase 2).

        Args:
            liquidacion: Instancia de LiquidacionGeneral
            proyecto: Instancia de Proyecto
            revision_results: Lista de RevisionCalculoData del cálculo
            subtotal: Subtotal calculado
            igv_monto: Monto IGV calculado
            total_liquidacion: Total de liquidación
            total_a_pagar: Total a pagar
            variables: VariablesFinancierasResult con igv_valor y uit_valor
            cobra: Booleano indicando si la revisión cobra
            liq_edif: Instancia de LiquidacionEdificacion
            edificaciones_proyectistas: Lista pre-materializada de proyectistas (opcional).
            edificaciones_delegados: Lista pre-materializada de delegados (opcional).

        Returns:
            LiquidacionEdificacionesResult con campos planos
        """
        from modules.liquidaciones.domain.schemas import (
            LiquidacionEdificacionesResult,
            EspecialidadData,
            TarifaEdificacionData,
            EdificacionRevisionData,
            ProyectistaEdificacionData,
            DelegadoEdificacionData,
        )

        # ── Construir revisiones ───────────────────────────────────────────────────
        revisiones = []
        for rev in revision_results:
            if hasattr(rev, 'especialidades') and rev.especialidades:
                primera_esp = rev.especialidades[0]
                esp_id = primera_esp.id
                esp_nombre = primera_esp.nombre
            else:
                esp_id = getattr(rev, 'tarifa', None) and getattr(rev.tarifa, 'id', None)
                esp_nombre = getattr(rev, 'especialidad_nombre', None) or getattr(rev, 'especialidad', None) or ''
            revisiones.append(EdificacionRevisionData(
                id=rev.id,
                especialidad=EspecialidadData(
                    id=esp_id,
                    nombre=esp_nombre,
                ),
                tarifa=TarifaEdificacionData(
                    id=rev.tarifa.id,
                    derecho_minimo=rev.tarifa.derecho_minimo,
                    derecho_maximo=rev.tarifa.derecho_maximo,
                    porcentaje_minimo_uit=rev.tarifa.porcentaje_minimo_uit,
                ),
                porcentaje_liquidacion=Decimal('0'),
                habilitada=True,
            ))

        # ── Construir proyectistas ───────────────────────────────────────────────
        if edificaciones_proyectistas is None:
            from modules.liquidaciones.domain.models import LiquidacionProyectista
            _proyectistas_qs = LiquidacionProyectista.objects.filter(
                liquidacion_general=liq_edif.liquidacion
            ).select_related('proyectista__perfil_ingeniero', 'proyectista__especialidad')
            proyectistas_to_process = [lp.proyectista for lp in _proyectistas_qs]
        else:
            proyectistas_to_process = edificaciones_proyectistas

        proyectistas = []
        for p in proyectistas_to_process:
            perfil = p.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            proyectistas.append(ProyectistaEdificacionData(
                id=p.id,
                perfil_ingeniero_id=p.perfil_ingeniero_id,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=p.especialidad_id,
                especialidad_nombre=p.especialidad.nombre if p.especialidad else None,
                descripcion=p.descripcion,
            ))

        # ── Construir delegados ───────────────────────────────────────────────────
        if edificaciones_delegados is None:
            _delegados_qs = liq_edif.liquidacion.liquidacion_delegados.select_related(
                'delegado__perfil_ingeniero', 'delegado__especialidad'
            ).all()
            delegados_to_process = list(_delegados_qs)
        else:
            delegados_to_process = edificaciones_delegados

        delegados = []
        for item in delegados_to_process:
            d = getattr(item, 'delegado', item)
            perfil = d.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            delegados.append(DelegadoEdificacionData(
                id=d.id,
                perfil_ingeniero_id=d.perfil_ingeniero_id,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=d.especialidad_id,
                especialidad_nombre=d.especialidad.nombre if d.especialidad else None,
                tipo=d.tipo if hasattr(d, 'tipo') else None,
            ))

        # ── Construir contactos ──────────────────────────────────────────────────
        if contactos_orm is None:
            _contactos_qs = liquidacion.contactos.select_related('contacto').all()
            contactos_orm = list(_contactos_qs)
        contactos = LiquidacionEdificacionesResultBuilder.build_contactos_data(contactos_orm)

        # ── Obtener valor_proyecto desde LiquidacionPorcentajeObra ────────────────
        if valor_proyecto is None:
            valor_proyecto = Decimal('0')
            lpo = liquidacion.liquidacion_porcentaje_obra.first()
            if lpo:
                valor_proyecto = lpo.valor_proyecto

        # ── Construir resultado plano ────────────────────────────────────────────
        return LiquidacionEdificacionesResult(
            id=liquidacion.id,
            public_id=liquidacion.public_id or '',
            estado=liquidacion.estado,
            fecha_registro=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
            expediente=liquidacion.expediente or None,
            observacion=liquidacion.observacion,
            numero_revision=liquidacion.numero_revision,
            tipo_tramite=liq_edif.tipo_tramite,
            tramite_accion=liq_edif.tramite_accion,
            # Entidad (campos sueltos que el presenter combina en nested)
            entidad_id=uuid.UUID(str(proyecto.entidad.id)) if proyecto.entidad else None,
            entidad_tipo=proyecto.entidad_tipo_documento,
            entidad_nombre=proyecto.entidad_razon_social,
            entidad_ruc=proyecto.entidad_numero_documento,
            # Proyecto (campos sueltos)
            proyecto_id=proyecto.id,
            proyecto_public_id=proyecto.public_id or '',
            proyecto_nombre=proyecto.denominacion,
            proyecto_direccion=proyecto.direccion,
            # Municipalidad
            municipalidad_id=liquidacion.municipalidad.id,
            municipalidad_nombre=liquidacion.municipalidad.nombre,
            # Listas
            proyectistas=proyectistas,
            delegados=delegados,
            contactos=contactos,
            revisiones=revisiones,
            # Financieros (directos y como valores nested vía presenter)
            subtotal=subtotal,
            igv=igv_monto,
            total=total_liquidacion,
            total_a_pagar=total_a_pagar,
            # Variables financieras (para reference)
            igv_valor=variables.igv_valor,
            uit_valor=variables.uit_valor,
            valor_proyecto=valor_proyecto,
        )
