# Exploration: `inspectores-alpha-models`

## Alpha Inspector Model Inventory

### 1. `Inspector` (file: `modules/liquidaciones/domain/models/inspector.py`)

```python
class Inspector(BaseModel):
    history = HistoricalRecords()

    perfil_ingeniero = models.ForeignKey(
        "usuarios.PerfilIngeniero",
        on_delete=models.PROTECT,
        related_name="inspectores_liquidacion",
        verbose_name="Perfil de Ingeniero",
    )
    especialidad = models.ForeignKey(
        "Especialidad",          # ← from usuarios.PerfilIngeniero Especialidad
        on_delete=models.PROTECT,
        related_name="inspectores",
        verbose_name="Especialidad",
    )
    tipo_liquidacion = models.CharField(
        max_length=30,
        choices=TipoLiquidacion.choices,   # EDIFICACION, HABILITACION_URBANA
        verbose_name="Tipo de Liquidacion",
    )
    categoria = PositiveSmallIntegerField(null=True, blank=True)
    numero_registro = CharField(max_length=50)
    vigencia = DateField()
    status = CharField(
        max_length=20,
        choices=DelegadoStatus.choices,    # ACTIVO, INACTIVO, SUSPENDIDO
        default=DelegadoStatus.ACTIVO,
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["perfil_ingeniero", "tipo_liquidacion", "especialidad", "numero_registro"],
                name="unique_inspector_registro",
            )
        ]
```

**Key characteristics:**
- Catalog of inspectors eligible for construction inspections by tipo_liquidacion
- FK to `PerfilIngeniero` (already exists in betha at `usuarios/domain/models/perfil_ingeniero.py`)
- FK to `Especialidad` (same model, already in betha)
- Uses `DelegadoStatus` and `TipoLiquidacion` constants — both already present in betha
- Has `simple_history` tracking (`HistoricalRecords`)
- Inherits `BaseModel` (UUID pk + created_at + updated_at)

### 2. `LiquidacionInspector` (file: `modules/liquidaciones/domain/models/liquidacion_inspector.py`)

```python
class LiquidacionInspector(BaseModel):
    history = HistoricalRecords()

    liquidacion = ForeignKey("LiquidacionGeneral", on_delete=CASCADE, related_name="liquidacion_inspectores")
    inspector = ForeignKey("Inspector", on_delete=PROTECT, related_name="liquidacion_inspectores")
    periodo = CharField(max_length=100, blank=True, null=True)
    dictamen_revision = CharField(
        max_length=20,
        choices=DictamenRevision.choices,   # CONFORME, NO_CONFORME, PENDIENTE, AP_OB
        blank=True, null=True,
    )
    fecha_presentacion = DateField(blank=True, null=True)
    fecha_revision = DateField(blank=True, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["liquidacion", "inspector"], name="unique_liquidacion_inspector")
        ]
```

**Key characteristics:**
- Explicit M2M junction table between `LiquidacionGeneral` and `Inspector`
- Tracks inspection workflow: periodo, dictamen_revision, fecha_presentacion, fecha_revision
- Uses `DictamenRevision` constant — already present in betha
- Same `BaseModel` + `HistoricalRecords` conventions

---

## Betha Current State Comparison

| Aspect | Alpha | Betha |
|--------|-------|-------|
| `Inspector` model | Exists in `domain/models/inspector.py` | **Empty file** (`inspector.py` exists, 0 bytes) |
| `LiquidacionInspector` model | Exists in `domain/models/liquidacion_inspector.py` | **Does not exist** |
| `LiquidacionDelegado` model | Separate file `liquidacion_delegado.py` | Appended at bottom of `delegado.py` (functionally equivalent) |
| `DelegadoStatus` constant | Yes | Yes (in `constants.py`) |
| `DictamenRevision` constant | Yes | Yes (in `constants.py`) |
| `TipoLiquidacion` constant | Yes | Yes (in `constants.py`) |
| `PerfilIngeniero` model | Yes | Yes (at `usuarios/domain/models/perfil_ingeniero.py`) |
| `Especialidad` model | Yes | Yes (at `usuarios/domain/models/perfil_ingeniero.py`) |
| `LiquidacionGeneral` model | Yes | Yes |

**Conclusion:** Both models are **entirely missing** from betha (empty placeholder file for Inspector, no LiquidacionInspector at all).

