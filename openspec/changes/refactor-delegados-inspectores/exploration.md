# Exploration: Refactorización de Delegados e Inspectores

**Status**: `success`
**Date**: 2026-08-15
**Project**: comision-asuntos-municipales
**Phase**: sdd-explore

---

## 1. Modelos Actuales — Campos Exactos

### `Delegado` (`backend/modules/liquidaciones/domain/models/delegado.py:14`)
| Campo | Tipo | Notas |
|-------|------|-------|
| `perfil_ingeniero` | OneToOneField → PerfilIngeniero | Identidad del ingeniero |
| `especialidad_revision` | ForeignKey → EspecialidadRevision | nullable, blank |
| `history` | HistoricalRecords | Auditoría |

**Properties existentes**: Ninguna. `nombre_completo` y `cip` vienen de `perfil_ingeniero`.

---

### `DelegadoMunicipalidad` (`backend/modules/liquidaciones/domain/models/delegado.py:48`)
⚠️ **Esta es la tabla "operativa" a renombrar a `DelegadoOperacion`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `delegado` | ForeignKey → Delegado | related_name: `municipalidades_asignadas` |
| `municipalidad` | ForeignKey → Municipalidad | related_name: `delegados` |
| `liquidacion_revision` | ForeignKey → TipoLiquidacion | nullable, blank (asignación por tipo de liquidación) |
| `tipo` | CharField(max=20) | choices: `TipoDelegado.TITULAR` / `ALTERNO` |
| `history` | HistoricalRecords | |

- `unique_together`: (delegado, municipalidad, liquidacion_revision)
- **No tiene campo `revisiones`** — el usuario quiere agregarlo aquí.

**Vigencia**: через отдельную таблицу `DelegadoMunicipalidadPeriodo` (line 100):
- FK → `DelegadoMunicipalidad` (CASCADE)
- Hereda de `VigenciaModel`: `periodo_inicio`, `periodo_fin`
- `history`: HistoricalRecords

---

### `Inspector` (`backend/modules/liquidaciones/domain/models/inspector.py:13`)
| Campo | Tipo | Notas |
|-------|------|-------|
| `perfil_ingeniero` | OneToOneField → PerfilIngeniero | Identidad del ingeniero |
| `especialidad_revision` | ForeignKey → EspecialidadRevision | nullable, blank |
| `history` | HistoricalRecords | |

- `unique_together`: (perfil_ingeniero, especialidad_revision)

**No tiene tabla operativa propia** — `InspectorTipoLiquidacion` hace su vez.

---

### `InspectorTipoLiquidacion` (`backend/modules/liquidaciones/domain/models/inspector.py:45`)
⚠️ **Esta es la tabla "operativa" a renombrar a `InspectorOperacion`**

| Campo | Tipo | Notas |
|-------|------|-------|
| `inspector` | ForeignKey → Inspector | related_name: `tipos_liquidacion` |
| `tipo_liquidacion` | ForeignKey → TipoLiquidacion | related_name: `inspectores` |
| `categoria` | CharField(max_length=1) | **ABC — valores actuales del seed** |
| `numero_registro` | CharField(max=50) | |
| `telefono` | CharField(max=20) | nullable, blank — **NO se povo del seed** |
| `email` | EmailField(max=100) | nullable, blank — **viene de PerfilIngeniero.correo_personal** |

- `unique_together`: (inspector, tipo_liquidacion, numero_registro)
- **No tiene campo `revisiones`** — el usuario quiere agregarlo aquí.

**Vigencia**: через отдельную таблицу `InspectorAsignacionPeriodo` (line 105):
- FK → `InspectorTipoLiquidacion` (PROTECT)
- Hereda de `VigenciaModel`: `periodo_inicio`, `periodo_fin`
- `history`: HistoricalRecords

---

### `PerfilIngeniero` (`backend/modules/usuarios/domain/models/perfil_ingeniero.py:125`)
| Campo | Tipo | Notas |
|-------|------|-------|
| `usuario` | OneToOneField → User | nullable, blank |
| `nombres` | CharField(max=200) | |
| `apellido_paterno` | CharField(max=100) | |
| `apellido_materno` | CharField(max=100) | |
| `fecha_nacimiento` | DateField | nullable |
| `genero` | CharField(max=20) | nullable |
| `cip` | CharField(max=20, unique) | **Se guarda con 0 a la izquierda: "041426"** |
| `dni` | CharField(max=8, unique) | |
| `correo_personal` | EmailField(max=255) | nullable |
| `correo_institucional` | EmailField(max=255) | nullable |
| `direccion` | CharField(max=512) | nullable |
| `ubigeo` | CharField(max=6) | nullable |
| `especialidad` | ForeignKey → EspecialidadIngeniero | nullable |
| `capitulo` | ForeignKey → Capitulo | nullable |
| **@property `nombre_completo`** | | `self.nombres + " " + self.apellido_paterno + " " + self.apellido_materno` |

