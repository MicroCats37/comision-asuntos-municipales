# Exploration: Limpiar y Reseedear Datos

## 1. Inventario de Seeds (Management Commands)

### 1.1 Seeds de Entidades

| Comando | Qué crea | Fuente | Idempotente | Depende de |
|---------|----------|--------|-------------|------------|
| `load_ubigeo` | UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito | `utils/ubigeo_constants.py` | Sí (update_or_create) | Ninguno |
| `seed_municipalidades` | Municipalidad | `seeds/municipalidades.json` | Sí (update_or_create por codigo) | load_ubigeo (para cargar ubigeo primero, no obligatorio) |

### 1.2 Seeds de Finanzas

| Comando | Qué crea | Fuente | Idempotente | Depende de |
|---------|----------|--------|-------------|------------|
| `seed_finanzas` | UIT (histórico 2000-2026), IGV | `seeds/uit_historico.json`, `seeds/igv_default.json` | Sí (update_or_create por periodo_inicio) | Ninguno |

### 1.3 Seeds de Usuarios/Colegiados

| Comando | Qué crea | Fuente | Idempotente | Depende de |
|---------|----------|--------|-------------|------------|
| `seed_colegiados` (en `usuarios`) | PerfilIngeniero, Capitulo, EspecialidadIngeniero, IngenieroHabilitacion | `liquidaciones/seeds/colegiados_reales.json` | Sí (get_or_create por cip) | Ninguno |

### 1.4 Seeds de Liquidaciones

| Comando | Qué crea | Fuente | Idempotente | Depende de |
|---------|----------|--------|-------------|------------|
| `seed_tarifas` | TarifaLiquidacionBase, TarifaPorcentajeObra, TarifaPorMetroCuadrado, TarifaPorCategoriaVisitas, DerechoPorcentajeObra, DerechoPorMetroCuadrado | `seeds/tarifas_cam_2026.json` | Sí (update_or_create) | Ninguno (crea Especialidad si no existe) |
| `seed_tarifas_all` | TarifaLiquidacionBase + TarifaPorcentajeObra + ReglaTarifaEdificacion (edificación) + TarifaPorMetroCuadrado + ReglaTarifaLiquidacion (HU/MS/IV/Taludes) + TarifaPorCategoriaVisitas + ReglaTarifaInspeccionObra | `seeds/tarifas_all.json` | Sí | Requiere Especialidades ya creadas |
| `seed_tarifas_edificacion` | Idem seed_tarifas_all pero SOLO edificación. **BORRA** tarifas EDIFICACION existentes antes de crear | `seeds/tarifas_edificacion.json` | **NO** (borra y recrea EDIFICACION) | Especialidades (creadas por seed_colegiados o load_delegados_reales) |
| `seed_delegados` | Delegado, DelegadoMunicipalidad, DelegadoMunicipalidadPeriodo | `seeds/delegados_reales.json` | Sí (get_or_create) | seed_colegiados, seed_municipalidades |
| `load_delegados_reales` | **LEGACY/ROTO** — importa modelos antigos (MunicipalidadDelegado, PeriodoDelegado) que ya NO existen. Usa `seed_delegados` en su lugar | `seeds/delegados_reales.json` | N/A | Roto — no ejecutar |
| `seed_inspectores` | Inspector, InspectorTipoLiquidacion, InspectorAsignacionPeriodo | `seeds/inspectores_reales.json` | Sí (get_or_create) | seed_colegiados |
| `seed_real_all` | Orchestrator: ejecuta `load_ubigeo` → `load_delegados_reales` | N/A | N/A | Depende de sus sub-comandos |
| `cleanup_especialidad_duplicates` | Limpia Especialidad duplicadas por acentos | N/A | N/A | Ninguno |
| `build_colegiados_reales_json` | Genera `colegiados_reales.json` desde endpoint CIP | Endpoint CIP | N/A | delegationados_reales.json como input |

