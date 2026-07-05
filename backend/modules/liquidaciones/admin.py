"""Admin — registration for liquidaciones models."""

from decimal import Decimal, ROUND_HALF_UP

from django.contrib import admin
from django import forms
from simple_history.admin import SimpleHistoryAdmin
from nested_admin import NestedModelAdmin, NestedTabularInline

from .models import (
    ContactoProyecto,
    Delegado,
    Especialidad,
    LiquidacionGeneral,
    LiquidacionContacto,
    LiquidacionDocumentos,
    LiquidacionEdificacion,
    LiquidacionEdificacionProxy,
    Proyecto,
    ProyectoEmpresarial,
    ProyectoPersonaNatural,
    Proyectista,
    LiquidacionDelegado,
    LiquidacionPorcentajeObra,
    MunicipalidadDelegado,
    ReglaTarifaEdificacion,
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)
from .domain.constants import EstadoLiquidacion, TipoTramiteEdificaciones, TramiteAccion

from modules.finanzas.models import IGV, UIT


class LiquidacionDelegadoInline(NestedTabularInline):
    """Inline para gestionar delegados asignados a una liquidación/revisión."""

    model = LiquidacionDelegado
    fk_name = "liquidacion"
    fields = [
        "delegado",
        "delegado_cip",
        "delegado_especialidad",
        "delegado_banco",
        "delegado_status",
    ]
    readonly_fields = [
        "delegado_cip",
        "delegado_especialidad",
        "delegado_banco",
        "delegado_status",
    ]
    extra = 1
    autocomplete_fields = ["delegado"]
    ordering = ["delegado__perfil_ingeniero__apellido_paterno"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "delegado__perfil_ingeniero",
                "delegado__especialidad",
                "delegado__banco",
            )
        )

    def delegado_cip(self, obj):
        if obj and obj.pk and obj.delegado_id:
            return obj.delegado.perfil_ingeniero.cip
        return "-"

    delegado_cip.short_description = "CIP"

    def delegado_especialidad(self, obj):
        if obj and obj.pk and obj.delegado_id:
            return str(obj.delegado.especialidad)
        return "-"

    delegado_especialidad.short_description = "Especialidad"

    def delegado_banco(self, obj):
        if obj and obj.pk and obj.delegado_id and obj.delegado.banco:
            return obj.delegado.banco.nombre
        return "-"

    delegado_banco.short_description = "Banco"

    def delegado_status(self, obj):
        if obj and obj.pk and obj.delegado_id:
            return obj.delegado.get_status_display()
        return "-"

    delegado_status.short_description = "Estado"


class RevisionInline(NestedTabularInline):
    """
    Inline para ver reingresos/subsiguientes liquidaciones vinculadas.

    NOTA: liquidacion_previa era FK singular en LiquidacionGeneral, ahora es M2M liquidaciones_previas.
    Este inline ya no funciona con el fk_name anterior — necesita ser adaptado.
    Por ahora se deshabilita el inline hasta que se reimplemente con M2M.
    """
    # model = LiquidacionGeneral
    # fk_name = "liquidacion_previa"  # YA NO EXISTE - liquidacion_previa es ahora M2M liquidaciones_previas
    fields = ["delegados_resumen", "created_at"]
    extra = 0
    readonly_fields = ["delegados_resumen", "created_at"]
    ordering = ["-created_at"]
    show_change_link = True
    # inlines = [LiquidacionDelegadoInline]  # Deshabilitado hasta reimplementar con M2M

    def delegados_resumen(self, obj):
        if not obj:
            return "-"
        rd_list = list(
            obj.liquidacion_delegados.select_related(
                "delegado__perfil_ingeniero",
                "delegado__especialidad",
            ).order_by("delegado__perfil_ingeniero__apellido_paterno")[:4]
        )
        rd_count = len(rd_list)
        if rd_count == 0:
            return "Sin delegados"
        rd_list_orig = rd_list[:3]
        nombres = [rd.delegado.perfil_ingeniero.apellido_paterno for rd in rd_list_orig]
        if rd_count > 3:
            return f"{', '.join(nombres)} (+{rd_count - 3})"
        return f"{', '.join(nombres)}"

    delegados_resumen.short_description = "Delegados"