**No tiene campo `telefono` ni `celular`** — el teléfono en `InspectorTipoLiquidacion` es un duplicado independiente.

**CIP con 0 a la izquierda** (`backend/modules/usuarios/domain/services/core/perfil_ingeniero_core_service.py:21`):
```python
def _normalizar_cip(self, cip: str) -> str:
    cip = str(cip).strip().replace('-', '').replace(' ', '')
    return cip.zfill(6)[:6]  # → "041426" stored
```
**No hay propiedad `cip_sin_ceros`** — la presentación sin ceros es responsabilidad del caller/presenter.

---

## 2. Categoría Inspector ↔ Tarifa IO: Relación Hoy

### Inspector (actual)
- `InspectorTipoLiquidacion.categoria`: CharField(max_length=1)
- Valores del seed `inspectores_reales.json`: **1, 2, 3, 4** (números guardados como string)
- Seed de inspectores: `backend/modules/liquidaciones/management/commands/seed_inspectores.py:171-188`

### Tarifa IO (actual)
- `TarifaPorCategoriaVisitas.categoria_visitas`: CharField(max_length=50), choices=`TramiteAccion.choices`
- `TramiteAccion` (`backend/modules/liquidaciones/domain/constants.py:75`): **A, B, C, D**
- Seed `tarifas_cam_2026.json`: categorias A, B, C, D con porcentajes UIT

###Frontend Inspeccion Obra
- `visitasFormSchema` (`frontend/src/features/liquidaciones/schemas/liquidacion-visitas-form.schema.ts:13`):
  ```typescript
  categoria: z.enum(["C1", "C2", "C3", "C4"], ...)
  ```
- **MISMATCH**: frontend espera C1-C4, backend tiene A-D.

### Seed Tarifas All (para 2026)
- `tarifas_all.json` usa `"categoria": "C1"`, `"C2"`, `"C3"`, `"C4"` — diferente de `tarifas_cam_2026.json` (A, B, C, D).

### Mapeo Actual
**No hay mapeo automático** entre `Inspector.categoria` y `TarifaPorCategoriaVisitas.categoria_visitas`. Son independientes:
- El inspector tiene una categoría numérica (1-4) que representa su nivel/clasificación
- La tarifa de IO tiene categoría A/B/C/D que representa el tipo de trámite

**El usuario propone**: unificar a 1-4 (la misma para inspector y tarifa IO).

---

## 3. Inventario de Usos — Archivos a Tocar

### Renombrar `DelegadoMunicipalidad` → `DelegadoOperacion`

| Archivo | Tipo | Impacto |
|---------|------|---------|
| `backend/modules/liquidaciones/domain/models/delegado.py:48` | Model definition | Renombrar clase |
| `backend/modules/liquidaciones/domain/models/__init__.py` | Import/exports | Actualizar nombre exportado |
| `backend/modules/liquidaciones/models.py` | Django models | Actualizar reference |
| `backend/modules/liquidaciones/admin/profesionales_admin.py:72` | Admin class | Renombrar `DelegadoMunicipalidadAdmin` |
| `backend/modules/liquidaciones/admin/profesionales_admin.py:19` | Inline class | Renombrar `DelegadoMunicipalidadInline` |
| `backend/modules/liquidaciones/management/commands/seed_delegados.py:131` | Seed command | Actualizar `get_or_create(DelegadoMunicipalidad, ...)` |
| `backend/modules/liquidaciones/tests/integration/test_delegados.py` | Tests | 8 references |
| `backend/modules/liquidaciones/tests/e2e/test_delegados_liquidacion_e2e.py` | E2E tests | |
| `backend/modules/liquidaciones/tests/integration/test_delegados_asignaciones.py` | Tests | |

### Renombrar `InspectorTipoLiquidacion` → `InspectorOperacion`