---

## 2. Estado Actual de la BD Dev

### 2.1 Modelos de Especialidades

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| EspecialidadRevision | **3** | Códigos: '01' (Civil), '02' (Sanitaria), '03' (Eléctrica/Mecánica). Nombres con encoding corrupto en terminal |
| EspecialidadIngeniero | **7** | Diferentes de EspecialidadRevision — código + capítulo como clave |
| Capitulo | **5** | Registros: 02 (Civil), 09 (Sanitaria), 05 (Mecánica y Mecánica Eléctrica), 15 (Eléctrica), 16 (Electrónica) |

### 2.2 Modelos de Usuarios

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| PerfilIngeniero | **195** | Contiene datos de identity + CIP |

### 2.3 Modelos de Entidades

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| UbigeoDepartamento | **25** | Completo |
| UbigeoProvincia | **196** | Completo |
| UbigeoDistrito | **1893** | Completo |
| Municipalidad | **89** | Solo L* (municipalidades distritales) |

### 2.4 Modelos de Finanzas

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| UIT | **27** | Histórico 2000-2026 |
| IGV | **1** | 18% |

### 2.5 Modelos de Delegados

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| Delegado | **95** | Todos tienen `especialidad_revision` asignada (ninguno NULL) |
| DelegadoMunicipalidad | **650** | Asignaciones municipio-delegado |
| LiquidacionDelegado | **3** | Solo 3 asignaciones de delegado a liquidación (problema: liquidaciones orphaned) |

### 2.6 Modelos de Inspectores

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| Inspector | **124** | Con PerfilIngeniero asociado |

### 2.7 Modelos de Tarifas

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| TarifaLiquidacionBase | **6** | Tipos: EDIFICACION, HABILITACION_URBANA, otras |
| TarifaPorcentajeObra | **3** | Detalle para tarifas porcentuales |
| TarifaPorMetroCuadrado | **0** | No existe aún |
| TarifaPorCategoriaVisitas | **0** | No existe aún |
| DerechoPorcentajeObra | **1** | 2026, pct_min=0.02 UIT |
| DerechoPorMetroCuadrado | **1** | 2026, min=1000, max=10000 |

### 2.8 Modelos de Liquidaciones

| Modelo | Cantidad | Observaciones |
|--------|----------|--------------|
| LiquidacionGeneral | **4** | Todas tipo EDIFICACION, estado=PENDIENTE |
| LiquidacionEdificacion | **4** | Detalle para las 4 LG — **correcto** |
| LiquidacionPorcentajeObra | **4** | **AISLADAS** — no están linked a ninguna LiquidacionGeneral via `liquidacion_porcentaje_obra` |
| LiquidacionHabilitacionUrbana | **0** | — |
| LiquidacionMecanicaSuelos | **0** | — |
| LiquidacionImpactoVial | **0** | — |
| LiquidacionTaludes | **0** | — |
| LiquidacionInspeccionObra | **0** | — |
| LiquidacionPorMetroCuadrado | **0** | — |
| LiquidacionPorCategoriaVisitas | **0** | — |

---

## 3. Inconsistencias Detectadas

### 3.1 CRÍTICA: Liquidaciones sin detalles de cálculo

**Problema**: Las 4 `LiquidacionGeneral` tienen `LiquidacionEdificacion` (detalle de tipo trámite), pero **NINGUNA** tiene `LiquidacionPorcentajeObra` (detalle de cálculo).

**Evidencia**:
```
LG ID=0f6ba1ab-f1d1-4244-8bd2-721a51e2e3c6
  -> Edificaciones: ID=b34da1de-fd60-493a-863c-14d4815182e3 numero=3
  -> LiquidacionPorcentajeObra: NONE  ← FALTA
```

Esto significa que las liquidaciones no tienen valores de proyecto, porcentajes aplicados ni cálculos de derecho.

