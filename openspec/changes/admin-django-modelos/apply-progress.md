# SDD Apply Progress — Admin Django Modelos

## Status: COMPLETE ✅

---

## Admin Structure Created

### `modules/usuarios/admin/` (package)
```
admin/
├── __init__.py        # registers all submodules
├── usuario_admin.py   # Usuario (UserAdmin extended for custom user with DNI)
└── perfil_admin.py    # PerfilIngeniero
└── catalogo_admin.py  # Capitulo, EspecialidadIngeniero, EspecialidadRevision, IngenieroHabilitacion
```
**Registered:** Usuario, PerfilIngeniero, Capitulo, EspecialidadIngeniero, EspecialidadRevision, IngenieroHabilitacion

### `modules/entidades/admin/` (package)
```
admin/
├── __init__.py               # registers all submodules
├── entidad_admin.py           # Entidad
├── banco_admin.py             # Banco (with ContactoBancoInline)
├── municipalidad_admin.py     # Municipalidad (with inlines), UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
└── contacto_admin.py         # Contacto
```
**Registered:** Entidad, Banco, Contacto, Municipalidad, UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito

### `modules/finanzas/admin/` (package)
```
admin/
├── __init__.py           # registers all submodules
└── impuestos_admin.py    # IGV, UIT
```
**Registered:** IGV, UIT

### `modules/liquidaciones/admin/` (package)
```
admin/
├── __init__.py               # registers all submodules
├── catalogos_admin.py         # TipoLiquidacion, LiquidacionEspecialidadDisponibles
├── profesionales_admin.py     # Delegado, Inspector, Proyectista (with nested inlines)
├── tarifas_admin.py          # TarifaLiquidacionBase, derechos, tarifas
├── liquidacion_admin.py        # LiquidacionGeneral (conditional get_inlines), LiquidacionCodigo
└── proyecto_admin.py          # Proyecto
```
**Registered:** TipoLiquidacion, LiquidacionEspecialidadDisponibles, Delegado, DelegadoMunicipalidad, Inspector, InspectorTipoLiquidacion, Proyectista, TarifaLiquidacionBase, TarifaPorMetroCuadrado, TarifaPorCategoriaVisitas, TarifaPorcentajeObra, DerechoPorcentajeObra, DerechoPorMetroCuadrado, LiquidacionGeneral, LiquidacionCodigo, Proyecto

---

## get_inlines() Conditional Logic — LiquidacionGeneral

`LiquidacionGeneralAdmin.get_inlines(request, obj)` returns inlines based on `obj.tipo_liquidacion.codigo`:

| tipo_liquidacion | Conditional inlines shown |
|-----------------|--------------------------|
| **All types** | LiquidacionDelegadoInline, LiquidacionInspectorInline, LiquidacionProyectistaInline, LiquidacionContactoInline, LiquidacionDocumentosInline |
| EDIFICACION | + LiquidacionEdificacionInline + LiquidacionPorcentajeObraInline |
| HABILITACION_URBANA | + LiquidacionHabilitacionUrbanaInline + LiquidacionPorMetroCuadradoInline |
| MECANICA_SUELOS | + LiquidacionMecanicaSuelosInline + LiquidacionPorMetroCuadradoInline |
| TALUDES | + LiquidacionTaludesInline + LiquidacionPorMetroCuadradoInline |
| INSPECCION_OBRA | + LiquidacionInspeccionObraInline + LiquidacionPorCategoriaVisitasInline |
| IMPACTO_VIAL | + LiquidacionImpactoVialInline + LiquidacionPorMetroCuadradoInline |

This prevents the "forced tables" problem where all 15+ inlines would appear for every liquidation regardless of type.

---

## AppConfig.ready() Modifications

Each `apps.py` was updated with:
```python
def ready(self):
    """Import admin package to trigger admin registration."""
    from . import admin  # noqa: F401
```

Modified apps: `UsuariosConfig`, `EntidadesConfig`, `FinanzasConfig`, `LiquidacionesConfig`

---

## Validations

| Check | Result |
|-------|--------|
| `manage.py check` | ✅ System check identified no issues (0 silenced) |
| `admin.site._registry` count | ✅ 38 models total (31 from our modules + 7 from third-party apps) |

**Third-party registered models (not our code):**
- `auth.group`
- `django_q.failure`, `django_q.ormq`, `django_q.schedule`, `django_q.success`
- `token_blacklist.blacklistedtoken`, `token_blacklist.outstandingtoken`

---

## Model Count by Module

| Module | Registered | Inline/Not standalone | Historical*/Proxy |
|--------|-----------|----------------------|-------------------|
| usuarios | 6 | 0 | 0 |
| entidades | 7 | 2 (ContactoBanco, ContactoMunicipalidad as standalone not needed) | 0 |
| finanzas | 2 | 0 | 0 |
| liquidaciones | 16 | ~15 (all OneToOne extensions + inline bridge tables) | ~all have HistoricalRecords |
| **Total** | **31** | ~17 inline-only | All Historical excluded |

---

## Key Technical Decisions

1. **`admin/` package per module** (not `admin.py`) — required grouping by domain sub-package
2. **`get_inlines()` for conditional display** — only relevant inlines per `tipo_liquidacion`
3. **`RelatedOnlyFieldListFilter`** (not `RelatedOnlyDropdownFilter`) — correct class name in Django 5.2
4. **Direct submodule imports** — several models not re-exported via `modules.X.domain.models.__init__.py`
5. **`core/admin.py` preserved** — the `get_app_list` wrapper promoting LiquidacionGeneral to top still works
6. **`apps.py.ready()` for autodiscovery** — Django doesn't auto-find `admin/` folders; `AppConfig.ready()` handles it cleanly

---

## NOT Registered (By Design)

- **Historical*** — auto-generated by django-simple-history
- **Proxy models** — MunicipalidadProvincial, MunicipalidadDistrital, ProyectoEmpresarial, ProyectoPersonaNatural
- **Inline-only models** — LiquidacionDelegado, LiquidacionInspector, LiquidacionProyectista, LiquidacionContacto, LiquidacionDocumentos (shown as inlines, not standalone)
- **OneToOne extension models** — LiquidacionEdificacion, LiquidacionHabilitacionUrbana, LiquidacionMecanicaSuelos, LiquidacionTaludes, LiquidacionInspeccionObra, LiquidacionImpactoVial (shown as inlines, not standalone)
- **Calculation inline models** — LiquidacionPorMetroCuadrado, LiquidacionPorCategoriaVisitas, LiquidacionPorcentajeObra, LiquidacionPorcentajeObraDetalle (shown as inlines)

---

## Risks

1. **Historical model exclusion** — relies on developers NOT registering Historical* models manually in future admin additions
2. **`core/admin.py` interaction** — the `get_app_list` wrapper runs after our registrations; confirmed compatible
3. **`LiquidacionPorcentajeObraDetalle` not standalone** — shown as nested inline within LiquidacionPorcentajeObra (which is correct)
