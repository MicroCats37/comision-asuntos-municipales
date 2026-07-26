"""
TaludesPresenter — transforma resultados domain a schemas HTTP para Taludes.
"""
import uuid as _uuid
from decimal import Decimal
from typing import Optional, Union

from modules.liquidaciones.domain.schemas.taludes import (
    LiquidacionTaludesResult,
)
from modules.liquidaciones.domain.schemas.shared import (
    LiquidacionM2CalculoData,
    CotizacionM2QuoteData,
)
from modules.liquidaciones.domain.schemas import (
    LiquidacionGeneralListItem,
    LiquidacionGeneralResult,
    CotizacionQuoteData,
)
from modules.liquidaciones.presentation.schemas.taludes_schemas import (
    LiquidacionTaludesOut,
    LiquidacionTaludesListItemOut,
    TarifaM2Out,
    LiquidacionM2CalculoOut,
    TarifaOut,
    ValorBaseCalculoOut,
    TotalesOut,
    EntidadOut,
    ProyectoOut,
    LiquidacionOut,
    MunicipalidadesSnapshotOut,
    CotizacionM2QuoteOut,
    CotizacionM2RevisionOut,
    CotizacionM2MetadataOut,
    CotizacionQuoteOut,
    CotizacionRevisionOut,
    CotizacionMetadataOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    EntidadListItemOut,
    ProyectoListItemOut,
    MunicipalidadListItemOut,
    ValoresListItemOut,
    ProyectistaListItemOut,
    DelegadoListItemOut,
    ContactoListItemOut,
    RevisionListItemCleanOut,
    TarifaRevisionOut,
    EspecialidadRevisionOut,
    EspecialidadBasicaOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
    CotizacionTarifaOut as CotizacionTarifaOutEdif,
)


