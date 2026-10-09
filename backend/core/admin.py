"""Core admin UI customizations."""

from types import MethodType

from django.contrib import admin

# ---------------------------------------------------------------------------------------------
# SECTION DEFINITIONS — order defines sidebar order
# Each entry: (section_name, [model_object_names in display order])
# ---------------------------------------------------------------------------------------------
_LIQUIDACIONES_SECTION_ORDER = [
    ("Liquidación", ["LiquidacionGeneral", "LiquidacionDelegado"]),
    (
        "Liquidaciones por Tipo",
        [
            "LiquidacionEdificacionProxy",
            "LiquidacionHabilitacionUrbanaProxy",
            "LiquidacionMecanicaSuelosProxy",
            "LiquidacionTaludesProxy",
            "LiquidacionInspeccionObraProxy",
            "LiquidacionImpactoVialProxy",
        ],
    ),
    (
        "Tarifas y Reglas",
        [
            "TarifaLiquidacionBase",
            "TarifaPorMetroCuadrado",
            "TarifaPorCategoriaVisitas",
            "TarifaPorcentajeObra",
            "DerechoPorcentajeObra",
            "DerechoPorMetroCuadrado",
            "LiquidacionEspecialidadDisponibles",
        ],
    ),
    (
        "Profesionales",
        [
            "Delegado",
            "DelegadoOperacion",
            "Inspector",
            "InspectorOperacion",
            "Proyectista",
        ],
    ),
    ("Catálogos", ["TipoLiquidacion"]),
    ("Proyectos", ["Proyecto"]),
    ("Inspecciones", ["LiquidacionInspector"]),
]

# Fast lookup: model_name -> section name
_MODEL_TO_SECTION = {model_name: section for section, names in _LIQUIDACIONES_SECTION_ORDER for model_name in names}

# ---------------------------------------------------------------------------------------------
# FINANZAS SECTION DEFINITIONS — order defines sidebar order
# ---------------------------------------------------------------------------------------------
_FINANZAS_SECTION_ORDER = [
    (
        "RH Inspector",
        [
            "ReciboHonorarioInspectorMensual",
            "RegistroPagoInspector",
        ],
    ),
    (
        "RH Delegado",
        [
            "ReciboHonorarioDelegado",
            "ReciboHonorarioDelegadoMensual",
        ],
    ),
    (
        "Repartición Estacional",
        [
            "RHReparticionEstacional",
        ],
    ),
    (
        "Impuestos y Tasas",
        [
            "IGV",
            "UIT",
            "TasaDelegado",
        ],
    ),
    (
        "Descuentos Inspector",
        [
            "EscalaDescuentoInspector",
            "RangoDescuentoInspector",
            "ReciboHonorarioInspector",
        ],
    ),
]

_FINANZAS_MODEL_TO_SECTION = {model_name: section for section, names in _FINANZAS_SECTION_ORDER for model_name in names}


def _build_finanzas_sections(finanzas_app):
    """Build pseudo-app entries for finanzas models, grouped by section."""
    all_models = finanzas_app["models"]

    # Index all models by object_name for O(1) lookup
    by_name = {m["object_name"]: m for m in all_models}

    # Collect models per section, preserving section order and model order within
    section_models = {section: [] for section, _ in _FINANZAS_SECTION_ORDER}
    for section, model_names in _FINANZAS_SECTION_ORDER:
        for name in model_names:
            if name in by_name:
                section_models[section].append(by_name[name])

    # Build pseudo-app entries
    pseudo_apps = []
    for (section_name, _), models in zip(_FINANZAS_SECTION_ORDER, section_models.values()):
        if not models:
            continue
        first_model = models[0]
        pseudo_apps.append(
            {
                "app_label": section_name.lower().replace(" ", "_"),
                "app_name": section_name,
                "app_url": first_model["admin_url"],
                "has_module_perms": True,
                "has_visible_models": True,
                "models": models,
                "name": section_name,
            }
        )

    return pseudo_apps


def _build_liquidacion_sections(liquidaciones_app):
    """Build pseudo-app entries for liquidaciones models, grouped by section."""
    all_models = liquidaciones_app["models"]

    # Index all models by object_name for O(1) lookup
    by_name = {m["object_name"]: m for m in all_models}

    # Collect models per section, preserving section order and model order within
    section_models = {section: [] for section, _ in _LIQUIDACIONES_SECTION_ORDER}
    for section, model_names in _LIQUIDACIONES_SECTION_ORDER:
        for name in model_names:
            if name in by_name:
                section_models[section].append(by_name[name])

    # Build pseudo-app entries
    pseudo_apps = []
    for (section_name, _), models in zip(_LIQUIDACIONES_SECTION_ORDER, section_models.values()):
        if not models:
            continue
        first_model = models[0]
        pseudo_apps.append(
            {
                "app_label": section_name.lower().replace(" ", "_"),
                "app_name": section_name,
                "app_url": first_model["admin_url"],
                "has_module_perms": True,
                "has_visible_models": True,
                "models": models,
                "name": section_name,
            }
        )

    return pseudo_apps


def _regroup_app_list(original_get_app_list):
    """
    Return a get_app_list wrapper that groups liquidaciones and finanzas
    models into pseudo-app sections.
    """

    def get_app_list(self, request, app_label=None):
        app_list = original_get_app_list(request, app_label)

        liquidaciones_app = None
        finanzas_app = None
        for app in app_list:
            if app["app_label"] == "liquidaciones":
                liquidaciones_app = app
            elif app["app_label"] == "finanzas":
                finanzas_app = app

        if not liquidaciones_app and not finanzas_app:
            return app_list

        result = [app for app in app_list if app["app_label"] not in ("liquidaciones", "finanzas")]

        if liquidaciones_app:
            result.extend(_build_liquidacion_sections(liquidaciones_app))

        if finanzas_app:
            result.extend(_build_finanzas_sections(finanzas_app))

        return result

    return get_app_list


if not getattr(admin.site, "_cam_liquidacion_promoted", False):
    admin.site.get_app_list = MethodType(
        _regroup_app_list(admin.site.get_app_list),
        admin.site,
    )
    admin.site._cam_liquidacion_promoted = True
