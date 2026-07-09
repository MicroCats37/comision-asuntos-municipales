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
from modules.finanzas.presentation.controllers.finanzas_controller import FinanzasController
from modules.liquidaciones.presentation.controllers.liquidacion_edificaciones_controller import LiquidacionEdificacionesController
from modules.liquidaciones.presentation.controllers.liquidaciones_general_controller import LiquidacionesGeneralController
from modules.liquidaciones.presentation.controllers.proyectista_controller import ProyectistaController
from modules.liquidaciones.presentation.controllers.proyecto_controller import ProyectoController
from modules.liquidaciones.presentation.controllers.habilitacion_urbana_controller import HabilitacionUrbanaController
from modules.liquidaciones.presentation.controllers.mecanica_suelos_controller import MecanicaSuelosController
from modules.liquidaciones.presentation.controllers.impacto_vial_controller import ImpactoVialController
from modules.liquidaciones.presentation.controllers.taludes_controller import TaludesController
from modules.liquidaciones.presentation.controllers.inspeccion_obra_controller import InspeccionObraController
from modules.entidades.presentation.controllers.entidad_controller import EntidadesController
from modules.entidades.presentation.controllers.consulta_controller import ConsultaController

import os

api_version = "2.0.0"
api_namespace = "api"

if os.environ.get("PYTEST_CURRENT_TEST"):
    import sys
    from ninja.errors import ConfigError
    import uuid

    # Singleton simple: intentamos reusar la instancia si ya existe en sys
    if hasattr(sys, "_ninja_api_instance"):
        api = sys._ninja_api_instance
    else:
        # Si no existe en sys, la creamos cuidando de problemas de registro repetido
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
            # Si el namespace 'api-test-suite' ya fue tomado por otra instancia muerta pero registrada
            # generamos un nombre aleatorio que no colisione
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

# ── Finanzas Controllers ─
api.register_controllers(FinanzasController)

# ── Liquidaciones Controllers ─
# Specific controllers registered BEFORE general to avoid route collision
# (specific routes like /liquidaciones/edificaciones are matched before /liquidaciones/{id})
api.register_controllers(LiquidacionEdificacionesController)
api.register_controllers(HabilitacionUrbanaController)
api.register_controllers(MecanicaSuelosController)
api.register_controllers(ImpactoVialController)
api.register_controllers(TaludesController)
api.register_controllers(InspeccionObraController)
api.register_controllers(LiquidacionesGeneralController)
api.register_controllers(ProyectistaController)
api.register_controllers(ProyectoController)

# ── Entidades Controllers ─
api.register_controllers(EntidadesController)
api.register_controllers(ConsultaController)

# ── Exception handlers globales ────────────────────────────────
register_exception_handlers(api)

# ── Routers por módulo (Legacy o Funcionales) ──────────────────
# TODO: Aquí se registrarán otros módulos según se migren.