| Archivo | Tipo | Impacto |
|---------|------|---------|
| `backend/modules/liquidaciones/domain/models/inspector.py:45` | Model definition | Renombrar clase |
| `backend/modules/liquidaciones/domain/models/__init__.py` | Import/exports | Actualizar nombre exportado |
| `backend/modules/liquidaciones/models.py` | Django models | Actualizar reference |
| `backend/modules/liquidaciones/admin/profesionales_admin.py:102` | Admin class | Renombrar `InspectorTipoLiquidacionAdmin` |
| `backend/modules/liquidaciones/admin/profesionales_admin.py:38` | Inline class | Renombrar `InspectorTipoLiquidacionInline` |
| `backend/modules/liquidaciones/management/commands/seed_inspectores.py:183` | Seed command | Actualizar `get_or_create(InspectorTipoLiquidacion, ...)` |
| `backend/modules/liquidaciones/tests/integration/test_inspectores.py` | Tests | 8+ references |
| `backend/modules/liquidaciones/presentation/schemas/inspector/inspector_schemas.py` | API schemas | Renombrar en comments/docs |
| `backend/modules/liquidaciones/presentation/presenters/inspector_presenter.py` | Presenter | Actualizar field names |

### Agregar `revisiones` a tablas operativas

- `DelegadoMunicipalidad` (→ DelegadoOperacion): agregar `revisiones` IntegerField
- `InspectorTipoLiquidacion` (→ InspectorOperacion): agregar `revisiones` IntegerField
- Migration necesaria

### Cambiar categoría inspector: ABC → 1234

| Área | Hoy | Propuesta |
|------|-----|-----------|
| `InspectorTipoLiquidacion.categoria` | CharField(max_length=1), choices=A/B/C/D | CharField(max_length=2), choices=1/2/3/4 |
| `TarifaPorCategoriaVisitas.categoria_visitas` | choices=A/B/C/D (TramiteAccion) | choices=1/2/3/4 (nuevo enum) |
| `TramiteAccion` constant | A/B/C/D | Eliminar o mantener para compatibilidad? |
| Seed inspectores | `categoria: 4` (int) → stored as "4" | Igual, pero con max_length=2 |
| Seed tarifas | `"categoria_visitas": "A"` | → `"1"`, `"2"`, `"3"`, `"4"` |
| Frontend Zod | `z.enum(["C1","C2","C3","C4"])` | → `z.enum(["1","2","3","4"])` |

### Properties de email/telefono desde PerfilIngeniero

- `InspectorTipoLiquidacion.telefono` — **el seed no lo povo**, es un campo huérfano. Verificar si algún código lo usa.
- `InspectorTipoLiquidacion.email` — **viene de PerfilIngeniero.correo_personal**, podría ser property

```python
# En InspectorTipoLiquidacion (o InspectorOperacion)
@property
def email(self) -> str | None:
    return self.inspector.perfil_ingeniero.correo_personal

# PerfilIngeniero ya tiene nombre_completo property
```

**Necesita verificar**: ¿el admin de inspectores o los schemas muestran `telefono` directamente de InspectorTipoLiquidacion? Si sí, la property rompería el admin read.

### CIP sin ceros a la izquierda

- `PerfilIngeniero.cip` se guarda como string zfill(6): "041426"
- Display sin ceros: "41426"
- Agregar property:
```python
@property
def cip_sin_ceros(self) -> str:
    return str(int(self.cip))  # "041426" → 41426
```
- Revisar presenters que muestran cip: `DelegadoMunicipalidadesOut`, `PerfilIngenieroOut`, `InspectorOut`

---

## 4. Riesgos y Decisiones

### Riesgo 1: Mismatch de categorías con frontend
El frontend de visitas (`liquidacion-visitas-form.schema.ts`) usa C1-C4. El backend de tarifas (tarifas_cam_2026.json) usa A-D. El seed de inspectores usa 1-4. **Son tres sistemas con tres valores distintos para "categoría"**. La unificación a 1-4 debe incluir:
1. Actualizar seed_tarifas para usar 1-4 en lugar de A-D
2. Actualizar TramiteAccion o reemplazarlo con nuevo enum CategoriaInspector
3. Actualizar frontend Zod schema para usar 1-4
4. Migración de datos en DB

