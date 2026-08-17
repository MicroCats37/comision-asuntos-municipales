# SDD Explore: Arquitectura de Tests — Liquidaciones

**Proyecto**: `comision-asuntos-municipales`
**Fecha**: 2026-08-15
**Fase**: Exploration
**Backend**: Django 5.2 + Django Ninja, `backend/` (venv `backend\.venv`)

---

## 1. Inventario de Endpoints de Liquidaciones

### 1.1 Controladores y Rutas

#### LiquidacionGeneralController — `/liquidaciones/generales`
| Método | Ruta | Operación | Auth | Motor |
|--------|------|-----------|------|-------|
| GET | `/liquidaciones/generales/` | Listar todas (paginated, filtros) | JWT | General |
| GET | `/liquidaciones/generales/ultimas-revisiones` | Última revisión por proyecto+tipo | JWT | General |

#### LiquidacionEdificacionesController — `/liquidaciones/edificaciones` (Motor PO)
| Método | Ruta | Operación | Auth | Motor |
|--------|------|-----------|------|-------|
| GET | `/edificaciones/tarifas/vigentes` | Tarifas vigentes | No | PO |
| GET | `/edificaciones/` | Listar (paginated, filtros) | JWT | PO |
| GET | `/edificaciones/{id}` | Detalle | No | PO |
| POST | `/edificaciones/nueva-liquidacion/primera-revision` | Crear primera revisión | JWT | PO |
| POST | `/edificaciones/nueva-revision` | Nueva revisión (3 o 5) | JWT | PO |
| GET | `/edificaciones/ultima-revision` | Última revisión por proyecto | JWT | PO |
| POST | `/edificaciones/cotizar` | Cotizar sin persistir | No | PO |

#### LiquidacionTaludesController — `/liquidaciones/taludes` (Motor PO)
| Método | Ruta | Operación | Auth | Motor |
|--------|------|-----------|------|-------|
| GET | `/taludes/` | Listar (paginated, filtros) | JWT | PO |
| GET | `/taludes/{id}` | Detalle | No | PO |
| GET | `/taludes/tarifas/vigentes` | Tarifas vigentes | No | PO |
| POST | `/taludes/nueva-liquidacion/primera-revision` | Crear | JWT | PO |
| POST | `/taludes/cotizar` | Cotizar sin persistir | No | PO |

#### LiquidacionMecanicaSuelosController — `/liquidaciones/mecanica-suelos` (Motor M2)
| Método | Ruta | Operación | Auth | Motor |
|--------|------|-----------|------|-------|
| GET | `/mecanica-suelos/tarifas/vigentes` | Tarifas vigentes | No | M2 |
| GET | `/mecanica-suelos/` | Listar (paginated, filtros) | No | M2 |
| GET | `/mecanica-suelos/{id}` | Detalle | No | M2 |
| POST | `/mecanica-suelos/nueva-liquidacion/primera-revision` | Crear | JWT | M2 |
| POST | `/mecanica-suelos/cotizar` | Cotizar | No | M2 |

#### LiquidacionHabilitacionUrbanaController — `/liquidaciones/habilitacion-urbana` (Motor M2)
| Método | Ruta | Operación | Auth | Motor |
|--------|------|-----------|------|-------|
| GET | `/habilitacion-urbana/tarifas/vigentes` | Tarifas vigentes | No | M2 |
| GET | `/habilitacion-urbana/` | Listar (paginated, filtros) | No | M2 |
| GET | `/habilitacion-urbana/{id}` | Detalle | No | M2 |
| POST | `/habilitacion-urbana/nueva-liquidacion/primera-revision` | Crear | JWT | M2 |
| POST | `/habilitacion-urbana/cotizar` | Cotizar | No | M2 |

#### LiquidacionInspeccionObraController — `/liquidaciones/inspeccion-obra` (Motor IO)
| Método | Ruta | Operación | Auth | Motor |
|--------|------|-----------|------|-------|
| GET | `/inspeccion-obra/tarifas/vigentes` | Tarifas vigentes | No | IO |
| GET | `/inspeccion-obra/` | Listar (paginated, filtros) | No | IO |
| GET | `/inspeccion-obra/{id}` | Detalle | No | IO |
| POST | `/inspeccion-obra/cotizar` | Cotizar | No | IO |
| POST | `/inspeccion-obra/nueva-liquidacion/primera-revision` | Crear | JWT | IO |
| POST | `/inspeccion-obra/nueva-liquidacion/primera-revision-desde-previa` | Crear desde previa | JWT | IO |

