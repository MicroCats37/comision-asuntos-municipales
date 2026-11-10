"""
Shared admin building blocks for validity-period ("vigencia") models.

The mixin gives every vigencia model the same admin experience:

- a **date-aware changelist**: ordering by ``-periodo_inicio``, a
  ``date_hierarchy`` drill-down and a "Vigencia" filter (vigente hoy / vigente
  en una fecha / no vigente / sin fecha de cierre),
- **unambiguous status columns**: ``Vigente hoy`` (the runtime semantics used
  by the calculators: the validity window contains today) and ``Abierto``
  (no end date). The legacy ``vigente`` column meant "open ended", which is a
  different thing,
- the **history view** (``simple_history``),
- the **atomic rollover**: adding a new period closes the previously open
  period of the same scope at ``periodo_inicio - 1 day``.

The admin layer only presents: every rule lives in
:mod:`core_application.vigencia.services`.
"""

from datetime import date

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.forms.models import InlineForeignKeyField, construct_instance
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from core_application.vigencia.constraints import mensaje_de_solapamiento
from core_application.vigencia.services import (
    MENSAJE_PERIODO_SIN_FIN,
    cerrar_vigencias_previas,
    scope_de,
)

#: Name of the form field that drives the rollover.
CAMPO_CERRAR_VIGENCIA_ANTERIOR = "cerrar_vigencia_anterior"

#: Query-string parameter used by the "Vigente en fecha X" filter.
PARAMETRO_FECHA_VIGENCIA = "vigencia_fecha"

MENSAJE_ROLLOVER = _(
    "La vigencia anterior del mismo ámbito fue cerrada automáticamente el día "
    "anterior al inicio de este período."
)


class VigenteHoyFilter(SimpleListFilter):
    """Filter validity periods by their relation to a reference date."""

    title = _("Vigencia")
    parameter_name = "vigencia"

    def lookups(self, request, model_admin):
        return (
            ("hoy", _("Vigente hoy")),
            ("fecha", _("Vigente en fecha X")),
            ("no_vigente", _("No vigente hoy")),
            ("abierto", _("Sin fecha de cierre")),
        )

    def queryset(self, request, queryset):
        valor = self.value()
        hoy = date.today()

        if valor == "hoy":
            return self._vigentes_en(queryset, hoy)
        if valor == "fecha":
            fecha = self._fecha_de_request(request)
            if fecha is None:
                return queryset.none()
            return self._vigentes_en(queryset, fecha)
        if valor == "no_vigente":
            return queryset.exclude(self._condiciones_vigentes(hoy))
        if valor == "abierto":
            return queryset.filter(periodo_fin__isnull=True)
        return queryset

    @staticmethod
    def _condiciones_vigentes(fecha):
        return (
            Q(periodo_inicio__lte=fecha)
            & (Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=fecha))
        )

    @classmethod
    def _vigentes_en(cls, queryset, fecha):
        return queryset.filter(cls._condiciones_vigentes(fecha))

    @staticmethod
    def _fecha_de_request(request):
        crudo = request.GET.get(PARAMETRO_FECHA_VIGENCIA)
        if not crudo:
            return None
        try:
            return date.fromisoformat(crudo)
        except ValueError:
            return None