### Riesgo 2: Campo `telefono` en InspectorTipoLiquidacion
El seed de inspectores **no povo telefono** (solo crea el campo vacío). Existe como campo directo en el modelo, pero la fuente real de datos de contacto es `PerfilIngeniero.correo_personal`. Si se convierte en property, hay que verificar que no haya código que escriba a ese campo directamente.

### Riesgo 3: unique_together constraint
`InspectorTipoLiquidacion` tiene `unique_together: (inspector, tipo_liquidacion, numero_registro)`. Si se renombra la clase, la constraint en la migration也跟着改名. Hay que verificar migrations.

### Riesgo 4:vigencia model ya existe
`DelegadoMunicipalidadPeriodo` y `InspectorAsignacionPeriodo` ya implementan vigencia con `VigenciaModel`. Si el usuario quiere que `revisiones` sea parte de la vigencia, hay que clarificar el diseño.

### Riesgo 5: Backend admin naming
Los admins actuales se llaman `DelegadoMunicipalidadAdmin` y `InspectorTipoLiquidacionAdmin`. Si se renombran las clases de modelo, los admins deben seguir el nuevo nombre por convención Django.

---

## 5. Recomendación de Diseño

### Estructura Objetivo

```
DelegadoOperacion (hoy DelegadoMunicipalidad)
├── FK → Delegado
├── FK → Municipalidad  
├── FK → TipoLiquidacion (nullable) -- tipo de liquidación asignado
├── CharField tipo (TITULAR/ALTERNO)
├── IntegerField revisiones = 0  -- NUEVO
├── related_name: "operaciones"
└── unique_together: (delegado, municipalidad, liquidacion_revision)

DelegadoOperacionPeriodo (hoy DelegadoMunicipalidadPeriodo)
├── FK → DelegadoOperacion (CASCADE)
├── periodo_inicio: DateField
├── periodo_fin: DateField (nullable = vigente)
└── Hereda: HistoricalRecords

InspectorOperacion (hoy InspectorTipoLiquidacion)
├── FK → Inspector
├── FK → TipoLiquidacion
├── CharField categoria (choices: "1","2","3","4")  -- CAMBIADO de ABC a 1234
├── CharField numero_registro
├── IntegerField revisiones = 0  -- NUEVO
├── property email  -- deriv from PerfilIngeniero.correo_personal
├── property telefono  -- deriv from ??? (PerfilIngeniero no tiene telefono)
├── related_name: "operaciones"
└── unique_together: (inspector, tipo_liquidacion, numero_registro)

InspectorOperacionPeriodo (hoy InspectorAsignacionPeriodo)
├── FK → InspectorOperacion (PROTECT)
├── periodo_inicio: DateField
├── periodo_fin: DateField (nullable = vigente)
└── Hereda: HistoricalRecords
```

### PerfilIngeniero — Properties

```python
# En PerfilIngeniero (backend/modules/usuarios/domain/models/perfil_ingeniero.py)
@property
def cip_sin_ceros(self) -> str:
    """CIP sin ceros a la izquierda: '041426' → '41426'"""
    return str(int(self.cip))

@property  
def telefono(self) -> str | None:
    """Telefono del ingeniero — consultar fuente correcta si existe"""
    # NOTA: PerfilIngeniero NO tiene campo telefono actualmente
    # Si se agrega a PerfilIngeniero, esta property lo derivaría
    return getattr(self, 'telefono', None)
```

### Mapeo Categoría Inspector → Tarifa IO

Si la categoría del inspector (1-4) debe corresponderse con la categoría de la tarifa IO:
- Crear constante `CategoriaTarifa` con choices 1/2/3/4
- `TarifaPorCategoriaVisitas.categoria_visitas` usa esta nueva constante
- El frontend muestra la misma categoría tanto para inspector como para tarifa

### Decisión: `revisiones` en tabla operativa
El campo `revisiones` (contador de cuántas veces se ha usado en una liquidación) va en la tabla operativa:
- `DelegadoOperacion.revisiones` (IntegerField, default=0)
- `InspectorOperacion.revisiones` (IntegerField, default=0)

Se incrementaría en el flujo de creación de `LiquidacionDelegado` / `LiquidacionInspector`.

---

## 6. Archivos Clave para la Refactorización