#### LiquidacionImpactoVialController — `/liquidaciones/impacto-vial` (Motor PO)
| Método | Ruta | Operación | Auth | Motor |
|--------|------|-----------|------|-------|
| GET | `/impacto-vial/` | Listar (paginated, filtros) | JWT | PO |
| GET | `/impacto-vial/{id}` | Detalle | No | PO |
| GET | `/impacto-vial/tarifas/vigentes` | Tarifas vigentes | No | PO |
| POST | `/impacto-vial/nueva-liquidacion/primera-revision` | Crear | JWT | PO |
| POST | `/impacto-vial/cotizar` | Cotizar sin persistir | No | PO |

#### DelegadoController — `/delegados`
| Método | Ruta | Operación | Auth |
|--------|------|-----------|------|
| GET | `/delegados/` | Listar todos (paginated, filtros) | No |
| GET | `/delegados/{id}/municipalidades` | Municipalidades del delegado | No |
| GET | `/delegados/municipalidad/{id}` | Delegados por municipalidad | No |

#### LiquidacionDelegadoController — `/liquidaciones`
| Método | Ruta | Operación | Auth |
|--------|------|-----------|------|
| GET | `/liquidaciones/delegados/vigentes` | Delegados vigentes | No |
| GET | `/liquidaciones/delegados-asignaciones` | Lista asignaciones | No |
| PATCH | `/liquidaciones/{id}/delegados` | Batch crear/eliminar delegados | No |

#### InspectorController — `/inspectores`
| Método | Ruta | Operación | Auth |
|--------|------|-----------|------|
| GET | `/inspectores/` | Listar todos | No |
| GET | `/inspectores/vigentes` | Inspectores vigentes | No |
| GET | `/inspectores/{id}` | Detalle | No |

#### TarifasHistoricasController — `/liquidaciones`
| Método | Ruta | Operación | Auth |
|--------|------|-----------|------|
| GET | `/liquidaciones/{tipo}/tarifas/historicas` | Tarifas históricas | No |
| GET | `/liquidaciones/derechos/historicos` | Derechos históricos | No |

---

## 2. Inventario de Servicios y Flujos Clave

### 2.1 Core Services (puros — ORM + matemática, sin lógica de negocio)

| Servicio | Responsabilidad | Métodos clave |
|----------|----------------|---------------|
| `LiquidacionGeneralCoreService` | Entidad, Proyecto, LiquidacionGeneral (ORM) | `create_entidad`, `create_proyecto`, `create_liquidacion_general`, `get_uit_vigente`, `get_igv_vigente` |
| `LiquidacionPorcentajeObraCoreService` | Motor PO: resolución tarifas, cálculo, creación | `resolver_tarifas`, `calcular_cotizacion_po`, `crear_liquidacion_po` |
| `LiquidacionPorMetroCuadradoCoreService` | Motor M2: tarifas M2, derechos, cálculo | `get_tarifa_vigente_por_tipo`, `get_derecho_minimo_m2_vigente`, `calcular_cotizacion_m2` |
| `LiquidacionPorCategoriaVisitasCoreService` | Motor IO: tarifas visitas, cálculo | `get_tarifas_vigentes`, `calcular_subtotal_visitas` |
| `DelegadoCoreService` | Delegados y asignaciones | `list_delegados`, `obtener_delegados_vigentes` |
| `InspectorCoreService` | Inspectores | `list_inspectores`, `list_inspectores_vigentes` |

### 2.2 Orchestrators (orquestan core services + lógica de negocio)

