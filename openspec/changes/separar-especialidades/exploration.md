# Exploration: Separar Especialidad en EspecialidadIngeniero + EspecialidadRevision

## Status

**success** — Exploration complete.

---

## Executive Summary

The existing `Especialidad` table (`usuarios_especialidad`) serves TWO conceptually different purposes that should be split:

1. **PerfilIngeniero.especialidad** — the professional specialty from CIP (codes 01/02/04/07/10, chapters 02/05/09/15)
2. **Tariff/revision models** — `TarifaPorcentajeObra`, `LiquidacionPorcentajeObraDetalle`, `LiquidacionEspecialidadDisponibles` — which only need 3 specialty records (Civil, Sanitaria, Eléctrica/Mecánica)

The separation is **architecturally clean** and **low-risk for the tariff side** (only 3 records), but **medium-risk for the ingeniero side** (need to preserve existing FK data).

---

## Mapa de Referencias → Nueva Tabla

| Referencia actual | Archivo | ¿Va a EspecialidadIngeniero o EspecialidadRevision? |
|-------------------|---------|---------------------------------------------------|
| `PerfilIngeniero.especialidad` FK | `usuarios/domain/models/perfil_ingeniero.py:141` | **EspecialidadIngeniero** |
| `TarifaPorcentajeObra.especialidad` FK | `liquidaciones/domain/models/tarifas_reglas.py:149` | **EspecialidadRevision** |
| `LiquidacionPorcentajeObraDetalle.especialidad` FK | `liquidaciones/domain/models/liquidacion_tipo/liquidacion_tipo.py:265` | **EspecialidadRevision** |
| `LiquidacionEspecialidadDisponibles.especialidad` FK | `liquidaciones/domain/models/liquidacion/liquidacion_general/liquidacion.py:330` | **EspecialidadRevision** |
| `LiquidacionGeneral.especialidades_revisadas` M2M | `liquidaciones/domain/models/liquidacion/liquidacion_general/liquidacion.py:34` | **EspecialidadRevision** |
| `EspecialidadOut` (API schema) | `liquidaciones/presentation/schemas/delegado/delegado_schemas.py:11` | **Ambiguous** — ver sección API |
| Tests referencing `Especialidad` | Various in `tests/e2e/` and `tests/integration/` | **EspecialidadIngeniero** para fixture de tests de tarifas |

---

## 1. Definición del Alcance

### Modelo actual

```
Especialidad (usuarios_especialidad)
├── codigo: CharField(4), unique
├── nombre: CharField(100), unique
├── + BaseModel (UUID, timestamps)
└── + HistoricalRecords
```

### Nuevos modelos

**Opción A (recomendada): Renombrar + crear nueva**

1. `Especialidad` → **renombrar** a `EspecialidadIngeniero` (mantiene codigo + nombre)
2. **Crear** `EspecialidadRevision` con los MISMOS campos (codigo + nombre) pero sin relación con PerfilIngeniero

**Opción B: Crear dos nuevas y dejar la vieja huérfana**

Más compleja, mayor riesgo de migración.

**Recomendación: Opción A** — menor impacto, los nombres son semánticamente claros.

### Campo capítulo en EspecialidadIngeniero

Según el análisis en `CONTRASTE_ESPECIALIDADES.md`:
- El código `01` (60 ingenieros) se divide por capítulo: 02=Civil (42), 09=Sanitaria (18)
- Los capítulos 05 y 15 (códigos 02, 04, 07, 10) → Eléctrica/Mecánica unificada

**Decisión pendiente: ¿Agregar FK a Capitulo en EspecialidadIngeniero?**
- Hoy `PerfilIngeniero` ya tiene `capitulo` FK separado
- `EspecialidadIngeniero` no necesita capítulo si el mapeo a tarifa se hace en aplicación
- Pero si el código CIP `01` se distingue solo por capítulo, podría necesitarse en el modelo

---

## 2. Impacto en Código

### Modelos (5 archivos)

