---
name: cam-contrato-wrapper
description: "Trigger: leer contrato, contrastar wrappers, validar endpoint, módulo liquidación, polimorfismo, retención, snapshot, proyecto inline. Valida y construye endpoints en el proyecto CAM-CIP siguiendo el contrato arquitectónico estricto."
license: Apache-2.0
metadata:
  author: "comision-asuntos-municipales"
  version: "1.0"
---

## Activation Contract

Activate este skill cuando:
- Se va a crear un nuevo endpoint en `modules/liquidaciones`.
- Se necesita validar el Input/Output de un endpoint contra un contrato MD.
- Se va a implementar un nuevo tipo de liquidación (Edificación, M2, Visitas, etc.).
- Se va a agregar lógica de cálculo tarifario.

NO activar para:
- CRUD genérico de otras apps (entidades, finanzas, usuarios).
- Cambios puramente de frontend.

## Hard Rules

### 1. Arquitectura de 4 capas (NO NEGOCIABLE)
- **Controller**: Solo delega. Cero `if`/`for`/ORM.
- **Presenter**: `@staticmethod` puro. NO lógica. NO ORM.
- **Orchestrator**: Solo valida y delega. Lanza `HttpError`.
- **Flujo**: Único con `@transaction.atomic`. Orquesta Core calls.
- **Core**: ORM puro. CERO `@transaction.atomic`. CERO lógica de negocio.

### 2. Wrappers (Polimorfismo)
- **3 wrappers en Output**: `liquidacion_general`, `liquidacion_tipo`, `liquidacion_especifica`.
- **2 wrappers en Input**: `liquidacion_general`, `liquidacion_especifica` (sin `liquidacion_tipo`).
- TODOS los FK van como objeto anidado con `id` adentro, EXCEPTO los IDs seleccionables por el usuario en Input (municipalidad_id, distrito_id, tarifa_m2_id) que van planos.

### 3. Schemas
- Heredan OBLIGATORIAMENTE de `core.types.BaseSchema`.
- NUNCA heredan de `ninja.Schema`.
- Todos los inputs llevan `Field(..., description=...)`.

### 4. NO se inventan campos
Los campos válidos vienen EXCLUSIVAMENTE de los modelos Django. Antes de proponer un JSON, leer el modelo y validar 1:1.

### 5. Imports
- SIEMPRE absolutos: `from modules.xxx.domain.services...`
- NUNCA usar `...`

## Decision Gates

| Necesitas | Acción |
|-----------|--------|
| Crear un endpoint nuevo | Lee `docs/contracts/{TIPO}_CONTRACT.md` primero |
| Validar contrato | Usa `sdd-explore` para contrastar código vs MD |
| Crear tests | Usa `@pytest.mark.asyncio` + `AsyncClient` de Django (NO `TestAsyncClient`) |
| Aplicar corrección arquitectónica | Usa `sdd-apply` que re-lee `contract/PLAN_REFACTORIZACION.md` |

## Execution Steps

1. **Lee SIEMPRE primero**:
   - `backend/contract/PLAN_REFACTORIZACION.md` (reglas arquitectónicas).
   - `backend/docs/contracts/{TIPO}_CONTRACT.md` (contrato JSON).

2. **Para Input de liquidación**:
   - `liquidacion_general` lleva: `municipalidad_id`, `expediente`, `observacion`, `proyecto` (inline).
   - `liquidacion_especifica` lleva: `datos` + `tarifa`.
   - NO incluir: `usuario_creador` (viene del JWT), `retencion` (default false), `estado`, `numero_revision`.

3. **Para Output de liquidación**:
   - `liquidacion_general`: ID + FKs planos (`municipalidad_id`, `distrito_id`, `igv_id`, `uit_id`) + `usuario_creador: { id }` + `proyecto` completo + totales + `sub_total` + `total`.
   - `liquidacion_tipo`: `id` + `numero` (de `AutoNumeroModel`).
   - `liquidacion_especifica`: `datos` (cálculos) + `tarifa` (referencia).
   - NO incluir: `igv_snapshot`, `uit_snapshot`, `tipo_calculo`, `concepto`.

4. **Para crear tests async**:
   - Usar `AsyncClient` de Django (`from django.test import AsyncClient`).
   - NO usar `TestAsyncClient` de Ninja (rompe con `pytest-django`).
   - Marcar tests con `@pytest.mark.asyncio` y `@pytest.mark.django_db`.

## Campos prohibidos (NUNCA incluir en JSON)

- ❌ `tipo_calculo` (no existe en modelos)
- ❌ `concepto` (no existe)
- ❌ `subtotal` sin guión bajo (correcto: `sub_total`)
- ❌ `igv_snapshot` / `uit_snapshot` sueltos o anidados
- ❌ `usuario_creador_id` plano en Input (es objeto anidado en Output)
- ❌ IDs planos con `_id` para entidades NO seleccionables por el usuario

## Output Contract

Después de aplicar este skill:
- Endpoint creado con 4 capas separadas.
- Schemas heredando de `BaseSchema`.
- Tests usando `AsyncClient` de Django (NO `TestAsyncClient`).
- `@transaction.atomic` SOLO en el Flujo.
- Sin campos inventados.
- 100% conforme al contrato MD.

## References

- `backend/contract/PLAN_REFACTORIZACION.md` — Biblia arquitectónica.
- `backend/docs/contracts/HU_LIQUIDACION_CONTRACT.md` — Contrato HU (plantilla).
- `backend/conftest.py` — Fixtures de test (incluye `test_async_client`).
- `backend/core/types.py` — `BaseSchema` (herencia obligatoria).