### 3.2 CRÍTICA: LiquidacionPorcentajeObra huérfanas

**Problema**: Existen 4 registros `LiquidacionPorcentajeObra` en la BD, pero **NINGUNA** está vinculada a una `LiquidacionGeneral` a través de la relación `liquidacion_porcentaje_obra`.

**Evidencia**:
- `LiquidacionPorcentajeObra.objects.count() == 4`
- Pero al hacer `lg.liquidacion_porcentaje_obra` para cualquier LiquidacionGeneral, retorna `DoesNotExist`

**Causa probable**: Las liquidaciones se crearon sin invocar el cálculo de `LiquidacionPorcentajeObra`, o los detalles se borraron.

### 3.3 CRÍTICA: TarifaLiquidacionBase no tiene campo `especialidades`

**Problema**: Los seeds `seed_tarifas_all` y `seed_tarifas_edificacion` référencian `tarifa_base.especialidades.set(especialidades)` pero el modelo `TarifaLiquidacionBase` en esta BD **NO tiene** campo M2M `especialidades`.

**Evidencia**:
```
# En seed_tarifas_all.py línea 330:
tarifa_base.especialidades.set(especialidades)

# Pero TarifaLiquidacionBase._meta.get_fields() no incluye 'especialidades'
```

**Impacto**: Los seeds `seed_tarifas_all` y `seed_tarifas_edificacion` **FALLARÁN** si se ejecutan.

### 3.4 MEDIA: LiquidacionDelegado huérfanas

**Problema**: Solo 3 `LiquidacionDelegado` existen, pero hay 4 `LiquidacionGeneral` con 3 delegados asignados cada una (según `liquidacion_delegados.all()`).

**Evidencia**:
```
LiquidacionDelegado total: 3
LiquidacionGeneral total: 4
Pero LG 0f6ba1ab tiene 3 LiquidacionDelegado via M2M
```

Las 3 LiquidacionDelegado están linked a LG, pero no hay 4ta. Esto sugiere que la asignación de delegados no está completa.

### 3.5 BAJA: EspecialidadRevision con encoding corrupto en terminal

**Problema**: Los nombres de EspecialidadRevision se muestran con caracteres corruptos (`Ingenier�a Civil` en vez de `Ingeniería Civil`).

**No es problema de BD** — es issue de encoding en la terminal Windows/PowerShell. Los datos en la BD están correctos.

### 3.6 MEDIA: `load_delegados_reales` está obsoleto

**Problema**: El comando `load_delegados_reales` importa `MunicipalidadDelegado` y `PeriodoDelegado` que **ya no existen** en el modelo actual (fueron reemplazados por `DelegadoMunicipalidad` y `DelegadoMunicipalidadPeriodo`).

**Evidencia**: El archivo `load_delegados_reales.py` tiene comentario `[LEGACY — NO USAR]` en la línea 2.

**Acción**: No ejecutar este comando.

---

## 4. Análisis de Archivos de Datos Fuente (Seeds JSON)

### 4.1 Seeds que existen y están completos

| Archivo | Existe | Completo | Observaciones |
|---------|--------|----------|--------------|
| `seeds/tarifas_cam_2026.json` | ✅ | ✅ | 5 tarifas %, 2 M2, 4 visitas |
| `seeds/tarifas_all.json` | ✅ | ✅ | 4 edificación, 2 M2, 4 inspeccion |
| `seeds/tarifas_edificacion.json` | ✅ | ✅ | Solo edificación |
| `seeds/delegados_reales.json` | ✅ | ✅ | 95 delegados, 767 asignaciones, 100 municipalidades |
| `seeds/colegiados_reales.json` | ✅ | ✅ | 95 colegiados con datos completos |
| `seeds/inspectores_reales.json` | ✅ | ✅ | 124 inspectores |
| `seeds/municipalidades.json` | ✅ | ✅ | 89 municipalidades |
| `seeds/uit_historico.json` | ✅ | ✅ | 27 registros UIT |
| `seeds/igv_default.json` | ✅ | ✅ | 1 registro IGV |