---

## Proposed Placement / Adaptation Plan

### Where to add in betha

Following betha's existing pattern where `LiquidacionDelegado` is appended at the bottom of `delegado.py` rather than a separate file, there are two options:

**Option A — Mirror alpha exactly** (recommended for consistency with alpha):
- `inspector.py` → populate the empty file with the `Inspector` model
- `liquidacion_inspector.py` → create new file with `LiquidacionInspector` model

**Option B — Follow betha's local convention** (group LiquidacionInspector near LiquidacionDelegado):
- `inspector.py` → populate with `Inspector` model
- Append `LiquidacionInspector` at the bottom of `delegado.py` alongside `LiquidacionDelegado`

**Recommendation: Option A** — Mirror alpha structure. The `LiquidacionDelegado` grouping in betha was likely an initial adaptation; keeping inspector models in their own files maintains clean separation and makes future sync with alpha easier.

### Files to modify

1. **`backend/modules/liquidaciones/domain/models/inspector.py`** — populate with `Inspector` model
2. **`backend/modules/liquidaciones/domain/models/liquidacion_inspector.py`** — create with `LiquidacionInspector` model
3. **`backend/modules/liquidaciones/domain/models/__init__.py`** — add exports for `Inspector` and `LiquidacionInspector`
4. **`backend/modules/liquidaciones/models.py`** — add exports for `Inspector` and `LiquidacionInspector`
5. **`backend/modules/liquidaciones/admin.py`** — register ModelAdmin classes (if not already covered)

### Required constants

All needed constants (`DelegadoStatus`, `DictamenRevision`, `TipoLiquidacion`) already exist in `backend/modules/liquidaciones/domain/constants.py`. No new constants needed.

### Dependencies check

| Dependency | Betha path | Status |
|------------|-----------|--------|
| `BaseModel` | `core.models.BaseModel` | ✅ Exists |
| `HistoricalRecords` | `simple_history.models.HistoricalRecords` | ✅ Used by all Betha models |
| `DelegadoStatus` | `domain/constants.py` | ✅ Exists |
| `DictamenRevision` | `domain/constants.py` | ✅ Exists |
| `TipoLiquidacion` | `domain/constants.py` | ✅ Exists |
| `PerfilIngeniero` | `usuarios.domain.models.perfil_ingeniero.PerfilIngeniero` | ✅ Exists |
| `Especialidad` | `usuarios.domain.models.perfil_ingeniero.Especialidad` | ✅ Exists |
| `LiquidacionGeneral` | `domain/models/liquidacion/liquidacion.py` | ✅ Exists |

---

## Exact Apply Checklist (next phase)

1. [ ] Populate `backend/modules/liquidaciones/domain/models/inspector.py` with the `Inspector` model class
2. [ ] Create `backend/modules/liquidaciones/domain/models/liquidacion_inspector.py` with the `LiquidacionInspector` model class
3. [ ] Add to `domain/models/__init__.py`:
     - `from .inspector import Inspector`
     - `from .liquidacion_inspector import LiquidacionInspector`
     - Add both to `__all__`
4. [ ] Add to `backend/modules/liquidaciones/models.py`:
     - `Inspector` and `LiquidacionInspector` in the import from `.domain.models`
     - Add both to `__all__`
5. [ ] Register in `admin.py`: `InspectorAdmin` and `LiquidacionInspectorAdmin`
6. [ ] Run `makemigrations liquidaciones` and `migrate` (or confirm planned reset/rebuild handles it)
7. [ ] Verify no naming conflicts — `Inspector` does not clash with any existing model

---

## Risks

1. **Empty `inspector.py` placeholder**: Betha already has a stub file at `inspector.py`. The apply phase must populate it, not create a new file. Edit vs. write distinction matters.
2. **`related_name` collision**: `inspectores_liquidacion` on `PerfilIngeniero` and `inspectores` on `Especialidad` must be verified as unused elsewhere in betha.
3. **Migration approach**: User mentioned "planned reset/rebuild." If migrations are being reset, the apply phase should confirm whether `makemigrations` is still needed or if the rebuild covers new models.
4. **Alpha sync divergence**: Keeping the two-file structure (Option A) means future alpha→betha syncs will need to maintain the same file split.
