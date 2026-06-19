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
    LiquidacionEdificaciones,
    LiquidacionEdificacionesProxy,
    EdificacionesTarifa,
    EdificacionesRevision,
    Proyecto,
    ProyectoEmpresarial,
    ProyectoPersonaNatural,
    Proyectista,
    RevisionDelegado,
)
from .domain.constants import EstadoLiquidacion, TipoTramiteEdificaciones, TramiteAccion

from modules.finanzas.models import IGV, UIT


class RevisionDelegadoInline(NestedTabularInline):
    """Inline para gestionar delegados asignados a una liquidación/revisión."""

    model = RevisionDelegado
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
    # inlines = [RevisionDelegadoInline]  # Deshabilitado hasta reimplementar con M2M

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
    list_display = ["perfil_ingeniero", "tipo_display", "especialidad", "banco", "status"]
    list_filter = ["tipo", "status", "especialidad", "banco"]
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

    def tipo_display(self, obj):
        return obj.get_tipo_display()

    tipo_display.short_description = "Tipo"


@admin.register(Proyectista)
class ProyectistaAdmin(SimpleHistoryAdmin):
    list_display = ["nombres", "apellidos"]
    search_fields = ["nombres", "apellidos"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["apellidos", "nombres"]


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
        "entidad__apellidos",
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
        "entidad__nombres",
        "entidad__apellidos",
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


class LiquidacionEdificacionesInline(NestedTabularInline):
    """Inline para gestionar el perfil de Edificaciones de una LiquidacionGeneral."""

    model = LiquidacionEdificaciones
    fk_name = "liquidacion"
    fields = ["revisiones"]
    readonly_fields = ["created_at", "updated_at"]
    extra = 1


@admin.register(LiquidacionEdificacionesProxy)
class LiquidacionEdificacionesProxyAdmin(NestedModelAdmin, SimpleHistoryAdmin):
    """
    Admin proxy para crear/editar Liquidaciones del régimen Edificaciones.
    Internamente crea un registro LiquidacionGeneral (padre) con LiquidacionEdificaciones
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
        "proyecto__entidad__apellidos",
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
                    "valor_proyecto",
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
    inlines = [LiquidacionEdificacionesInline]

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
        """Muestra numero_revision desde LiquidacionEdificaciones inline."""
        try:
            return obj.edificaciones.numero_revision if hasattr(obj, 'edificaciones') and obj.edificaciones else "-"
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
        # liquidacion_previa ahora es M2M liquidaciones_previas
        previas = list(obj.liquidaciones_previas.order_by('-created_at')[:1])
        if not previas:
            return "-"
        previa = previas[0]
        try:
            num_rev = previa.edificaciones.numero_revision if hasattr(previa, 'edificaciones') and previa.edificaciones else "?"
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
    search_fields = ["proyecto__denominacion", "proyecto__entidad__razon_social", "proyecto__entidad__apellidos"]
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
                    "valor_proyecto",
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
    inlines = [RevisionDelegadoInline, LiquidacionEdificacionesInline]

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
        """Muestra numero_revision desde LiquidacionEdificaciones."""
        try:
            return obj.edificaciones.numero_revision if hasattr(obj, 'edificaciones') and obj.edificaciones else "-"
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
            num_rev = previa.edificaciones.numero_revision if hasattr(previa, 'edificaciones') and previa.edificaciones else "?"
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
            return self._money(obj.valor_proyecto)
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


class LiquidacionEdificacionesForm(forms.ModelForm):
    """
    Formulario unificado para crear/editar LiquidacionEdificaciones.
    Expone campos de LiquidacionGeneral (padre) junto con LiquidacionEdificaciones (hijo).
    En modo add crea primero LiquidacionGeneral y luego LiquidacionEdificaciones.
    En modo change sincroniza ambos registros.

    NOTA: numero_revision vive en LiquidacionEdificaciones, no en LiquidacionGeneral.
    liquidacion_previa era FK singular, ahora es M2M liquidaciones_previas.
    expediente fue removido del modelo.
    """

    # ── Campos de LiquidacionGeneral (padre) ──────────────────────────────
    proyecto = forms.ModelChoiceField(
        queryset=Proyecto.objects.all(),
        label="Proyecto",
        required=True,
    )
    valor_proyecto = forms.DecimalField(
        label="Valor de Obra",
        required=True,
        max_digits=12,
        decimal_places=2,
    )
    fecha_registro = forms.DateField(
        label="Fecha de Registro",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    usuario_creador = forms.ModelChoiceField(
        queryset=None,  # se llena en __init__
        label="Usuario Creador",
        required=False,
    )
    igv = forms.ModelChoiceField(
        queryset=IGV.objects.all(),
        label="IGV",
        required=True,
    )
    uit = forms.ModelChoiceField(
        queryset=UIT.objects.all(),
        label="UIT",
        required=True,
    )
    estado = forms.ChoiceField(
        label="Estado",
        choices=EstadoLiquidacion.choices,
        required=True,
    )
    # NOTE: liquidacion_previa era FK singular, ahora es M2M liquidaciones_previas en LiquidacionGeneral
    # Ya no se expone como campo de formulario directo
    observacion = forms.CharField(
        label="Observación",
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = LiquidacionEdificaciones
        fields = [
            "proyecto",
            "valor_proyecto",
            "fecha_registro",
            "usuario_creador",
            "igv",
            "uit",
            "estado",
            "observacion",
            "revisiones",
            # numero_revision vive en LiquidacionEdificaciones, no en LiquidacionGeneral
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields["usuario_creador"].queryset = User.objects.all()
        # En change, precargar datos del liquidacion padre
        if self.instance.pk and hasattr(self.instance, "liquidacion"):
            liq = self.instance.liquidacion
            self.fields["proyecto"].initial = liq.proyecto_id
            self.fields["valor_proyecto"].initial = liq.valor_proyecto
            self.fields["fecha_registro"].initial = liq.fecha_registro
            self.fields["usuario_creador"].initial = liq.usuario_creador_id
            self.fields["igv"].initial = liq.igv_id
            self.fields["uit"].initial = liq.uit_id
            self.fields["estado"].initial = liq.estado
            self.fields["observacion"].initial = liq.observacion

    def save(self, commit=True):
        # Si instance.pk tiene liquidacion ya asignada → update
        if self.instance.pk and hasattr(self.instance, "liquidacion"):
            liq = self.instance.liquidacion
        else:
            # Crear LiquidacionGeneral padre
            liq = LiquidacionGeneral()
        liq.proyecto = self.cleaned_data["proyecto"]
        liq.valor_proyecto = self.cleaned_data["valor_proyecto"]
        if self.cleaned_data.get("fecha_registro"):
            liq.fecha_registro = self.cleaned_data["fecha_registro"]
        if self.cleaned_data.get("usuario_creador"):
            liq.usuario_creador = self.cleaned_data["usuario_creador"]
        liq.igv = self.cleaned_data["igv"]
        liq.uit = self.cleaned_data["uit"]
        liq.estado = self.cleaned_data["estado"]
        liq.observacion = self.cleaned_data.get("observacion") or ""
        liq.save()
        self.instance.liquidacion = liq
        return super().save(commit=commit)


@admin.register(LiquidacionEdificaciones)
class LiquidacionEdificacionesAdmin(NestedModelAdmin, SimpleHistoryAdmin):
    """
    Admin para LiquidacionEdificaciones — forma completa similar a LiquidacionGeneralAdmin.

    Limitaciones:
    - RevisionDelegadoInline no puede inlar abuelos directamente bajo LiquidacionEdificaciones
      porque RevisionDelegado FK apunta a LiquidacionGeneral (padre), no a LiquidacionEdificaciones.
      Los delegados se gestionan desde LiquidacionGeneralAdmin padre.
    - EdificacionesClasificacionEspecialidadesInline tampoco funciona directamente porque
      su FK apunta a EdificacionesClasificacion, no a LiquidacionEdificaciones.
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
        # ── Cálculos referenciales (readonly, igual que LiquidacionGeneralAdmin) ──
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
    autocomplete_fields = ["revisiones"]
    ordering = ["-created_at"]
    form = LiquidacionEdificacionesForm
    # NOTA: No se pueden incluir inlines de RevisionDelegado porque su fk_name="liquidacion"
    # apunta a LiquidacionGeneral, no a LiquidacionEdificaciones. Los delegados se gestionan
    # desde LiquidacionGeneralAdmin. Tampoco se pueden inlar EdificacionesClasificacionEspecialidades.
    inlines = []

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
            .prefetch_related("revisiones", "revisiones__especialidad", "proyectistas")
        )

    def get_changeform_initial_data(self, request):
        """Pre-llenar usuario_creador con el usuario actual."""
        return {"usuario_creador": request.user.pk}

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj) or [])
        if obj is not None:  # Change view — mostrar liquidacion como solo lectura
            readonly.append("liquidacion")
        return readonly

    def numero_revision_display(self, obj):
        return obj.numero_revision

    numero_revision_display.short_description = "N° Revisión"

    # ── Métodos de cálculo (copiados de LiquidacionGeneralAdmin para consistencia) ──

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
            num_rev = previa.edificaciones.numero_revision if hasattr(previa, 'edificaciones') and previa.edificaciones else "?"
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
        liq = obj.liquidacion if obj else None
        if not liq or not liq.proyecto_id:
            return None
        return liq.valor_proyecto

    def calculo_valor_obra(self, obj):
        liq = obj.liquidacion if obj else None
        if liq and liq.proyecto_id:
            return self._money(liq.valor_proyecto)
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
        if obj is None:  # Add view
            return [
                (
                    "Datos de la liquidación",
                    {
                        "fields": (
                            "proyecto",
                            "estado",
                        ),
                    },
                ),
                (
                    "Configuración financiera",
                    {
                        "fields": (
                            "igv",
                            "uit",
                            "valor_proyecto",
                        ),
                        "description": "Debajo de cada referencia se muestra el dato aplicado de su tabla relacionada.",
                    },
                ),
                (
                    "Delegados asignados",
                    {
                        "fields": ("delegados_display",),
                    },
                ),
                (
                    "Datos de Edificación",
                    {
                        "fields": ("revisiones",),
                    },
                ),
                (
                    "Registro",
                    {
                        "fields": ("fecha_registro", "usuario_creador"),
                    },
                ),
            ]
        else:  # Change view — incluye cálculos y datos completos
            return [
                (
                    "Datos de la liquidación",
                    {
                        "fields": (
                            "liquidacion",
                            "proyecto",
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
                            "valor_proyecto",
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
                    "Datos de Edificación",
                    {
                        "fields": ("revisiones",),
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


@admin.register(RevisionDelegado)
class RevisionDelegadoAdmin(SimpleHistoryAdmin):
    list_display = ["liquidacion", "numero_revision_display", "proyecto", "delegado", "created_at"]
    list_filter = ["delegado__tipo", "delegado__especialidad"]
    search_fields = [
        "liquidacion__proyecto__denominacion",
        "delegado__perfil_ingeniero__nombres",
        "delegado__perfil_ingeniero__apellido_paterno",
        "delegado__perfil_ingeniero__apellido_materno",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["liquidacion", "delegado"]
    ordering = ["liquidacion", "delegado"]

    def numero_revision_display(self, obj):
        """Obtiene numero_revision desde LiquidacionEdificaciones, no LiquidacionGeneral."""
        try:
            return obj.liquidacion.edificaciones.numero_revision if hasattr(obj.liquidacion, 'edificaciones') and obj.liquidacion.edificaciones else "?"
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


# EdificacionesClasificacion model moved to domain — admin registration pending model availability.


@admin.register(EdificacionesTarifa)
class EdificacionesTarifaAdmin(SimpleHistoryAdmin):
    list_display = ["porcentaje_minimo_uit", "derecho_minimo", "derecho_maximo", "periodo_inicio", "periodo_fin"]
    list_filter = ["periodo_inicio"]
    search_fields = ["periodo_inicio"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-periodo_inicio"]


@admin.register(EdificacionesRevision)
class EdificacionesRevisionAdmin(SimpleHistoryAdmin):
    list_display = ["tarifa", "especialidad", "porcentaje_liquidacion", "periodo_inicio", "periodo_fin", "habilitada"]
    list_filter = ["especialidad"]
    search_fields = ["especialidad__nombre"]
    readonly_fields = ["created_at", "updated_at", "habilitada"]
    autocomplete_fields = ["tarifa", "especialidad"]
    ordering = ["-periodo_inicio"]


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
