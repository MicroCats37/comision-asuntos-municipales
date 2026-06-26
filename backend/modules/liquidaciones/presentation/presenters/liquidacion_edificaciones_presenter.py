"""
LiquidacionEdificacionesPresenter — transforma resultados a esquemas HTTP.
"""
from typing import Union

from modules.liquidaciones.domain.schemas import (
    LiquidacionEdificacionesResult,
    NuevaRevisionFormularioResult,
    EdificacionRevisionData,
    CotizacionQuoteData,
    DelegadosVigentesResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
    LiquidacionSnapshotOut,
    NuevaRevisionFormularioOut,
    RevisionVigenteOut,
    CotizacionQuoteOut,
    CotizacionRevisionOut,
    CotizacionTarifaOut,
    CotizacionTotalesOut,
    CotizacionMetadataOut,
    DelegadosVigentesOut,
)


class LiquidacionEdificacionesPresenter:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP.
    """

    @staticmethod
    def present_snapshot(result: LiquidacionEdificacionesResult) -> LiquidacionSnapshotOut:
        """
        Transforma un LiquidacionEdificacionesResult a LiquidacionSnapshotOut.

        Args:
            result: LiquidacionEdificacionesResult del flujo

        Returns:
            LiquidacionSnapshotOut schema para respuesta HTTP
        """
        # Construir entidad si existe
        entidad = None
        if result.proyecto_entidad_id:
            from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import EntidadOut
            entidad = EntidadOut(
                id=result.proyecto_entidad_id,
                tipo=result.proyecto_entidad_tipo,
                nombre=result.proyecto_entidad_nombre,
                ruc=result.proyecto_entidad_ruc,
            )

        # Construir proyecto (sin proyectista — ahora vive en edificaciones)
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import ProyectoOut
        proyecto = ProyectoOut(
            id=result.proyecto_id,
            public_id=result.proyecto_public_id,
            nombre=result.proyecto_nombre,
            direccion=result.proyecto_direccion,
            valor_proyecto=float(result.valor_proyecto),
            entidad=entidad,
        )

        # Construir municipalidad anidada
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
            LiquidacionOut,
            MunicipalidadesSnapshotOut,
            ProvinciaBasicSnapshotOut,
            DistritoBasicSnapshotOut,
        )
        # Para la respuesta de crear_primera_revision, no tenemos toda la info de provincia/distrito
        # ya que LiquidacionEdificacionesResult solo tiene municipalidad_id y municipalidad_nombre
        municipalidad = MunicipalidadesSnapshotOut(
            id=result.municipalidad_id,
            nombre=result.municipalidad_nombre,
            codigo=None,
            provincia=None,
            distrito=None,
        )

        # Construir liquidacion (con expediente)
        liquidacion = LiquidacionOut(
            id=result.liquidacion_id,
            public_id=result.liquidacion_public_id,
            estado=result.estado,
            fecha_creacion=result.fecha_creacion,
            proyecto=proyecto,
            municipalidad=municipalidad,
            expediente=getattr(result, 'expediente', None),
            observacion=result.observacion or '',
        )

        # Construir proyectistas desde edificaciones_proyectistas (ahora en result, no en proyecto)
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import ProyectistaOut
        from modules.liquidaciones.domain.models import Proyectista
        edificaciones_proyectistas = []
        for p in result.edificaciones_proyectistas:
            if isinstance(p, dict):
                # Dict desde snapshot - nuevo formato con perfil_ingeniero_*
                edificaciones_proyectistas.append(ProyectistaOut(
                    id=p.get('id'),
                    perfil_ingeniero_id=p.get('perfil_ingeniero_id'),
                    perfil_ingeniero_nombres=p.get('perfil_ingeniero_nombres'),
                    perfil_ingeniero_apellidos=p.get('perfil_ingeniero_apellidos'),
                    perfil_ingeniero_cip=p.get('perfil_ingeniero_cip'),
                    especialidad_id=p.get('especialidad_id'),
                    especialidad_nombre=p.get('especialidad_nombre'),
                    descripcion=p.get('descripcion'),
                ))
            elif isinstance(p, Proyectista):
                # Proyectista model instance - acceder via perfil_ingeniero FK
                perfil = p.perfil_ingeniero
                edificaciones_proyectistas.append(ProyectistaOut(
                    id=p.id,
                    perfil_ingeniero_id=str(p.perfil_ingeniero_id) if p.perfil_ingeniero_id else None,
                    perfil_ingeniero_nombres=getattr(perfil, 'nombres', None) if perfil else None,
                    perfil_ingeniero_apellidos=f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None,
                    perfil_ingeniero_cip=getattr(perfil, 'cip', None) if perfil else None,
                    especialidad_id=str(p.especialidad_id) if p.especialidad_id else None,
                    especialidad_nombre=p.especialidad.nombre if p.especialidad else None,
                    descripcion=p.descripcion,
                ))
            else:
                # ProyectistaSnapshotData u otro schema object
                edificaciones_proyectistas.append(ProyectistaOut(
                    id=p.id,
                    perfil_ingeniero_id=getattr(p, 'perfil_ingeniero_id', None),
                    perfil_ingeniero_nombres=getattr(p, 'perfil_ingeniero_nombres', None),
                    perfil_ingeniero_apellidos=getattr(p, 'perfil_ingeniero_apellidos', None),
                    perfil_ingeniero_cip=getattr(p, 'perfil_ingeniero_cip', None),
                    especialidad_id=getattr(p, 'especialidad_id', None),
                    especialidad_nombre=getattr(p, 'especialidad_nombre', None),
                    descripcion=getattr(p, 'descripcion', None),
                ))

        # Construir revisiones de edificaciones
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
            DelegadoOut,
            EdificacionesOut,
            RevisionOut,
            TarifaOut,
        )
        edificaciones_delegados = []
        for d in result.edificaciones_delegados:
            if isinstance(d, dict):
                edificaciones_delegados.append(DelegadoOut(
                    id=d.get('id'),
                    perfil_ingeniero_id=d.get('perfil_ingeniero_id'),
                    perfil_ingeniero_nombres=d.get('perfil_ingeniero_nombres'),
                    perfil_ingeniero_apellidos=d.get('perfil_ingeniero_apellidos'),
                    perfil_ingeniero_cip=d.get('perfil_ingeniero_cip'),
                    especialidad_id=d.get('especialidad_id'),
                    especialidad_nombre=d.get('especialidad_nombre'),
                    tipo=d.get('tipo'),
                ))
            else:
                edificaciones_delegados.append(DelegadoOut(
                    id=getattr(d, 'id', None),
                    perfil_ingeniero_id=getattr(d, 'perfil_ingeniero_id', None),
                    perfil_ingeniero_nombres=getattr(d, 'perfil_ingeniero_nombres', None),
                    perfil_ingeniero_apellidos=getattr(d, 'perfil_ingeniero_apellidos', None),
                    perfil_ingeniero_cip=getattr(d, 'perfil_ingeniero_cip', None),
                    especialidad_id=getattr(d, 'especialidad_id', None),
                    especialidad_nombre=getattr(d, 'especialidad_nombre', None),
                    tipo=getattr(d, 'tipo', None),
                ))

        edificaciones_revisiones = []
        for rev in result.edificaciones_revisiones:
            # rev puede ser un dict o un EdificacionRevisionData
            # NOTE: numero_revision fue removido de cada revisión — solo existe en nivel edificaciones
            if isinstance(rev, EdificacionRevisionData):
                edificaciones_revisiones.append(RevisionOut(
                    id=rev.id,
                    especialidad=rev.especialidad.nombre if hasattr(rev.especialidad, 'nombre') else str(rev.especialidad),
                    tarifa=TarifaOut(
                        id=rev.tarifa.id,
                        derecho_minimo=float(rev.tarifa.derecho_minimo),
                        derecho_maximo=float(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                        porcentaje_minimo_uit=float(rev.tarifa.porcentaje_minimo_uit),
                    ),
                    monto_base=float(rev.monto_base) if hasattr(rev, 'monto_base') else 0.0,
                    cobra=rev.cobra if hasattr(rev, 'cobra') else False,
                ))
            else:
                # fallback para dict
                edificaciones_revisiones.append(RevisionOut(
                    id=str(rev.get('id', '')),
                    especialidad=rev.get('especialidad', ''),
                    tarifa=TarifaOut(
                        id=str(rev.get('tarifa', {}).get('id', '')),
                        derecho_minimo=float(rev.get('tarifa', {}).get('derecho_minimo', 0)),
                        derecho_maximo=float(rev.get('tarifa', {}).get('derecho_maximo', 0)) if rev.get('tarifa', {}).get('derecho_maximo') else None,
                        porcentaje_minimo_uit=float(rev.get('tarifa', {}).get('porcentaje_minimo_uit', 0)),
                    ),
                    monto_base=float(rev.get('monto_base', 0)),
                    cobra=rev.get('cobra', False),
                ))

        edificaciones = EdificacionesOut(
            public_id=result.edificaciones_public_id,
            numero_revision=result.numero_revision,
            tipo_tramite=result.edificaciones_tipo_tramite,
            tramite_accion=result.edificaciones_tramite_accion,
            proyectistas=edificaciones_proyectistas,
            delegados=edificaciones_delegados,
            revisiones=edificaciones_revisiones,
        )

        # Construir totales
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import TotalesOut
        totales = TotalesOut(
            subtotal=float(result.totales_subtotal),
            igv=float(result.totales_igv),
            total=float(result.totales_total_liquidacion),
            liquidacion_total=float(result.totales_total_liquidacion),
            total_a_pagar=float(result.totales_total_a_pagar),
        )

        return LiquidacionSnapshotOut(
            liquidacion=liquidacion,
            edificaciones=edificaciones,
            totales=totales,
        )

    @staticmethod
    def present_formulario(result: NuevaRevisionFormularioResult) -> NuevaRevisionFormularioOut:
        """
        Transforma resultado de formulario de nueva revisión.

        Args:
            result: NuevaRevisionFormularioResult

        Returns:
            NuevaRevisionFormularioOut schema para respuesta HTTP
        """
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import RevisionVigenteOut, ProyectistaOut

        revisiones_vigentes = []
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import EspecialidadBasicaOut
        for rev in result.revisiones_vigentes:
            if hasattr(rev, 'id'):
                # Es RevisionVigenteResult
                # Construir lista de especialidades desde M2M
                especialidades_list = [
                    EspecialidadBasicaOut(
                        id=str(esp.id),
                        nombre=esp.nombre,
                    )
                    for esp in rev.especialidades
                ]
                revisiones_vigentes.append(RevisionVigenteOut(
                    id=str(rev.id),
                    especialidades=especialidades_list,
                    tarifa_id=str(rev.tarifa_id),
                    porcentaje_liquidacion=float(rev.porcentaje_liquidacion),
                    derecho_minimo=float(rev.derecho_minimo),
                    derecho_maximo=float(rev.derecho_maximo) if rev.derecho_maximo else None,
                    porcentaje_minimo_uit=float(rev.porcentaje_minimo_uit),
                    habilitada=rev.habilitada,
                ))

        # Proyectistas actuales (heredados de la liquidación previa)
        from modules.liquidaciones.domain.models import Proyectista
        proyectistas_actuales = []
        for p in result.proyectistas_actuales:
            if isinstance(p, dict):
                # Dict - nuevo formato con perfil_ingeniero_*
                proyectistas_actuales.append(ProyectistaOut(
                    id=p.get('id'),
                    perfil_ingeniero_id=p.get('perfil_ingeniero_id'),
                    perfil_ingeniero_nombres=p.get('perfil_ingeniero_nombres'),
                    perfil_ingeniero_apellidos=p.get('perfil_ingeniero_apellidos'),
                    perfil_ingeniero_cip=p.get('perfil_ingeniero_cip'),
                    especialidad_id=p.get('especialidad_id'),
                    especialidad_nombre=p.get('especialidad_nombre'),
                    descripcion=p.get('descripcion'),
                ))
            elif isinstance(p, Proyectista):
                # Proyectista model instance
                perfil = p.perfil_ingeniero
                proyectistas_actuales.append(ProyectistaOut(
                    id=p.id,
                    perfil_ingeniero_id=str(p.perfil_ingeniero_id) if p.perfil_ingeniero_id else None,
                    perfil_ingeniero_nombres=getattr(perfil, 'nombres', None) if perfil else None,
                    perfil_ingeniero_apellidos=f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip() or None,
                    perfil_ingeniero_cip=getattr(perfil, 'cip', None) if perfil else None,
                    especialidad_id=str(p.especialidad_id) if p.especialidad_id else None,
                    especialidad_nombre=p.especialidad.nombre if p.especialidad else None,
                    descripcion=p.descripcion,
                ))
            else:
                # ProyectistaSnapshotData u otro
                proyectistas_actuales.append(ProyectistaOut(
                    id=getattr(p, 'id', None),
                    perfil_ingeniero_id=getattr(p, 'perfil_ingeniero_id', None),
                    perfil_ingeniero_nombres=getattr(p, 'perfil_ingeniero_nombres', None),
                    perfil_ingeniero_apellidos=getattr(p, 'perfil_ingeniero_apellidos', None),
                    perfil_ingeniero_cip=getattr(p, 'perfil_ingeniero_cip', None),
                    especialidad_id=getattr(p, 'especialidad_id', None),
                    especialidad_nombre=getattr(p, 'especialidad_nombre', None),
                    descripcion=getattr(p, 'descripcion', None),
                ))

        return NuevaRevisionFormularioOut(
            liquidacion_previa_id=str(result.liquidacion_previa_id),
            numero_revision=result.numero_revision,
            cobra=result.cobra,
            proyecto_id=str(result.proyecto_id),
            proyecto_public_id=result.proyecto_public_id,
            proyecto_nombre=result.proyecto_nombre,
            valor_proyecto=float(result.valor_proyecto),
            valor_base_calculo=float(result.valor_base_calculo),
            revisiones_vigentes=revisiones_vigentes,
            proyectistas_actuales=proyectistas_actuales,
        )

    @staticmethod
    def present_cotizacion(result: CotizacionQuoteData) -> CotizacionQuoteOut:
        """
        Transforma un CotizacionQuoteData a CotizacionQuoteOut.

        Args:
            result: CotizacionQuoteData del flujo (cálculo sin persistencia)

        Returns:
            CotizacionQuoteOut schema para respuesta HTTP
        """
        cotizacion_revisiones = []
        for rev in result.revisiones:
            cotizacion_revisiones.append(CotizacionRevisionOut(
                id=rev.id,
                especialidad=rev.especialidad,
                tarifa=CotizacionTarifaOut(
                    id=rev.tarifa.id,
                    derecho_minimo=float(rev.tarifa.derecho_minimo),
                    derecho_maximo=float(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                    porcentaje_minimo_uit=float(rev.tarifa.porcentaje_minimo_uit),
                ),
                monto_base=float(rev.monto_base),
                cobra=rev.cobra,
            ))

        return CotizacionQuoteOut(
            numero_revision=result.numero_revision,
            revisiones=cotizacion_revisiones,
            totales=CotizacionTotalesOut(
                subtotal=float(result.totales.subtotal),
                igv=float(result.totales.igv),
                total=float(result.totales.total),
                liquidacion_total=float(result.totales.liquidacion_total),
                total_a_pagar=float(result.totales.total_a_pagar),
            ),
            metadata=CotizacionMetadataOut(
                igv_valor=float(result.metadata.igv_valor),
                uit_valor=float(result.metadata.uit_valor),
                cobra=result.metadata.cobra,
            ),
        )

    @staticmethod
    def present_delegados_vigentes(result: DelegadosVigentesResult) -> DelegadosVigentesOut:
        """
        Transforma un DelegadosVigentesResult a DelegadosVigentesOut.

        Args:
            result: DelegadosVigentesResult del flujo

        Returns:
            DelegadosVigentesOut schema para respuesta HTTP
        """
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
            DelegadoVigenteOut,
            EspecialidadBasicaDelegadoOut,
        )

        delegados_out = []
        for dele in result.delegados:
            especialidad_out = None
            if dele.especialidad:
                especialidad_out = EspecialidadBasicaDelegadoOut(
                    id=dele.especialidad.id,
                    nombre=dele.especialidad.nombre,
                )
            delegados_out.append(DelegadoVigenteOut(
                id=dele.id,
                nombre_completo=dele.nombre_completo,
                cip=dele.cip,
                especialidad=especialidad_out,
                tipo=dele.tipo,
            ))

        return DelegadosVigentesOut(delegados=delegados_out)
