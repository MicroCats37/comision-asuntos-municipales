"""Core admin UI customizations."""

from types import MethodType

from django.contrib import admin


def _promote_liquidacion_get_app_list(original_get_app_list):
    """Return a get_app_list wrapper that promotes LiquidacionGeneral to the top."""

    def get_app_list(self, request, app_label=None):
        app_list = original_get_app_list(request, app_label)

        liquidaciones_app = None
        liquidacion_model = None
        related_models = []

        for app in app_list:
            if app["app_label"] != "liquidaciones":
                continue

            liquidaciones_app = app
            for model in app["models"]:
                if model["object_name"] == "LiquidacionGeneral":
                    liquidacion_model = model
                elif model["object_name"] == "RevisionDelegado":
                    related_models.append(model)
            break

        if not liquidaciones_app or not liquidacion_model:
            return app_list

        liquidaciones_app["models"] = [
            model
            for model in liquidaciones_app["models"]
            if model["object_name"] not in {"LiquidacionGeneral", "RevisionDelegado"}
        ]

        if not liquidaciones_app["models"]:
            app_list = [app for app in app_list if app is not liquidaciones_app]

        app_list.insert(
            0,
            {
                "app_label": "liquidacion_principal",
                "app_name": "Liquidación",
                "app_url": liquidacion_model["admin_url"],
                "has_module_perms": True,
                "has_visible_models": True,
                "models": [liquidacion_model] + related_models,
                "name": "Liquidación",
            },
        )
        return app_list

    return get_app_list


if not getattr(admin.site, "_cam_liquidacion_promoted", False):
    admin.site.get_app_list = MethodType(
        _promote_liquidacion_get_app_list(admin.site.get_app_list),
        admin.site,
    )
    admin.site._cam_liquidacion_promoted = True
