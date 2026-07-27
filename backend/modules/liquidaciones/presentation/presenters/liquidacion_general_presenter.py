"""
LiquidacionGeneralPresenter — transforma resultados a esquemas HTTP para liquidaciones generales.
"""
import uuid as _uuid
from typing import Optional

from modules.liquidaciones.domain.schemas import (
    LiquidacionGeneralResult,
    LiquidacionGeneralListItem,
    DelegadosVigentesResult,
    InspectoresVigentesResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    LiquidacionGeneralOut,
    LiquidacionGeneralListItemOut,
    ProyectoGeneralOut,
    EntidadGeneralOut,
    ProyectoListItemOut,
    EntidadListItemOut,
    MunicipalidadListItemOut,
    ValoresListItemOut,
    ProyectistaListItemOut,
    DelegadoListItemOut,
    InspectorListItemOut,
    ContactoListItemOut,
    TarifaRevisionOut,
    EspecialidadRevisionOut,
    RevisionListItemOut,
    DelegadosVigentesOut,
    InspectoresVigentesOut,
)


class LiquidacionGeneralPresenter:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP
    para el controlador de liquidaciones generales.
    """

    @staticmethod
    def present(result: LiquidacionGeneralResult) -> LiquidacionGeneralOut:
        """
        Transforma un LiquidacionGeneralResult a LiquidacionGeneralOut.

        Args:
            result: LiquidacionGeneralResult con campos planos

        Returns:
            LiquidacionGeneralOut schema para respuesta HTTP
        """
        entidad = None
        if result.entidad_id or result.entidad_nombre:
            entidad = EntidadGeneralOut(
                id=result.entidad_id,
                tipo=result.entidad_tipo,
                nombre=result.entidad_nombre,
                ruc=result.entidad_ruc,
            )

        proyecto = None
        if result.proyecto_id or result.proyecto_nombre:
            proyecto = ProyectoGeneralOut(
                id=result.proyecto_id or _uuid.UUID('00000000-0000-0000-0000-000000000000'),
                public_id=result.proyecto_public_id or '',
                nombre=result.proyecto_nombre or '',
                direccion=result.proyecto_direccion,
            )

        subtotal = float(result.subtotal) if result.subtotal else 0.0
        igv = float(result.igv) if result.igv else 0.0
        total = float(result.total) if result.total else 0.0
        total_a_pagar = float(result.total_a_pagar) if result.total_a_pagar else 0.0

        return LiquidacionGeneralOut(
            id=result.id,
            public_id=result.public_id,
            estado=result.estado,
            tipo_liquidacion=result.tipo_liquidacion,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            expediente=result.expediente,
            observacion=result.observacion,
            municipalidad_nombre=result.municipalidad_nombre,
            proyecto=proyecto,
            entidad=entidad,
            subtotal=subtotal,
            igv=igv,
            total=total,
            total_a_pagar=total_a_pagar,
        )

    @staticmethod
    def _build_proyecto(result: LiquidacionGeneralListItem) -> ProyectoListItemOut:
        entidad = None
        if result.proyecto.entidad_id or result.proyecto.entidad_nombre:
            entidad = EntidadListItemOut(
                id=result.proyecto.entidad_id,
                tipo=result.proyecto.entidad_tipo,
                nombre=result.proyecto.entidad_nombre,
                ruc=result.proyecto.entidad_ruc,
            )
        return ProyectoListItemOut(
            id=result.proyecto.id,
            public_id=result.proyecto.public_id,
            nombre=result.proyecto.nombre,
            direccion=result.proyecto.direccion,
            valor_proyecto=result.proyecto.valor_proyecto,
            entidad=entidad,
        )

    @staticmethod
    def _build_entidad(result: LiquidacionGeneralListItem) -> Optional[EntidadListItemOut]:
        if not result.entidad or not result.entidad.id:
            return None
        return EntidadListItemOut(
            id=result.entidad.id,
            tipo=result.entidad.tipo,
            nombre=result.entidad.nombre,
            ruc=result.entidad.ruc,
        )

    @staticmethod
    def present_list_item(result: LiquidacionGeneralListItem) -> LiquidacionGeneralListItemOut:
        """
        Transforma un LiquidacionGeneralListItem a LiquidacionGeneralListItemOut.

        Args:
            result: LiquidacionGeneralListItem de la lista paginada

        Returns:
            LiquidacionGeneralListItemOut schema para respuesta HTTP
        """
        return LiquidacionGeneralListItemOut(
            id=result.id,
            public_id=result.public_id,
            estado=result.estado,
            tipo_liquidacion=result.tipo_liquidacion,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            tramite_accion=result.tramite_accion,
            tipo_tramite=result.tipo_tramite,
            expediente=result.expediente,
            observacion=result.observacion,
            proyecto=LiquidacionGeneralPresenter._build_proyecto(result),
            entidad=LiquidacionGeneralPresenter._build_entidad(result),
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
            inspectores=[
                InspectorListItemOut(
                    id=i.id,
                    perfil_ingeniero_id=i.perfil_ingeniero_id,
                    perfil_ingeniero_nombres=i.perfil_ingeniero_nombres,
                    perfil_ingeniero_apellidos=i.perfil_ingeniero_apellidos,
                    perfil_ingeniero_cip=i.perfil_ingeniero_cip,
                    especialidad_id=i.especialidad_id,
                    especialidad_nombre=i.especialidad_nombre,
                    tipo_liquidacion=i.tipo_liquidacion,
                    categoria=i.categoria,
                    numero_registro=i.numero_registro,
                    vigencia=i.vigencia.isoformat() if i.vigencia else None,
                ) for i in result.inspectores
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
                RevisionListItemOut(
                    id=r.id,
                    especialidades=[
                        EspecialidadRevisionOut(id=e.id, nombre=e.nombre)
                        for e in r.especialidades
                    ],
                    tarifa=TarifaRevisionOut(**r.tarifa.model_dump()) if r.tarifa else None,
                ) for r in result.revisiones
            ],
            subtotal=result.subtotal,
            igv=result.igv,
            total=result.total,
            total_a_pagar=result.total_a_pagar,
        )

    @staticmethod
    def present_list(
        results: list[LiquidacionGeneralListItem],
    ) -> list[LiquidacionGeneralListItemOut]:
        """
        Transforma una lista de LiquidacionGeneralListItem a lista de LiquidacionGeneralListItemOut.

        Args:
            results: Lista de LiquidacionGeneralListItem

        Returns:
            Lista de LiquidacionGeneralListItemOut
        """
        return [LiquidacionGeneralPresenter.present_list_item(r) for r in results]

    @staticmethod
    def present_delegados_vigentes(result: DelegadosVigentesResult) -> DelegadosVigentesOut:
        from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
            DelegadoVigenteOut,
            EspecialidadBasicaDelegadoOut,
        )

        return DelegadosVigentesOut(
            delegados=[
                DelegadoVigenteOut(
                    id=d.id,
                    nombre_completo=d.nombre_completo,
                    cip=d.cip,
                    especialidad=EspecialidadBasicaDelegadoOut(
                        id=d.especialidad.id,
                        nombre=d.especialidad.nombre,
                    ) if d.especialidad else None,
                    tipo=d.tipo,
                )
                for d in result.delegados
            ]
        )

    @staticmethod
    def present_inspectores_vigentes(result: InspectoresVigentesResult) -> InspectoresVigentesOut:
        from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
            InspectorVigenteOut,
            EspecialidadBasicaDelegadoOut,
        )

        return InspectoresVigentesOut(
            inspectores=[
                InspectorVigenteOut(
                    id=i.id,
                    nombre_completo=i.nombre_completo,
                    cip=i.cip,
                    especialidad=EspecialidadBasicaDelegadoOut(
                        id=i.especialidad.id,
                        nombre=i.especialidad.nombre,
                    ) if i.especialidad else None,
                    tipo_liquidacion=i.tipo_liquidacion,
                    categoria=i.categoria,
                    numero_registro=i.numero_registro,
                    vigencia=i.vigencia.isoformat(),
                )
                for i in result.inspectores
            ]
        )