class VigenciaAdminForm(forms.ModelForm):
    """
    Admin form for validity-period models.

    Adds the visible rollover switch (on by default) and validates that the
    period does not overlap another period of the same scope.
    """

    cerrar_vigencia_anterior = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Cerrar la vigencia vigente anterior"),
        help_text=_(
            "Cierra automáticamente, el día anterior al inicio de este período, la "
            "vigencia abierta del mismo ámbito."
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        periodo_inicio = cleaned_data.get("periodo_inicio")
        periodo_fin = cleaned_data.get("periodo_fin")

        if periodo_inicio and periodo_fin and periodo_fin < periodo_inicio:
            self.add_error(
                "periodo_fin",
                _(
                    "La fecha de fin de la vigencia no puede ser anterior a la "
                    "fecha de inicio."
                ),
            )

        cerrar_anterior = cleaned_data.get(CAMPO_CERRAR_VIGENCIA_ANTERIOR)
        if cerrar_anterior and periodo_inicio:
            abiertos = self._periodos_abiertos(cleaned_data)
            for abierto in abiertos:
                if abierto.periodo_inicio >= periodo_inicio:
                    self.add_error("periodo_inicio", MENSAJE_PERIODO_SIN_FIN)
                    break
            else:
                if self._hay_solapamiento_no_resoluble(
                    cleaned_data, periodo_inicio, periodo_fin, abiertos
                ):
                    campos = tuple(
                        getattr(self.instance.__class__, "vigencia_scope_fields", ())
                        or ()
                    )
                    self.add_error("periodo_inicio", mensaje_de_solapamiento(campos))

        return cleaned_data

    def _post_clean(self):
        """Defer exclusion-constraint validation when rollover resolves it."""
        if not self.cleaned_data.get(CAMPO_CERRAR_VIGENCIA_ANTERIOR) or not self.instance._state.adding:
            return super()._post_clean()

        opts = self._meta
        exclude = self._get_validation_exclusions()
        for name, field in self.fields.items():
            if isinstance(field, InlineForeignKeyField):
                exclude.add(name)

        try:
            self.instance = construct_instance(
                self, self.instance, opts.fields, opts.exclude
            )
            self.instance.full_clean(
                exclude=exclude,
                validate_unique=False,
                validate_constraints=False,
            )
        except ValidationError as error:
            self._update_errors(error)

        if self._validate_unique:
            self.validate_unique()

    def _periodos_abiertos(self, cleaned_data):
        """Open periods of the same scope as the submitted values."""
        modelo = self.instance.__class__
        scope = {}
        for campo in getattr(modelo, "vigencia_scope_fields", ()) or ():
            valor = cleaned_data.get(campo)
            scope[f"{campo}_id"] = getattr(valor, "pk", valor)
        return list(modelo.objects.filter(periodo_fin__isnull=True, **scope))

    def _hay_solapamiento_no_resoluble(
        self, cleaned_data, periodo_inicio, periodo_fin, abiertos
    ):
        """Check closed siblings because rollover only resolves open periods."""
        modelo = self.instance.__class__
        scope = {}
        for campo in getattr(modelo, "vigencia_scope_fields", ()) or ():
            valor = cleaned_data.get(campo)
            scope[f"{campo}_id"] = getattr(valor, "pk", valor)

        hermanos = modelo.objects.filter(**scope).exclude(
            pk__in=[abierto.pk for abierto in abiertos]
        )
        if periodo_fin is not None:
            hermanos = hermanos.filter(periodo_inicio__lte=periodo_fin)
        return hermanos.filter(
            Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=periodo_inicio)
        ).exists()


class VigenciaAdminMixin(SimpleHistoryAdmin):
    """
    Date-aware admin behaviour shared by every validity-period model.
    """

    ordering = ["-periodo_inicio"]
    date_hierarchy = "periodo_inicio"
    list_filter = [VigenteHoyFilter]
    form = VigenciaAdminForm

    def get_list_display(self, request):
        return [*self.list_display, "vigente_hoy", "periodo_abierto"]

    @admin.display(boolean=True, description=_("Vigente hoy"))
    def vigente_hoy(self, obj):
        """True when the validity window contains today (runtime semantics)."""
        hoy = date.today()
        if obj.periodo_inicio is None or obj.periodo_inicio > hoy:
            return False
        return obj.periodo_fin is None or obj.periodo_fin >= hoy

    @admin.display(boolean=True, description=_("Abierto"))
    def periodo_abierto(self, obj):
        """True when the validity period has no end date."""
        return obj.periodo_fin is None

    def get_form(self, request, obj=None, **kwargs):
        """The rollover switch only makes sense when adding a new period."""
        form_class = super().get_form(request, obj, **kwargs)
        if obj is not None:
            form_class.base_fields.pop(CAMPO_CERRAR_VIGENCIA_ANTERIOR, None)
        return form_class

    def save_model(self, request, obj, form, change):
        """
        Save the object, closing the previously open period of the same scope.

        The rollover is atomic: either the previous period is closed *and* the
        new one is created, or nothing changes at all.
        """
        if change or not form.cleaned_data.get(CAMPO_CERRAR_VIGENCIA_ANTERIOR):
            super().save_model(request, obj, form, change)
            return

        with transaction.atomic():
            try:
                cerrados = cerrar_vigencias_previas(
                    obj.__class__,
                    scope=scope_de(obj),
                    periodo_inicio=obj.periodo_inicio,
                )
            except ValidationError:
                # The form already validates this case; re-raise so the
                # transaction is rolled back instead of saving an inconsistent row.
                raise
            super().save_model(request, obj, form, change)

        if cerrados:
            self.message_user(request, MENSAJE_ROLLOVER, messages.SUCCESS)