| Archivo | Cambio |
|---------|--------|
| `backend/modules/usuarios/domain/models/perfil_ingeniero.py` | Renombrar `class Especialidad` → `class EspecialidadIngeniero` |
| `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_general/liquidacion.py` | Cambiar FK `usuarios.Especialidad` → `usuarios.EspecialidadRevision` en `LiquidacionEspecialidadDisponibles` y `LiquidacionGeneral` M2M |
| `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/tarifas_reglas.py` | Cambiar FK `usuarios.Especialidad` → `usuarios.EspecialidadRevision` en `TarifaPorcentajeObra` |
| `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/liquidacion_tipo.py` | Cambiar FK `usuarios.Especialidad` → `usuarios.EspecialidadRevision` en `LiquidacionPorcentajeObraDetalle` |
| `backend/modules/liquidaciones/models.py` | Actualizar re-export: `Especialidad` → `EspecialidadIngeniero` + agregar `EspecialidadRevision` |

### 5 imports rotos (éstos ya están rotos, no son nuevos)

| Archivo | Error | Acción |
|---------|-------|--------|
| `backend/seed_tarifas_all.py:44` | Intenta `from modules.liquidaciones.domain.models.especialidades import Especialidad` (módulo no existe) | Fix: importar desde `modules.usuarios.domain.models.perfil_ingeniero` |
| `backend/seed_tarifas_edificacion.py:36` | Mismo módulo inexistente | Fix: misma corrección |
| `backend/load_delegados_reales.py:37` | Mismo módulo inexistente | Fix: misma corrección |
| `backend/cleanup_especialidad_duplicates.py:27` | Mismo módulo inexistente | Fix: misma corrección |
| `backend/diagnostic.py:12` | Mismo módulo inexistente | Fix: misma corrección |

**Además**, estos 4 archivos también usan `Especialidad` pero desde la ruta correcta:

| Archivo | Cambio |
|---------|--------|
| `backend/modules/liquidaciones/management/commands/seed_tarifas.py:34` | Import correcto pero cambia a `EspecialidadRevision` |
| `backend/modules/liquidaciones/management/commands/seed_colegiados.py:17` | `Especialidad` → `EspecialidadIngeniero` |
| `backend/modules/liquidaciones/domain/models/__init__.py:5` | `Especialidad` → `EspecialidadIngeniero` |
| `backend/modules/liquidaciones/tests/conftest.py:17` | `Especialidad` → `EspecialidadIngeniero` |
| `backend/modules/liquidaciones/tests/e2e/*.py` (3 archivos) | `Especialidad` → `EspecialidadIngeniero` |
| `backend/modules/liquidaciones/tests/integration/*.py` (6 archivos) | `Especialidad` → `EspecialidadIngeniero` |

### Schemas

| Archivo | Cambio |
|---------|--------|
| `backend/modules/liquidaciones/domain/schemas.py:178` | `EspecialidadRevisionData` está **vacío** (`pass`) — placeholder que necesita implementarse |
| `backend/modules/liquidaciones/presentation/schemas/delegado/delegado_schemas.py:11` | `EspecialidadOut` — **ver impacto API** |

### Presenters

| Archivo | Cambio |
|---------|--------|
| `backend/modules/liquidaciones/presentation/presenters/delegado_presenter.py` | `_map_perfil_ingeniero` usa `EspecialidadOut` — podría necesitar cambio si la especialidad del ingeniero cambia de schema |

### Seeds

| Archivo | Cambio |
|---------|--------|
| `backend/modules/usuarios/management/commands/seed_colegiados.py` | Poblar `EspecialidadIngeniero` con códigos CIP (01, 02, 04, 07, 10) — 5 registros |
| `backend/modules/liquidaciones/management/commands/seed_tarifas.py` | Poblar `EspecialidadRevision` con 3 registros: Civil, Sanitaria, Eléctrica/Mecánica |
| `backend/modules/liquidaciones/management/commands/load_delegados_reales.py` | Fix import + usar `EspecialidadRevision` para mapeo |

---

## 3. Migrations

### Migraciones necesarias

