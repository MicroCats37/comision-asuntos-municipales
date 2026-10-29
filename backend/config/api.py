"""
Instancia central de NinjaExtraAPI.
Aquí se registran todos los routers y controllers del proyecto.
"""

from ninja_extra import ControllerBase, NinjaExtraAPI, api_controller, http_post
from ninja_extra.permissions import AllowAny
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import TokenBlackListController, TokenVerificationController
from ninja_jwt.schema_control import SchemaControl
from ninja_jwt.settings import api_settings as ninja_jwt_api_settings

from core.exceptions import register_exception_handlers
from core.security import jwt_required_docs
from modules.usuarios.presentation.controllers.auth_controller import AuthLoginController
from modules.usuarios.presentation.controllers.ingeniero_habilitado_controller import IngenieroHabilitadoController
from modules.entidades.presentation.controllers.entidad_controller import EntidadesController
from modules.entidades.presentation.controllers.consulta_controller import ConsultaController
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_habilitacion_urbana_controller import (
    LiquidacionHabilitacionUrbanaController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_inspeccion_obra_controller import (
    LiquidacionInspeccionObraController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_mecanica_suelos_controller import (
    LiquidacionMecanicaSuelosController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_edificaciones_controller import (
    LiquidacionEdificacionesController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_impacto_vial_controller import (
    LiquidacionImpactoVialController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_taludes_controller import (
    LiquidacionTaludesController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_general_controller import (
    LiquidacionGeneralController,
)
from modules.liquidaciones.presentation.controllers.delegado_controller import (
    DelegadoController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_delegado_controller import (
    LiquidacionDelegadoController,
)
from modules.liquidaciones.presentation.controllers.inspector_controller import (
    InspectorController,
    LiquidacionInspectorController,
)
from modules.liquidaciones.presentation.controllers.tarifas_historicas_controller import (
    TarifasHistoricasController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_legacy.liquidacion_edificaciones_legacy_controller import (
    LiquidacionEdificacionesLegacyController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_legacy.liquidacion_taludes_legacy_controller import (
    LiquidacionTaludesLegacyController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_legacy.liquidacion_impacto_vial_legacy_controller import (
    LiquidacionImpactoVialLegacyController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_legacy.liquidacion_habilitacion_urbana_legacy_controller import (
    LiquidacionHabilitacionUrbanaLegacyController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_legacy.liquidacion_mecanica_suelos_legacy_controller import (
    LiquidacionMecanicaSuelosLegacyController,
)
from modules.liquidaciones.presentation.controllers.liquidacion_legacy.liquidacion_inspeccion_obra_legacy_controller import (
    LiquidacionInspeccionObraLegacyController,
)
from modules.finanzas.presentation.controllers.variables_controller import VariablesController
from modules.finanzas.presentation.controllers.rh_delegado.mensual_controller import (
    RHDelegadoMensualController,
)
from modules.finanzas.presentation.controllers.rh_delegado.detalle_controller import (
    RHDelegadoDetalleController,
)
from modules.finanzas.presentation.controllers.rh_inspector.mensual_controller import (
    RHInspectorMensualController,
)
from modules.finanzas.presentation.controllers.rh_inspector.detalle_controller import (
    RHInspectorDetalleController,
)
from modules.finanzas.presentation.controllers.rh_reparticion_estacional.controller import (
    RHReparticionEstacionalController,
)

import os

api_version = "2.0.0"
api_namespace = "api"

# ── Autenticación global ─────────────────────────────────────────────────────
# `auth=JWTAuth()` es la ÚNICA fuente de autenticación del API: toda operación
# que no declare `auth=None` de forma explícita hereda este JWTAuth.
# La allowlist pública se declara exclusivamente en los controllers marcados
# con `auth=None` (login modular + ciclo de vida técnico del token).
_jwt_schema = SchemaControl(ninja_jwt_api_settings)

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
                docs_decorator=jwt_required_docs,
            )
        except ConfigError:
            api = NinjaExtraAPI(
                title="Generic API (Test)",
                version=api_version,
                urls_namespace=f"api-test-{uuid.uuid4().hex[:6]}",
                description="Generic API Boilerplate",
                auth=JWTAuth(),
                docs_url="/docs",
                docs_decorator=jwt_required_docs,
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
        docs_decorator=jwt_required_docs,
    )


@api_controller("/token", permissions=[AllowAny], tags=["token"], auth=None)
class NinjaJWTPublicTokenController(ControllerBase, TokenVerificationController):
    """Operaciones públicas del ciclo de vida del token: ``refresh`` y ``verify``.

    ``POST /token/pair`` de django-ninja-jwt **no** se expone: la aplicación ya
    tiene su propia superficie de login en ``/auth/login/{username,dni,email}``
    y un segundo camino público de credenciales sería una entrada redundante y
    no deseable. ``/token/refresh`` y ``/token/verify`` sí son técnicos e
    indispensables: el cliente presenta el refresh token en el body (sin access
    token todavía) y la verificación opera sobre el valor del token.
    """

    auto_import = False

    @http_post(
        "/refresh",
        response=_jwt_schema.obtain_pair_refresh_schema.get_response_schema(),
        url_name="token_refresh",
        operation_id="token_refresh",
    )
    def refresh_token(self, refresh_token: _jwt_schema.obtain_pair_refresh_schema):
        return refresh_token.to_response_schema()


@api_controller("/token", tags=["token"])
class NinjaJWTProtectedTokenController(ControllerBase):
    """Credential exchange retained behind the API's global JWT auth."""

    auto_import = False

    @http_post(
        "/pair",
        response=_jwt_schema.obtain_pair_schema.get_response_schema(),
        url_name="token_obtain_pair",
        operation_id="token_obtain_pair",
    )
    def obtain_token(self, user_token: _jwt_schema.obtain_pair_schema):
        user_token.check_user_authentication_rule()
        return user_token.to_response_schema()


@api_controller("/token", permissions=[AllowAny], tags=["token"], auth=None)
class NinjaJWTBlacklistController(TokenBlackListController):
    """Expose django-ninja-jwt refresh-token revocation."""

    auto_import = False


# ── Controllers JWT ─
api.register_controllers(NinjaJWTPublicTokenController)
api.register_controllers(NinjaJWTProtectedTokenController)
api.register_controllers(NinjaJWTBlacklistController)

# ── Auth Controllers (modular login by username/dni/email) ─
api.register_controllers(AuthLoginController)

# ── Ingeniero Habilitado Controllers ─
api.register_controllers(IngenieroHabilitadoController)

# ── Entidades Controllers ─
api.register_controllers(EntidadesController)
api.register_controllers(ConsultaController)

# ── Liquidaciones Controllers ─
api.register_controllers(LiquidacionHabilitacionUrbanaController)
api.register_controllers(LiquidacionInspeccionObraController)
api.register_controllers(LiquidacionMecanicaSuelosController)
api.register_controllers(LiquidacionEdificacionesController)
api.register_controllers(LiquidacionImpactoVialController)
api.register_controllers(LiquidacionTaludesController)
api.register_controllers(LiquidacionGeneralController)

# ── Liquidaciones Legacy Controllers (T7) ─
api.register_controllers(LiquidacionEdificacionesLegacyController)
api.register_controllers(LiquidacionTaludesLegacyController)
api.register_controllers(LiquidacionImpactoVialLegacyController)
api.register_controllers(LiquidacionHabilitacionUrbanaLegacyController)
api.register_controllers(LiquidacionMecanicaSuelosLegacyController)
api.register_controllers(LiquidacionInspeccionObraLegacyController)

# ── Delegados Controllers ─
api.register_controllers(DelegadoController)

# ── Delegados de Liquidación ─
api.register_controllers(LiquidacionDelegadoController)

# ── Inspectores Controllers ─
api.register_controllers(InspectorController)
api.register_controllers(LiquidacionInspectorController)

# ── Tarifas y Derechos Históricos ─
api.register_controllers(TarifasHistoricasController)

# ── Finanzas Controllers ─
api.register_controllers(VariablesController)
api.register_controllers(RHDelegadoMensualController)
api.register_controllers(RHDelegadoDetalleController)
api.register_controllers(RHInspectorMensualController)
api.register_controllers(RHInspectorDetalleController)
api.register_controllers(RHReparticionEstacionalController)

# ── Exception handlers globales ────────────────────────────────
register_exception_handlers(api)
