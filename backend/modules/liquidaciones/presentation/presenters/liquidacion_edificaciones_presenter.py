"""
LiquidacionEdificacionesPresenter — transforma resultados a esquemas HTTP.
"""
import uuid
from typing import Union

from modules.liquidaciones.domain.schemas import (
    LiquidacionEdificacionesResult,
    NuevaRevisionFormularioResult,
    EdificacionRevisionData,
    CotizacionQuoteData,
    DelegadosVigentesResult,
    ProyectistaEdificacionData,
    DelegadoEdificacionData,
    ContactoData,
)
from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
    LiquidacionEdificacionOut,
    NuevaRevisionFormularioOut,
    RevisionVigenteOut,
    CotizacionQuoteOut,
    CotizacionRevisionOut,
    CotizacionTarifaOut,
    CotizacionTotalesOut,
    CotizacionMetadataOut,
    DelegadosVigentesOut,
    EspecialidadBasicaOut,
    EspecialidadOut,
    EntidadOut,
    ProyectoOut,
    MunicipalidadOut,
    ProvinciaBasicOut,
    DistritoBasicOut,
    ProyectistaOut,
    DelegadoOut,
    RevisionOut,
    TarifaOut,
    TotalesOut,
    ContactoEdificacionOut,
    ValoresOut,
)


