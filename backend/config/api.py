"""
Instancia central de NinjaExtraAPI.
Aquí se registran todos los routers y controllers del proyecto.
"""

from ninja_extra import NinjaExtraAPI
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController

from core.exceptions import register_exception_handlers
from modules.usuarios.presentation.controllers.auth_controller import AuthLoginController
from modules.usuarios.presentation.controllers.ingeniero_habilitado_controller import IngenieroHabilitadoController
from modules.entidades.presentation.controllers.entidad_controller import EntidadesController
from modules.entidades.presentation.controllers.consulta_controller import ConsultaController
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_habilitacion_urbana_controller import (
    LiquidacionHabilitacionUrbanaController,
)

import os

api_version = "2.0.0"
api_namespace = "api"

if os.environ.get("PYTEST_CURRENT_TEST"):
    import sys
    from ninja.errors import ConfigError
    import uuid

    if hasattr(sys, "_ninja_api_instance"):
        api = sys._ninja_api_instance
    else:
        try:
            api = NinjaExtraAPI(
                title="Generic API (Test)",
                version=api_version,
                urls_namespace="api-test-suite",
                description="Generic API Boilerplate",
                auth=JWTAuth(),
                docs_url="/docs",
            )
        except ConfigError:
            api = NinjaExtraAPI(
                title="Generic API (Test)",
                version=api_version,
                urls_namespace=f"api-test-{uuid.uuid4().hex[:6]}",
                description="Generic API Boilerplate",
                auth=JWTAuth(),
                docs_url="/docs",
            )
        sys._ninja_api_instance = api
else:
    api = NinjaExtraAPI(
        title="Generic API",
        version=api_version,
        urls_namespace=api_namespace,
        description="Generic API Boilerplate",
        auth=JWTAuth(),
        docs_url="/docs",
    )

# ── Controllers JWT (token/pair, token/refresh, token/verify) ─
api.register_controllers(NinjaJWTDefaultController)

# ── Auth Controllers (modular login by username/dni/email) ─
api.register_controllers(AuthLoginController)

# ── Ingeniero Habilitado Controllers ─
api.register_controllers(IngenieroHabilitadoController)

# ── Entidades Controllers ─
api.register_controllers(EntidadesController)
api.register_controllers(ConsultaController)

# ── Liquidaciones Controllers ─
api.register_controllers(LiquidacionHabilitacionUrbanaController)

# ── Exception handlers globales ────────────────────────────────
register_exception_handlers(api)