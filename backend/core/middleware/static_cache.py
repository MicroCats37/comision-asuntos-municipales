"""
Middleware para agregar headers de caché a rutas de datos estáticos.

Rutas que se cachean (1 año):
- /api/entidades/ubigeo/distritos
- /api/entidades/municipalidades
"""

from django.http import HttpResponse


CACHEABLE_PREFIXES = [
    # DESACTIVADO EN PRUEBAS — el cache de 1 año en distritos causaba que el
    # navegador mostrara distritos obsoletos (viejos UUIDs) tras reseed.
    # /api/entidades/ubigeo/distritos
    # /api/entidades/municipalidades
]

ONE_YEAR = 31536000


class StaticDataCacheMiddleware:
    """Agrega Cache-Control: public, max-age=1 año a rutas de datos estáticos."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        path = request.path
        if any(path.startswith(prefix) for prefix in CACHEABLE_PREFIXES):
            if isinstance(response, HttpResponse):
                response["Cache-Control"] = f"public, max-age={ONE_YEAR}"

        return response