| Orchestrator | Envuelve | Flujos que orquesta |
|--------------|----------|---------------------|
| `LiquidacionGeneralOrchestrator` | `LiquidacionGeneralCoreService` | `listar_liquidaciones_generales`, `listar_ultimas_liquidaciones_generales` |
| `LiquidacionEdificacionesOrchestrator` | PO core + General core | crear, cotizar, tarifas vigentes, detalle, lista, última revisión |
| `LiquidacionTaludesOrchestrator` | PO core + General core | idem edificaciones |
| `LiquidacionMecanicaSuelosOrchestrator` | M2 core + General core | idem |
| `LiquidacionHabilitacionUrbanaOrchestrator` | M2 core + General core | idem |
| `LiquidacionInspeccionObraOrchestrator` | IO core + General core | idem + crear desde previa |
| `LiquidacionImpactoVialOrchestrator` | PO core + General core | idem |
| `DelegadosBatchOrchestrator` | `DelegadoCoreService` | `obtener_delegados_vigentes`, `procesar_batch_delegados`, `listar_asignaciones` |
| `TarifasHistoricasOrchestrator` | — | `obtener_tarifas_historicas` |

### 2.3 Flujos de Negocio Críticos a Testear

| # | Flujo | Motor | Descripción |
|---|-------|-------|-------------|
| 1 | Crear liquidación PO (primera revisión) | PO | Crear liquidacion con valor_declarado y tarifas (auto-fill o explícito) |
| 2 | Crear liquidación M2 (HU, MS) | M2 | Crear con area_solicitada y tarifa_m2 |
| 3 | Crear liquidación IO | IO | Crear con cantidad_visitas y categoria |
| 4 | Cotizar PO sin persistir | PO | Verificar cálculo sin crear registro |
| 5 | Cotizar M2 sin persistir | M2 | Verificar cálculo sin crear registro |
| 6 | Cotizar IO sin persistir | IO | Verificar cálculo sin crear registro |
| 7 | Nueva revisión (edificaciones) | PO | Crear revisión 3 o 5 desde previa |
| 8 | Asignar delegados a liquidación | Batch | PATCH con create/delete de LiquidacionDelegado |
| 9 | Crear recibo honorario | — | Finanzas: calcular CIP, CODEMU, Fondo Común |
| 10 | Validación: valor negativo/zero | Todos | 400 para inputs inválidos |
| 11 | Tarifas vigentes por tipo | Todos | GET tarifas vigentes para el tipo |
| 12 | Lista/paginación liquidaciones | General | Filtros por tipo, municipalidad, fecha |

---

## 3. Estado Actual de los Tests — Inventario Completo

### 3.1 Estructura de Archivos

```
backend/modules/liquidaciones/tests/
├── conftest.py                          # 290 líneas — fixtures compartidos
├── integration/
│   ├── test_tarifas_historicas.py      # ~50 tests
│   ├── test_taludes_list.py             # ~5 tests
│   ├── test_taludes_detail.py           # ~3 tests
│   ├── test_ms_tarifas_vigentes.py      # ~5 tests
│   ├── test_ms_list.py                  # ~5 tests
│   ├── test_ms_detail.py                # ~3 tests
│   ├── test_ms_cotizar.py               # ~5 tests
│   ├── test_mecanica_suelos_nueva_liquidacion.py  # 10 tests
│   ├── test_iv_list.py                 # ~5 tests
│   ├── test_iv_detail.py               # ~3 tests
│   ├── test_io_nueva_liquidacion.py     # 2 tests
│   ├── test_io_list.py                 # ~5 tests
│   ├── test_io_detail.py               # ~3 tests
│   ├── test_hu_nueva_liquidacion.py    # ~8 tests
│   ├── test_hu_list.py                 # ~5 tests
│   ├── test_hu_detail.py               # ~3 tests
│   ├── test_hu_endpoint.py             # ~5 tests
│   ├── test_inspectores.py             # ~8 tests
│   ├── test_edificaciones_tarifas_vigentes.py  # ~5 tests
│   ├── test_edificaciones_nueva_revision.py    # ~5 tests
│   ├── test_edificaciones_nueva_liquidacion.py # 18 tests ⚠️
│   ├── test_edificaciones_list.py     # ~5 tests
│   ├── test_edificaciones_detail.py    # ~3 tests
│   ├── test_delegados_asignaciones.py # ~10 tests
│   └── test_delegados.py              # ~20 tests
└── e2e/
    ├── test_delegados_liquidacion_e2e.py  # 12 tests
    ├── test_e2e_taludes.py                # ~1 test
    ├── test_e2e_mecanica_suelos.py        # ~1 test
    ├── test_e2e_inspeccion_obra.py        # ~1 test
    ├── test_e2e_impacto_vial.py           # ~1 test
    ├── test_e2e_habilitacion_urbana.py    # ~1 test
    └── test_e2e_edificaciones.py          # 1 test ⚠️

backend/modules/finanzas/tests/
├── integration/
│   ├── test_variables_vigentes.py        # ~5 tests
│   ├── test_recibo_honorario.py         # 18 tests (unit + integration)
│   └── test_recibo_honorario_e2e.py     # ~10 tests
└── unit/
    └── (vacío — solo factories/__init__.py)
```

