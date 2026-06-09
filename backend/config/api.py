"""
Instancia central de NinjaExtraAPI.
Aquí se registran todos los routers y controllers del proyecto.
"""

from ninja_extra import NinjaExtraAPI
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController

from core.exceptions import register_exception_handlers

import os

api_version = "2.0.0"
api_namespace = "api-v2"

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

# ── Exception handlers globales ───────────────────────────────
register_exception_handlers(api)

# ── Routers por módulo (Legacy o Funcionales) ──────────────────
# TODO: Aquí se registrarán otros módulos según se migren.
