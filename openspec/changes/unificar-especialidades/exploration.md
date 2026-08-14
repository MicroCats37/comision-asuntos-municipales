# SDD Exploration: Unificar Especialidades

**Change**: `unificar-especialidades`
**Phase**: `explore`
**Date**: 2026-08-12
**Project**: `comision-asuntos-municipales`
**Backend**: Django 5.2 + Django Ninja

---

## Hallazgo Principal: Solo existe UNA tabla `Especialidad`

**No existen dos tablas `EspecialidadIngeniero` y `EspecialidadRevision`**. El usuario parece estar riferido a un concepto propuesto en la versión alpha que **nunca fue implementado**.

Lo que existe es:

| Alias conceptual | Ubicación real | Tabla DB |
|-----------------|---------------|----------|
| "EspecialidadIngeniero" (propuesta) | `usuarios.PerfilIngeniero.especialidad` FK | `usuarios_especialidad` |
| "EspecialidadRevision" (propuesta) | `liquidaciones.TarifaPorcentajeObra.especialidad` FK | `usuarios_especialidad` |

**Ambas referencias apuntan a la MISMA tabla `usuarios_especialidad`** — la misma clase `Especialidad` en `modules/usuarios/domain/models/perfil_ingeniero.py`.

---

## Modelo Único `Especialidad`

**Archivo**: `backend/modules/usuarios/domain/models/perfil_ingeniero.py` (línea 47)

```python
class Especialidad(BaseModel):
    history = HistoricalRecords()
    codigo = models.CharField(max_length=4, unique=True, verbose_name="Código de Especialidad")
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de Especialidad")

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"
        ordering = ["nombre"]
```

- **Tabla DB**: `usuarios_especialidad`
- **App**: `usuarios`
- **Campos**: `id` (UUID), `created_at`, `updated_at`, `codigo`, `nombre`
- **HistoricalRecords**: Sí (`HistoricalEspecialidad` → tabla `usuarios_historicalespecialidad`)

### Comparación de Atributos

| Campo | Especialidad (unica) |
|-------|---------------------|
| `id` | UUID (PK) |
| `codigo` | CharField(4), unique |
| `nombre` | CharField(100), unique |
| `created_at` | DateTimeField |
| `updated_at` | DateTimeField |

**No hay segunda tabla con atributos idénticos o diferentes** — solo existe esta.

---

## Todas las Referencias a `Especialidad`

### Modelos que referencian `usuarios.Especialidad`

| Modelo | Campo | Tipo | Ubicación |
|--------|-------|------|-----------|
| `PerfilIngeniero` | `especialidad` | FK (nullable) | `usuarios.PerfilIngeniero` |
| `HistoricalPerfilIngeniero` | `especialidad` | FK | `usuarios.HistoricalPerfilIngeniero` |
| `LiquidacionGeneral` | `especialidades_revisadas` | M2M | `liquidaciones.LiquidacionGeneral` |
| `LiquidacionEspecialidadDisponibles` | `especialidad` | FK | `liquidaciones.LiquidacionEspecialidadDisponibles` |
| `HistoricalLiquidacionEspecialidadDisponibles` | `especialidad` | FK | `liquidaciones.Historical...` |
| `TarifaPorcentajeObra` | `especialidad` | FK | `liquidaciones.TarifaPorcentajeObra` |
| `HistoricalTarifaPorcentajeObra` | `especialidad` | FK | `liquidaciones.Historical...` |
| `LiquidacionPorcentajeObraDetalle` | `especialidad` | FK | `liquidaciones.LiquidacionPorcentajeObraDetalle` |
| `HistoricalLiquidacionPorcentajeObraDetalle` | `especialidad` | FK | `liquidaciones.Historical...` |

### Imports que usan `Especialidad`