### Modelos (fuente de verdad)
- `backend/modules/liquidaciones/domain/models/delegado.py` — `Delegado`, `DelegadoMunicipalidad`, `DelegadoMunicipalidadPeriodo`
- `backend/modules/liquidaciones/domain/models/inspector.py` — `Inspector`, `InspectorTipoLiquidacion`, `InspectorAsignacionPeriodo`
- `backend/modules/usuarios/domain/models/perfil_ingeniero.py` — `PerfilIngeniero`

### Constants
- `backend/modules/liquidaciones/domain/constants.py` — `TramiteAccion` (A/B/C/D), `TipoDelegado`, `CategoriaDelegado`
- `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/tarifas_reglas.py` — `TarifaPorCategoriaVisitas`

### Admins
- `backend/modules/liquidaciones/admin/profesionales_admin.py`

### Seeds
- `backend/modules/liquidaciones/management/commands/seed_delegados.py`
- `backend/modules/liquidaciones/management/commands/seed_inspectores.py`
- `backend/modules/liquidaciones/management/commands/seed_tarifas.py`

### Schemas/Presenters
- `backend/modules/liquidaciones/presentation/schemas/inspector/inspector_schemas.py`
- `backend/modules/liquidaciones/presentation/presenters/inspector_presenter.py`
- `backend/modules/liquidaciones/presentation/schemas/delegado/delegado_schemas.py`

### Frontend
- `frontend/src/features/liquidaciones/schemas/liquidacion-visitas-form.schema.ts` — C1-C4 enum

### Tests
- `backend/modules/liquidaciones/tests/integration/test_delegados.py`
- `backend/modules/liquidaciones/tests/integration/test_inspectores.py`
- `backend/modules/liquidaciones/tests/integration/test_delegados_asignaciones.py`
- `backend/modules/liquidaciones/tests/e2e/test_delegados_liquidacion_e2e.py`
- `backend/modules/liquidaciones/tests/e2e/test_e2e_inspeccion_obra.py`

---

## 7. Riesgos

1. **Categorías ABC vs 1234 vs C1-C4**: tres sistemas con valores distintos. Requiere migración coordinada de seed + modelo + frontend.
2. **`telefono` huérfano**: el campo existe en InspectorTipoLiquidacion pero no se povo del seed. Si se convierte a property, verificar que nada escriba directamente a él.
3. **Migrations con unique_together**: el constraint name lleva el nombre del modelo; renombrar requiere nueva migration.
4. **`revisiones` semantics**: ¿se incrementa por cada liquidación asociada o por cada período de vigencia? Necesita clarificación con el usuario.
5. **Frontend C1-C4 enum**: el schema Zod usa C1-C4 pero el backend usa A-D. Esto es un bug existente que la refactorización debería resolver, no ignorar.

---

## 8. Próximos Pasos Recomendados

1. **Clarificación con usuario**: 
   - ¿`revisiones` es contador de liquidaciones o de períodos de asignación?
   - ¿La categoría 1-4 del inspector se mapea directamente a la categoría 1-4 de la tarifa IO?
   - ¿El teléfono del inspector de dónde viene (PerfilIngeniero no tiene telefono)?

2. **sdd-propose**: definir alcance preciso del rename + cambios de categoría + properties

3. **sdd-spec**: escribir delta specs con escenarios de migración de datos

4. **sdd-design**: diseñar la migración de ABC → 1234 con datos existentes

**Ready for Proposal**: Yes — el estado actual está completamente cartografiado. La decisión principal que necesita el usuario es la semantics de `revisiones` y la estrategia de migración de categorías.

---

## 9. Diseño Detallado — Refactorización Completa

### 9.1 Renombrar Tablas

| Modelo actual | Modelo nuevo | Tabla DB |
|-------------|-------------|----------|
| `DelegadoMunicipalidad` | `DelegadoOperacion` | `liquidaciones_delegadomunicipalidad` → `liquidaciones_delegadooperacion` |
| `DelegadoMunicipalidadPeriodo` | `DelegadoOperacionPeriodo` | `liquidaciones_delegadomunicipalidadperiodo` → `liquidaciones_delegadooperacionperiodo` |
| `InspectorTipoLiquidacion` | `InspectorOperacion` | `liquidaciones_inspectortipoliquidacion` → `liquidaciones_inspectoroperacion` |
| `InspectorAsignacionPeriodo` | `InspectorOperacionPeriodo` | `liquidaciones_inspectorasignacionperiodo` → `liquidaciones_inspectoroperacionperiodo` |

### 9.2 Properties a Implementar

