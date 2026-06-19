# Modelado DB — Liquidaciones CAM
## Análisis CORREGIDO a nivel Base de Datos y Recomendaciones

**Proyecto:** aplicacion  
**Fecha:** 2026-06-12  
**Alcance:** Módulo `liquidaciones` — modelos, migraciones y lógica de negocio financiera

> **NOTA DE CORRECCIÓN:** Este documento reemplaza la versión anterior que contenía varios análisis incorrectos. Las principales correcciones se indican en cada sección.

---

## 1. Resumen del Modelo Actual (CORREGIDO)

### 1.1 Tablas existentes en DB vs Modelos Python

| Tabla DB | Modelo Python | Observaciones |
|----------|---------------|---------------|
| `liquidaciones_liquidacion` | `Liquidacion` (en `revision.py`) | Shell vacío en DB, pero el modelo Python tiene campos financieros |
| `liquidaciones_revision` | `Revision` (nombre esperado pero NO existe así) | El modelo Python se llama `Liquidacion` (!) |
| `liquidaciones_revisiondelegado` | `RevisionDelegado` | DB tiene FK `revision`, modelo Python tiene FK `liquidacion` |
| `liquidaciones_proyecto` | `Proyecto` | OK |
| `liquidaciones_porcentajeliquidacion` | `PorcentajeRevision` (en `liquidacion.py`) | **NOMBRE INCORRECTO** — DB dice `PorcentajeLiquidacion`, Python dice `PorcentajeRevision` |
| `liquidaciones_porcentajerevision` | **NO EXISTE** | |
| `liquidaciones_igv` | `IGV` | OK |
| `liquidaciones_uit` | `UIT` | OK |
| `liquidaciones_derechominimo` | `DerechoMinimo` | OK |
| `liquidaciones_delegado` | `Delegado` | OK |
| `liquidaciones_especialidad` | `Especialidad` | OK |
| `liquidaciones_proyectista` | `Proyectista` | OK |

### 1.2 Diagrama Simplificado del Modelo Actual (CORREGIDO)

```
┌──────────────────────────────────────────────────────────────┐
│  PROYECTO                                                    │
│  valor_obra │ entidad (FK) │ proyectista (FK)               │
└────────────────────────┬─────────────────────────────────────┘
                         │ 1:N
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  LIQUIDACION (shell en DB)                                   │
│  id (UUID) │ created_at │ updated_at                         │
│  revision (FK, nullable desde 0005) ───────────────────────►  │
└────────────────────────┬─────────────────────────────────────┘
                         │ 1:N
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  REVISION (contiene los campos financieros en DB)           │
│  igv (FK) │ uit (FK) │ derecho_minimo (FK) │ porcentaje_    │
│  liquidacion (FK) │ numero │ estado │ liquidacion (FK)     │
└────────────────────────┬─────────────────────────────────────┘
                         │ 1:N
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  REVISIONDELEGADO (puente N:M)                               │
│  revision (FK en DB) │ delegado (FK)                        │
│  ⚠️ El modelo Python tiene FK liquidacion (INCORRECTO)      │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 Modelo Python Real (lo que existe ahora)

**`domain/models/revision.py`** define:
```python
class Liquidacion(BaseModel):  # ← Se llama Liquidacion pero tiene campos de Revision
    proyecto = FK(Proyecto)
    numero = PositiveIntegerField
    igv = FK(IGV)
    uit = FK(UIT)
    derecho_minimo = FK(DerechoMinimo)
    porcentaje_revision = FK(PorcentajeRevision)  # ← Nombre incorrecto
    estado = CharField
    liquidacion_previa = FK(self)
```

**`domain/models/liquidacion.py`** define:
```python
class PorcentajeRevision(BaseModel):  # ← DB tiene PorcentajeLiquidacion
    porcentaje = DecimalField
    especialidades = M2M(Especialidad)  # ← M2M no existe en DB!
    periodo_inicio = DateField
    periodo_fin = DateField
```

**`domain/models/revision_delegado.py`** define:
```python
class RevisionDelegado(BaseModel):
    liquidacion = FK(Liquidacion)  # ← INCORRECTO! DB tiene FK revision
    delegado = FK(Delegado)
```

---

## 2. Problemas Críticos Identificados (CORREGIDOS)

### 2.1 Issue CRÍTICO: Naming mismatch `PorcentajeLiquidacion` vs `PorcentajeRevision`

```
# domain/models/__init__.py línea 6:
from .liquidacion import Liquidacion, PorcentajeLiquidacion  # ← NO EXISTE!