1. **Create `EspecialidadRevision` model** — nueva tabla `liquidaciones_especialidadrevision`
2. **Add FK constraints** — temporarily nullable para copiar datos
3. **Data migration** — poblar `EspecialidadRevision` con 3 registros (Civil, Sanitaria, Eléctrica/Mecánica) usando el mapeo por capítulo
4. **Update FK references** — cambiar `LiquidacionEspecialidadDisponibles.especialidad`, `TarifaPorcentajeObra.especialidad`, `LiquidacionPorcentajeObraDetalle.especialidad`, `LiquidacionGeneral.especialidades_revisadas` a `EspecialidadRevision`
5. **Rename `Especialidad` to `EspecialidadIngeniero`** — requiere rename table `usuarios_especialidad` → `usuarios_especialidadingeniero`
6. **HistoricalRecords** — asegurar que las tablas históricas también se renombren

**Estimado: 4-6 migrations** (incluyendo una data migration)

---

## 4. Datos

### Datos actuales en `usuarios_especialidad`

```
SELECT codigo, nombre FROM usuarios_especialidad;
 results:
 01 | Ingeniería Civil
 01 | Ingeniería Sanitaria (mixed in same table, same code!)
 02 | Ingeniería Mecánica y Mecánica Eléctrica
 04 | Ingeniería Eléctrica
 07 | Ingeniería Eléctrica
 10 | Ingeniería Eléctrica
```

**Problema**: El código `01` aparece DOS veces con nombres diferentes (Civil y Sanitaria), pero el código es único constraint.

### Mapeo para migración

| Código CIP | Capítulo | EspecialidadRevision (tarifa) |
|-----------|----------|-------------------------------|
| 01 | 02 (CIVIL) | Civil |
| 01 | 09 (SANITARIA) | Sanitaria |
| 02, 04, 07, 10 | 05, 15 | Eléctrica/Mecánica |

### EspecialidadIngeniero

- Se llena desde CIP con `codigo_especialidad` + `capitulo`
- 95 ingenieros → 5 especialidades (01 Civil, 01 Sanitaria, 02, 04, 07, 10 → Eléctrica/Mecánica)
- Necesita guardar tanto código como capítulo para distinguir Civil de Sanitaria

### EspecialidadRevision

- Solo 3 registros: Civil, Sanitaria, Eléctrica/Mecánica
- Se poblaría en el seed o en data migration

---

## 5. Seeds

### seed_colegiados.py

**Actual**: Crea `Especialidad` con códigos "01", "02", etc.

**Nuevo**: Crear `EspecialidadIngeniero` con:
```python
# Mapeo capítulo → nombre de especialidad de ingeniero
ESPECIALIDAD_INGENIERO_MAP = {
    ("01", "02"): ("01", "Ingeniería Civil"),
    ("01", "09"): ("01", "Ingeniería Sanitaria"),
    ("02", "05"): ("02", "Ingeniería Mecánica"),
    ("04", "15"): ("04", "Ingeniería Eléctrica"),
    ("07", "15"): ("07", "Ingeniería Eléctrica"),
    ("10", "15"): ("10", "Ingeniería Eléctrica"),
}
```

### seed_tarifas.py (y seed_tarifas_all.py, seed_tarifas_edificacion.py)

**Problema**: estos seeds importan desde módulo inexistente + usan `Especialidad` para tarifas.

**Nuevo**:
1. Fix imports: `from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadIngeniero`
2. Poblar `EspecialidadRevision` con 3 registros
3. Poblar `TarifaPorcentajeObra` con FK a `EspecialidadRevision`

### load_delegados_reales.py

**Problema**: Importa desde módulo inexistente + usa `Especialidad` para mapeo.

**Nuevo**:
1. Fix imports
2. Mantener `EspecialidadIngeniero` para el perfil del ingeniero
3. Usar mapeo por capítulo para derivar `EspecialidadRevision` cuando se crean liquidaciones

---

## 6. API Pública

### GET /delegados/

**Contrato actual**:
```python
class EspecialidadOut(BaseSchema):
    id: uuid.UUID
    codigo: str
    nombre: str

class PerfilIngenieroOut(BaseSchema):
    # ...
    especialidad: Optional[EspecialidadOut] = None
```