#### PerfilIngeniero (perfil_ingeniero.py:218+)
```python
@property
def cip_sin_ceros(self) -> str:
    """CIP sin ceros a la izquierda: '041426' → '41426'."""
    return str(int(self.cip)) if self.cip else ""
```

#### InspectorOperacion (inspector.py, post-renombrar)
```python
@property
def cip_sin_ceros(self) -> str:
    """CIP del inspector sin ceros a la izquierda."""
    return self.inspector.perfil_ingeniero.cip_sin_ceros

@property
def numero_registro(self) -> str:
    """Número de registro calculado: f'CAM{cip_sin_ceros}{categoria}'."""
    return f"CAM{self.cip_sin_ceros}{self.categoria}"

@property
def email(self) -> Optional[str]:
    """Email del inspector desde PerfilIngeniero.correo_personal."""
    return self.inspector.perfil_ingeniero.correo_personal

@property
def telefono(self) -> Optional[str]:
    """Teléfono del inspector desde PerfilIngeniero.celular."""
    return self.inspector.perfil_ingeniero.celular
```

#### DelegadoOperacion (delegado.py, post-renombrar)
```python
@property
def email(self) -> Optional[str]:
    """Email del delegado desde PerfilIngeniero.correo_personal."""
    return self.delegado.perfil_ingeniero.correo_personal

@property
def telefono(self) -> Optional[str]:
    """Teléfono del delegado desde PerfilIngeniero.celular."""
    return self.delegado.perfil_ingeniero.celular
```

### 9.3 Migración de Datos

#### InspectorTipoLiquidacion → InspectorOperacion

| Campo actual | Storage actual | Destino post-refactor | Acción migration |
|-------------|---------------|----------------------|-----------------|
| `numero_registro` | CharField DB | **Property calculada** | Eliminar columna — se calcula como `f"CAM{cip_sin_ceros}{categoria}"` |
| `telefono` | CharField DB | **Property** → `PerfilIngeniero.celular` | Data migration: copiar a `PerfilIngeniero.celular`, luego eliminar columna |
| `email` | EmailField DB | **Property** → `PerfilIngeniero.correo_personal` | Data migration: copiar a `PerfilIngeniero.correo_personal`, luego eliminar columna |
| `categoria` | CharField "1","2","3","4" | **Mantener como CharField** (o FK si se especifica) | Sin cambio |

#### Pasos de migración sugeridos:
1. **Data migration**: Para cada `InspectorTipoLiquidacion`, copiar `telefono` → `PerfilIngeniero.celular` del inspector asociado
2. **Data migration**: Para cada `InspectorTipoLiquidacion`, copiar `email` → `PerfilIngeniero.correo_personal` del inspector asociado
3. **Schema migration**: Remover columnas `telefono`, `email` de `InspectorTipoLiquidacion`
4. **Schema migration**: Renombrar tabla de `inspectortipoliquidacion` → `inspectoroperacion`
5. **Schema migration**: Renombrar tabla de `inspectorasignacionperiodo` → `inspectoroperacionperiodo`

### 9.4 Mapeo de Categorías — Decisión Requerida

| Sistema | Campo | Valores actuales | Notas |
|---------|-------|-----------------|-------|
| **Inspector** | `InspectorTipoLiquidacion.categoria` | "1", "2", "3", "4" | CharField del seed |
| **Tarifa IO** | `TarifaPorCategoriaVisitas.categoria_visitas` | "A", "B", "C", "D" | `TramiteAccion.choices` |
| **Frontend IO** | `visitasFormSchema.categoria` | `"C1"`, `"C2"`, `"C3"`, `"C4"` | Zod enum |

**Problema**: Tres sistemas de categorías diferentes (1-4 inspector, A-D tarifa, C1-C4 frontend).

**Recomendación**: Unificar a 1-4 en todos los sistemas, requiere:
1. Actualizar `TramiteAccion` o crear nuevo enum `CategoriaTarifa`
2. Actualizar seeds de tarifas para usar 1-4 en lugar de A-D
3. Actualizar frontend Zod schema para usar 1-4 en lugar de C1-C4
4. Migration de datos en `TarifaPorCategoriaVisitas.categoria_visitas`

### 9.5 Seeds — Cambios Requeridos

