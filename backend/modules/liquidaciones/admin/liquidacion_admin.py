"""Proxy-based admin classes for LiquidacionGeneral filtered by tipo.

Each proxy model (LiquidacionEdificacionProxy, etc.) is a filtered view of
LiquidacionGeneral by tipo_liquidacion__codigo. Native inlines work because
the parent model is LiquidacionGeneral and the specific models (edificaciones,
etc.) have FK back to it.
"""

from functools import partial

from django import forms
from django.contrib import admin
from django.contrib.admin.checks import InlineModelAdminChecks
from django.core.exceptions import ValidationError
from django.forms.formsets import DELETION_FIELD_NAME
from django.forms.models import (
    BaseInlineFormSet,
    BaseModelFormSet,
    modelformset_factory,
)
from django.utils import timezone

# Import from domain/models (re-exported via models.py)
from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionContacto,
    LiquidacionDocumentos,
    LiquidacionProyectista,
    LiquidacionDelegado,
    LiquidacionComprobante,
    # Specific models (for inlines)
    LiquidacionEdificacion,
    LiquidacionHabilitacionUrbana,
    LiquidacionMecanicaSuelos,
    LiquidacionTaludes,
    LiquidacionInspeccionObra,
    LiquidacionImpactoVial,
    # Calculation models (for inlines)
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    LiquidacionPorcentajeObraAcumulacion,
    # Inspector
    LiquidacionInspector,
    # Proxy models
    LiquidacionEdificacionProxy,
    LiquidacionHabilitacionUrbanaProxy,
    LiquidacionMecanicaSuelosProxy,
    LiquidacionTaludesProxy,
    LiquidacionInspeccionObraProxy,
    LiquidacionImpactoVialProxy,
)
# LiquidacionCodigo imported directly from domain (not in models.py re-exports)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionCodigo,
)
from modules.liquidaciones.domain.constants import CategoriaIO, TipoLiquidacion
# El MODELO TipoLiquidacion (alias) es distinto del enum TipoLiquidacion de
# domain.constants: el admin necesita la fila para resolver un codigo a un id
# constante y que el planner use el indice del changelist.
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.finanzas.domain.models.registro_pago_inspector import RegistroPagoInspector


# =============================================================================
# ALWAYS-VISIBLE INLINES (attached to LiquidacionGeneral)
# =============================================================================


class LiquidacionDelegadoFormSet(BaseInlineFormSet):
    """Formset que precarga lo que usa `LiquidacionDelegado.__str__`.

    `__str__` es `f"{self.delegado} @ {self.liquidacion}"` y el template del
    admin lo pinta por fila: sin estas relaciones, cada fila dispara 4
    queries (delegado + perfil_ingeniero + liquidacion + proyecto).
    """

    def get_queryset(self):
        return super().get_queryset().select_related(
            "delegado__perfil_ingeniero",
            "liquidacion__proyecto",
            "especialidad_revision",
        )


class LiquidacionDelegadoInline(admin.TabularInline):
    """Inline for LiquidacionDelegado (delegate assigned to this liquidation).

    Direct FK relation (no join to the RH detail tables), so it stays cheap:
    no pre-populated rows and bounded autocomplete widgets for the foreign keys.
    """

    model = LiquidacionDelegado
    formset = LiquidacionDelegadoFormSet
    extra = 0
    autocomplete_fields = [
        "delegado",
        "especialidad_revision",
        "delegado_operacion",
    ]
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionProyectistaInline(admin.TabularInline):
    """Inline for LiquidacionProyectista (proyectista on this liquidation)."""

    model = LiquidacionProyectista
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionContactoInline(admin.TabularInline):
    """Inline for LiquidacionContacto (contact on this liquidation)."""

    model = LiquidacionContacto
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionDocumentosInline(admin.TabularInline):
    """Inline for LiquidacionDocumentos (uploaded documents)."""

    model = LiquidacionDocumentos
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionComprobanteInline(admin.TabularInline):
    """Inline for LiquidacionComprobante (comprobantes de liquidación)."""

    model = LiquidacionComprobante
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# =============================================================================
# SPECIFIC MODEL INLINES (OneToOne extensions — conditional by tipo_liquidacion)
# =============================================================================


class LiquidacionEdificacionInline(admin.StackedInline):
    """Inline for LiquidacionEdificacion (OneToOne extension, EDIFICACION only)."""

    model = LiquidacionEdificacion
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionHabilitacionUrbanaInline(admin.StackedInline):
    """Inline for LiquidacionHabilitacionUrbana (OneToOne, HABILITACION_URBANA only)."""

    model = LiquidacionHabilitacionUrbana
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionMecanicaSuelosInline(admin.StackedInline):
    """Inline for LiquidacionMecanicaSuelos (OneToOne, MECANICA_SUELOS only)."""

    model = LiquidacionMecanicaSuelos
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionTaludesInline(admin.StackedInline):
    """Inline for LiquidacionTaludes (OneToOne, TALUDES only)."""

    model = LiquidacionTaludes
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionInspeccionObraInline(admin.StackedInline):
    """Inline for LiquidacionInspeccionObra (OneToOne, INSPECCION_OBRA only)."""

    model = LiquidacionInspeccionObra
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionImpactoVialInline(admin.StackedInline):
    """Inline for LiquidacionImpactoVial (OneToOne, IMPACTO_VIAL only)."""

    model = LiquidacionImpactoVial
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


