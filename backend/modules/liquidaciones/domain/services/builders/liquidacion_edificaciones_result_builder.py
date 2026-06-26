"""
Liquidaciones Edificaciones Result Builder — construye DTOs de resultado.

Este módulo contiene la lógica de construcción de resultados (snapshots, results,
fallback results) que antes vivía en el flujo. El flujo delega la construcción
de DTOs a este builder, manteniendo su responsabilidad en la coordinación de
pasos del caso de uso (validación, transacciones, llamadas core).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.liquidaciones.models import LiquidacionGeneral, LiquidacionEdificaciones


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

    Agrupa métodos de construcción de estructuras anidadas tipadas que antes
    vivían en el flujo. Al estar separados, el flujo solo coordina pasos de
    negocio y delega la construcción de DTOs a este builder.

    NOTE: Este builder recibe instancias ORM y produce domain DTOs/schemas.
    Es un Domain Result Builder, no un HTTP Presenter. Accede a relaciones
    ORM (select_related, prefetch_related) para construir las estructuras
    tipadas de forma eficiente con bulk fetches.
    """

    @staticmethod
    def build_proyectistas_snapshot_data(proyectistas_orm_list: list) -> list:
        """
        Construye una lista de ProyectistaSnapshotData desde instancias ORM de Proyectista.

        Este método recibe instancias ORM del modelo Proyectista (con relaciones
        select_related de perfil_ingeniero y especialidad ya cargadas) y produce
        una lista del schema ProyectistaSnapshotData para uso en el dominio.

        Args:
            proyectistas_orm_list: Lista de instancias de Proyectista (ORM) con
                relaciones preloadadas: perfil_ingeniero y especialidad.

        Returns:
            Lista de ProyectistaSnapshotData
        """
        from modules.liquidaciones.domain.schemas import ProyectistaSnapshotData

        result = []
        for p in proyectistas_orm_list:
            perfil = p.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = (
                f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} "
                f"{getattr(perfil, 'apellido_materno', '') if perfil else ''}"
            ).strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            result.append(ProyectistaSnapshotData(
                id=str(p.id),
                perfil_ingeniero_id=str(p.perfil_ingeniero_id) if p.perfil_ingeniero_id else None,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=str(p.especialidad_id) if p.especialidad_id else None,
                especialidad_nombre=p.especialidad.nombre if p.especialidad else None,
                descripcion=p.descripcion,
            ))
        return result

    @staticmethod
    def build_snapshot_data(
        liquidacion: "LiquidacionGeneral",
        proyecto,
        revision_results: list,
        subtotal: Decimal,
        igv_monto: Decimal,
        total_liquidacion: Decimal,
        total_a_pagar: Decimal,
        variables,
        cobra: bool,
        liq_edif: "LiquidacionEdificaciones",
    ):
        """
        Construye el schema tipado del snapshot según la estructura del contexto.

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
            liq_edif: Instancia de LiquidacionEdificaciones

        Returns:
            LiquidacionSnapshotResult
        """
        from modules.liquidaciones.domain.schemas import (
            LiquidacionSnapshotResult,
            LiquidacionSnapshotData,
            ProyectoSnapshotData,
            EntidadSnapshotData,
            DistritoBasicSnapshotData,
            ProvinciaBasicSnapshotData,
            MunicipalidadesSnapshotData,
            EdificacionesSnapshotData,
            ProyectistaSnapshotData,
            DelegadoSnapshotData,
            RevisionSnapshotData,
            TarifaSnapshotData,
            TotalesSnapshotData,
            MetadataSnapshotData,
        )

        # Build nested sections with typed Pydantic models
        entidad_data = None
        if proyecto.entidad:
            entidad_data = EntidadSnapshotData(
                id=str(proyecto.entidad.id),
                tipo=proyecto.entidad.tipo_documento,
                nombre=proyecto.entidad.razon_social,
                ruc=proyecto.entidad.numero_documento,
            )

        # Build distrito nested object for proyecto
        distrito_data = None
        if proyecto.distrito:
            provincia_prov = None
            if proyecto.distrito.provincia:
                provincia_prov = ProvinciaBasicSnapshotData(
                    id=str(proyecto.distrito.provincia.id),
                    nombre=proyecto.distrito.provincia.nombre,
                )
            distrito_data = DistritoBasicSnapshotData(
                id=str(proyecto.distrito.id),
                nombre=proyecto.distrito.nombre,
                provincia=provincia_prov,
            )

        proyecto_data = ProyectoSnapshotData(
            id=str(proyecto.id),
            public_id=str(proyecto.public_id) if proyecto.public_id else '',
            nombre=proyecto.denominacion,
            direccion=proyecto.direccion or '',
            valor_proyecto=float(liquidacion.valor_proyecto),
            entidad=entidad_data,
            distrito=distrito_data,
        )

        # Build municipalidad nested object
        provincia_muni = None
        distrito_muni = None
        if liquidacion.municipalidad:
            if liquidacion.municipalidad.provincia:
                provincia_muni = ProvinciaBasicSnapshotData(
                    id=str(liquidacion.municipalidad.provincia.id),
                    nombre=liquidacion.municipalidad.provincia.nombre,
                )
            if liquidacion.municipalidad.distrito:
                provincia_del_distrito = None
                if liquidacion.municipalidad.distrito.provincia:
                    provincia_del_distrito = ProvinciaBasicSnapshotData(
                        id=str(liquidacion.municipalidad.distrito.provincia.id),
                        nombre=liquidacion.municipalidad.distrito.provincia.nombre,
                    )
                distrito_muni = DistritoBasicSnapshotData(
                    id=str(liquidacion.municipalidad.distrito.id),
                    nombre=liquidacion.municipalidad.distrito.nombre,
                    provincia=provincia_del_distrito,
                )
        municipalidad_data = MunicipalidadesSnapshotData(
            id=str(liquidacion.municipalidad.id) if liquidacion.municipalidad else uuid.UUID(int=0),
            nombre=liquidacion.municipalidad.nombre if liquidacion.municipalidad else '',
            codigo=liquidacion.municipalidad.codigo if liquidacion.municipalidad else None,
            provincia=provincia_muni,
            distrito=distrito_muni,
        )

        liquidacion_data = LiquidacionSnapshotData(
            id=str(liquidacion.id),
            public_id=liquidacion.public_id or '',
            numero_liquidacion=generar_numero_liquidacion(liq_edif.numero_revision),
            estado=liquidacion.estado,
            fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
            proyecto=proyecto_data,
            municipalidad=municipalidad_data,
            expediente=liquidacion.expediente or None,
            observacion=liquidacion.observacion or '',
        )

        # Build revisiones from typed RevisionCalculoData
        revisiones_data = []
        for rev in revision_results:
            revisiones_data.append(RevisionSnapshotData(
                id=str(rev.id),
                especialidad=rev.especialidad,
                tarifa=TarifaSnapshotData(
                    id=str(rev.tarifa.id),
                    derecho_minimo=str(rev.tarifa.derecho_minimo),
                    derecho_maximo=str(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                    porcentaje_minimo_uit=str(rev.tarifa.porcentaje_minimo_uit),
                ),
                monto_base=float(rev.monto_base),
                cobra=rev.cobra,
                derecho=float(rev.derecho),
            ))

        # Construir proyectistas desde LiquidacionEdificaciones
        _proyectistas_qs = liq_edif.proyectistas.select_related('perfil_ingeniero', 'especialidad').all()
        proyectistas_data = []
        for p in _proyectistas_qs:
            perfil = p.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            proyectistas_data.append(ProyectistaSnapshotData(
                id=str(p.id),
                perfil_ingeniero_id=str(p.perfil_ingeniero_id) if p.perfil_ingeniero_id else None,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=str(p.especialidad_id) if p.especialidad_id else None,
                especialidad_nombre=p.especialidad.nombre if p.especialidad else None,
                descripcion=p.descripcion,
            ))

        # Construir delegados desde LiquidacionDelegado
        _delegados_qs = liq_edif.liquidacion.liquidacion_delegados.select_related(
            'delegado__perfil_ingeniero', 'delegado__especialidad'
        ).all()
        delegados_data = []
        for liquidacion_delegado in _delegados_qs:
            d = liquidacion_delegado.delegado
            perfil = d.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            delegados_data.append(DelegadoSnapshotData(
                id=str(d.id),
                perfil_ingeniero_id=str(d.perfil_ingeniero_id) if d.perfil_ingeniero_id else None,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=str(d.especialidad_id) if d.especialidad_id else None,
                especialidad_nombre=d.especialidad.nombre if d.especialidad else None,
                tipo=d.tipo if hasattr(d, 'tipo') else None,
            ))

        edificaciones_data = EdificacionesSnapshotData(
            public_id=liq_edif.public_id or '',
            numero_revision=liq_edif.numero_revision,
            tipo_tramite=liq_edif.tipo_tramite,
            tramite_accion=liq_edif.tramite_accion,
            proyectistas=proyectistas_data,
            delegados=delegados_data,
            revisiones=revisiones_data,
        )

        totales_data = TotalesSnapshotData(
            subtotal=float(subtotal),
            sub_total=float(subtotal),
            igv=float(igv_monto),
            total=float(total_liquidacion),
            liquidacion_total=float(total_liquidacion),
            total_a_pagar=float(total_a_pagar),
        )

        metadata_data = MetadataSnapshotData(
            igv_valor=float(variables.igv_valor),
            uit_valor=float(variables.uit_valor),
            cobra=cobra,
        )

        return LiquidacionSnapshotResult(
            liquidacion=liquidacion_data,
            edificaciones=edificaciones_data,
            totales=totales_data,
            _metadata=metadata_data,
        )

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
        liq_edif: "LiquidacionEdificaciones",
        edificaciones_proyectistas: list = None,
        edificaciones_delegados: list = None,
    ):
        """
        Construye LiquidacionEdificacionesResult desde datos de creación.

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
            liq_edif: Instancia de LiquidacionEdificaciones
            edificaciones_proyectistas: Lista pre-materializada de proyectistas (opcional,
                para evitar acceso ORM en contexto async). Si no se provee, se consulta directamente.
            edificaciones_delegados: Lista pre-materializada de delegados (opcional,
                para evitar acceso ORM en contexto async). Si no se provee, se consulta directamente.

        Returns:
            LiquidacionEdificacionesResult
        """
        from modules.liquidaciones.domain.schemas import (
            LiquidacionEdificacionesResult,
            EspecialidadData,
            TarifaEdificacionData,
            EdificacionRevisionData,
            ProyectistaSnapshotData,
            DelegadoSnapshotData,
        )

        edificaciones_revisiones = []
        for rev in revision_results:
            edificaciones_revisiones.append(EdificacionRevisionData(
                id=str(rev.id),
                especialidad=EspecialidadData(
                    id=str(rev.tarifa.id),
                    nombre=rev.especialidad,
                ),
                tarifa=TarifaEdificacionData(
                    id=str(rev.tarifa.id),
                    derecho_minimo=rev.tarifa.derecho_minimo,
                    derecho_maximo=rev.tarifa.derecho_maximo,
                    porcentaje_minimo_uit=rev.tarifa.porcentaje_minimo_uit,
                ),
                porcentaje_liquidacion=Decimal('0'),
                habilitada=True,
            ))

        # Construir proyectistas desde la lista pre-materializada o desde el QuerySet
        if edificaciones_proyectistas is None:
            _proyectistas_qs = liq_edif.proyectistas.select_related('perfil_ingeniero', 'especialidad').all()
            proyectistas_to_process = list(_proyectistas_qs)
        else:
            proyectistas_to_process = edificaciones_proyectistas

        edificaciones_proyectistas = []
        for p in proyectistas_to_process:
            perfil = p.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            edificaciones_proyectistas.append(ProyectistaSnapshotData(
                id=str(p.id),
                perfil_ingeniero_id=str(p.perfil_ingeniero_id) if p.perfil_ingeniero_id else None,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=str(p.especialidad_id) if p.especialidad_id else None,
                especialidad_nombre=p.especialidad.nombre if p.especialidad else None,
                descripcion=p.descripcion,
            ))

        # Construir delegados desde la lista pre-materializada o desde el QuerySet
        if edificaciones_delegados is None:
            _delegados_qs = liq_edif.liquidacion.liquidacion_delegados.select_related(
                'delegado__perfil_ingeniero', 'delegado__especialidad'
            ).all()
            delegados_to_process = list(_delegados_qs)
        else:
            delegados_to_process = edificaciones_delegados

        edificaciones_delegados_result = []
        for item in delegados_to_process:
            d = getattr(item, 'delegado', item)
            perfil = d.perfil_ingeniero
            perfil_ingeniero_nombres = getattr(perfil, 'nombres', None) if perfil else None
            perfil_ingeniero_apellidos = f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None
            perfil_ingeniero_cip = getattr(perfil, 'cip', None) if perfil else None
            edificaciones_delegados_result.append(DelegadoSnapshotData(
                id=str(d.id),
                perfil_ingeniero_id=str(d.perfil_ingeniero_id) if d.perfil_ingeniero_id else None,
                perfil_ingeniero_nombres=perfil_ingeniero_nombres,
                perfil_ingeniero_apellidos=perfil_ingeniero_apellidos,
                perfil_ingeniero_cip=perfil_ingeniero_cip,
                especialidad_id=str(d.especialidad_id) if d.especialidad_id else None,
                especialidad_nombre=d.especialidad.nombre if d.especialidad else None,
                tipo=d.tipo if hasattr(d, 'tipo') else None,
            ))

        return LiquidacionEdificacionesResult(
            liquidacion_id=str(liquidacion.id),
            liquidacion_public_id=liquidacion.public_id or '',
            numero_revision=liq_edif.numero_revision,
            estado=liquidacion.estado,
            fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
            proyecto_id=str(proyecto.id),
            proyecto_public_id=proyecto.public_id or '',
            proyecto_nombre=proyecto.denominacion,
            proyecto_direccion=proyecto.direccion,
            proyecto_entidad_id=str(proyecto.entidad.id) if proyecto.entidad else None,
            proyecto_entidad_tipo=proyecto.entidad.tipo_documento if proyecto.entidad else None,
            proyecto_entidad_nombre=proyecto.entidad.nombre_completo if proyecto.entidad else None,
            proyecto_entidad_ruc=proyecto.entidad.numero_documento if proyecto.entidad else None,
            municipalidad_id=str(liquidacion.municipalidad.id),
            municipalidad_nombre=liquidacion.municipalidad.nombre,
            expediente=liquidacion.expediente or None,
            edificaciones_proyectistas=edificaciones_proyectistas,
            edificaciones_delegados=edificaciones_delegados_result,
            edificaciones_public_id=liq_edif.public_id or '',
            edificaciones_tipo_tramite=liq_edif.tipo_tramite,
            edificaciones_tramite_accion=liq_edif.tramite_accion,
            observacion=liquidacion.observacion,
            edificaciones_revisiones=edificaciones_revisiones,
            igv_valor=variables.igv_valor,
            uit_valor=variables.uit_valor,
            valor_proyecto=liquidacion.valor_proyecto,
            totales_subtotal=subtotal,
            totales_igv=igv_monto,
            totales_total_liquidacion=total_liquidacion,
            totales_total_a_pagar=total_a_pagar,
        )

    @staticmethod
    def build_result_from_liquidacion(liquidacion: "LiquidacionGeneral"):
        """
        Construye resultado básico desde liquidación sin snapshot.

        Args:
            liquidacion: Instancia de LiquidacionGeneral

        Returns:
            LiquidacionSnapshotFallbackResult
        """
        from modules.liquidaciones.domain.schemas import (
            LiquidacionSnapshotFallbackResult,
            LiquidacionFallbackData,
            ProyectoFallbackData,
            EdificacionesFallbackData,
            TotalesFallbackData,
            MunicipalidadesSnapshotData,
            ProvinciaBasicSnapshotData,
            DistritoBasicSnapshotData,
        )

        proyecto = liquidacion.proyecto
        liq_edif = liquidacion.edificaciones if hasattr(liquidacion, 'edificaciones') else None
        numero_revision = liq_edif.numero_revision if liq_edif else 0

        # Build municipalidad nested object
        provincia_muni = None
        distrito_muni = None
        if liquidacion.municipalidad:
            if liquidacion.municipalidad.provincia:
                provincia_muni = ProvinciaBasicSnapshotData(
                    id=str(liquidacion.municipalidad.provincia.id),
                    nombre=liquidacion.municipalidad.provincia.nombre,
                )
            if liquidacion.municipalidad.distrito:
                provincia_del_distrito = None
                if liquidacion.municipalidad.distrito.provincia:
                    provincia_del_distrito = ProvinciaBasicSnapshotData(
                        id=str(liquidacion.municipalidad.distrito.provincia.id),
                        nombre=liquidacion.municipalidad.distrito.provincia.nombre,
                    )
                distrito_muni = DistritoBasicSnapshotData(
                    id=str(liquidacion.municipalidad.distrito.id),
                    nombre=liquidacion.municipalidad.distrito.nombre,
                    provincia=provincia_del_distrito,
                )
        municipalidad_data = MunicipalidadesSnapshotData(
            id=str(liquidacion.municipalidad.id) if liquidacion.municipalidad else uuid.UUID(int=0),
            nombre=liquidacion.municipalidad.nombre if liquidacion.municipalidad else '',
            codigo=liquidacion.municipalidad.codigo if liquidacion.municipalidad else None,
            provincia=provincia_muni,
            distrito=distrito_muni,
        )

        return LiquidacionSnapshotFallbackResult(
            liquidacion=LiquidacionFallbackData(
                id=str(liquidacion.id),
                public_id=liquidacion.public_id or '',
                numero_liquidacion=generar_numero_liquidacion(numero_revision),
                estado=liquidacion.estado,
                fecha_creacion=liquidacion.created_at.isoformat() if liquidacion.created_at else '',
                proyecto=ProyectoFallbackData(
                    id=str(proyecto.id),
                    public_id=str(proyecto.public_id) if proyecto.public_id else '',
                    nombre=proyecto.denominacion,
                    direccion=proyecto.direccion or '',
                    valor_proyecto=float(liquidacion.valor_proyecto),
                ),
                municipalidad=municipalidad_data,
                expediente=liquidacion.expediente or None,
                observacion=liquidacion.observacion or '',
            ),
            edificaciones=EdificacionesFallbackData(
                public_id=liq_edif.public_id if liq_edif else "",
                numero_revision=numero_revision,
                tipo_tramite=liq_edif.tipo_tramite if liq_edif else "",
                tramite_accion=liq_edif.tramite_accion if liq_edif else "",
                revisiones=[],
            ),
            totales=TotalesFallbackData(
                subtotal=0.0,
                igv=0.0,
                total=0.0,
                liquidacion_total=0.0,
                total_a_pagar=0.0,
            ),
        )

    @staticmethod
    def build_snapshot_list_item(
        liquidacion_orm,
        edificacion_orm,
        snapshot_orm,
        proyectistas_orm_list: list,
    ) -> dict:
        """
        Construye un item de lista de snapshots con toda su estructura anidada.

        Este método recibe instancias ORM ya materializadas y con sus relaciones
        prefetched/selected (proyecto__entidad, proyecto__distrito__provincia,
        municipalidad__provincia, municipalidad__distrito__provincia,
        edificacion__revisiones__tarifa, edificacion__revisiones__especialidades,
        edificacion__proyectistas) y construye el dict anidado completo
        para el endpoint de lista de snapshots.

        El core service se encarga de la query y paginación, delegando la
        construcción del item de resultado a este builder.

        Args:
            liquidacion_orm: Instancia de LiquidacionGeneral con relaciones
                prefetched: proyecto__entidad, proyecto__distrito__provincia,
                municipalidad__provincia, municipalidad__distrito__provincia.
            edificacion_orm: Instancia de LiquidacionEdificaciones con relaciones
                prefetched: revisiones__tarifa, revisiones__especialidades, proyectistas.
            snapshot_orm: Instancia de LiquidacionSnapshot (puede ser None).
            proyectistas_orm_list: Lista de instancias de Proyectista (ORM) con
                relaciones preloadadas: perfil_ingeniero, especialidad.

        Returns:
            Dict con la estructura anidada del item de snapshot.
        """
        # Construir entidad anidada
        entidad_data = None
        proyecto = liquidacion_orm.proyecto
        if proyecto and proyecto.entidad:
            entidad_data = {
                'id': str(proyecto.entidad.id),
                'tipo': proyecto.entidad.tipo_documento,
                'nombre': proyecto.entidad.nombre_completo,
                'ruc': getattr(proyecto.entidad, 'numero_documento', None),
            }

        # Construir distrito nested para proyecto
        distrito_data = None
        if proyecto and proyecto.distrito:
            provincia_prov = None
            if proyecto.distrito.provincia:
                provincia_prov = {
                    'id': str(proyecto.distrito.provincia.id),
                    'nombre': proyecto.distrito.provincia.nombre,
                }
            distrito_data = {
                'id': str(proyecto.distrito.id),
                'nombre': proyecto.distrito.nombre,
                'provincia': provincia_prov,
            }

        # Construir proyecto_data
        proyecto_data = {
            'id': str(proyecto.id),
            'public_id': str(proyecto.public_id) if proyecto.public_id else '',
            'nombre': proyecto.denominacion,
            'direccion': proyecto.direccion,
            'valor_proyecto': float(liquidacion_orm.valor_proyecto),
            'entidad': entidad_data,
            'distrito': distrito_data,
        }

        # Construir proyectistas_data usando el builder helper
        proyectistas_data = LiquidacionEdificacionesResultBuilder.build_proyectistas_snapshot_data(
            proyectistas_orm_list
        )

        # Determinar numero_revision y numero_liquidacion desde snapshot o fallback ORM
        numero_revision = edificacion_orm.numero_revision if edificacion_orm else 0
        numero_liquidacion = None  # Se leerá del snapshot si está disponible

        # Construir revisions_data desde snapshot o fallback ORM
        revisiones_data = []
        if snapshot_orm and snapshot_orm.data:
            liquidacion_snapshot = snapshot_orm.data.get('liquidacion', {})
            numero_liquidacion = liquidacion_snapshot.get('numero_liquidacion')
            edificaciones_snapshot = snapshot_orm.data.get('edificaciones', {})
            numero_revision = edificaciones_snapshot.get('numero_revision', numero_revision)
            revisions_snapshot = edificaciones_snapshot.get('revisiones', [])
            if revisions_snapshot:
                revisiones_data = [{
                    'id': str(rev.get('id', '')),
                    'especialidad': rev.get('especialidad', ''),
                    'tarifa': rev.get('tarifa', {}),
                    'monto_base': float(rev.get('monto_base', 0)),
                    'cobra': rev.get('cobra', True),
                    'derecho': float(rev.get('derecho', 0)),
                } for rev in revisions_snapshot]
            # Tomar proyectistas del snapshot si existen
            if 'proyectistas' in edificaciones_snapshot:
                proyectistas_data = edificaciones_snapshot.get('proyectistas', [])
        elif edificacion_orm:
            # Fallback a ORM cuando no hay snapshot
            for rev in edificacion_orm.revisiones.all():
                especialidades = list(rev.especialidades.all())
                primera_esp = especialidades[0] if especialidades else None
                revisiones_data.append({
                    'id': str(rev.id),
                    'especialidad': primera_esp.nombre if primera_esp else '',
                    'tarifa': {
                        'id': str(rev.tarifa.id),
                        'derecho_minimo': float(rev.tarifa.derecho_minimo),
                        'derecho_maximo': float(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                        'porcentaje_minimo_uit': float(rev.tarifa.porcentaje_minimo_uit),
                    },
                    'monto_base': float(getattr(rev, 'monto_base', 0)),
                    'cobra': getattr(rev, 'cobra', True),
                    'derecho': float(getattr(rev, 'derecho', 0)),
                })

        # Construir totales_data desde snapshot JSON
        totales_data = {
            'subtotal': 0.0,
            'sub_total': 0.0,
            'igv': 0.0,
            'total': 0.0,
            'liquidacion_total': 0.0,
            'total_a_pagar': 0.0,
        }
        if snapshot_orm and snapshot_orm.data:
            snapshot_totales = snapshot_orm.data.get('totales', totales_data)
            # Ensure sub_total exists for backwards compat
            if 'sub_total' not in snapshot_totales and 'subtotal' in snapshot_totales:
                snapshot_totales['sub_total'] = snapshot_totales['subtotal']
            totales_data = snapshot_totales

        # Extraer datos de edificacion desde snapshot o fallback
        edificacion_public_id = ""
        edificacion_tipo_tramite = ""
        edificacion_tramite_accion = ""
        if snapshot_orm and snapshot_orm.data:
            edificaciones_snapshot = snapshot_orm.data.get('edificaciones', {})
            edificacion_public_id = edificaciones_snapshot.get('public_id', '')
            edificacion_tipo_tramite = edificaciones_snapshot.get('tipo_tramite', '')
            edificacion_tramite_accion = edificaciones_snapshot.get('tramite_accion', '')
        if not edificacion_public_id and edificacion_orm:
            edificacion_public_id = edificacion_orm.public_id or ''
        if not edificacion_tipo_tramite and edificacion_orm:
            edificacion_tipo_tramite = edificacion_orm.tipo_tramite or ''
        if not edificacion_tramite_accion and edificacion_orm:
            edificacion_tramite_accion = edificacion_orm.tramite_accion or ''

        edificaciones_data = {
            'public_id': edificacion_public_id,
            'numero_revision': numero_revision,
            'tipo_tramite': edificacion_tipo_tramite,
            'tramite_accion': edificacion_tramite_accion,
            'proyectistas': proyectistas_data,
            'delegados': [],  # TODO: Implementar cuando se agregue soporte para delegados en snapshot list
            'revisiones': revisiones_data,
        }

        # Extraer liquidacion y municipalidad desde snapshot o fallback
        liquidacion_public_id = ""
        municipalidad_data = {
            'id': None,
            'nombre': '',
            'codigo': None,
            'provincia': None,
            'distrito': None,
        }
        if snapshot_orm and snapshot_orm.data:
            liquidacion_snapshot = snapshot_orm.data.get('liquidacion', {})
            liquidacion_public_id = liquidacion_snapshot.get('public_id', '')
            muni_snapshot = liquidacion_snapshot.get('municipalidad', {})
            if muni_snapshot:
                municipalidad_data = muni_snapshot
            elif liquidacion_snapshot.get('municipalidad_id'):
                municipalidad_data = {
                    'id': liquidacion_snapshot.get('municipalidad_id'),
                    'nombre': liquidacion_snapshot.get('municipalidad_nombre', ''),
                    'codigo': None,
                    'provincia': None,
                    'distrito': None,
                }
        if not liquidacion_public_id:
            liquidacion_public_id = liquidacion_orm.public_id or ''
        # Si no tenemos municipalidad del snapshot, construir desde ORM
        if not municipalidad_data.get('id') and liquidacion_orm.municipalidad:
            provincia_muni = None
            distrito_muni = None
            if liquidacion_orm.municipalidad.provincia:
                provincia_muni = {
                    'id': str(liquidacion_orm.municipalidad.provincia.id),
                    'nombre': liquidacion_orm.municipalidad.provincia.nombre,
                }
            if liquidacion_orm.municipalidad.distrito:
                provincia_del_distrito = None
                if liquidacion_orm.municipalidad.distrito.provincia:
                    provincia_del_distrito = {
                        'id': str(liquidacion_orm.municipalidad.distrito.provincia.id),
                        'nombre': liquidacion_orm.municipalidad.distrito.provincia.nombre,
                    }
                distrito_muni = {
                    'id': str(liquidacion_orm.municipalidad.distrito.id),
                    'nombre': liquidacion_orm.municipalidad.distrito.nombre,
                    'provincia': provincia_del_distrito,
                }
            municipalidad_data = {
                'id': str(liquidacion_orm.municipalidad.id),
                'nombre': liquidacion_orm.municipalidad.nombre,
                'codigo': liquidacion_orm.municipalidad.codigo,
                'provincia': provincia_muni,
                'distrito': distrito_muni,
            }

        # Usar numero_liquidacion del snapshot si está disponible, si no calcular desde numero_revision
        if numero_liquidacion is None:
            numero_liquidacion = generar_numero_liquidacion(numero_revision)

        return {
            'liquidacion_id': str(liquidacion_orm.id),
            'public_id': liquidacion_public_id,
            'numero_liquidacion': numero_liquidacion,
            'estado': liquidacion_orm.estado,
            'fecha_registro': liquidacion_orm.fecha_registro.isoformat() if liquidacion_orm.fecha_registro else '',
            'municipalidad': municipalidad_data,
            'expediente': liquidacion_orm.expediente if hasattr(liquidacion_orm, 'expediente') else None,
            'observacion': liquidacion_orm.observacion,
            'proyecto': proyecto_data,
            'edificaciones': edificaciones_data,
            'totales': totales_data,
        }