**Total estimado**: ~250 tests

### 3.2 Análisis de Repetición de Fixtures

#### Patrón de repetición identificado

Cada archivo de test define SUS PROPIAS versiones locales de los fixtures que YA EXISTEN en `conftest.py`. El problema NO es que no haya fixtures compartidos — el problema es que los tests no los usan.

**Ejemplo concreto**: `test_edificaciones_nueva_liquidacion.py` (1049 líneas) define localmente:
- `ubigeo_departamento`, `ubigeo_provincia`, `ubigeo_distrito` (copia exacta de conftest)
- `create_user`, `auth_client`, `api_client` (copia exacta de conftest)
- `municipalidad` (copia de conftest)
- `tarifa_liquidacion_base_edificacion`, `especialidad_estructuras`, `especialidad_arquitectura`, `especialidad_installaciones` (copias)
- `tarifa_porcentaje_obra_estructuras`, `igv_vigente`, `uit_vigente`, `derecho_porcentaje_vigente` (copias)
- `valid_payload_auto_fill`, `valid_payload_explicit`, `valid_tarifa_ids` (payloads quemados como dict literales)

**El mismo patrón se repite en**:
- `test_e2e_edificaciones.py` (~330 líneas, redefine todo)
- `test_mecanica_suelos_nueva_liquidacion.py` (~638 líneas, redefine todo)
- `test_io_nueva_liquidacion.py` (~224 líneas, redefine todo)
- `test_hu_nueva_liquidacion.py` (~similar)
- `test_e2e_mecanica_suelos.py`, `test_e2e_inspeccion_obra.py`, etc.

#### Cuantificación de la repetición

| Fixture | Veces redefinido | Líneas duplicadas |
|---------|-----------------|-------------------|
| `ubigeo_departamento` | ~10 archivos | ~100 |
| `ubigeo_provincia` | ~10 archivos | ~100 |
| `ubigeo_distrito` | ~10 archivos | ~100 |
| `create_user` | ~10 archivos | ~100 |
| `auth_client` | ~8 archivos | ~80 |
| `municipalidad` | ~8 archivos | ~80 |
| `igv_vigente` | ~6 archivos | ~60 |
| `uit_vigente` | ~6 archivos | ~60 |
| `tarifa_liquidacion_base_*` | ~4 archivos por tipo | ~160 |
| `especialidad_*` | ~4 archivos | ~80 |
| `derecho_porcentaje_vigente` | ~4 archivos | ~40 |

**Total de código duplicado por fixtures**: ~960+ líneas

#### Hardcode identificado

1. **Fechas quemadas**: `date(2024, 1, 1)` en igv_vigente, uit_vigente, tarifa_liquidacion_base — en TODOS los tests
2. **Valores literales**: `Decimal("0.18")` IGV, `Decimal("5150.00")` UIT, `Decimal("500.00")` derecho_minimo, `Decimal("50000.00")` derecho_maximo
3. **Expedientes**: `"EXP-EDIF-2024-001"`, `"EXP-MS-2024-001"` hardcodeados en payloads
4. **RUCs**: `"20456789012"` a `"20456789019"` inventados
5. **Nombres**: `"Proyecto Test Edificaciones"`, `"Propietario Test SAC"` hardcodeados
6. **UUIDs inventados**: `uuid.uuid4()` para casos negativos (correcto), pero UUIDs en `test_batch_liquidacion_no_encontrada_404`
7. **Porcentajes**: `Decimal("0.0010")`, `Decimal("0.0005")`, `Decimal("0.0003")` hardcodeados en tarifas
8. **costo_por_m2**: `Decimal("150.0000")` en MS