class LiquidacionEdificacionesPresenter:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP.
    """

    @staticmethod
    def _build_municipalidad_out(municipalidad_id, municipalidad_nombre) -> "MunicipalidadOut":
        """Helper para construir MunicipalidadesSnapshotOut/MunicipalidadOut."""
        from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
            MunicipalidadOut,
        )
        return MunicipalidadOut(
            id=municipalidad_id or uuid.UUID('00000000-0000-0000-0000-000000000000'),
            nombre=municipalidad_nombre or '',
            codigo=None,
            provincia=None,
            distrito=None,
        )

    @staticmethod
    def present(result: LiquidacionEdificacionesResult) -> LiquidacionEdificacionOut:
        """
        Transforma un LiquidacionEdificacionesResult (plano) a LiquidacionEdificacionOut.

        Este es el método primario de presentación para los endpoints de lectura y creación
        de liquidaciones de edificaciones (excepto cotizar).

        Args:
            result: LiquidacionEdificacionesResult con campos planos (Phase 2 refactor)

        Returns:
            LiquidacionEdificacionOut schema para respuesta HTTP
        """
        # ── Entidad ─────────────────────────────────────────────────────────────
        entidad = None
        if result.entidad_id or result.entidad_nombre:
            entidad = EntidadOut(
                id=result.entidad_id,
                tipo=result.entidad_tipo,
                nombre=result.entidad_nombre,
                ruc=result.entidad_ruc,
            )

        # ── Proyecto ───────────────────────────────────────────────────────────
        proyecto = ProyectoOut(
            id=result.proyecto_id or uuid.UUID('00000000-0000-0000-0000-000000000000'),
            public_id=result.proyecto_public_id or '',
            nombre=result.proyecto_nombre or '',
            direccion=result.proyecto_direccion,
            valor_proyecto=float(result.valor_proyecto) if result.valor_proyecto else 0.0,
            entidad=entidad,
        )

        # ── Municipalidad ──────────────────────────────────────────────────────
        municipalidad = LiquidacionEdificacionesPresenter._build_municipalidad_out(
            result.municipalidad_id, result.municipalidad_nombre
        )

        # ── Proyectistas ───────────────────────────────────────────────────────
        proyectistas_out = []
        for p in result.proyectistas:
            if isinstance(p, ProyectistaEdificacionData):
                proyectistas_out.append(ProyectistaOut(
                    id=p.id,
                    perfil_ingeniero_id=p.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=p.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=p.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=p.perfil_ingeniero_cip,
                    especialidad_id=p.especialidad_id,
                    especialidad_nombre=p.especialidad_nombre,
                    descripcion=p.descripcion,
                ))
            elif isinstance(p, dict):
                proyectistas_out.append(ProyectistaOut(
                    id=p.get('id'),
                    perfil_ingeniero_id=p.get('perfil_ingeniero_id'),
                    perfil_ingeniero_nombres=p.get('perfil_ingeniero_nombres'),
                    perfil_ingeniero_apellidos=p.get('perfil_ingeniero_apellidos'),
                    perfil_ingeniero_cip=p.get('perfil_ingeniero_cip'),
                    especialidad_id=p.get('especialidad_id'),
                    especialidad_nombre=p.get('especialidad_nombre'),
                    descripcion=p.get('descripcion'),
                ))
            else:
                proyectistas_out.append(ProyectistaOut(
                    id=getattr(p, 'id', None),
                    perfil_ingeniero_id=getattr(p, 'perfil_ingeniero_id', None),
                    perfil_ingeniero_nombres=getattr(p, 'perfil_ingeniero_nombres', None),
                    perfil_ingeniero_apellidos=getattr(p, 'perfil_ingeniero_apellidos', None),
                    perfil_ingeniero_cip=getattr(p, 'perfil_ingeniero_cip', None),
                    especialidad_id=getattr(p, 'especialidad_id', None),
                    especialidad_nombre=getattr(p, 'especialidad_nombre', None),
                    descripcion=getattr(p, 'descripcion', None),
                ))

        # ── Delegados ──────────────────────────────────────────────────────────
        delegados_out = []
        for d in result.delegados:
            if isinstance(d, DelegadoEdificacionData):
                delegados_out.append(DelegadoOut(
                    id=d.id,
                    perfil_ingeniero_id=d.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=d.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=d.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=d.perfil_ingeniero_cip,
                    especialidad_id=d.especialidad_id,
                    especialidad_nombre=d.especialidad_nombre,
                    tipo=d.tipo,
                ))
            elif isinstance(d, dict):
                delegados_out.append(DelegadoOut(
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
                delegados_out.append(DelegadoOut(
                    id=getattr(d, 'id', None),
                    perfil_ingeniero_id=getattr(d, 'perfil_ingeniero_id', None),
                    perfil_ingeniero_nombres=getattr(d, 'perfil_ingeniero_nombres', None),
                    perfil_ingeniero_apellidos=getattr(d, 'perfil_ingeniero_apellidos', None),
                    perfil_ingeniero_cip=getattr(d, 'perfil_ingeniero_cip', None),
                    especialidad_id=getattr(d, 'especialidad_id', None),
                    especialidad_nombre=getattr(d, 'especialidad_nombre', None),
                    tipo=getattr(d, 'tipo', None),
                ))

        # ── Contactos ──────────────────────────────────────────────────────────
        contactos_out = []
        for c in result.contactos:
            if isinstance(c, ContactoData):
                contactos_out.append(ContactoEdificacionOut(
                    id=c.id,
                    nombres=c.nombres,
                    apellidos=c.apellidos,
                    dni=c.dni,
                    cargo=c.cargo,
                    telefono=c.telefono,
                    celular=c.celular,
                    email=c.email,
                    direccion=c.direccion,
                    principal=c.principal,
                    descripcion=c.descripcion,
                ))
            elif isinstance(c, dict):
                contactos_out.append(ContactoEdificacionOut(
                    id=c.get('id'),
                    nombres=c.get('nombres'),
                    apellidos=c.get('apellidos'),
                    dni=c.get('dni'),
                    cargo=c.get('cargo'),
                    telefono=c.get('telefono'),
                    celular=c.get('celular'),
                    email=c.get('email'),
                    direccion=c.get('direccion'),
                    principal=c.get('principal', False),
                    descripcion=c.get('descripcion'),
                ))
            else:
                contactos_out.append(ContactoEdificacionOut(
                    id=getattr(c, 'id', None),
                    nombres=getattr(c, 'nombres', None),
                    apellidos=getattr(c, 'apellidos', None),
                    dni=getattr(c, 'dni', None),
                    cargo=getattr(c, 'cargo', None),
                    telefono=getattr(c, 'telefono', None),
                    celular=getattr(c, 'celular', None),
                    email=getattr(c, 'email', None),
                    direccion=getattr(c, 'direccion', None),
                    principal=getattr(c, 'principal', False),
                    descripcion=getattr(c, 'descripcion', None),
                ))

        # ── Revisiones ─────────────────────────────────────────────────────────
        revisiones_out = []
        for rev in result.revisiones:
            if isinstance(rev, EdificacionRevisionData):
                if rev.especialidades:
                    especialidades_list = [
                        EspecialidadOut(
                            id=uuid.UUID(str(esp.id)) if not isinstance(esp.id, uuid.UUID) else esp.id,
                            nombre=str(esp.nombre) if esp.nombre else '',
                        )
                        for esp in rev.especialidades
                    ]
                else:
                    # Sin especialidades — usar lista vacía, no fallback a singular
                    especialidades_list = []
                revisiones_out.append(RevisionOut(
                    id=rev.id,
                    especialidades=especialidades_list,
                    tarifa=TarifaOut(
                        id=rev.tarifa.id,
                        derecho_minimo=float(rev.tarifa.derecho_minimo),
                        derecho_maximo=float(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                        porcentaje_minimo_uit=float(rev.tarifa.porcentaje_minimo_uit),
                        porcentaje_liquidacion=float(rev.tarifa.porcentaje_liquidacion),
                    ),
                ))
            elif isinstance(rev, dict):
                esp_list = rev.get('especialidades', [])
                if esp_list:
                    especialidades_list = [
                        EspecialidadOut(
                            id=uuid.UUID(str(esp.get('id'))) if esp.get('id') else uuid.uuid4(),
                            nombre=str(esp.get('nombre', '')) if esp.get('nombre') else '',
                        )
                        for esp in esp_list
                    ]
                else:
                    # Sin especialidades — usar lista vacía, no fallback a singular
                    especialidades_list = []
                revisiones_out.append(RevisionOut(
                    id=str(rev.get('id', '')),
                    especialidades=especialidades_list,
                    tarifa=TarifaOut(
                        id=str(rev.get('tarifa', {}).get('id', '')),
                        derecho_minimo=float(rev.get('tarifa', {}).get('derecho_minimo', 0)),
                        derecho_maximo=float(rev.get('tarifa', {}).get('derecho_maximo', 0)) if rev.get('tarifa', {}).get('derecho_maximo') else None,
                        porcentaje_minimo_uit=float(rev.get('tarifa', {}).get('porcentaje_minimo_uit', 0)),
                        porcentaje_liquidacion=float(rev.get('tarifa', {}).get('porcentaje_liquidacion', 0)) if rev.get('tarifa', {}).get('porcentaje_liquidacion') else 0.0,
                    ),
                ))
            else:
                revisiones_out.append(RevisionOut(
                    id=getattr(rev, 'id', uuid.uuid4()),
                    especialidades=[],
                    tarifa=TarifaOut(
                        id=getattr(getattr(rev, 'tarifa', None), 'id', uuid.uuid4()),
                        derecho_minimo=0.0,
                        derecho_maximo=None,
                        porcentaje_minimo_uit=0.0,
                        porcentaje_liquidacion=0.0,
                    ),
                ))

        # ── Valores financieros ─────────────────────────────────────────────────
        valores = ValoresOut(
            subtotal=float(result.subtotal),
            igv=float(result.igv),
            total=float(result.total),
            total_a_pagar=float(result.total_a_pagar),
        )

        # ── Armar LiquidacionEdificacionOut plano ────────────────────────────────
        return LiquidacionEdificacionOut(
            id=result.id,
            public_id=result.public_id,
            estado=result.estado,
            fecha_registro=result.fecha_registro,
            expediente=result.expediente,
            observacion=result.observacion,
            numero_revision=result.numero_revision,
            tipo_tramite=result.tipo_tramite,
            tramite_accion=result.tramite_accion,
            proyecto=proyecto,
            entidad=entidad,
            municipalidad=municipalidad,
            valores=valores,
            proyectistas=proyectistas_out,
            delegados=delegados_out,
            contactos=contactos_out,
            revisiones=revisiones_out,
            subtotal=float(result.subtotal),
            igv=float(result.igv),
            total=float(result.total),
            total_a_pagar=float(result.total_a_pagar),
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
                # ProyectistaEdificacionData u otro
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
            tipo_tramite=result.tipo_tramite,
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
            # rev.especialidades contains EspecialidadBasicaResult objects with id: uuid.UUID (stored as string internally)
            # Explicitly convert to handle string-to-UUID coercion
            if rev.especialidades:
                especialidades_out = [
                    EspecialidadBasicaOut(
                        id=uuid.UUID(str(esp.id)) if not isinstance(esp.id, uuid.UUID) else esp.id,
                        nombre=str(esp.nombre) if esp.nombre else '',
                    )
                    for esp in rev.especialidades
                ]
            else:
                especialidades_out = []
            cotizacion_revisiones.append(CotizacionRevisionOut(
                id=rev.id,
                especialidades=especialidades_out,
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
                valor_base_calculo=float(result.metadata.valor_base_calculo),
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
