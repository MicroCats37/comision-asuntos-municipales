"""
Helpers HTTP compartidos por los tests de liquidaciones.

`ninja.testing.TestClient` NO devuelve una respuesta 404 cuando el path no
resuelve contra ninguna ruta de la API: lanza `Exception("Cannot resolve ...")`
(ver `ninja/testing/client.py::_resolve`). Y cuando el path resuelve contra una
ruta que no admite el metodo pedido, Django responde 405 Method Not Allowed.

`status_de_ruta_retirada` normaliza ambos casos a un status HTTP para que los
tests puedan afirmar la invariante real de un endpoint RETIRADO: no sirve el
listado ni el payload canonico.

No es un modulo de fixtures: no define `@pytest.fixture` y no se registra en
`conftest.py`. Los test files lo importan directamente.
"""
from typing import Any


def status_de_ruta_retirada(client: Any, path: str) -> int:
    """
    Devuelve el status HTTP de un endpoint retirado.

    - 404: ninguna ruta de la API resuelve el path (el cliente lanza Exception).
    - 405: el path resuelve contra una ruta que no admite GET.
    - Cualquier otro status significa que el endpoint retirado SIGUE sirviendo
      algo, y el test que lo consume debe fallar.
    """
    try:
        response = client.get(path)
    except Exception as exc:  # noqa: BLE001 - ninja lanza Exception plano
        assert "Cannot resolve" in str(exc), (
            f"Error inesperado al invocar el endpoint retirado {path!r}: {exc}"
        )
        return 404
    return response.status_code