@admin.register(Delegado)
class DelegadoAdmin(SimpleHistoryAdmin):
    list_display = ["perfil_ingeniero", "especialidad", "banco", "status"]
    list_filter = ["status", "especialidad", "banco"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__apellido_materno",
        "perfil_ingeniero__cip",
        "especialidad__nombre",
        "banco__nombre",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["perfil_ingeniero", "especialidad", "banco"]
    ordering = [
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__apellido_materno",
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("perfil_ingeniero", "especialidad", "banco")
        )


@admin.register(MunicipalidadDelegado)
class MunicipalidadDelegadoAdmin(SimpleHistoryAdmin):
    list_display = [
        "delegado",
        "municipalidad",
        "tipo",
        "activo",
        "delegado_cip",
        "delegado_especialidad",
    ]
    list_filter = [
        "activo",
        "tipo",
        "municipalidad",
        "delegado__status",
        "delegado__especialidad",
    ]
    search_fields = [
        "delegado__perfil_ingeniero__nombres",
        "delegado__perfil_ingeniero__apellido_paterno",
        "delegado__perfil_ingeniero__apellido_materno",
        "delegado__perfil_ingeniero__cip",
        "municipalidad__nombre",
        "municipalidad__codigo",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["delegado", "municipalidad"]
    ordering = [
        "delegado__perfil_ingeniero__apellido_paterno",
        "delegado__perfil_ingeniero__apellido_materno",
        "municipalidad__nombre",
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "delegado__perfil_ingeniero",
                "delegado__especialidad",
                "municipalidad",
            )
        )

    def delegado_cip(self, obj):
        if obj and obj.pk and obj.delegado_id and obj.delegado.perfil_ingeniero_id:
            return obj.delegado.perfil_ingeniero.cip
        return "-"

    delegado_cip.short_description = "CIP"
    delegado_cip.boolean = False

    def delegado_especialidad(self, obj):
        if obj and obj.pk and obj.delegado_id:
            return str(obj.delegado.especialidad)
        return "-"

    delegado_especialidad.short_description = "Especialidad"
    delegado_especialidad.boolean = False


@admin.register(Proyectista)
class ProyectistaAdmin(SimpleHistoryAdmin):
    list_display = ["perfil_ingeniero", "especialidad", "descripcion"]
    list_filter = ["especialidad"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__apellido_materno",
        "perfil_ingeniero__cip",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["perfil_ingeniero__apellido_paterno", "perfil_ingeniero__apellido_materno", "perfil_ingeniero__nombres"]
    autocomplete_fields = ["perfil_ingeniero", "especialidad"]

    def perfil_ingeniero(self, obj):
        if obj.perfil_ingeniero:
            return f"{obj.perfil_ingeniero.apellido_paterno} {obj.perfil_ingeniero.apellido_materno}, {obj.perfil_ingeniero.nombres}"
        return "-"

    perfil_ingeniero.short_description = "Perfil Ingeniero"


@admin.register(Proyecto)
class ProyectoAdmin(SimpleHistoryAdmin):
    list_display = [
        "denominacion",
        "entidad",
        "nombre_propietario",
    ]
    search_fields = [
        "denominacion",
        "nombre_propietario",
        "entidad__razon_social",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["denominacion"]
    autocomplete_fields = ["entidad"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("entidad")
        )

    def entity_display(self, obj):
        if obj.entidad:
            return str(obj.entidad)
        return "-"

    entity_display.short_description = "Entidad"


@admin.register(ProyectoEmpresarial)
class ProyectoEmpresarialAdmin(SimpleHistoryAdmin):
    list_display = [
        "denominacion",
        "entidad",
        "nombre_propietario",
    ]
    search_fields = ["denominacion", "entidad__razon_social"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["denominacion"]
    autocomplete_fields = ["entidad"]

    def get_queryset(self, request):
        return ProyectoEmpresarial.objects.all()


@admin.register(ProyectoPersonaNatural)
class ProyectoPersonaNaturalAdmin(SimpleHistoryAdmin):
    list_display = [
        "denominacion",
        "entidad",
        "nombre_propietario",
    ]
    search_fields = [
        "denominacion",
        "entidad__razon_social",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["denominacion"]
    autocomplete_fields = ["entidad"]

    def get_queryset(self, request):
        return ProyectoPersonaNatural.objects.all()


@admin.register(ContactoProyecto)
class ContactoProyectoAdmin(SimpleHistoryAdmin):
    list_display = ["proyecto", "contacto", "principal", "activo"]
    list_filter = ["principal", "activo"]
    search_fields = [
        "proyecto__denominacion",
        "contacto__nombres",
        "contacto__apellidos",
    ]
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionEdificacionInline(NestedTabularInline):
    """Inline para gestionar el perfil de Edificacion de una LiquidacionGeneral."""

    model = LiquidacionEdificacion
    fk_name = "liquidacion"
    # NOTE: valor_proyecto y valor_base_calculo viven en LiquidacionPorcentajeObra, no aqui
    fields = ["tipo_tramite", "tramite_accion"]
    readonly_fields = ["created_at", "updated_at"]
    extra = 1


@admin.register(LiquidacionEdificacionProxy)
class LiquidacionEdificacionProxyAdmin(NestedModelAdmin, SimpleHistoryAdmin):
    """
    Admin proxy para crear/editar Liquidaciones del régimen Edificacion.
    Internamente crea un registro LiquidacionGeneral (padre) con LiquidacionEdificacion
    como inline hijo — el flujo Django estándar parent+inline.
    """

    list_display = [
        "liquidacion_proxy_numero_revision",
        "proyecto",
        "estado",
        "igv",
        "uit",
        "delegados_display",
        "created_at",
    ]
    list_filter = ["estado", "created_at", "igv", "uit"]
    search_fields = [
        "proyecto__denominacion",
        "proyecto__entidad__razon_social",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "proyecto_resumen",
        "liquidacion_previa_resumen",
        "delegados_display",
        "igv_porcentaje",
        "uit_porcentaje",
        "calculo_valor_obra",
        "calculo_subtotal",
        "calculo_igv",
        "calculo_total",
    ]
    fieldsets = (
        (
            "Datos de la liquidación",
            {
                "fields": (
                    "proyecto",
                    "proyecto_resumen",
                    "estado",
                    "liquidacion_previa_resumen",
                )
            },
        ),
        (
            "Configuración financiera",
            {
                "fields": (
                    "igv",
                    "igv_porcentaje",
                    "uit",
                    "uit_porcentaje",
                ),
                "description": "Debajo de cada referencia se muestra el dato aplicado de su tabla relacionada.",
            },
        ),
        (
            "Cálculo referencial",
            {
                "fields": (
                    "calculo_valor_obra",
                    "calculo_subtotal",
                    "calculo_igv",
                    "calculo_total",
                ),
                "description": "Cálculo referencial usando el valor de obra del proyecto y el IGV seleccionado.",
            },
        ),
        (
            "Delegados asignados",
            {
                "fields": ("delegados_display",),
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-created_at"]
    autocomplete_fields = [
        "proyecto",
        "igv",
        "uit",
    ]
    inlines = [LiquidacionEdificacionInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "proyecto",
                "proyecto__entidad",
                "igv",
                "uit",
            )
            .prefetch_related("edificaciones")
        )

    def liquidacion_proxy_numero_revision(self, obj):
        """Muestra numero_revision desde LiquidacionGeneral (fuente de verdad)."""
        try:
            return obj.numero_revision if obj else "-"
        except Exception:
            return "-"

    liquidacion_proxy_numero_revision.short_description = "N° Revisión"

    # ── Métodos de cálculo (reusados de LiquidacionGeneralAdmin) ──

    def proyecto_resumen(self, obj):
        if not obj or not obj.proyecto_id:
            return "-"
        proyecto = obj.proyecto
        entidad = getattr(proyecto, "entidad", None)
        entidad_txt = f" — {entidad}" if entidad else ""
        return f"{proyecto.denominacion}{entidad_txt}"

    proyecto_resumen.short_description = "Datos del proyecto"

    def liquidacion_previa_resumen(self, obj):
        if not obj or not hasattr(obj, 'edificaciones') or not obj.edificaciones:
            return "-"
        previas = list(obj.liquidaciones_previas.order_by('-created_at')[:1])
        if not previas:
            return "-"
        previa = previas[0]
        try:
            num_rev = previa.numero_revision if hasattr(previa, 'numero_revision') else "?"
        except Exception:
            num_rev = "?"
        return f"Revisión {num_rev} — {previa.proyecto} — {previa.estado}"

    liquidacion_previa_resumen.short_description = "Datos de liquidación previa"

    def igv_porcentaje(self, obj):
        if obj and obj.igv_id:
            return f"{float(obj.igv.valor) * 100:.2f}%"
        return "-"

    igv_porcentaje.short_description = "IGV %"

    def uit_porcentaje(self, obj):
        if obj and obj.uit_id:
            return f"S/ {obj.uit.valor}"
        return "-"

    uit_porcentaje.short_description = "UIT"

    def _money(self, value):
        if value is None:
            return "-"
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculo_subtotal(self, obj):
        if not obj or not obj.proyecto_id:
            return None
        return obj.proyecto.valor_obra

    def calculo_valor_obra(self, obj):
        if obj and obj.proyecto_id:
            # Leer desde LiquidacionPorcentajeObra (valor_proyecto)
            if hasattr(obj, 'liquidacion_porcentaje_obra') and obj.liquidacion_porcentaje_obra.exists():
                lpo = obj.liquidacion_porcentaje_obra.first()
                if lpo and lpo.valor_proyecto:
                    return self._money(lpo.valor_proyecto)
            return self._money(obj.proyecto.valor_obra)
        return "-"

    calculo_valor_obra.short_description = "Valor de obra"

    def calculo_subtotal(self, obj):
        return self._money(self._calculo_subtotal(obj))

    calculo_subtotal.short_description = "Subtotal"

    def calculo_igv(self, obj):
        subtotal = self._calculo_subtotal(obj)
        if subtotal is None or not obj.igv_id:
            return "-"
        igv_amount = subtotal * obj.igv.valor
        return f"{self._money(igv_amount)} ({float(obj.igv.valor) * 100:.2f}%)"

    calculo_igv.short_description = "IGV"

    def calculo_total(self, obj):
        subtotal = self._calculo_subtotal(obj)
        if subtotal is None or not obj.igv_id:
            return "-"
        igv_amount = subtotal * obj.igv.valor
        return self._money(subtotal + igv_amount)

    calculo_total.short_description = "Total"

    def delegados_display(self, obj):
        rd_list = list(
            obj.liquidacion_delegados.select_related(
                "delegado__perfil_ingeniero",
                "delegado__especialidad",
            ).order_by("delegado__perfil_ingeniero__apellido_paterno")[:6]
        )
        if not rd_list:
            return "-"
        if len(rd_list) > 5:
            nombres = [str(rd.delegado) for rd in rd_list[:5]]
            return ", ".join(nombres) + f" (+{len(rd_list) - 5} más)"
        nombres = [str(rd.delegado) for rd in rd_list]
        return ", ".join(nombres)

    delegados_display.short_description = "Delegados"


@admin.register(LiquidacionGeneral)
class LiquidacionGeneralAdmin(NestedModelAdmin, SimpleHistoryAdmin):
    list_display = [
        "liquidacion_numero_revision",
        "proyecto",
        "estado",
        "igv",
        "uit",
        "delegados_display",
        "created_at",
    ]
    list_filter = ["estado", "created_at", "igv", "uit"]
    search_fields = ["proyecto__denominacion", "proyecto__entidad__razon_social"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "proyecto_resumen",
        "liquidacion_previa_resumen",
        "delegados_display",
        "igv_porcentaje",
        "uit_porcentaje",
        "calculo_valor_obra",
        "calculo_subtotal",
        "calculo_igv",
        "calculo_total",
    ]
    fieldsets = (
        (
            "Datos de la liquidación",
            {
                "fields": (
                    "proyecto",
                    "proyecto_resumen",
                    "estado",
                    "liquidacion_previa_resumen",
                )
            },
        ),
        (
            "Configuración financiera",
            {
                "fields": (
                    "igv",
                    "igv_porcentaje",
                    "uit",
                    "uit_porcentaje",
                ),
                "description": "Debajo de cada referencia se muestra el dato aplicado de su tabla relacionada.",
            },
        ),
        (
            "Cálculo referencial",
            {
                "fields": (
                    "calculo_valor_obra",
                    "calculo_subtotal",
                    "calculo_igv",
                    "calculo_total",
                ),
                "description": "Cálculo referencial usando el valor de obra del proyecto y el IGV seleccionado.",
            },
        ),
        (
            "Delegados asignados",
            {
                "fields": ("delegados_display",),
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    ordering = ["-created_at"]
    autocomplete_fields = [
        "proyecto",
        "igv",
        "uit",
    ]
    inlines = [LiquidacionDelegadoInline, LiquidacionEdificacionInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "proyecto",
                "proyecto__entidad",
                "igv",
                "uit",
            )
            .prefetch_related("edificaciones")
        )

    def liquidacion_numero_revision(self, obj):
        """Muestra numero_revision desde LiquidacionGeneral (fuente de verdad)."""
        try:
            return obj.numero_revision if obj else "-"
        except Exception:
            return "-"

    liquidacion_numero_revision.short_description = "N° Revisión"

    def proyecto_resumen(self, obj):
        if not obj or not obj.proyecto_id:
            return "-"
        proyecto = obj.proyecto
        entidad = getattr(proyecto, "entidad", None)
        entidad_txt = f" — {entidad}" if entidad else ""
        return f"{proyecto.denominacion}{entidad_txt}"

    proyecto_resumen.short_description = "Datos del proyecto"

    def liquidacion_previa_resumen(self, obj):
        if not obj:
            return "-"
        previas = list(obj.liquidaciones_previas.order_by('-created_at')[:1])
        if not previas:
            return "-"
        previa = previas[0]
        try:
            num_rev = previa.numero_revision if hasattr(previa, 'numero_revision') else "?"
        except Exception:
            num_rev = "?"
        return f"Revisión {num_rev} — {previa.proyecto} — {previa.estado}"

    liquidacion_previa_resumen.short_description = "Datos de liquidación previa"

    def igv_porcentaje(self, obj):
        if obj and obj.igv_id:
            return f"{float(obj.igv.valor) * 100:.2f}%"
        return "-"

    igv_porcentaje.short_description = "IGV %"

    def uit_porcentaje(self, obj):
        if obj and obj.uit_id:
            return f"S/ {obj.uit.valor}"
        return "-"

    uit_porcentaje.short_description = "UIT"

    def _money(self, value):
        if value is None:
            return "-"
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculo_subtotal(self, obj):
        if not obj or not obj.proyecto_id:
            return None
        return obj.proyecto.valor_obra

    def calculo_valor_obra(self, obj):
        if obj and obj.proyecto_id:
            # Leer desde LiquidacionPorcentajeObra (valor_proyecto)
            if hasattr(obj, 'liquidacion_porcentaje_obra') and obj.liquidacion_porcentaje_obra.exists():
                lpo = obj.liquidacion_porcentaje_obra.first()
                if lpo and lpo.valor_proyecto:
                    return self._money(lpo.valor_proyecto)
            return self._money(obj.proyecto.valor_obra)
        return "-"

    calculo_valor_obra.short_description = "Valor de obra"

    def calculo_subtotal(self, obj):
        return self._money(self._calculo_subtotal(obj))

    calculo_subtotal.short_description = "Subtotal"

    def calculo_igv(self, obj):
        subtotal = self._calculo_subtotal(obj)
        if subtotal is None or not obj.igv_id:
            return "-"
        igv_amount = subtotal * obj.igv.valor
        return f"{self._money(igv_amount)} ({float(obj.igv.valor) * 100:.2f}%)"

    calculo_igv.short_description = "IGV"

    def calculo_total(self, obj):
        subtotal = self._calculo_subtotal(obj)
        if subtotal is None or not obj.igv_id:
            return "-"
        igv_amount = subtotal * obj.igv.valor
        return self._money(subtotal + igv_amount)

    calculo_total.short_description = "Total"

    def delegados_display(self, obj):
        rd_list = list(
            obj.liquidacion_delegados.select_related(
                "delegado__perfil_ingeniero",
                "delegado__especialidad",
            ).order_by("delegado__perfil_ingeniero__apellido_paterno")[:6]
        )
        if not rd_list:
            return "-"
        if len(rd_list) > 5:
            nombres = [str(rd.delegado) for rd in rd_list[:5]]
            return ", ".join(nombres) + f" (+{len(rd_list) - 5} más)"
        nombres = [str(rd.delegado) for rd in rd_list]
        return ", ".join(nombres)

    delegados_display.short_description = "Delegados"


class LiquidacionEdificacionForm(forms.ModelForm):
    """
    Formulario para crear/editar LiquidacionEdificacion.
    Expone campos de LiquidacionEdificacion (tipo_tramite, tramite_accion).
    Los valores de cálculo (valor_proyecto, valor_base_calculo) viven en LiquidacionPorcentajeObra.
    """

    class Meta:
        model = LiquidacionEdificacion
        fields = ["tipo_tramite", "tramite_accion"]


@admin.register(LiquidacionEdificacion)
class LiquidacionEdificacionAdmin(NestedModelAdmin, SimpleHistoryAdmin):
    """
    Admin para LiquidacionEdificacion.
    Muestra el tipo de trámite y acción, más datos de la LiquidacionGeneral padre.
    Los valores de cálculo (valor_proyecto, valor_base_calculo) se leen desde LiquidacionPorcentajeObra.
    """
    list_display = ["liquidacion", "numero_revision_display", "created_at"]
    list_filter = ["liquidacion__estado"]
    search_fields = [
        "liquidacion__proyecto__denominacion",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "liquidacion",
        "proyecto_resumen",
        "liquidacion_previa_resumen",
        "delegados_display",
        "igv_porcentaje",
        "uit_porcentaje",
        "calculo_valor_obra",
        "calculo_subtotal",
        "calculo_igv",
        "calculo_total",
        "valor_proyecto_display",
        "valor_base_calculo_display",
    ]
    autocomplete_fields = []
    ordering = ["-created_at"]
    form = LiquidacionEdificacionForm

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "liquidacion__proyecto",
                "liquidacion__proyecto__entidad",
                "liquidacion__igv",
                "liquidacion__uit",
            )
            .prefetch_related("liquidacion__liquidacion_porcentaje_obra__tarifa_aplicada")
        )

    def get_changeform_initial_data(self, request):
        """Pre-llenar usuario_creador con el usuario actual."""
        return {"usuario_creador": request.user.pk}

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj) or [])
        if obj is not None:
            readonly.append("liquidacion")
        return readonly

    def numero_revision_display(self, obj):
        try:
            return obj.liquidacion.numero_revision if obj and obj.liquidacion else "?"
        except Exception:
            return "?"

    numero_revision_display.short_description = "N° Revisión"

    def valor_proyecto_display(self, obj):
        """Muestra valor_proyecto desde LiquidacionPorcentajeObra."""
        if obj and obj.liquidacion_id:
            lpo_qs = LiquidacionPorcentajeObra.objects.filter(liquidacion_general=obj.liquidacion)
            if lpo_qs.exists():
                return self._money(lpo_qs.first().valor_proyecto)
        return "-"

    valor_proyecto_display.short_description = "Valor Proyecto"

    def valor_base_calculo_display(self, obj):
        """Muestra valor_base_calculo desde LiquidacionPorcentajeObra."""
        if obj and obj.liquidacion_id:
            lpo_qs = LiquidacionPorcentajeObra.objects.filter(liquidacion_general=obj.liquidacion)
            if lpo_qs.exists():
                return self._money(lpo_qs.first().valor_base_calculo)
        return "-"

    valor_base_calculo_display.short_description = "Valor Base Cálculo"

    def proyecto_resumen(self, obj):
        liq = obj.liquidacion if obj else None
        if not liq or not liq.proyecto_id:
            return "-"
        proyecto = liq.proyecto
        entidad = getattr(proyecto, "entidad", None)
        entidad_txt = f" — {entidad}" if entidad else ""
        return f"{proyecto.denominacion}{entidad_txt}"

    proyecto_resumen.short_description = "Datos del proyecto"

    def liquidacion_previa_resumen(self, obj):
        liq = obj.liquidacion if obj else None
        if not liq:
            return "-"
        previas = list(liq.liquidaciones_previas.order_by('-created_at')[:1])
        if not previas:
            return "-"
        previa = previas[0]
        try:
            num_rev = previa.numero_revision if hasattr(previa, 'numero_revision') else "?"
        except Exception:
            num_rev = "?"
        return f"Revisión {num_rev} — {previa.proyecto} — {previa.estado}"

    liquidacion_previa_resumen.short_description = "Datos de liquidación previa"

    def igv_porcentaje(self, obj):
        liq = obj.liquidacion if obj else None
        if liq and liq.igv_id:
            return f"{float(liq.igv.valor) * 100:.2f}%"
        return "-"

    igv_porcentaje.short_description = "IGV %"

    def uit_porcentaje(self, obj):
        liq = obj.liquidacion if obj else None
        if liq and liq.uit_id:
            return f"S/ {liq.uit.valor}"
        return "-"

    uit_porcentaje.short_description = "UIT"

    def _money(self, value):
        if value is None:
            return "-"
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculo_subtotal(self, obj):
        """Calcula desde LiquidacionPorcentajeObra si existe."""
        if not obj or not obj.liquidacion_id:
            return None
        lpo_qs = LiquidacionPorcentajeObra.objects.filter(liquidacion_general=obj.liquidacion)
        if lpo_qs.exists():
            return lpo_qs.first().valor_proyecto
        return obj.liquidacion.proyecto.valor_obra if obj.liquidacion and obj.liquidacion.proyecto else None

    def calculo_valor_obra(self, obj):
        """Muestra valor de obra desde LiquidacionPorcentajeObra."""
        if obj and obj.liquidacion_id:
            lpo_qs = LiquidacionPorcentajeObra.objects.filter(liquidacion_general=obj.liquidacion)
            if lpo_qs.exists():
                return self._money(lpo_qs.first().valor_proyecto)
        return "-"

    calculo_valor_obra.short_description = "Valor de obra"

    def calculo_subtotal(self, obj):
        return self._money(self._calculo_subtotal(obj))

    calculo_subtotal.short_description = "Subtotal"

    def calculo_igv(self, obj):
        subtotal = self._calculo_subtotal(obj)
        liq = obj.liquidacion if obj else None
        if subtotal is None or not liq or not liq.igv_id:
            return "-"
        igv_amount = subtotal * liq.igv.valor
        return f"{self._money(igv_amount)} ({float(liq.igv.valor) * 100:.2f}%)"

    calculo_igv.short_description = "IGV"

    def calculo_total(self, obj):
        subtotal = self._calculo_subtotal(obj)
        liq = obj.liquidacion if obj else None
        if subtotal is None or not liq or not liq.igv_id:
            return "-"
        igv_amount = subtotal * liq.igv.valor
        return self._money(subtotal + igv_amount)

    calculo_total.short_description = "Total"

    def delegados_display(self, obj):
        liq = obj.liquidacion if obj else None
        if not liq:
            return "-"
        rd_list = list(
            liq.liquidacion_delegados.select_related(
                "delegado__perfil_ingeniero",
                "delegado__especialidad",
            ).order_by("delegado__perfil_ingeniero__apellido_paterno")[:6]
        )
        if not rd_list:
            return "-"
        if len(rd_list) > 5:
            nombres = [str(rd.delegado) for rd in rd_list[:5]]
            return ", ".join(nombres) + f" (+{len(rd_list) - 5} más)"
        nombres = [str(rd.delegado) for rd in rd_list]
        return ", ".join(nombres)

    delegados_display.short_description = "Delegados"

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return [
                (
                    "Datos de la liquidación",
                    {
                        "fields": (
                            "liquidacion",
                            "tipo_tramite",
                            "tramite_accion",
                        ),
                    },
                ),
            ]
        else:
            return [
                (
                    "Datos de la liquidación",
                    {
                        "fields": (
                            "liquidacion",
                            "proyecto_resumen",
                            "numero_revision_display",
                            "estado",
                            "liquidacion_previa_resumen",
                        ),
                    },
                ),
                (
                    "Configuración financiera",
                    {
                        "fields": (
                            "igv",
                            "igv_porcentaje",
                            "uit",
                            "uit_porcentaje",
                            "valor_proyecto_display",
                            "valor_base_calculo_display",
                        ),
                    },
                ),
                (
                    "Cálculo referencial",
                    {
                        "fields": (
                            "calculo_valor_obra",
                            "calculo_subtotal",
                            "calculo_igv",
                            "calculo_total",
                        ),
                    },
                ),
                (
                    "Delegados asignados",
                    {
                        "fields": ("delegados_display",),
                    },
                ),
                (
                    "Auditoría",
                    {
                        "fields": ("created_at", "updated_at"),
                        "classes": ("collapse",),
                    },
                ),
            ]


@admin.register(LiquidacionDelegado)
class LiquidacionDelegadoAdmin(SimpleHistoryAdmin):
    list_display = [
        "liquidacion_public_id",
        "numero_revision_display",
        "proyecto",
        "delegado",
        "periodo",
        "dictamen_revision",
        "fecha_presentacion",
        "fecha_revision",
    ]
    list_filter = [
        "delegado__especialidad",
        "dictamen_revision",
        "periodo",
    ]
    search_fields = [
        "liquidacion__public_id",
        "liquidacion__proyecto__denominacion",
        "delegado__perfil_ingeniero__nombres",
        "delegado__perfil_ingeniero__apellido_paterno",
        "delegado__perfil_ingeniero__apellido_materno",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["liquidacion", "delegado"]
    ordering = ["-liquidacion__created_at", "delegado"]
    date_hierarchy = "fecha_presentacion"

    def liquidacion_public_id(self, obj):
        return obj.liquidacion.public_id or str(obj.liquidacion_id)

    liquidacion_public_id.short_description = "Liq. N°"
    liquidacion_public_id.admin_order_field = "liquidacion__public_id"

    def numero_revision_display(self, obj):
        """Obtiene numero_revision desde LiquidacionGeneral (fuente de verdad)."""
        try:
            # numero_revision vive en LiquidacionGeneral, no en LiquidacionEdificacion
            return obj.liquidacion.numero_revision if hasattr(obj.liquidacion, 'numero_revision') else "?"
        except Exception:
            return "?"

    numero_revision_display.short_description = "N° Revisión"

    def proyecto(self, obj):
        return obj.liquidacion.proyecto

    proyecto.short_description = "Proyecto"


@admin.register(IGV)
class IGVAdmin(SimpleHistoryAdmin):
    list_display = ["valor", "periodo_inicio", "periodo_fin"]
    list_filter = ["periodo_inicio"]
    search_fields = ["valor"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-periodo_inicio"]


@admin.register(Especialidad)
class EspecialidadAdmin(SimpleHistoryAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]


@admin.register(UIT)
class UITAdmin(SimpleHistoryAdmin):
    list_display = ["valor", "periodo_inicio", "periodo_fin"]
    list_filter = ["periodo_inicio"]
    search_fields = ["valor"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-periodo_inicio"]


@admin.register(ReglaTarifaEdificacion)
class ReglaTarifaEdificacionAdmin(SimpleHistoryAdmin):
    """Admin para ReglaTarifaEdificacion."""
    list_display = ["tipo_tramite", "tramite_accion", "tarifa_base", "tarifa_porcentaje_display"]
    list_filter = ["tipo_tramite", "tramite_accion"]
    search_fields = [
        "tarifa_base__detalle_porcentual__porcentaje_liquidacion",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["tipo_tramite", "tramite_accion"]

    def tarifa_porcentaje_display(self, obj):
        """Muestra el porcentaje de la tarifa base."""
        if obj and obj.tarifa_base_id:
            try:
                detalle = obj.tarifa_base.detalle_porcentual
                if detalle:
                    return f"{float(detalle.porcentaje_liquidacion) * 100:.2f}%"
            except Exception:
                pass
        return "-"

    tarifa_porcentaje_display.short_description = "% Tarifa"


@admin.register(TarifaLiquidacionBase)
class TarifaLiquidacionBaseAdmin(SimpleHistoryAdmin):
    """Admin para TarifaLiquidacionBase."""
    list_display = [
        "id",
        "tipo_liquidacion",
        "periodo_inicio",
        "periodo_fin",
        "especialidades_display",
        "created_at",
    ]
    list_filter = ["tipo_liquidacion", "periodo_inicio"]
    search_fields = [
        "tipo_liquidacion",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-periodo_inicio"]
    filter_horizontal = ["especialidades"]

    def especialidades_display(self, obj):
        if not obj:
            return "-"
        specs = list(obj.especialidades.all())
        if not specs:
            return "-"
        if len(specs) <= 4:
            return ", ".join([s.nombre for s in specs])
        return ", ".join([s.nombre for s in specs[:4]]) + f" (+{len(specs) - 4})"

    especialidades_display.short_description = "Especialidades"


@admin.register(TarifaPorcentajeObra)
class TarifaPorcentajeObraAdmin(SimpleHistoryAdmin):
    """Admin para TarifaPorcentajeObra."""
    list_display = [
        "id",
        "tarifa_base",
        "porcentaje_liquidacion_display",
        "derecho_minimo",
        "derecho_maximo",
        "porcentaje_minimo_uit",
        "created_at",
    ]
    list_filter = []
    search_fields = [
        "tarifa_base__tipo_liquidacion",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def porcentaje_liquidacion_display(self, obj):
        if obj and obj.porcentaje_liquidacion is not None:
            return f"{float(obj.porcentaje_liquidacion) * 100:.4f}%"
        return "-"

    porcentaje_liquidacion_display.short_description = "% Liquidación"


# EdificacionesClasificacion model moved to domain — admin registration pending model availability.


# Legacy models removed from admin registration:
# - EdificacionesEspecialidades: usar EspecialidadesLiquidacion
# - EdificacionesTarifa: usar TarifaLiquidacionBase + TarifaPorcentajeObra
# - EdificacionesRevision: usar TarifaLiquidacionBase + TarifaPorcentajeObra
# Estos modelos aún existen en el código (no eliminados) por si se necesitan para migración,
# pero no están registrados en admin ni exportados como parte activa de la arquitectura.


# EdificacionesClasificacionEspecialidades model removed - specialties now stored
# directly on EdificacionesClasificacion via M2M field.
# Admin registration removed.


# TipoLiquidacion model no longer exists - admin registration removed
# @admin.register(TipoLiquidacion)
# class TipoLiquidacionAdmin(SimpleHistoryAdmin):
#     list_display = ["nombre", "porcentaje_derecho_minimo", "periodo_inicio", "periodo_fin", "especialidades_resumen"]
#     list_filter = ["periodo_inicio", "especialidades"]
#     search_fields = ["nombre", "especialidades__nombre"]
#     readonly_fields = ["created_at", "updated_at", "especialidades_resumen"]
#     filter_horizontal = ["especialidades"]
#     ordering = ["-periodo_inicio"]
#
#     def especialidades_resumen(self, obj):
#         if obj:
#             especialidades = obj.especialidades.all()
#             if not especialidades:
#                 return "-"
#             nombres = [str(e) for e in especialidades]
#             if len(nombres) > 4:
#                 return ", ".join(nombres[:4]) + f" (+{len(nombres) - 4})"
#             return ", ".join(nombres)
#         return "-"
#
#     especialidades_resumen.short_description = "Especialidades"
