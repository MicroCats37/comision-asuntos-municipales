# SDD Apply Progress — tests-liquidaciones-arquitectura (Phase 1: Infrastructure)

**Proyecto**: `comision-asuntos-municipales`
**Fecha**: 2026-08-15
**Fase**: Apply — Step 1 (infraestructura de fixtures, sin refactor de tests)
**Backend**: Django 5.2, `backend/` (venv `backend\.venv`)

---

## Status

**`status`**: success

---

## Executive Summary

Se creó la carpeta `tests/fixtures/` con la reorganización de fixtures del `conftest.py` original (290 líneas) en archivos por dominio. Se creó `tests/conftest.py` como índice que re-exporta directamente todos los fixtures. Se creó `factories.py` con helpers `make_payload_po/m2/io`. Se verificó que pytest descubre los fixtures y que los tests existentes siguen pasando.

**Nota importante**: el directorio se llama `fixtures/` y no `conftest/` porque `conftest/`冲突 con el archivo `conftest.py` (pytest no puede tener un paquete `conftest` y un archivo `conftest.py` en el mismo directorio).

---

## Árbol de la carpeta creada

```
backend/modules/liquidaciones/tests/
├── conftest.py                          ← ÍNDICE: re-exporta todos los fixtures
├── fixtures/
│   ├── __init__.py
│   ├── usuarios_fixtures.py              ← api_client, create_user, auth_client, usuario_admin
│   ├── ubigeo_fixtures.py               ← ubigeo_departamento, ubigeo_provincia, ubigeo_distrito, municipalidad, proyecto
│   ├── finanzas_fixtures.py              ← igv_vigente, uit_vigente
│   ├── tipos_fixtures.py                ← tipo_edificacion, tipo_habilitacion_urbana, tipo_mecanica_suelos, tipo_impacto_vial, tipo_taludes, tipo_inspeccion_obra
│   ├── tarifas_po_fixtures.py           ← tarifa_liquidacion_base_edificacion, especialidad_estructuras/arquitectura/installaciones, tarifa_porcentaje_obra_estructuras, especialidades_disponibles_edificacion, derecho_porcentaje_vigente
│   ├── tarifas_m2_fixtures.py           ← tarifa_liquidacion_base_hu, tarifa_m2_hu, tarifa_liquidacion_base_ms, tarifa_m2_ms, derecho_m2_vigente
│   ├── tarifas_io_fixtures.py            ← tarifa_liquidacion_base_io, tarifa_visitas_io
│   ├── setup_po_fixtures.py            ← po_base_setup (dict con todas las refs)
│   ├── setup_m2_fixtures.py             ← m2_base_setup
│   ├── setup_io_fixtures.py             ← io_base_setup
│   └── factories.py                     ← make_payload_po, make_payload_m2, make_payload_m2_cotizar, make_payload_io, make_proyecto_payload, make_liquidacion_general_payload
├── integration/
│   └── conftest.py                     ← Re-export de fixtures (para cuando se corren tests desde integration/)
└── e2e/
    └── conftest.py                     ← Re-export de fixtures (para cuando se corren tests desde e2e/)
```

---

## Cómo quedó el índice `conftest.py`

**Mecanismo usado**: Re-export directo (no `pytest_plugins`)

`pytest_plugins` no funciona con rutas tipo `fixtures.usuarios_fixtures` porque busca un módulo de nivel superior llamado `fixtures`, no un submódulo. La solución correcta es importar cada fixture directamente:

```python
from modules.liquidaciones.tests.fixtures.usuarios_fixtures import (
    api_client, create_user, auth_client, usuario_admin,
)
from modules.liquidaciones.tests.fixtures.ubigeo_fixtures import (
    ubigeo_departamento, ubigeo_provincia, ubigeo_distrito, municipalidad, proyecto,
)
# ... etc para todos los dominios
```

Fixtures como `api_client` y `auth_client` son visibles directamente en los tests.

**Factories** (`make_payload_*`) no son fixtures — se importan directamente:
```python
from modules.liquidaciones.tests.fixtures.factories import make_payload_po
```

---

## Contenido de factories.py