### 3.3 Tipos de Tests

| Categoría | Count | Características |
|-----------|-------|-----------------|
| **Integration** (HTTP real, con DB) | ~200 | `TestClient(api)`, `@pytest.mark.django_db`, fixtures locales |
| **E2E** (flujo completo, HTTP real) | ~20 | `TestClient(api)`, mismos patterns que integration |
| **Unit** (cálculo puro, sin DB) | ~30 | Solo Finanzas: `test_calcular_honorarios` |

**Hallazgo**: La carpeta `e2e/` NO contiene tests E2E reales (navegador, Selenium, etc.). Son los MISMOS tests de integración con otro nombre. No hay diferencia funcional entre `test_integration/test_edificaciones_nueva_liquidacion.py` y `test_e2e/test_e2e_edificaciones.py`.

---

## 4. Análisis de Fixtures Actuales

### 4.1 Contenido de `conftest.py` (290 líneas)

```
Fixtures definidos:
- tipo_edificacion, tipo_habilitacion_urbana, tipo_mecanica_suelos,
  tipo_impacto_vial, tipo_taludes, tipo_inspeccion_obra
- api_client, create_user, auth_client
- ubigeo_departamento, ubigeo_provincia, ubigeo_distrito
- municipalidad, proyecto
- igv_vigente, uit_vigente
- tarifa_liquidacion_base_edificacion
- especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones
- tarifa_porcentaje_obra_estructuras
- especialidades_disponibles_edificacion
- derecho_porcentaje_vigente
- usuario_admin (alias)
- tarifa_liquidacion_base_io, tarifa_visitas_io
```

### 4.2 Lo Bueno ✅

1. `conftest.py` tiene fixtures bien organizados por categoría (tipo, ubigeo, entidad, finanzas, tarifas)
2. Las dependencias están correctamente encadenadas (`municipalidad` depende de `ubigeo_distrito`)
3. Existe el patrón de `auth_client` unificado con JWT
4. `especialidades_disponibles_edificacion` demuestra pensamiento de fixture compuesto
5. La convención de nombres es consistente (`tipo_X`, `ubigeo_X`, `tarifa_X`)

### 4.3 Lo Malo ❌

1. **NO SE USA**: los archivos de test definen SUS PROPIAS versiones locales en lugar de importar desde conftest
2. **Faltan fixtures**: no hay `tarifa_por_metro_cuadrado`, `derecho_por_metro_cuadrado` para MS/HU
3. **Faltan fixtures**: no hay `tarifa_por_categoria_visitas` para IO
4. **Faltan fixtures de helper**: no hay factories de payload (`make_payload_edificacion`, `make_payload_ms`)
5. **Faltan fixtures compuestos**: no hay `proyecto_edificacion`, `municipalidad_lima`, etc.
6. **Faltan fixtures de finanzas**: igv/uit no están en conftest de finanzas
7. **Fragmentación**: cada test crea su propio `proyecto` inline en payloads en lugar de usar el fixture
8. **Sin granularidad**: los payloads son diccionarios literales quemados en vez de helpers parametrizables

### 4.4 Impacto

El 90% del código de setup de cada test ES DUPLICADO. Cuando se necesita cambiar el año de vigencia de IGV (ej: 2025), hay que modificar ~10 archivos en vez de 1.

---

## 5. Recomendación de Arquitectura de Tests

### 5.1 Estrategia de Fixtures

#### Nivel 1 — Base fixtures (conftest.py principal)

```python
# Fixtures de infraestructura
api_client, auth_client, create_user

# Fixtures de datos reference (inmutables por test)
ubigeo_lima, municipalidad_lima
igv_18, uit_5150
usuario_admin
```

#### Nivel 2 — Domain fixtures por módulo

```python
# liquidaciones/tests/fixtures/
#   conftest.py compartido para liquidaciones
#   po_fixtures.py — Motor PorcentajeObra
#   m2_fixtures.py — Motor Metro Cuadrado
#   io_fixtures.py — Motor Inspeccion Obra
#   делегад fixtures.py — Delegados
```