# domain/models/liquidacion.py solo define:
class PorcentajeRevision(BaseModel):  # ← Se llama diferente!
```

- La tabla `porcentajeliquidacion` fue creada por `0001_initial.py` (línea 975)
- El modelo Python se llama `PorcentajeRevision`
- `mock_proyectos.py` línea 28 intenta importar `PorcentajeLiquidacion` — **fallaría en runtime**

### 2.2 Issue CRÍTICO: Naming mismatch `RevisionDelegado.revision` vs `liquidacion`

```
# migration 0002_initial.py línea 593-601:
RevisionDelegado:
    revision = FK(Revision)  # ← EN DB ES revision

# domain/models/revision_delegado.py línea 19:
class RevisionDelegado(BaseModel):
    liquidacion = FK(Liquidacion)  # ← EN PYTHON ES liquidacion (INCORRECTO!)
```

- El modelo Python tiene FK `liquidacion` pero la base de datos tiene FK `revision`
- `admin.py` línea 27 usa `fk_name = "revision"` — esto no existe en el modelo Python!

### 2.3 Issue CRÍTICO: Admin inline usa `fk_name` incorrecto

```python
# admin.py línea 23-27:
class RevisionDelegadoInline(NestedTabularInline):
    model = RevisionDelegado
    fk_name = "revision"  # ← El modelo tiene liquidacion, no revision!
```

Esto rompería el inline en el admin.

### 2.4 Issue: Infracción a la Inmutabilidad Financiera (CORREGIDO)

El contexto anterior decía que `Revision` tenía las FK. **CORREGIDO:** El modelo Python `Liquidacion` (en `revision.py`) tiene las FK a `IGV`, `UIT`, `DerechoMinimo`, `PorcentajeRevision`. El problema es el mismo: si se cambian los valores de configuración, todas las liquidaciones referenciadas se verían afectadas.

### 2.5 Issue: M2M en `PorcentajeRevision` no existe en DB

```python
# liquidacion.py:
especialidades = models.ManyToManyField("Especialidad", ...)  # ← M2M existe

# migration 0001:
# NO hay tabla pivot para this M2M!
```

La tabla `porcentajeliquidacion` en DB no tiene la relación M2M.

### 2.6 Issue: Falta campo `concepto` dinámico

La lógica de negocio requiere conceptos dinámicos:
- `Derecho Inicial` (Revisión 1)
- `Subsanación gratuita` (Revisión 2, Ley 29090)
- `Reingreso Sanitarias`, `Reingreso Estructuras`, etc. (Revisión 3+)

**No existe** campo `concepto` en `Liquidacion` (DB shell) ni en el modelo Python `Liquidacion`.

### 2.7 Issue: `liquidacion_previa` en el modelo Python `Liquidacion`

El self-FK `liquidacion_previa` está en el modelo Python `Liquidacion` (no en `Revision` como decía el contexto anterior). Esto es correcto según el modelo Python, pero hay que verificar si existe en DB.

---

## 3. Modelo DB Recomendado (basado en la lógica de negocio)

### 3.1 Principios de Diseño

1. **Inmutabilidad financiera:** Los valores de IGV, UIT, derecho mínimo, porcentaje se **COPIAN** como campos `Decimal` en `Liquidacion` al momento de creación. Las FK a tablas de config son solo para validación/referencia en el momento de creación.

2. **Concepto dinámico:** Cada `Liquidacion` tiene un `concepto` texto que describe el tipo de instancia.

3. **Separación Liquidacion ↔ Revision técnica:** `Liquidacion` = financials, `Revision` = detalles técnicos por especialidad (delegado, observaciones, resultado).

4. **`numero` en `Liquidacion`:** El número secuencial es por instancia de pago, no por revisión técnica.

5. **`liquidacion_previa` en `Liquidacion`:** Para encadenar instancias de pago (Rev 1 → Rev 2 → Rev 3+).

### 3.2 Esquema Recomendado

```
┌─────────────────────────────────────────────────────────────┐
│ LIQUIDACION (tabla principal financiera)                   │
│─────────────────────────────────────────────────────────────│
│ id: UUID (PK)                                               │
│ proyecto_id: FK → Proyecto                                 │
│ numero: PositiveInteger (único por proyecto)                │
│ concepto: CharField(100)  # "Derecho Inicial", etc.          │
│                                                          │
│ # ── Valores COPIADOS al momento de creación ──           │
│ igv_porcentaje: Decimal(6,4)  # copiado de IGV config      │
│ igv_config_id: FK → IGV (referencia, no usar después)     │
│ uit_valor: Decimal(12,2)  # copiado de UIT config          │
│ uit_config_id: FK → UIT                                   │
│ derecho_minimo_porcentaje: Decimal(6,4)                     │
│ derecho_minimo_config_id: FK → DerechoMinimo              │
│ porcentaje_revision_porcentaje: Decimal(6,4)               │
│ porcentaje_revision_config_id: FK → PorcentajeRevision      │
│                                                          │
│ # ── Metadata ──                                           │
│ estado: CharField(20)  # PENDIENTE/APROBADA/REINGRESADA    │
│ liquidacion_previa_id: FK → Liquidacion (nullable)         │
│ created_at, updated_at                                     │
│ history: HistoricalRecords                               │
└─────────────────────────────────────────────────────────────┘
          │ 1:N
          ▼