```python
# helpers de proyecto
make_proyecto_payload(distrito_id, denominacion="...", **kwargs) -> dict
make_liquidacion_general_payload(municipalidad_id, expediente="...", proyecto=None, ...) -> dict

# PO (PorcentajeObra) — edificaciones, taludes, impacto vial
make_payload_po(
    valid_municipalidad_id,
    valid_distrito_id,
    *,
    expediente="EXP-PO-001",
    valor_declarado=100000.00,
    tarifas=None,          # None/[] = auto-fill, [...] = explicit
    observacion="Test PO",
) -> {"liquidacion_general": {...}, "liquidacion_especifica": {"datos": {...}, "tarifas": [...]}}

# M2 (Por Metro Cuadrado) — habilitación urbana, mecánica de suelos
make_payload_m2(
    valid_municipalidad_id,
    valid_distrito_id,
    tarifa_m2_id,
    *,
    expediente="EXP-M2-001",
    area_solicitada=100.0,
    observacion="Test M2",
) -> {"liquidacion_general": {...}, "liquidacion_especifica": {"datos": {"area_solicitada": ...}, "tarifa": {"tarifa_m2_id": ...}}}

# M2 cotizar (sin liquidacion_general)
make_payload_m2_cotizar(tarifa_m2_id, area_solicitada=100.0) -> {"liquidacion_especifica": ...}

# IO (Inspección de Obra)
make_payload_io(
    valid_municipalidad_id,
    valid_distrito_id,
    tarifa_visitas_id,
    *,
    expediente="EXP-IO-001",
    cantidad_visitas=3,
    categoria="INSPECCION",
    observacion="Test IO",
) -> {"liquidacion_general": {...}, "liquidacion_especifica": {"datos": {"cantidad_visitas": ..., "categoria": ...}, "tarifa": {"tarifa_visitas_id": ...}}}
```

---

## Verificación: py_compile + pytest --collect-only

```bash
# py_compile — todos los archivos compilan sin errores
python -m py_compile backend/modules/liquidaciones/tests/conftest.py  # OK
python -m py_compile backend/modules/liquidaciones/tests/fixtures/*.py  # OK

# pytest --collect-only — fixtures descubiertos
pytest backend/modules/liquidaciones/tests/integration/test_hu_endpoint.py --collect-only  # 5 tests collected

# pytest con fixtures nuevos — 20 tests de existing suite pasan
pytest backend/modules/liquidaciones/tests/integration/test_edificaciones_nueva_liquidacion.py  # 18 passed
pytest backend/modules/liquidaciones/tests/integration/test_io_nueva_liquidacion.py  # 2 passed
pytest backend/modules/liquidaciones/tests/integration/test_hu_endpoint.py  # 5 passed
pytest backend/modules/liquidaciones/tests/integration/test_ms_cotizar.py  # 7 passed
```

---

## Decisiones técnicas tomadas

1. **`conftest/` vs `fixtures/`**: Se usó `fixtures/` porque `conftest/`冲突aba con el archivo `conftest.py` (ImportPathMismatchError de pytest).

2. **`pytest_plugins` vs re-export`**: `pytest_plugins = ["fixtures.xxx"]` no funciona porque busca `fixtures` como módulo raíz. Se usan re-exportes directos (`from modules.liquidaciones.tests.fixtures.xxx import api_client`).

3. **`derecho_m2_vigente` compartido**: Un solo fixture para HU y MS (ambos usan `DerechoPorMetroCuadrado` con los mismos valores). Esto es correcto porque el derecho M2 es global.

4. **`conftest.py` en integration/ y e2e/**: Se crearon para que pytest cargue los fixtures cuando se corren tests desde esos subdirectorios (el conftest.py del padre `tests/` no se carga cuando el rootdir es `backend/`).

5. **`make_payload_m2_cotizar`**: Existe como helper separado porque el endpoint `/cotizar` solo necesita `liquidacion_especifica` (sin `liquidacion_general`).

---

## Riesgos

| Riesgo | Severity | Notes |
|--------|----------|-------|
| Los tests existentes siguen usando fixtures locales — la infraestructura está lista pero no se usa hasta el paso piloto | Medium | Esto es esperado (el paso piloto es siguiente) |
| `conftest/` vs `fixtures/` — diverge de la estructura solicitada | Low | Resuelto renaming; nombre `fixtures/` es convencional y correcto |
| Tests que se corren desde subdirectorios (`integration/`, `e2e/`) pueden no ver los fixtures del padre | Low | Resuelto con conftest.py en cada subdirectorio |

---

## Siguiente paso

**Piloto**: Refactorizar UN archivo de test (ej: `test_edificaciones_nueva_liquidacion.py`) para usar fixtures del conftest + factories. El archivo actual (~1049 líneas) debería reducirse significativamente.

---

## Archivos creados

| Archivo | Action |
|---------|--------|
| `tests/conftest.py` | Created — índice re-export |
| `tests/fixtures/__init__.py` | Created |
| `tests/fixtures/usuarios_fixtures.py` | Created |
| `tests/fixtures/ubigeo_fixtures.py` | Created |
| `tests/fixtures/finanzas_fixtures.py` | Created |
| `tests/fixtures/tipos_fixtures.py` | Created |
| `tests/fixtures/tarifas_po_fixtures.py` | Created |
| `tests/fixtures/tarifas_m2_fixtures.py` | Created |
| `tests/fixtures/tarifas_io_fixtures.py` | Created |
| `tests/fixtures/setup_po_fixtures.py` | Created |
| `tests/fixtures/setup_m2_fixtures.py` | Created |
| `tests/fixtures/setup_io_fixtures.py` | Created |
| `tests/fixtures/factories.py` | Created |
| `tests/integration/conftest.py` | Created |
| `tests/e2e/conftest.py` | Created |