#### Nivel 3 — Helper factories (NO fixtures — funciones)

```python
def make_proyecto_lg(
    municipalidad,
    ubigeo_distrito,
    denominacion="Proyecto Test",
    expediente="EXP-DEFAULT",
    **kwargs
) -> dict:
    """Factory de payload liquidacion_general.proyecto para cualquier test."""
    return {
        "denominacion": denominacion,
        "nombre_propietario": "Propietario Test SAC",
        "direccion": "Av. Test 123",
        "distrito_id": str(ubigeo_distrito.id),
        "entidad": {
            "tipo_documento": "RUC",
            "numero_documento": "20456789012",
            "razon_social": "Propietario Test SAC",
        },
    }

def make_payload_edificacion(
    municipalidad_id,
    distrito_id,
    *,
    expediente="EXP-EDIF-001",
    valor_declarado=100000.00,
    tarifas=None,  # None = auto-fill, [] = vacío, list = explícito
) -> dict:
    """Factory de payload completo para edificaciones."""
    ...

def make_payload_m2(
    municipalidad_id,
    distrito_id,
    *,
    expediente="EXP-M2-001",
    area_solicitada=100.0,
) -> dict:
    """Factory para MS y HU."""
    ...
```

### 5.2 Separación por Capa

| Capa | Ubicación | DB | Qué testear | Ejemplo |
|------|-----------|----|-------------|---------|
| **Unit** | `finanzas/tests/unit/` | No | Lógica pura de cálculo | `test_calcular_honorarios` (Finanzas) |
| **Integration** | `*/tests/integration/` | Sí | Endpoints HTTP con fixture compartido | `test_edificaciones_nueva_liquidacion` |
| **E2E** (futuro) | `*/tests/e2e/` | Sí | Flujo completo real (navegador) | Tests con Playwright/Selenium |

**Nota**: La carpeta `e2e/` actual NO es E2E — son integration tests con otro nombre. Recomendación: renombrar a `integration/` o distinguir con prefijo `itest_`.

### 5.3 Estrategia de Datos

1. **Aislar cada test**: `django_db` con `transaction` o `reset_sequences` para evitar colisiones
2. **Usar factories/helpers** para crear payloads en vez de diccionarios literales hardcodeados
3. **Fixtures compartidos** del conftest (NO redefinirlos en cada archivo)
4. **Parametrizar fixtures** con `Indirect parametrization` para cubrir múltiples casos
5. **NO usar seeds**: cada test crea sus datos — no depender de datos de BD real

### 5.4 Estructura de Archivos Propuesta

```
backend/modules/liquidaciones/tests/
├── conftest.py                          # 290 → ~500 líneas (base + domain fixtures)
├── factories.py                          # Helper factories de payload (NUEVO)
├── unit/
│   ├── test_po_calculo.py               # Unit tests motor PO
│   ├── test_m2_calculo.py               # Unit tests motor M2
│   └── test_io_calculo.py               # Unit tests motor IO
├── integration/
│   ├── conftest.py                      # Integration-specific fixtures
│   ├── test_edificaciones_flows.py      # Unificar: nueva_liq + tariffs + cotizar
│   ├── test_edificaciones_validacion.py  # Casos de validación
│   ├── test_m2_flows.py                 # HU + MS flows
│   ├── test_io_flows.py                 # IO flows
│   ├── test_delegados_flows.py          # Asignaciones + batch
│   ├── test_general_listados.py         # Endpoints generales
│   ├── test_inspectores.py
│   └── test_tarifas_historicas.py
└── e2e/                                 # RESERVADO para tests de navegador
    └── README.txt                       # "Usar Playwright para e2e real"

backend/modules/finanzas/tests/
├── conftest.py
├── factories.py
├── unit/
│   └── test_recibo_honorario_calculo.py  # TestCalcularHonorarios
└── integration/
    ├── conftest.py
    ├── test_recibo_honorario.py          # Model + DB tests
    └── test_recibo_honorario_e2e.py      # HTTP endpoint tests
```

### 5.5 Homogeneidad — Fixture Genérico por Motor

En vez de 4 archivos con setup duplicado para PO (Edificaciones, Taludes, Impacto Vial):