### 4.2 Seeds que referencian campos/modelos inexistentes

**PROBLEMA**: `seed_tarifas_all.py` y `seed_tarifas_edificacion.py` référencian:
1. `tarifa_base.especialidades.set(especialidades)` — el campo M2M `especialidades` no existe en `TarifaLiquidacionBase`
2. `ReglaTarifaEdificacion` — puede no existir en el modelo actual
3. `ReglaTarifaLiquidacion` — puede no existir
4. `ReglaTarifaInspeccionObra` — puede no existir

### 4.3 Modelo de Tarifa actual en BD

```
TarifaLiquidacionBase fields:
  - id (UUID)
  - created_at, updated_at
  - periodo_inicio, periodo_fin
  - tipo_liquidacion (FK)

  // Relaciones a detalles:
  - detalle_m2 (OneToOne → TarifaPorMetroCuadrado)
  - detalle_visitas (OneToOne → TarifaPorCategoriaVisitas)
  - detalle_porcentual (OneToOne → TarifaPorcentajeObra)
  
  // NO tiene campo especialidades M2M
```

---

## 5. Orden de Reseed Recomendado

### 5.1 Secuencia Completa de Reseed

```
PASO 0: Limpieza de liquidaciones existentes
============================================
1. Eliminar todas las liquidaciones (porque el usuario quiere limpiar TODAS)
   - LiquidacionDelegado (3 registros)
   - LiquidacionPorcentajeObra (4 registros huérfanos)
   - LiquidacionEdificacion (4 registros)
   - LiquidacionGeneral (4 registros)

PASO 1: Datos base (sin dependencias)
======================================
2. seed_finanzas          → UIT + IGV (sin dependencias)
3. load_ubigeo           → Departamentos/Provincias/Distritos (sin dependencias)

PASO 2: Datos de usuarios y entidades
======================================
4. seed_municipalidades   → Municipalidades (necesita ubigeo cargado)

PASO 3: Colegiados y especialidades
=====================================
5. seed_colegiados        → PerfilIngeniero + Capitulo + EspecialidadIngeniero
   (necesita colegiados_reales.json — que depende de build_colegiados_reales_json)
   - Si colegiados_reales.json ya existe con los 95 registros, usar directo
   - Si no, ejecutar build_colegiados_reales_json primero

PASO 4: Delegados
==================
6. seed_delegados        → Delegado + DelegadoMunicipalidad + DelegadoMunicipalidadPeriodo
   (necesita seed_colegiados + seed_municipalidades)

PASO 5: Inspectores
====================
7. seed_inspectores       → Inspector + InspectorTipoLiquidacion + InspectorAsignacionPeriodo
   (necesita seed_colegiados)

PASO 6: Tarifas — ATENCIÓN
===========================
⚠️ PROBLEMA: seed_tarifas_all y seed_tarifas_edificacion usan campos que no existen
en el modelo actual de BD.

8. seed_tarifas          → Funciona correctamente con el modelo actual
   - Crea TarifaLiquidacionBase
   - Crea TarifaPorcentajeObra (sin FK especialidad)
   - Crea TarifaPorMetroCuadrado
   - Crea TarifaPorCategoriaVisitas
   - Crea DerechoPorcentajeObra
   - Crea DerechoPorMetroCuadrado

   ⚠️ NO USA el campo especialidades (que no existe)

   Para tarifas de EDIFICACION con especialidades:
   - seed_tarifas_all y seed_tarifas_edificacion FALLARÁN
   - Alternativa: usar seed_tarifas para crear solo las tarifas base
```

### 5.2 Comando de Limpieza Sugerido