| Archivo | Import path | Propósito |
|---------|-----------|-----------|
| `modules/usuarios/management/commands/seed_colegiados.py` | `from modules.usuarios.domain.models.perfil_ingeniero import Especialidad` | Seed ingenieros |
| `modules/liquidaciones/management/commands/seed_tarifas.py` | `from modules.usuarios.domain.models.perfil_ingeniero import Especialidad` | Seed tarifas |
| `modules/liquidaciones/management/commands/seed_tarifas_all.py` | `from modules.liquidaciones.domain.models.especialidades import Especialidad` | ⚠️ **ROTO** — módulo no existe |
| `modules/liquidaciones/management/commands/seed_tarifas_edificacion.py` | `from modules.liquidaciones.domain.models.especialidades import Especialidad` | ⚠️ **ROTO** |
| `modules/liquidaciones/management/commands/load_delegados_reales.py` | `from modules.liquidaciones.domain.models.especialidades import Especialidad` | ⚠️ **ROTO** |
| `modules/liquidaciones/management/commands/cleanup_especialidad_duplicates.py` | `from modules.liquidaciones.domain.models.especialidades import Especialidad` | ⚠️ **ROTO** |
| `backend/diagnostic.py` | `from modules.liquidaciones.domain.models.especialidades import Especialidad` | ⚠️ **ROTO** |

### Schemas y Resultados que usan `Especialidad`

| Archivo | Clase | Tipo |
|---------|-------|------|
| `liquidaciones/domain/schemas.py` | `EspecialidadData`, `EspecialidadBasicaResult` | Pydantic (vacíos/pass) |
| `liquidaciones/domain/schemas.py` | `EspecialidadRevisionData` | Pydantic (vacío/pass) |
| `liquidaciones/domain/results/delegado/delegado_result.py` | `EspecialidadResult` | Pydantic domain DTO |
| `liquidaciones/presentation/schemas/delegado/delegado_schemas.py` | `EspecialidadOut` | API output schema |

### APIs que exponen `Especialidad`

- `GET /delegados/?especialidad_id=<uuid>` — filtro en `DelegadoController.list_delegados()`
- `DelegadoOut.perfil_ingeniero.especialidad` → `EspecialidadOut(id, codigo, nombre)` — respuesta API

### Seeds que pueblan `Especialidad`

1. **`seed_colegiados`** (`usuarios`): Crea `Especialidad` con `codigo` del CIP y `nombre = codigo` (ej. "01", "02"). **Problema**: usa el código numérico como nombre, no el nombre real.
2. **`load_delegados_reales`** (`liquidaciones`): Crea `Especialidad` con nombre completo (ej. "Ingeniería Civil"). **Problema**: puede crear duplicados por diferencias de acentuación.
3. **`seed_tarifas_edificacion`** (`liquidaciones`): Crea `Especialidad` por nombre (ej. "Ingeniería Civil").

---

## Problema Real Descubierto

### Importes Rotos (5 archivos)

Los siguientes archivos importan `from modules.liquidaciones.domain.models.especialidades import Especialidad` pero **ese módulo no existe**:

1. `backend/modules/liquidaciones/management/commands/seed_tarifas_all.py` (línea 44)
2. `backend/modules/liquidaciones/management/commands/seed_tarifas_edificacion.py` (línea 36)
3. `backend/modules/liquidaciones/management/commands/load_delegados_reales.py` (línea 37)
4. `backend/modules/liquidaciones/management/commands/cleanup_especialidad_duplicates.py` (línea 27)
5. `backend/diagnostic.py` (línea 12)

**Estos comandos NO funcionan** — fallarían con `ModuleNotFoundError` al ejecutarse.

### Conflicto de Datos en Seeds

- `seed_colegiados` crea especialidades con `codigo` como `nombre` (ej. codigo="01", nombre="01")
- `load_delegados_reales` crea especialidades con nombre completo (ej. "Ingeniería Civil")
- Esto crea **registros duplicados o inconsistentes** en `usuarios_especialidad`

---

## Análisis de Impacto del Cambio Propuesto

### Escenario 1: "Eliminar EspecialidadIngeniero (PerfilIngeniero.especialidad)"

**No aplica** — no existe una tabla separada. La FK `PerfilIngeniero.especialidad` vive en `usuarios_especialidad`.

### Escenario 2: "Eliminar EspecialidadRevision (liquidaciones.especialidad)"

**No aplica** — no existe tabla separada. Los campos FK en `liquidaciones` también usan `usuarios_especialidad`.