┌─────────────────────────────────────────────────────────────┐
│ REVISION (detalles técnicos por especialidad)              │
│─────────────────────────────────────────────────────────────│
│ id: UUID (PK)                                               │
│ liquidacion_id: FK → Liquidacion                            │
│ numero: PositiveInteger (secuencial por liquidacion)       │
│ especialidad_id: FK → Especialidad                          │
│ delegado_id: FK → Delegado                                  │
│ resultado: CharField(20)  # APROBADO/RECHAZADO/OBSERVADO   │
│ observaciones: TextField (nullable)                        │
│ fecha_resultado: DateTimeField (nullable)                   │
│ created_at, updated_at                                     │
│ history: HistoricalRecords                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Cambios Recomendados por Fase

### Fase 1: Corrección de bugs blocking (críticos)

| # | Cambio | Riesgo | Archivos |
|---|--------|--------|----------|
| 1.1 | Renombrar `PorcentajeRevision` → `PorcentajeLiquidacion` en `liquidacion.py` | Medio — requiere migration | `domain/models/liquidacion.py` |
| 1.2 | Corregir FK `liquidacion` → `revision` en `RevisionDelegado` | Alto — rompe existing data | `domain/models/revision_delegado.py` |
| 1.3 | Corregir `fk_name` en `RevisionDelegadoInline` admin | Bajo | `admin.py` |

### Fase 2: Inmunidad financiera

| # | Cambio | Riesgo | Archivos |
|---|--------|--------|----------|
| 2.1 | Agregar campos `igv_porcentaje`, `uit_valor`, `derecho_minimo_porcentaje`, `porcentaje_revision_porcentaje` a `Liquidacion` | Alto — nuevo schema | `domain/models/revision.py` |
| 2.2 | Hacer `igv`, `uit`, etc. nullable después de copiar valores | Medio | Migration |

### Fase 3: Agregar `concepto` y limpiar modelo

| # | Cambio | Riesgo | Archivos |
|---|--------|--------|----------|
| 3.1 | Agregar campo `concepto` a `Liquidacion` | Bajo | `domain/models/revision.py` |
| 3.2 | Mover `numero` de `Liquidacion` Python a `Liquidacion` DB | Alto | `domain/models/revision.py`, `admin.py` |

### Fase 4: Separación Revision técnica

| # | Cambio | Riesgo | Archivos |
|---|--------|--------|----------|
| 4.1 | Agregar `especialidad` FK a `Revision` | Medio | `domain/models/revision.py` |
| 4.2 | Crear tabla M2M para `PorcentajeRevision.especialidades` | Medio | Nueva migration |

---

## 5. Riesgos de Migración

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Renombrar `PorcentajeRevision` pierde sync con DB | Crítico | Verificar qué existe en DB vs Python |
| Corregir FK en `RevisionDelegado` pierde datos | Alto | Crear data migration para renombrar columna |
| Copiar valores FK a campos Decimal requiere cálculos | Alto | Implementar en `save()` o signal |
| `fk_name` en admin no coincide con modelo | Alto | Corregir admin.py primero |

---

## 6. Artifactos Creados/Actualizados

- `context/modelado-db-liquidaciones-cam.md` — Este documento (versión corregida)
- Engram: `liquidaciones/exploration-corrections` — Hallazgos técnicos guardados

---

## 7. Siguiente Paso Recomendado

`/sdd-propose` para crear propuesta formal de refactor con:
- Fase 1: Fix naming mismatches (`PorcentajeRevision`, `RevisionDelegado.liquidacion`)
- Fase 2: Implementar inmutabilidad financiera con campos copiados
- Fase 3: Agregar `concepto` y renombrar `numero`
- Fase 4: Separar `Revision` técnica de `Liquidacion` financiera