```bash
# Desde backend/
python manage.py shell << 'EOF'
from modules.liquidaciones.domain.models import (
    LiquidacionGeneral, LiquidacionEdificacion, LiquidacionPorcentajeObra,
    LiquidacionDelegado, LiquidacionHabilitacionUrbana, LiquidacionMecanicaSuelos,
    LiquidacionImpactoVial, LiquidacionTaludes, LiquidacionInspeccionObra,
    LiquidacionPorMetroCuadrado, LiquidacionPorCategoriaVisitas,
)
# Borrar en orden correcto (detalles primero)
LiquidacionDelegado.objects.all().delete()
LiquidacionPorcentajeObra.objects.all().delete()
LiquidacionEdificacion.objects.all().delete()
LiquidacionGeneral.objects.all().delete()
print("Liquidaciones limpiadas")
EOF
```

---

## 6. Riesgos

### 6.1 Al limpiar liquidaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Perder datos de pruebas reales | Alto si las 4 liquidaciones son de prueba real | Confirmar con usuario antes de borrar |
| Perder asignaciones de delegados | Medio — LiquidacionDelegado solo tiene 3 registros | Regenerar después con seeds |
| Perder detalles de cálculo | Medio — LiquidacionPorcentajeObra están huérfanas de todas formas | No afectan si no se usaban |

### 6.2 Seeds que fallarían

| Seed | Fallo por | Solución |
|------|-----------|----------|
| `seed_tarifas_all` | Campo `especialidades` no existe en TarifaLiquidacionBase | Usar solo `seed_tarifas` que no usa ese campo |
| `seed_tarifas_edificacion` | Campo `especialidades` no existe + usa `ReglaTarifaEdificacion` que puede no existir | No ejecutar hasta que el modelo se actualice |
| `load_delegados_reales` | Modelo legacy importado ya no existe | No ejecutar — usar `seed_delegados` |
| `seed_real_all` | Llama a `load_delegados_reales` | No ejecutar hasta que se arregle |

### 6.3 Datos que se perderían al reseed completo

| Dato | Cantidad | Recuperable |
|------|----------|-------------|
| PerfilIngeniero (colegiados) | 195 | Sí — con seed_colegiados |
| Delegados | 95 | Sí — con seed_delegados |
| DelegadoMunicipalidad | 650 | Sí — con seed_delegados |
| Inspectores | 124 | Sí — con seed_inspectores |
| Liquidaciones | 4 | **NO** — si son de prueba,无所谓. Si son reales, confirmar primero |
| LiquidacionDelegado | 3 | **NO** — se regenera con liquidaciones nuevas |

---

## 7. Recomendación

### Para limpiar y reseedear correctamente:

1. **Confirmar con usuario** que las 4 liquidaciones existentes son de prueba y pueden borrarse
2. **Ejecutar limpieza** de liquidaciones
3. **Ejecutar seeds en orden**:
   - `seed_finanzas`
   - `load_ubigeo`
   - `seed_municipalidades`
   - `seed_colegiados`
   - `seed_delegados`
   - `seed_inspectores`
   - `seed_tarifas` (NO `seed_tarifas_all` ni `seed_tarifas_edificacion` — fallarían)

4. **NO ejecutar**: `load_delegados_reales`, `seed_real_all`, `seed_tarifas_all`, `seed_tarifas_edificacion`

5. **Post-seed**: Verificar que las tarifas de edificación se crearon correctamente (puede requerir actualizar el modelo `TarifaLiquidacionBase` para añadir el campo `especialidades` M2M)

---

## 8. Próximos Pasos

- `apply`: Ejecutar la limpieza de liquidaciones y el reseed en el orden correcto
- **Bloqueador**: Confirmar que las 4 liquidaciones existentes son de prueba
- **Bloqueador**: Decidir si se actualiza el modelo `TarifaLiquidacionBase` para añadir `especialidades` M2M (necesario para `seed_tarifas_all` y `seed_tarifas_edificacion`)