**Impacto**: `PerfilIngeniero.especialidad` apunta a `EspecialidadIngeniero`, cuyo schema `EspecialidadOut` es idêntico. **No hay cambio en el contrato API** si se mantiene el mismo schema output.

### API internas de tarifas

`GET /liquidaciones/especialidades-vigentes/` devuelve `EspecialidadBasica` (id, nombre). El source es `LiquidacionEspecialidadDisponibles` que cambia a FK `EspecialidadRevision`. **No hay cambio de contrato visible**.

### Frontend

El frontend tiene:
- `frontend/src/features/delegados/types/delegados.types.ts` — `especialidadSchema` con id, codigo, nombre
- `frontend/src/features_deprecated/liquidaciones/types/revisiones-vigentes.ts` — `EspecialidadBasica` con id, nombre

**Impacto en frontend: Mínimo**. Los schemas son simples y el cambio de nombre de tabla no afecta si los IDs se mantienen.

---

## 7. Estimación Total

| Categoría | Estimación |
|-----------|------------|
| **Archivos a tocar** | ~25 archivos |
| **Líneas estimadas** | ~400-600 líneas (modelos, migrations, seeds, tests) |
| **Migrations** | 4-6 (incluyendo data migration) |
| **Riesgo** | **Medio** |

**Desglose por capa**:
- Modelos: 5 archivos (~80 líneas)
- Migrations: 4-6 archivos (~200 líneas data + schema)
- Seeds/Commands: 5 archivos (~200 líneas)
- Tests: 10+ archivos (~150 líneas)
- Schemas/Presenters: 3 archivos (~50 líneas)

---

## 8. Decisiones Pendientes (para el usuario)

1. **¿Campo capítulo en EspecialidadIngeniero?**
   - Hoy `PerfilIngeniero` ya tiene `capitulo` FK separado
   - `EspecialidadIngeniero` podría no necesitarlo si el mapeo a tarifa se hace en aplicación
   - Si se necesita distinguir Civil de Sanitaria en la especialidad del ingeniero, habría que agregarlo

2. **¿Normalizar códigos en EspecialidadIngeniero?**
   - Los códigos CIP son 01, 02, 04, 07, 10 (5 valores)
   - ¿Se mantienen igual o se normalizan a algo más legible?

3. **¿EspecialidadRevision solo 3 registros?**
   - Civil, Sanitaria, Eléctrica/Mecánica
   - Confirmado por análisis de tarifas

4. **¿Eliminar o mantener tabla vieja?**
   - Opción A: Renombrar `Especialidad` → `EspecialidadIngeniero` y crear `EspecialidadRevision`
   - Opción B: Crear nuevas tablas y dejar `Especialidad` huérfana (más complejo)

5. **¿HistoricalRecords en ambas tablas?**
   - Ambas heredan de BaseModel (UUID, timestamps) + HistoricalRecords
   - Mantener en ambas para audit trail

---

## 9. Risks

1. **Riesgo de datos**: La tabla actual tiene código `01` con constraint unique, pero necesita dos registros (Civil y Sanitaria). La migración de datos requiere resolver este conflicto antes de renombrar.

2. **Riesgo de FK en transacción**: Cambiar FK de múltiples tablas simultáneamente requiere careful ordering de migrations.

3. **Riesgo de imports**: Los 5 archivos con imports rotos ya están rotos — no son nuevos bugs, pero indican que los seeds de tarifas NUNCA funcionaron.

4. **Riesgo de tests**: Los tests e2e y integration que usan `Especialidad` como fixture necesitarán actualizarse.

5. **Riesgo de nombre de capítulo**: Si el capítulo no está presente en algunos ingenieros, el mapeo a `EspecialidadRevision` falla silenciosamente.

---

## 10. Next Recommended

**`sdd-propose`** — El impacto está claro, pero hay 5 decisiones pendientes que requieren confirmación del usuario antes de proceder a spec.

---

## Artifacts

- Engram: `sdd/separar-especialidades/explore`
- OpenSpec: `openspec/changes/separar-especialidades/exploration.md`