class TaludesPresenter:
    """Transforma objetos de resultado del dominio a esquemas de respuesta HTTP para Taludes."""

    # =============================================================================
    # Helpers privados
    # =============================================================================

    @staticmethod
    def _build_entidad(result: LiquidacionTaludesResult) -> Optional[EntidadOut]:
        """Construir entidad anidada si existe."""
        if result.proyecto_entidad_id:
            return EntidadOut(
                id=result.proyecto_entidad_id,
                tipo=result.proyecto_entidad_tipo,
                nombre=result.proyecto_entidad_nombre,
                ruc=result.proyecto_entidad_ruc,
            )
        return None

    @staticmethod
    def _build_proyecto(result: LiquidacionTaludesResult) -> ProyectoOut:
        """Construir proyecto anidado."""
        return ProyectoOut(
            id=result.proyecto_id,
            public_id=result.proyecto_public_id,
            nombre=result.proyecto_nombre,
            direccion=result.proyecto_direccion,
            valor_proyecto=float(result.proyecto_valor_proyecto) if result.proyecto_valor_proyecto else 0.0,
            entidad=TaludesPresenter._build_entidad(result),
        )

    @staticmethod
    def _build_municipalidad(result: LiquidacionTaludesResult) -> MunicipalidadesSnapshotOut:
        """Construir municipalidad anidada (básica, sin detalle de provincia/distrito)."""
        return MunicipalidadesSnapshotOut(
            id=result.municipalidad_id,
            nombre=result.municipalidad_nombre,
            codigo=None,
        )

    @staticmethod
    def _build_liquidacion(result: LiquidacionTaludesResult) -> LiquidacionOut:
        """Construir liquidacion anidada."""
        return LiquidacionOut(
            id=result.liquidacion_id,
            public_id=result.liquidacion_public_id,
            estado=result.estado,
            fecha_creacion=result.fecha_creacion,
            proyecto=TaludesPresenter._build_proyecto(result),
            municipalidad=TaludesPresenter._build_municipalidad(result),
            expediente=getattr(result, "expediente", None),
            observacion=result.observacion or "",
        )

    @staticmethod
    def _build_totales(result: LiquidacionTaludesResult) -> TotalesOut:
        """Construir totales."""
        return TotalesOut(
            subtotal=float(result.totales_subtotal),
            igv=float(result.totales_igv),
            total=float(result.totales_total_liquidacion),
            liquidacion_total=float(result.totales_total_liquidacion),
            total_a_pagar=float(result.totales_total_a_pagar),
        )

    @staticmethod
    def _build_tarifa_m2(calculo: LiquidacionM2CalculoData) -> TarifaM2Out:
        """Construir tarifa M2 desde dato de cálculo."""
        return TarifaM2Out(
            id=calculo.tarifa.id,
            costo_por_m2=float(calculo.tarifa.costo_por_m2),
            area_m2=float(calculo.tarifa.area_m2),
            derecho_minimo=float(calculo.tarifa.derecho_minimo),
            derecho_maximo=float(calculo.tarifa.derecho_maximo) if calculo.tarifa.derecho_maximo else None,
        )

    @staticmethod
    def _build_calculo_m2(calculo_data: LiquidacionM2CalculoData) -> LiquidacionM2CalculoOut:
        """Construir salida de cálculo M2."""
        return LiquidacionM2CalculoOut(
            area_solicitada=float(calculo_data.area_solicitada),
            area_base_calculo=float(calculo_data.area_base_calculo),
            derecho=float(calculo_data.derecho),
            tarifa=TaludesPresenter._build_tarifa_m2(calculo_data),
        )

    @staticmethod
    def _build_tarifa_out(
        tarifa_id,
        derecho_minimo,
        derecho_maximo,
        porcentaje_minimo_uit,
        porcentaje_liquidacion,
    ) -> TarifaOut:
        """Construir tarifa porcentual (Edificaciones-style)."""
        return TarifaOut(
            id=tarifa_id,
            derecho_minimo=float(derecho_minimo),
            derecho_maximo=float(derecho_maximo) if derecho_maximo else None,
            porcentaje_minimo_uit=float(porcentaje_minimo_uit),
            porcentaje_liquidacion=float(porcentaje_liquidacion),
        )

    @staticmethod
    def _build_valor_base_calculo(
        valor_proyecto,
        valor_base_calculo,
        derecho,
        tarifa_id,
        derecho_minimo,
        derecho_maximo,
        porcentaje_minimo_uit,
        porcentaje_liquidacion,
    ) -> ValorBaseCalculoOut:
        """Construir salida de cálculo porcentual (Edificaciones-style)."""
        return ValorBaseCalculoOut(
            valor_proyecto=float(valor_proyecto),
            valor_base_calculo=float(valor_base_calculo),
            derecho=float(derecho),
            tarifa=TaludesPresenter._build_tarifa_out(
                tarifa_id,
                derecho_minimo,
                derecho_maximo,
                porcentaje_minimo_uit,
                porcentaje_liquidacion,
            ),
        )

    @staticmethod
    def _get_tramite_accion(result: LiquidacionTaludesResult) -> str:
        """Obtener tramite_accion desde el resultado."""
        return getattr(result, "tramite_accion", "PRIMERA_REVISION")

    # =============================================================================
    # Presenter principal (M2 legacy)
    # =============================================================================

    @staticmethod
    def present(
        result: LiquidacionTaludesResult,
        calculo_m2: LiquidacionM2CalculoData,
    ) -> LiquidacionTaludesOut:
        """
        Transforma un LiquidacionTaludesResult a LiquidacionTaludesOut (M2 legacy).
        """
        return LiquidacionTaludesOut(
            liquidacion=TaludesPresenter._build_liquidacion(result),
            tipo_liquidacion="TALUDES",
            tramite_accion=TaludesPresenter._get_tramite_accion(result),
            calculo_m2=TaludesPresenter._build_calculo_m2(calculo_m2),
            totales=TaludesPresenter._build_totales(result),
        )

    # =============================================================================
    # Presenter principal (porcentaje — Edificaciones-style)
    # =============================================================================

    @staticmethod
    def present_porcentaje(
        result: LiquidacionTaludesResult,
        liquidacion_porcentaje,
    ) -> LiquidacionTaludesOut:
        """
        Transforma un LiquidacionTaludesResult (porcentaje) a LiquidacionTaludesOut.

        Args:
            result: LiquidacionTaludesResult con valores calculados con IGV.
            liquidacion_porcentaje: LiquidacionPorcentajeObra ORM record.
        """
        tarifa = liquidacion_porcentaje.tarifa_aplicada
        return LiquidacionTaludesOut(
            liquidacion=TaludesPresenter._build_liquidacion(result),
            tipo_liquidacion="TALUDES",
            tramite_accion=TaludesPresenter._get_tramite_accion(result),
            calculo_porcentaje=TaludesPresenter._build_valor_base_calculo(
                valor_proyecto=liquidacion_porcentaje.valor_proyecto,
                valor_base_calculo=liquidacion_porcentaje.valor_base_calculo,
                derecho=result.totales_subtotal,
                tarifa_id=tarifa.id,
                derecho_minimo=tarifa.derecho_minimo,
                derecho_maximo=tarifa.derecho_maximo,
                porcentaje_minimo_uit=tarifa.porcentaje_minimo_uit,
                porcentaje_liquidacion=tarifa.porcentaje_liquidacion,
            ),
            totales=TaludesPresenter._build_totales(result),
        )

    # =============================================================================
    # Presenter para Cotización M2
    # =============================================================================

    @staticmethod
    def present_cotizacion(result: CotizacionM2QuoteData) -> CotizacionM2QuoteOut:
        """
        Transforma un CotizacionM2QuoteData a CotizacionM2QuoteOut.
        """
        calculo_rev = result.calculo_m2
        return CotizacionM2QuoteOut(
            numero_revision=result.numero_revision,
            calculo_m2=CotizacionM2RevisionOut(
                area_solicitada=float(calculo_rev.area_solicitada),
                area_base_calculo=float(calculo_rev.area_base_calculo),
                derecho=float(calculo_rev.derecho),
                tarifa=TarifaM2Out(
                    id=calculo_rev.tarifa.id,
                    costo_por_m2=float(calculo_rev.tarifa.costo_por_m2),
                    area_m2=float(calculo_rev.tarifa.area_m2),
                    derecho_minimo=float(calculo_rev.tarifa.derecho_minimo),
                    derecho_maximo=float(calculo_rev.tarifa.derecho_maximo) if calculo_rev.tarifa.derecho_maximo else None,
                ),
            ),
            totales=TotalesOut(
                subtotal=float(result.totales.subtotal),
                igv=float(result.totales.igv),
                total=float(result.totales.total),
                liquidacion_total=float(result.totales.liquidacion_total),
                total_a_pagar=float(result.totales.total_a_pagar),
            ),
            metadata=CotizacionM2MetadataOut(
                igv_valor=float(result.metadata.igv_valor),
                uit_valor=float(result.metadata.uit_valor),
                area_solicitada=float(result.metadata.area_solicitada) if result.metadata.area_solicitada else None,
            ),
        )

    @staticmethod
    def present_cotizacion_porcentaje(
        result: CotizacionQuoteData,
    ) -> CotizacionQuoteOut:
        """
        Transforma un CotizacionQuoteData (porcentaje-based) a CotizacionQuoteOut
        — Edificaciones parity: revisiones[], especialidades[], monto_base, cobra.

        Args:
            result: CotizacionQuoteData con revision data del cálculo Edificaciones-style.
        """
        # IV/Taludes no tienen especialidades M2M — empty list
        especialidades_out: list[EspecialidadBasicaOut] = []
        if result.revisiones and result.revisiones[0].especialidades:
            especialidades_out = [
                EspecialidadBasicaOut(
                    id=esp.id,
                    nombre=esp.nombre,
                )
                for esp in result.revisiones[0].especialidades
            ]

        rev = result.revisiones[0]
        return CotizacionQuoteOut(
            numero_revision=result.numero_revision,
            revisiones=[
                CotizacionRevisionOut(
                    id=rev.id,
                    especialidades=especialidades_out,
                    tarifa=CotizacionTarifaOutEdif(
                        id=rev.tarifa.id,
                        derecho_minimo=float(rev.tarifa.derecho_minimo),
                        derecho_maximo=float(rev.tarifa.derecho_maximo) if rev.tarifa.derecho_maximo else None,
                        porcentaje_minimo_uit=float(rev.tarifa.porcentaje_minimo_uit),
                        porcentaje_liquidacion=float(rev.tarifa.porcentaje_liquidacion),
                    ),
                    monto_base=float(rev.monto_base),
                    cobra=rev.cobra,
                )
            ],
            totales=TotalesOut(
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

    # =============================================================================
    # Presenter para Lista
    # =============================================================================

    @staticmethod
    def _build_entidad_list(result: LiquidacionGeneralListItem) -> Optional[EntidadListItemOut]:
        """Construir entidad anidada para list item."""
        if not result.entidad or not result.entidad.id:
            return None
        return EntidadListItemOut(
            id=result.entidad.id,
            tipo=result.entidad.tipo,
            nombre=result.entidad.nombre,
            ruc=result.entidad.ruc,
        )

    @staticmethod
    def _build_proyecto_list(result: LiquidacionGeneralListItem) -> ProyectoListItemOut:
        """Construir proyecto anidado para list item."""
        return ProyectoListItemOut(
            id=result.proyecto.id,
            public_id=result.proyecto.public_id,
            nombre=result.proyecto.nombre,
            direccion=result.proyecto.direccion,
            valor_proyecto=result.proyecto.valor_proyecto,
            entidad=TaludesPresenter._build_entidad_list(result),
        )

    @staticmethod
    def present_list_item(result: LiquidacionGeneralListItem) -> LiquidacionTaludesListItemOut:
        """
        Transforma un LiquidacionGeneralListItem a LiquidacionTaludesListItemOut.
        """
        return LiquidacionTaludesListItemOut(
            id=result.id,
            public_id=result.public_id,
            tipo_liquidacion=result.tipo_liquidacion,
            estado=result.estado,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            proyecto=TaludesPresenter._build_proyecto_list(result),
            entidad=TaludesPresenter._build_entidad_list(result),
            municipalidad=MunicipalidadListItemOut(
                id=result.municipalidad.id,
                nombre=result.municipalidad.nombre,
                codigo=result.municipalidad.codigo,
                provincia=result.municipalidad.provincia,
                distrito=result.municipalidad.distrito,
            ),
            valores=ValoresListItemOut(
                subtotal=result.valores.subtotal,
                igv=result.valores.igv,
                total=result.valores.total,
                total_a_pagar=result.valores.total_a_pagar,
            ),
            proyectistas=[
                ProyectistaListItemOut(
                    id=p.id,
                    perfil_ingeniero_id=p.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=p.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=p.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=p.perfil_ingeniero_cip,
                    especialidad_id=p.especialidad_id,
                    especialidad_nombre=p.especialidad_nombre,
                    descripcion=p.descripcion,
                ) for p in result.proyectistas
            ],
            delegados=[
                DelegadoListItemOut(
                    id=d.id,
                    perfil_ingeniero_id=d.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=d.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=d.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=d.perfil_ingeniero_cip,
                    especialidad_id=d.especialidad_id,
                    especialidad_nombre=d.especialidad_nombre,
                    tipo=d.tipo,
                ) for d in result.delegados
            ],
            contactos=[
                ContactoListItemOut(
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
                ) for c in result.contactos
            ],
            revisiones=[
                RevisionListItemCleanOut(
                    id=r.id,
                    especialidades=[
                        EspecialidadRevisionOut(id=e.id, nombre=e.nombre)
                        for e in r.especialidades
                    ],
                    tarifa=TarifaRevisionOut(**r.tarifa.model_dump()) if r.tarifa else None,
                ) for r in result.revisiones
            ],
        )

    @staticmethod
    def present_list(
        results: list[LiquidacionGeneralListItem],
    ) -> list[LiquidacionTaludesListItemOut]:
        """
        Transforma una lista de LiquidacionGeneralListItem a lista de LiquidacionTaludesListItemOut.
        """
        return [TaludesPresenter.present_list_item(r) for r in results]

    # =============================================================================
    # Presenter para Detalle (desde LiquidacionGeneralResult plano)
    # =============================================================================

    @staticmethod
    def _build_entidad_detail(result: LiquidacionGeneralResult) -> Optional[EntidadListItemOut]:
        """Construir entidad anidada para detail item desde campos planos."""
        if not result.entidad_id:
            return None
        return EntidadListItemOut(
            id=result.entidad_id,
            tipo=result.entidad_tipo,
            nombre=result.entidad_nombre,
            ruc=result.entidad_ruc,
        )

    @staticmethod
    def _build_proyecto_detail(result: LiquidacionGeneralResult) -> ProyectoListItemOut:
        """Construir proyecto anidado para detail item desde campos planos."""
        return ProyectoListItemOut(
            id=result.proyecto_id or _uuid.UUID('00000000-0000-0000-0000-000000000000'),
            public_id=result.proyecto_public_id or '',
            nombre=result.proyecto_nombre or '',
            direccion=result.proyecto_direccion,
            valor_proyecto=0.0,
            entidad=TaludesPresenter._build_entidad_detail(result),
        )

    @staticmethod
    def present_detail_item(result: LiquidacionGeneralResult) -> LiquidacionTaludesListItemOut:
        """
        Transforma un LiquidacionGeneralResult (DTO plano) a LiquidacionTaludesListItemOut.

        Args:
            result: LiquidacionGeneralResult con campos planos del detalle

        Returns:
            LiquidacionTaludesListItemOut schema para respuesta HTTP de detalle
        """
        subtotal = float(result.subtotal) if result.subtotal else 0.0
        igv = float(result.igv) if result.igv else 0.0
        total = float(result.total) if result.total else 0.0
        total_a_pagar = float(result.total_a_pagar) if result.total_a_pagar else 0.0

        return LiquidacionTaludesListItemOut(
            id=result.id,
            public_id=result.public_id,
            tipo_liquidacion=result.tipo_liquidacion,
            estado=result.estado,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            proyecto=TaludesPresenter._build_proyecto_detail(result),
            entidad=TaludesPresenter._build_entidad_detail(result),
            municipalidad=MunicipalidadListItemOut(
                id=result.municipalidad_id or _uuid.UUID('00000000-0000-0000-0000-000000000000'),
                nombre=result.municipalidad_nombre or '',
                codigo=None,
                provincia=None,
                distrito=None,
            ),
            valores=ValoresListItemOut(
                subtotal=subtotal,
                igv=igv,
                total=total,
                total_a_pagar=total_a_pagar,
            ),
            proyectistas=[],
            delegados=[],
            contactos=[],
            revisiones=[],
        )