# =============================================================================
# CALCULATION MODEL INLINES (conditional by tipo_liquidacion)
# =============================================================================


class LiquidacionPorMetroCuadradoInline(admin.StackedInline):
    """Inline for LiquidacionPorMetroCuadrado (M2 calculation, HU/MS/Taludes/IV)."""

    model = LiquidacionPorMetroCuadrado
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionPorCategoriaVisitasInline(admin.StackedInline):
    """Inline for LiquidacionPorCategoriaVisitas (visits calculation, IO only)."""

    model = LiquidacionPorCategoriaVisitas
    exclude = ["categoria"]
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class RegistroPagoInspectorFormSet(BaseModelFormSet):
    """Formset indirecto: LiquidacionGeneral -> Visitas -> RegistroPagoInspector."""

    @classmethod
    def get_default_prefix(cls):
        return "registros_pago_inspector"

    def __init__(self, *args, instance=None, save_as_new=False, **kwargs):
        self.parent_instance = instance
        self.visitas = None
        if instance and instance.pk:
            self.visitas = instance.liquidacion_visitas.order_by("id").first()
        queryset = (
            RegistroPagoInspector.objects.filter(
                liquidacion_por_categoria_visitas=self.visitas
            )
            if self.visitas
            else RegistroPagoInspector.objects.none()
        )
        kwargs["queryset"] = queryset
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        if any(self.errors) or not self.visitas:
            return
        periodo_actual = timezone.localdate()
        for form in self.extra_forms:
            if not form.cleaned_data or not form.has_changed():
                continue
            periodo = form.cleaned_data.get("periodo")
            mes = form.cleaned_data.get("mes")
            if periodo and mes and (periodo, mes) > (
                periodo_actual.year,
                periodo_actual.month,
            ):
                form.add_error(
                    "mes",
                    "No se pueden registrar visitas en un período futuro.",
                )
        total_pagadas = sum(
            form.cleaned_data.get("inspecciones_pagadas") or 0
            for form in self.forms
            if form.cleaned_data
        )
        programadas = self.visitas.cantidad_visitas or 0
        if total_pagadas > programadas:
            raise ValidationError(
                f"Las inspecciones pagadas ({total_pagadas}) superan las "
                f"programadas ({programadas})."
            )

    def save_new(self, form, commit=True):
        registro = form.save(commit=False)
        registro.liquidacion_por_categoria_visitas = self.visitas
        if not registro.fecha_registro:
            registro.fecha_registro = timezone.localdate()
        if commit:
            registro.save()
        return registro


class RegistroPagoInspectorInlineChecks(InlineModelAdminChecks):
    """Omite solo el check de FK directa; la relación la resuelve el formset."""

    def _check_relation(self, obj, parent_model):
        return []

    def _check_exclude_of_parent_model(self, obj, parent_model):
        return []


class RegistroPagoInspectorInline(admin.TabularInline):
    model = RegistroPagoInspector
    checks_class = RegistroPagoInspectorInlineChecks
    extra = 1
    can_delete = False
    verbose_name = "registro de visita"
    verbose_name_plural = "Registros de visitas"
    fields = [
        "periodo",
        "mes",
        "inspecciones_pagadas",
        "fecha_registro",
        "recibo_mensual",
    ]
    readonly_fields = ["fecha_registro", "recibo_mensual"]

    def has_change_permission(self, request, obj=None):
        return False

    def get_formset(self, request, obj=None, **kwargs):
        return modelformset_factory(
            RegistroPagoInspector,
            formset=RegistroPagoInspectorFormSet,
            fields=["periodo", "mes", "inspecciones_pagadas"],
            extra=self.get_extra(request, obj),
            can_delete=False,
        )


# =============================================================================
# RH DETAIL INLINE (indirect: LiquidacionGeneral -> LiquidacionDelegado -> Detalle)
#
# El detalle de honorario del delegado es la unidad de la que se genera el RH
# mensual. Las 75k filas que trae la importacion legacy son huerfanas
# (`recibo_mensual_id IS NULL`) y no eran visibles en ningun admin: este inline
# las hace visibles y editables dentro de la liquidacion.
#
# Reglas:
#   - Fila huerfana (sin RH mensual) -> editable a mano y borrable.
#   - Fila ligada a un RH mensual -> solo lectura: el flujo RH congela sus
#     valores al crear el recibo (`frozen at creation time`), asi que editarlos
#     dejaria stale el encabezado del recibo.
#   - `recibo_mensual` NUNCA se edita desde aqui y nunca se dibuja como
#     <select> sin acotar (fue el motivo por el que se retiro el inline
#     original).
# =============================================================================


class DetalleHonorarioDelegadoInlineChecks(InlineModelAdminChecks):
    """Omite solo los checks de FK directa; la relación la resuelve el formset."""

    def _check_relation(self, obj, parent_model):
        return []

    def _check_exclude_of_parent_model(self, obj, parent_model):
        return []