```python
# po_fixtures.py (NUEVO)
@pytest.fixture
def po_base_setup(db, tipo_po):
    """Setup base para cualquier test de motor PO (edificaciones/taludes/iv)."""
    # Crea ubigeo, municipalidad, igv, uit, derecho_po, tarifa_po con especialidades
    ...

# En test_edificaciones_nueva_liquidacion.py:
def test_po_crear_primera_revision(po_base_setup, make_payload_po):
    payload = make_payload_po(municipalidad=po_base_setup.municipalidad, ...)
    ...

# En test_taludes_list.py (reusa el MISMO setup base):
def test_taludes_list(po_base_setup):
    # Ya tiene municipalidad, igv, uit, derecho_po, tarifa_po listos
    ...
```

---

## 6. Plan de Implementación Sugerido

### Fase 1 — Consolidar Fixtures (semana 1)
1. Crear `liquidaciones/tests/factories.py` con `make_payload_*` helpers
2. Expandir `conftest.py` con fixtures que FALTAN (`tarifa_m2_ms`, `derecho_m2_vigente`, `tarifa_visitas_io`)
3. Crear `po_fixtures.py`, `m2_fixtures.py`, `io_fixtures.py`
4. Refactorizar UN archivo de test (ej: `test_edificaciones_nueva_liquidacion.py`) para usar fixtures de conftest + factories
5. Eliminar las definiciones locales duplicadas de ese archivo

### Fase 2 — Homogeneizar los 6 tipos (semana 2)
1. Aplicar el mismo patrón de refactor a los otros 5 tipos de liquidación
2. Crear el fixture genérico `po_base_setup` que cubra los 3 motores PO
3. Unificar payloads para PO: un solo `make_payload_po` con parámetro `motor`

### Fase 3 — Tests Unitarios de Core (semana 2-3)
1. Extraer los cálculos puros (`calcular_cotizacion_po`, `calcular_subtotal_visitas`) a tests unitarios sin DB
2. Agregar `test_po_calculo.py`, `test_m2_calculo.py`, `test_io_calculo.py`
3. Cubrir casos borde: clamping mínimo, clamping máximo, decimales

### Fase 4 — E2E Real (semana 3-4)
1. Evaluar si se necesita E2E real con Playwright
2. Si sí: crear `tests/e2e/` con tests de navegador
3. Si no: eliminar la carpeta `e2e/` y unificar con integration

---

## 7. Riesgos

1. **Resistencia al cambio**: hay ~250 tests existentes que habrían que refactorizar — podría haber pushback
2. **Tiempo de ejecución**: al estar todos los integration tests usando DB real, el suite es lento (~10-15 min proyectado)
3. **Fixtures circulares**: algunos fixtures tienen dependencias complejas (especialidades_disponibles_edificacion requiere 3 especialidades)
4. **Modelos aún en migración**: `test_recibo_honorario.py` tiene un test comentado (líneas 383-438) bloqueado por migración pendiente
5. **叛逆 —叛逆** (sic): el archivo `test_delegados_liquidacion_e2e.py` USA correctamente los fixtures de conftest en algunos puntos, pero mezcla helper functions locales (`_crear_delegado`) lo cual está bien pero no escala

---

## 8. Hallazgos Clave

1. **Conftest existe y está bien diseñado** — el problema no es que falten fixtures, es que no se usan
2. **El 90% de las líneas de setup son duplicadas** — 10 archivos redefinen los mismos ~10 fixtures
3. **No hay tests unitarios de liquidaciones** — todos usan `@pytest.mark.django_db` (DB real)
4. **E2E no es realmente E2E** — la carpeta `e2e/` contiene integration tests renombrados
5. **Finanzas tiene el mejor patrón** — `TestCalcularHonorarios` con tests unitarios puros (sin DB) es el modelo a seguir
6. **Los payloads son dictionaries literales hardcodeados** — no hay factories, lo que hace difícil parametrizar

---

## 9. next_recommended

**sdd-propose** — crear la propuesta formal de rediseño de arquitectura de tests con:
- Plan de migración detallado
- Definición de la nueva estructura de archivos
- Especificación de factories helpers
- Estrategia de separación unitaria vs integración