#### seed_inspectores.py
```python
# Actual:
itl, itl_created = InspectorTipoLiquidacion.objects.get_or_create(
    inspector=inspector,
    tipo_liquidacion=tipo,
    numero_registro=numero_registro,  # almacenado
    defaults={"categoria": str(categoria)},
)

# Post-refactor:
itl, itl_created = InspectorOperacion.objects.get_or_create(
    inspector=inspector,
    tipo_liquidacion=tipo,
    defaults={"categoria": str(categoria)},  # numero_registro es property
)
```

#### seed_delegados.py / load_delegados_reales.py
- Actualizar imports de `DelegadoMunicipalidad` → `DelegadoOperacion`
- Actualizar imports de `DelegadoMunicipalidadPeriodo` → `DelegadoOperacionPeriodo`
- Nota: `load_delegados_reales.py` línea 421 usa `MunicipalidadDelegado` — verificar si es bug existente

### 9.6 Archivos a Tocar por Fase

#### Fase 1: Modelos + Migration
- `backend/modules/liquidaciones/domain/models/delegado.py`
- `backend/modules/liquidaciones/domain/models/inspector.py`
- `backend/modules/usuarios/domain/models/perfil_ingeniero.py`
- `backend/modules/liquidaciones/domain/models/__init__.py`
- `backend/modules/liquidaciones/models.py`
- `backend/modules/liquidaciones/admin/profesionales_admin.py`
- `backend/modules/liquidaciones/management/commands/seed_inspectores.py`
- `backend/modules/liquidaciones/management/commands/seed_delegados.py`
- `backend/modules/liquidaciones/management/commands/load_delegados_reales.py`
- Migration Django

#### Fase 2: Schemas + Results
- `backend/modules/liquidaciones/presentation/schemas/inspector/inspector_schemas.py`
- `backend/modules/liquidaciones/domain/results/inspector/inspector_result.py`
- `backend/modules/liquidaciones/presentation/schemas/delegado/delegado_schemas.py`
- `backend/modules/liquidaciones/domain/results/delegado/delegado_result.py`

#### Fase 3: Core Services + Orchestrators
- `backend/modules/liquidaciones/domain/services/core/inspector/inspector_core_service.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/inspector_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/delegado_orchestrator.py`

#### Fase 4: Presenters
- `backend/modules/liquidaciones/presentation/presenters/inspector_presenter.py`
- `backend/modules/liquidaciones/presentation/presenters/delegado_presenter.py`

#### Fase 5: Tests
- `backend/modules/liquidaciones/tests/integration/test_inspectores.py`
- `backend/modules/liquidaciones/tests/integration/test_delegados.py`
- `backend/modules/liquidaciones/tests/integration/test_delegados_asignaciones.py`
- `backend/modules/liquidaciones/tests/e2e/test_delegados_liquidacion_e2e.py`
- `backend/modules/liquidaciones/tests/e2e/test_e2e_inspeccion_obra.py`

#### Fase 6: Frontend
- `frontend/src/features/inspectores/types/inspectores.types.ts`
- `frontend/src/features/inspectores/schemas/inspector-vigente.schema.ts`
- `frontend/src/features/liquidaciones/schemas/liquidacion-visitas-form.schema.ts` (si se unifica categoría)

### 9.7 Riesgos Confirmados

| Riesgo | Severidad | Mitigation |
|--------|-----------|------------|
| `numero_registro` como property rompe API existente | ALTO | Verificar que la API exponga `numero_registro` vía serializer — Django Ninja puede serializar properties. Test de integración. |
| `InspectorVigenteSchema.categoria` no existe en backend | ALTO | Frontend espera `categoria: z.number().nullable()` pero `InspectorVigenteResult` no tiene `categoria`. Agregar `categoria` al DTO o corregir schema frontend. |
| Categorías inspector (1-4) ≠ tarifa (A-D) ≠ frontend (C1-C4) | ALTO | Unificar a 1-4 requiere migración coordinada de seeds + modelo + frontend |
| `MunicipalidadDelegado` en load_delegados_reales.py línea 421 | MEDIO | ¿Bug existente o modelo diferente? Verificar antes de implementar |
| `ReglaTarifaInspeccionObra` referenciada pero no existe | MEDIO | Seed `seed_tarifas_all.py` referencia este modelo que no existe. Verificar si el seed funciona. |
| Migration de renombrar tablas es destructiva | MEDIO | Generar migration con `db_rename` para cambiar nombre de tabla sin perder datos |