### Escenario 3: Lo que SÍ podría tener sentido — Separar las dos CONCEPTUALIZACIONES

El documento `doc_dev/CONTRASTE_ESPECIALIDADES.md` describe un análisis donde:
- `EspecialidadIngeniero`: del CIP, código + capítulo (ej. código "01" + capítulo "02" = "Civil")
- `Especialidad` (tarifa): solo 3 registros: Civil, Sanitaria, Eléctrica/Mecánica

**Esto sería una refactorización real**, no una unificación. Implicaría:
1. Crear una NUEVA tabla `EspecialidadIngeniero` con campos adicionales (capitulo, etc.)
2. Migrar datos de `PerfilIngeniero.especialidad` → nueva tabla
3. Mantener `Especialidad` como catálogo de tarifas (sin cambios)

### Estimación de Impacto (si se hiciera la separación real)

| Componente | Archivos | Líneas |
|-----------|----------|--------|
| Nuevo modelo `EspecialidadIngeniero` | 1 | ~50 |
| FK `PerfilIngeniero.especialidad_ingeniero` | 1 model + 1 migration | ~10 |
| Actualizar `seed_colegiados` | 1 | ~20 |
| Actualizar `DelegadoOrchestrator` (mapeo) | 1 | ~10 |
| Actualizar `DelegadoPresenter` | 1 | ~10 |
| Migrations | 2 | ~50 |
| **Total estimado** | ~8 | ~150 |

---

## Recomendación

### No hay dos tablas que unificar.

**El usuario parece estar basándose en un documento de diseño (CONTRASTE_ESPECIALIDADES.md) que describe una propuesta de separación que nunca fue implementada.**

### Acciones recomendadas en lugar de "unificar":

1. **Corregir los 5 imports rotos** (`modules.liquidaciones.domain.models.especialidades`) — cambiar a `modules.usuarios.domain.models.perfil_ingeniero`
2. **Auditar los seeds** para evitar duplicados de `Especialidad` (el comando `cleanup_especialidad_duplicates.py` fue diseñado para esto pero no funciona por el import roto)
3. **Si el objetivo real es SEPARAR** las dos responsabilidades** (perfil vs tarifa): tratar esto como un SDD nuevo con `sdd-propose` para la "separación EspecialidadIngeniero vs EspecialidadTarifa"

### Veredicto

- **¿Existe `EspecialidadIngeniero` como tabla separada?** ❌ No
- **¿Existe `EspecialidadRevision` como tabla separada?** ❌ No  
- **¿Existe la tabla `usuarios_especialidad` que se usa en ambos contextos?** ✅ Sí
- **¿Hay imports rotos que causan problemas?** ✅ Sí (5 archivos)
- **¿Los seeds crean duplicados de especialidades?** ⚠️ Probablemente sí

---

## Riesgos

1. **Imports rotos** — 5 archivos con `ModuleNotFoundError` silenciado (posiblemente no se ejecutan los comandos que los usan)
2. **Datos inconsistentes** — `Especialidad.nombre` puede ser código ("01") o nombre completo ("Ingeniería Civil") dependiendo del seed usado
3. **Duplicados por acentuación** — `cleanup_especialidad_duplicates.py` fue diseñado para resolver esto pero no funciona
4. **API de Delegados expone `especialidad` del PerfilIngeniero** — cualquier cambio de modelo impacta la API pública `/delegados/`

---

## Conclusión

La solicitud de "unificar EspecialidadIngeniero con EspecialidadRevision" **no se puede ejecutar tal como está planteada** porque no existen dos tablas. Lo que existe es una sola tabla `usuarios_especialidad` usada en dos contextos diferentes (perfil de ingeniero y tarifas de liquidación).

**Próximo paso recomendado**: `sdd-propose` para una **separación real** de `EspecialidadIngeniero` (datos del CIP, con código + capítulo) de `Especialidad` como catálogo de tarifas, que es lo que el documento `CONTRASTE_ESPECIALIDADES.md` propone.

**Alternativa menor**: `sdd-propose` para **corregir los imports rotos** y **auditar/consolidar los seeds** de Especialidad.