class DetalleHonorarioDelegadoAdminForm(forms.ModelForm):
    """Fila del detalle de honorario RH.

    Las filas ya enlazadas a un RH mensual se muestran deshabilitadas: el
    flujo RH es su dueno. Las huerfanas (`recibo_mensual_id IS NULL`) quedan
    editables para poder corregir a mano la importacion legacy.
    """

    class Meta:
        model = DetalleHonorarioDelegado
        fields = [
            "liquidacion_delegado",
            "imp_bruto",
            "sub_total",
            "renta_cip",
            "aporte_codemu",
            "fondo_comun",
            "neto_honorario",
            "tasa_delegado",
        ]
        widgets = {
            "imp_bruto": forms.NumberInput(attrs={"step": "0.01"}),
            "sub_total": forms.NumberInput(attrs={"step": "0.01"}),
            "renta_cip": forms.NumberInput(attrs={"step": "0.01"}),
            "aporte_codemu": forms.NumberInput(attrs={"step": "0.01"}),
            "fondo_comun": forms.NumberInput(attrs={"step": "0.01"}),
            "neto_honorario": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.esta_ligada_a_rh():
            for field in self.fields.values():
                field.disabled = True
            self.fields["liquidacion_delegado"].required = False

    def esta_ligada_a_rh(self) -> bool:
        """True when the row belongs to a monthly RH receipt."""
        instance = self.instance
        return bool(instance and instance.pk and instance.recibo_mensual_id)


class DetalleHonorarioDelegadoFormSet(BaseModelFormSet):
    """Formset indirecto: LiquidacionGeneral -> LiquidacionDelegado -> Detalle."""

    @classmethod
    def get_default_prefix(cls):
        return "detalle_honorario_delegado"

    def __init__(self, *args, instance=None, save_as_new=False, **kwargs):
        self.parent_instance = instance
        self.asignaciones = []
        if instance and instance.pk:
            self.asignaciones = list(
                instance.liquidacion_delegados.select_related(
                    "delegado__perfil_ingeniero",
                    "especialidad_revision",
                ).all()
            )
        # Etiquetas precalculadas: `LiquidacionDelegado.__str__` atraviesa
        # `delegado` y `liquidacion`, y pintarlo por opcion del select
        # disparaba 2-3 queries por opcion y por formulario (el change page
        # paso de 64 a 362 queries).
        self._etiquetas = {
            str(asignacion.id): self._etiqueta(asignacion)
            for asignacion in self.asignaciones
        }
        kwargs["queryset"] = self._detalle_queryset()
        super().__init__(*args, **kwargs)
        # El selector de asignacion solo puede ofrecer las asignaciones de
        # ESTA liquidacion (el modelo tiene 75k filas).
        for form in self.forms:
            self._acotar_selector_asignacion(form)

    @property
    def empty_form(self):
        """Acota tambien la fila "Agregar otro".

        `BaseFormSet.empty_form` es una PROPIEDAD: cada acceso crea un form
        nuevo, asi que configurarlo en `__init__` no sirve. Sin acotarlo, esa
        fila pinta un <select> con las 75.512 asignaciones y cada
        `LiquidacionDelegado.__str__` cuesta 4 queries (=> cientos de miles).
        """
        form = super().empty_form
        self._acotar_selector_asignacion(form)
        return form

    def _acotar_selector_asignacion(self, form) -> None:
        field = form.fields.get("liquidacion_delegado")
        if field is None:
            return
        field.queryset = self._asignaciones_queryset()
        field.label_from_instance = self._label_asignacion

    @staticmethod
    def _etiqueta(asignacion) -> str:
        perfil = asignacion.delegado.perfil_ingeniero
        return f"{perfil.cip} · {asignacion.especialidad_revision.nombre}"

    def _label_asignacion(self, asignacion) -> str:
        # OJO: `dict.get(k, str(x))` evalua el fallback SIEMPRE (es un
        # argumento, no un default perezoso) -> `LiquidacionDelegado.__str__`
        # se ejecutaba en cada opcion del select (4 queries por opcion).
        etiqueta = self._etiquetas.get(str(asignacion.id))
        return etiqueta if etiqueta is not None else str(asignacion.id)

    def _asignaciones_queryset(self):
        if not self.parent_instance or not self.parent_instance.pk:
            return LiquidacionDelegado.objects.none()
        return LiquidacionDelegado.objects.filter(
            liquidacion_id=self.parent_instance.pk
        ).select_related("delegado__perfil_ingeniero", "especialidad_revision")

    def _detalle_queryset(self):
        # NOTA: el nombre NO puede ser `_queryset` — `BaseModelFormSet.get_queryset()`
        # cachea el queryset en `self._queryset` y lo pisaria con el metodo.
        ids = [asignacion.id for asignacion in self.asignaciones]
        if not ids:
            return DetalleHonorarioDelegado.objects.none()
        return (
            DetalleHonorarioDelegado.objects.filter(liquidacion_delegado_id__in=ids)
            .select_related(
                "recibo_mensual",
                "tasa_delegado",
                # La etiqueta de la fila usa la asignacion: sin esto, cada
                # fila del formset dispara queries al pintar su asignacion.
                "liquidacion_delegado__delegado__perfil_ingeniero",
                "liquidacion_delegado__especialidad_revision",
                "liquidacion_delegado__liquidacion",
            )
            .order_by(
                "liquidacion_delegado__delegado__perfil_ingeniero__apellido_paterno",
                "liquidacion_delegado__especialidad_revision__nombre",
                "created_at",
            )
        )

    def add_fields(self, form, index):
        """Deshabilita el checkbox DELETE en las filas ligadas a un RH mensual."""
        super().add_fields(form, index)
        instance = getattr(form, "instance", None)
        if instance is not None and instance.pk and instance.recibo_mensual_id:
            deletion_field = form.fields.get(DELETION_FIELD_NAME)
            if deletion_field is not None:
                deletion_field.disabled = True

    def delete_existing(self, obj, commit=True):
        """Una fila ligada a un RH mensual la administra el flujo RH: no se borra."""
        if obj.pk and obj.recibo_mensual_id:
            return
        super().delete_existing(obj, commit=commit)

    def clean(self):
        super().clean()
        if any(self.errors) or not self.asignaciones:
            return
        ligadas = {
            str(valor)
            for valor in DetalleHonorarioDelegado.objects.filter(
                liquidacion_delegado_id__in=[a.id for a in self.asignaciones],
                recibo_mensual__isnull=False,
            ).values_list("liquidacion_delegado_id", flat=True)
        }
        if not ligadas:
            return
        for form in self.extra_forms:
            if not form.cleaned_data or not form.has_changed():
                continue
            asignacion = form.cleaned_data.get("liquidacion_delegado")
            if asignacion and str(asignacion.id) in ligadas:
                form.add_error(
                    "liquidacion_delegado",
                    "Esta asignación ya tiene un detalle ligado a un RH mensual; "
                    "ese detalle lo administra el flujo RH.",
                )

    def save_new(self, form, commit=True):
        """Create the legacy detail without a monthly RH receipt."""
        detalle = form.save(commit=False)
        if not detalle.pk:
            # Detalle legacy: nace sin RH mensual.
            detalle.recibo_mensual = None
        if commit:
            detalle.save()
        return detalle


class DetalleHonorarioDelegadoInline(admin.TabularInline):
    """Inline del detalle de honorario RH de los delegados de la liquidacion.

    Relación indirecta (LiquidacionGeneral -> LiquidacionDelegado -> Detalle):
    Django no anida inlines, asi que el formset resuelve el padre — mismo
    patrón que `RegistroPagoInspectorInline`.
    """

    model = DetalleHonorarioDelegado
    checks_class = DetalleHonorarioDelegadoInlineChecks
    form = DetalleHonorarioDelegadoAdminForm
    formset = DetalleHonorarioDelegadoFormSet
    extra = 1
    can_delete = True
    verbose_name = "detalle de honorario del delegado"
    verbose_name_plural = "Detalles de honorarios de los delegados"
    fields = [
        "liquidacion_delegado",
        "imp_bruto",
        "sub_total",
        "renta_cip",
        "aporte_codemu",
        "fondo_comun",
        "neto_honorario",
        "tasa_delegado",
        "recibo_mensual",
        "created_at",
        "updated_at",
    ]
    readonly_fields = ["recibo_mensual", "created_at", "updated_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Selects acotados y sin N+1 al pintar sus opciones.

        `TasaDelegado.__str__` traverses `tipo_liquidacion`: sin
        `select_related` cada opcion del select dispara una query (y el
        change page lo multiplica por formulario).
        """
        if db_field.name == "tasa_delegado":
            kwargs["queryset"] = TasaDelegado.objects.select_related("tipo_liquidacion")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        # `inlineformset_factory` exige una FK directa al padre, que este
        # inline no tiene: el formset se construye a mano (igual que
        # `RegistroPagoInspectorInline`).
        return modelformset_factory(
            DetalleHonorarioDelegado,
            form=DetalleHonorarioDelegadoAdminForm,
            formset=DetalleHonorarioDelegadoFormSet,
            formfield_callback=partial(self.formfield_for_dbfield, request=request),
            fields=[
                "liquidacion_delegado",
                "imp_bruto",
                "sub_total",
                "renta_cip",
                "aporte_codemu",
                "fondo_comun",
                "neto_honorario",
                "tasa_delegado",
            ],
            extra=self.get_extra(request, obj),
            can_delete=self.can_delete and self.has_delete_permission(request, obj),
        )


class LiquidacionPorcentajeObraInline(admin.StackedInline):
    """Inline for LiquidacionPorcentajeObra (OneToOne, percentage calculation, Edificacion)."""

    model = LiquidacionPorcentajeObra
    extra = 0
    # `estrategia_cotizacion` es un snapshot persistido: lo fija el motor de
    # cotización, no el operador del admin.
    readonly_fields = ["estrategia_cotizacion", "created_at", "updated_at"]


class LiquidacionPorcentajeObraDetalleInline(admin.TabularInline):
    """Inline for LiquidacionPorcentajeObraDetalle (nested in LiquidacionPorcentajeObra)."""

    model = LiquidacionPorcentajeObraDetalle
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# =============================================================================
# ALWAYS-VISIBLE INLINES LIST
# =============================================================================


ALL_INLINES = [
    LiquidacionDelegadoInline,
    DetalleHonorarioDelegadoInline,
    LiquidacionProyectistaInline,
    LiquidacionContactoInline,
    LiquidacionDocumentosInline,
    LiquidacionComprobanteInline,
]


# =============================================================================
# BASE ADMIN FOR PROXY MODELS
# Reusable base class that filters by tipo_liquidacion__codigo and provides
# all general fields from LiquidacionGeneral plus type-specific inlines.
# =============================================================================


#: Cache codigo -> tipo_liquidacion id, POR REQUEST.
#:
#: El id se resuelve con una consulta (indice unico sobre `codigo`, ~0.2 ms)
#: y se memoiza en el request para no repetirla. No se cachea a nivel de
#: proceso: el id debe resolverse siempre contra la base de datos activa.
def _tipo_liquidacion_id(request, codigo: str) -> str | None:
    """Resolve a tipo_liquidacion codigo to its row id.

    El changelist filtra por un id CONSTANTE en vez de hacer el JOIN por
    ``codigo``. Con el JOIN (o con ``IN (subquery)``) el planner no puede usar
    el indice ``(tipo_liquidacion, legacy, fecha_registro DESC)`` y cae en un
    seq scan + sort de toda la tabla; con el id constante usa Index Scan y
    termina el sort (medido: 52-56 ms -> 0.2 ms de Execution Time).
    """
    if request is None:
        return _resolver_tipo_liquidacion_id(codigo)
    cache = getattr(request, "_tipo_liquidacion_ids", None)
    if cache is None:
        cache = {}
        request._tipo_liquidacion_ids = cache
    if codigo not in cache:
        cache[codigo] = _resolver_tipo_liquidacion_id(codigo)
    return cache[codigo]


def _resolver_tipo_liquidacion_id(codigo: str) -> str | None:
    resolved = (
        TipoLiquidacionModel.objects.filter(codigo=codigo)
        .values_list("id", flat=True)
        .first()
    )
    return str(resolved) if resolved is not None else None


class BaseLiquidacionProxyAdmin(admin.ModelAdmin):
    """
    Base admin for LiquidacionGeneral proxy models.

    Each subclass must define:
        tipo_codigo: The TipoLiquidacion enum value (e.g., TipoLiquidacion.EDIFICACION)
        specific_inline: The OneToOne extension inline class (e.g., LiquidacionEdificacionInline)
        calc_inline: The calculation inline class (e.g., LiquidacionPorcentajeObraInline) or None
        specific_related_name: The related_name on LiquidacionGeneral for the specific model
    """

    # General list display fields from LiquidacionGeneral
    list_display = [
        "numero",
        "expediente",
        "proyecto",
        "municipalidad",
        "estado",
        "total",
        "numero_revision",
        "fecha_registro",
    ]

    search_fields = [
        "expediente",
        "proyecto__nombre_propietario",
        "proyecto__entidad_numero_documento",
    ]

    list_filter = [
        "estado",
        "municipalidad",
        "fecha_registro",
        "legacy",
    ]

    fields = [
        "expediente",
        "proyecto",
        "municipalidad",
        "tipo_liquidacion",
        "estado",
        "numero_revision",
        "sub_total",
        "total",
        "fecha_registro",
        "observacion",
        "retencion",
        "legacy",
        "created_at",
        "updated_at",
    ]

    readonly_fields = [
        "proyecto",
        "municipalidad",
        "tipo_liquidacion",
        "fecha_registro",
        "legacy",
        "created_at",
        "updated_at",
    ]

    filter_horizontal = []

    # Disable expensive full count query in Django admin changelist.
    # The filtered proxy queryset makes a precise count cost-prohibitive for large tables.
    show_full_result_count = False
    changelist_select_related = ()
    changelist_prefetch_related = ()

    def get_queryset(self, request):
        """Filter by tipo_liquidacion id and optimize with select_related."""
        qs = super().get_queryset(request)
        # Filtro por id constante (no por JOIN sobre codigo): es lo que permite
        # al planner usar el indice (tipo_liquidacion, legacy, fecha_registro).
        tipo_id = _tipo_liquidacion_id(request, self.tipo_codigo)
        if tipo_id is None:
            return qs.none()
        qs = qs.filter(tipo_liquidacion_id=tipo_id)
        # Dynamically add specific related name to avoid N+1 on numero() display method.
        related_name = getattr(self, "specific_related_name", None)
        if related_name:
            qs = qs.select_related(
                "proyecto",
                "municipalidad",
                "tipo_liquidacion",
                "usuario_creador",
                related_name,
                *self.changelist_select_related,
            )
        else:
            qs = qs.select_related(
                "proyecto",
                "municipalidad",
                "tipo_liquidacion",
                "usuario_creador",
                *self.changelist_select_related,
            )
        if self.changelist_prefetch_related:
            qs = qs.prefetch_related(*self.changelist_prefetch_related)
        return qs.order_by("legacy", "-fecha_registro")

    def get_search_results(self, request, queryset, search_term):
        """Extend text search with an indexed, exact specific-liquidation number lookup."""
        base_queryset = queryset
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        try:
            numero = int(search_term)
        except (TypeError, ValueError):
            return queryset, may_have_duplicates

        related_name = getattr(self, "specific_related_name", None)
        if related_name:
            queryset |= base_queryset.filter(**{f"{related_name}__numero": numero})
        return queryset, may_have_duplicates

    # ── Display methods ────────────────────────────────────────────

    def numero(self, obj):
        """Display numero from the specific related model."""
        related_name = getattr(self, "specific_related_name", None)
        if related_name and hasattr(obj, related_name):
            specific = getattr(obj, related_name, None)
            if specific and hasattr(specific, "numero"):
                return specific.numero
        return "-"

    numero.short_description = "N°"
    # Prevent admin from sorting by this column — it would re-introduce the JOIN.
    numero.admin_order_field = None

    def expediente(self, obj):
        return obj.expediente or "-"

    expediente.short_description = "Expediente"

    def proyecto(self, obj):
        return str(obj.proyecto) if obj.proyecto else "-"

    proyecto.short_description = "Proyecto"

    def municipalidad(self, obj):
        return str(obj.municipalidad) if obj.municipalidad else "-"

    municipalidad.short_description = "Municipalidad"

    def estado(self, obj):
        return obj.estado or "-"

    estado.short_description = "Estado"

    def total(self, obj):
        if obj.total is None:
            return "-"
        return f"S/ {obj.total:,.2f}"

    total.short_description = "Total"

    def numero_revision(self, obj):
        return obj.numero_revision or "-"

    numero_revision.short_description = "Rev."

    def fecha_registro(self, obj):
        if not obj.fecha_registro:
            return "-"
        return obj.fecha_registro.strftime("%d/%m/%Y")

    fecha_registro.short_description = "Fecha"

    # ── Inlines ───────────────────────────────────────────────────

    def get_inlines(self, request, obj):
        """Return the type-specific, calculation, comprobante and delegate inlines.

        The RH detail inline IS exposed: it renders the imported (orphan)
        delegate honorario details, which are invisible in every other admin
        surface. Its rows stay bounded (no unbounded ``<select>`` on
        ``recibo_mensual``) and receipt-linked rows are read-only, so the RH
        lifecycle is not bypassed.
        """
        inlines = []
        if obj is not None:
            inlines.append(self.specific_inline)
            if self.calc_inline is not None:
                inlines.append(self.calc_inline)
            inlines.append(LiquidacionComprobanteInline)
            inlines.append(LiquidacionDelegadoInline)
            inlines.append(DetalleHonorarioDelegadoInline)
        return inlines

# =============================================================================
# PROXY ADMIN CLASSES
# =============================================================================


@admin.register(LiquidacionEdificacionProxy)
class LiquidacionEdificacionProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Edificación type."""

    tipo_codigo = TipoLiquidacion.EDIFICACION
    specific_inline = LiquidacionEdificacionInline
    calc_inline = LiquidacionPorcentajeObraInline
    specific_related_name = "edificaciones"
    changelist_select_related = ("liquidacion_porcentaje_obra",)

    list_display = BaseLiquidacionProxyAdmin.list_display + ["tipo_tramite_list"]

    def tipo_tramite_list(self, obj):
        calc = getattr(obj, "liquidacion_porcentaje_obra", None)
        if not calc:
            return "-"
        return calc.tipo_tramite if calc and calc.tipo_tramite else "-"

    tipo_tramite_list.short_description = "Tipo Trámite"


@admin.register(LiquidacionHabilitacionUrbanaProxy)
class LiquidacionHabilitacionUrbanaProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Habilitación Urbana type."""

    tipo_codigo = TipoLiquidacion.HABILITACION_URBANA
    specific_inline = LiquidacionHabilitacionUrbanaInline
    calc_inline = LiquidacionPorMetroCuadradoInline
    specific_related_name = "habilitacion_urbana"
    changelist_prefetch_related = ("liquidacion_m2",)

    list_display = BaseLiquidacionProxyAdmin.list_display + ["area_list"]

    def area_list(self, obj):
        calc = getattr(obj, "liquidacion_m2", None)
        if not calc:
            return "-"
        calc = calc.first()
        if not calc:
            return "-"
        return f"{calc.area_m2:,.2f} m²" if calc.area_m2 else "-"

    area_list.short_description = "Área"


@admin.register(LiquidacionMecanicaSuelosProxy)
class LiquidacionMecanicaSuelosProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Mecánica de Suelos type."""

    tipo_codigo = TipoLiquidacion.MECANICA_SUELOS
    specific_inline = LiquidacionMecanicaSuelosInline
    calc_inline = LiquidacionPorMetroCuadradoInline
    specific_related_name = "mecanica_suelos"
    changelist_prefetch_related = ("liquidacion_m2",)

    list_display = BaseLiquidacionProxyAdmin.list_display + ["area_list"]

    def area_list(self, obj):
        calc = getattr(obj, "liquidacion_m2", None)
        if not calc:
            return "-"
        calc = calc.first()
        if not calc:
            return "-"
        return f"{calc.area_m2:,.2f} m²" if calc.area_m2 else "-"

    area_list.short_description = "Área"


@admin.register(LiquidacionTaludesProxy)
class LiquidacionTaludesProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Taludes type."""

    tipo_codigo = TipoLiquidacion.TALUDES
    specific_inline = LiquidacionTaludesInline
    calc_inline = LiquidacionPorcentajeObraInline
    specific_related_name = "taludes"
    changelist_select_related = ("liquidacion_porcentaje_obra",)

    list_display = BaseLiquidacionProxyAdmin.list_display + ["tipo_tramite_list"]

    def tipo_tramite_list(self, obj):
        calc = getattr(obj, "liquidacion_porcentaje_obra", None)
        if not calc:
            return "-"
        return calc.tipo_tramite if calc.tipo_tramite else "-"

    tipo_tramite_list.short_description = "Tipo Trámite"


class LiquidacionInspeccionObraAdminForm(forms.ModelForm):
    categoria_inspeccion = forms.ChoiceField(
        choices=CategoriaIO.choices,
        required=False,
        label="Categoría de Inspección",
    )

    class Meta:
        model = LiquidacionInspeccionObraProxy
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            visitas = self.instance.liquidacion_visitas.order_by("id").first()
            if visitas:
                self.initial["categoria_inspeccion"] = visitas.categoria


@admin.register(LiquidacionInspeccionObraProxy)
class LiquidacionInspeccionObraProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Inspección de Obra type."""

    tipo_codigo = TipoLiquidacion.INSPECCION_OBRA
    specific_inline = LiquidacionInspeccionObraInline
    calc_inline = LiquidacionPorCategoriaVisitasInline
    specific_related_name = "inspeccion_obra"
    form = LiquidacionInspeccionObraAdminForm

    list_display = BaseLiquidacionProxyAdmin.list_display + [
        "categoria_list",
        "visitas_programadas",
        "inspecciones_pagadas",
        "saldo_inspecciones",
    ]
    fields = BaseLiquidacionProxyAdmin.fields.copy()
    fields[fields.index("sub_total"):fields.index("sub_total")] = [
        "categoria_inspeccion",
        "visitas_programadas",
        "inspecciones_pagadas",
        "saldo_inspecciones",
    ]
    readonly_fields = BaseLiquidacionProxyAdmin.readonly_fields + [
        "visitas_programadas",
        "inspecciones_pagadas",
        "saldo_inspecciones",
    ]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self._save_categoria(
            form.instance,
            form.cleaned_data.get("categoria_inspeccion") or None,
        )

    @staticmethod
    def _save_categoria(obj, categoria):
        visitas = obj.liquidacion_visitas.order_by("id").first()
        if visitas and visitas.categoria != categoria:
            visitas.categoria = categoria
            visitas.save(update_fields=["categoria", "updated_at"])

    def get_queryset(self, request):
        # El total de inspecciones pagadas se calcula en Python con el
        # prefetch: el `annotate(Sum(...))` sobre una relacion multi-valorada
        # anadia un JOIN + GROUP BY y costaba 190.9 ms frente a 18.7 ms sin
        # el (medido con la pagina de 100 filas de INSPECCION_OBRA).
        return super().get_queryset(request).prefetch_related(
            "liquidacion_visitas__registros_pago"
        )

    @staticmethod
    def _visitas(obj):
        visitas = list(obj.liquidacion_visitas.all())
        return visitas[0] if visitas else None

    def categoria_list(self, obj):
        visitas = self._visitas(obj)
        if not visitas or not visitas.categoria:
            return "-"
        return dict(CategoriaIO.choices).get(visitas.categoria, visitas.categoria)

    categoria_list.short_description = "Categoría"

    def visitas_programadas(self, obj):
        visitas = self._visitas(obj)
        return visitas.cantidad_visitas if visitas else 0

    visitas_programadas.short_description = "Programadas"

    def inspecciones_pagadas(self, obj):
        total = 0
        for visita in obj.liquidacion_visitas.all():
            for registro in visita.registros_pago.all():
                total += registro.inspecciones_pagadas or 0
        return total

    inspecciones_pagadas.short_description = "Pagadas"
    # Sin `admin_order_field`: ordenaria por la anotacion y reintroduiria el
    # JOIN + GROUP BY que este cambio elimina. Mismo criterio que `numero`.
    inspecciones_pagadas.admin_order_field = None

    def saldo_inspecciones(self, obj):
        return self.visitas_programadas(obj) - self.inspecciones_pagadas(obj)

    saldo_inspecciones.short_description = "Saldo pendiente"

    def get_inlines(self, request, obj):
        inlines = super().get_inlines(request, obj)
        if obj is not None:
            inlines.append(RegistroPagoInspectorInline)
        return inlines


@admin.register(LiquidacionImpactoVialProxy)
class LiquidacionImpactoVialProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Impacto Vial type."""

    tipo_codigo = TipoLiquidacion.IMPACTO_VIAL
    specific_inline = LiquidacionImpactoVialInline
    calc_inline = LiquidacionPorcentajeObraInline
    specific_related_name = "impacto_vial"
    changelist_select_related = ("liquidacion_porcentaje_obra",)

    list_display = BaseLiquidacionProxyAdmin.list_display + ["tipo_tramite_list"]

    def tipo_tramite_list(self, obj):
        calc = getattr(obj, "liquidacion_porcentaje_obra", None)
        if not calc:
            return "-"
        return calc.tipo_tramite if calc.tipo_tramite else "-"

    tipo_tramite_list.short_description = "Tipo Trámite"


# =============================================================================
# LIQUIDACIONGENERAL ADMIN (general view — all types)
# =============================================================================


@admin.register(LiquidacionGeneral)
class LiquidacionGeneralAdmin(admin.ModelAdmin):
    """
    Admin for LiquidacionGeneral (central liquidation model).

    Uses conditional get_inlines() to show only relevant inlines per tipo_liquidacion.
    """

    list_display = [
        "id",
        "proyecto",
        "municipalidad",
        "tipo_liquidacion",
        "estado",
        "total",
        "legacy",
        "fecha_registro",
    ]
    search_fields = [
        "proyecto__nombre_propietario",
        "expediente",
        "proyecto__entidad_numero_documento",
    ]
    list_filter = ["estado", "tipo_liquidacion", "municipalidad", "fecha_registro", "legacy"]
    readonly_fields = [
        "total",
        "sub_total",
        "fecha_registro",
        "igv_snapshot",
        "uit_snapshot",
        "legacy",
        "created_at",
        "updated_at",
    ]

    def get_inlines(self, request, obj):
        """
        Return conditional inlines based on tipo_liquidacion.
        """
        if obj is None:
            return ALL_INLINES

        tipo = obj.tipo_liquidacion.codigo if obj.tipo_liquidacion else None

        inlines = list(ALL_INLINES)

        if tipo == TipoLiquidacion.EDIFICACION:
            inlines.append(LiquidacionEdificacionInline)
            inlines.append(LiquidacionPorcentajeObraInline)
        elif tipo == TipoLiquidacion.HABILITACION_URBANA:
            inlines.append(LiquidacionHabilitacionUrbanaInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)
        elif tipo == TipoLiquidacion.MECANICA_SUELOS:
            inlines.append(LiquidacionMecanicaSuelosInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)
        elif tipo == TipoLiquidacion.TALUDES:
            inlines.append(LiquidacionTaludesInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)
        elif tipo == TipoLiquidacion.INSPECCION_OBRA:
            inlines.append(LiquidacionInspeccionObraInline)
            inlines.append(LiquidacionPorCategoriaVisitasInline)
        elif tipo == TipoLiquidacion.IMPACTO_VIAL:
            inlines.append(LiquidacionImpactoVialInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)

        return inlines


# =============================================================================
# LIQUIDACIONCODIGO ADMIN
# =============================================================================


@admin.register(LiquidacionCodigo)
class LiquidacionCodigoAdmin(admin.ModelAdmin):
    """Admin for account codes by liquidation type."""

    list_display = ["tipo_liquidacion", "codigo_cta"]
    search_fields = ["tipo_liquidacion__nombre", "codigo_cta"]
    list_filter = ["tipo_liquidacion"]
    readonly_fields = ["created_at", "updated_at"]

# =============================================================================
# HIDDEN WRAPPER ADMINS
# Registered but hidden from sidebar — use proxy admins for entry points.
# The wrapper admins (LiquidacionEdificacionAdmin, etc.) are hidden from the
# sidebar to avoid duplicate sections. They remain registered for backward
# compatibility with existing URLs.
# =============================================================================


class HiddenWrapperAdmin(admin.ModelAdmin):
    """Base for wrapper admins that are hidden from sidebar."""

    def has_module_permission(self, request):
        """Hide from sidebar index."""
        return False


# Register wrapper admins (specific models) as hidden
admin.site.register(LiquidacionEdificacion, HiddenWrapperAdmin)
admin.site.register(LiquidacionHabilitacionUrbana, HiddenWrapperAdmin)
admin.site.register(LiquidacionMecanicaSuelos, HiddenWrapperAdmin)
admin.site.register(LiquidacionTaludes, HiddenWrapperAdmin)
admin.site.register(LiquidacionInspeccionObra, HiddenWrapperAdmin)
admin.site.register(LiquidacionImpactoVial, HiddenWrapperAdmin)
# La acumulación es una proyección referencial del PO: se administra desde el
# inline del padre, no desde la barra lateral.
admin.site.register(LiquidacionPorcentajeObraAcumulacion, HiddenWrapperAdmin)


# =============================================================================
# LIQUIDACIONINSPECTOR ADMIN
# =============================================================================


@admin.register(LiquidacionInspector)
class LiquidacionInspectorAdmin(admin.ModelAdmin):
    """Admin for LiquidacionInspector (inspector associated to IO)."""

    list_display = ["liquidacion", "inspector", "dictamen_revision", "created_at"]
    search_fields = [
        "liquidacion__liquidacion__expediente",
        "inspector__perfil_ingeniero__nombres",
        "inspector__perfil_ingeniero__apellido_paterno",
    ]
    list_filter = ["dictamen_revision"]
    readonly_fields = ["created_at", "updated_at"]
