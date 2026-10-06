# Contraste: Códigos de Especialidad del Ingeniero vs Especialidades de Tarifa

## Propósito

Este documento registra el análisis de la relación entre los **códigos de especialidad del CIP** (los que vienen del endpoint de colegiados) y las **especialidades de tarifa** del seed antiguo. Sirve como base para la decisión de separar la tabla `Especialidad` en dos conceptos (como en la versión alpha):
- `EspecialidadIngeniero` — la especialidad profesional del ingeniero (del CIP)
- `Especialidad` — la especialidad de cálculo/tarifa

## 1. Fuentes de datos analizadas

| Fuente | Archivo | Contenido |
|--------|---------|-----------|
| Seed de delegados (antiguo) | `backend/modules/liquidaciones/seeds/delegados_reales.json` | 95 delegados con su especialidad textual |
| Seed de colegiados (materializado del CIP) | `backend/modules/liquidaciones/seeds/colegiados_reales.json` | 95 ingenieros con `codigo_especialidad` y `capitulo` |
| Endpoint CIP | `http://172.16.93.83:9001/api/v1/colegiado/{cip}` | Devuelve `codEspecialidad` y `capitulo` |
| Seed de inspectores (alpha) | `Temp/opencode/cam-alpha/.../inspectores_reales.json` | 124 inspectores con categorías |

## 2. Códigos de especialidad encontrados (95 colegiados)

| Código CIP | Cant. | Capítulo (registro_id) | Capítulo nombre |
|------------|-------|------------------------|-----------------|
| `01` | 60 | 02 (CIVIL) o 09 (SANITARIA) | Civil / Sanitaria |
| `02` | 18 | 05 (MECÁNICA) | Ing. Mecánica y Mec. Eléctrica |
| `04` | 10 | 15 (ELÉCTRICA) | Ing. Eléctrica |
| `07` | 1 | 15 (ELÉCTRICA) | Ing. Eléctrica |
| `10` | 6 | 15 (ELÉCTRICA) | Ing. Eléctrica |

**Total: 95 ingenieros** | Capítulos: 02, 05, 09, 15

## 3. Especialidades del seed antiguo (delegados)

El seed de delegados usa estas especialidades textuales:

| Especialidad textual | Sufijo (tipo de liquidación) |
|----------------------|------------------------------|
| Ingeniería Civil | - Edificaciones / - Habilitaciones Urbanas |
| Ingeniería Sanitaria | - Edificaciones |
| Ingeniería Eléctrica y Mecánica Eléctrica | - Edificaciones |

## 4. Relación código → especialidad (contraste cruzado)

Cruzando cada delegado (por CIP) entre su `codigo_especialidad` (colegiados) y su especialidad textual (delegados):

| Código CIP | Especialidad textual (seed antiguo) | Especialidad "padre" |
|------------|------------------------------------|---------------------|
| `01` | Ingeniería Civil - Edificaciones | **Civil** |
| `01` | Ingeniería Civil - Habilitaciones Urbanas | **Civil** |
| `01` | ⚠️ Ingeniería Sanitaria - Edificaciones | **Sanitaria** |
| `02` | Ing. Eléctrica y Mecánica Eléctrica - Edificaciones | **Eléctrica/Mecánica** |
| `04` | Ing. Eléctrica y Mecánica Eléctrica - Edificaciones | **Eléctrica/Mecánica** |
| `07` | Ing. Eléctrica y Mecánica Eléctrica - Edificaciones | **Eléctrica/Mecánica** |
| `10` | Ing. Eléctrica y Mecánica Eléctrica - Edificaciones | **Eléctrica/Mecánica** |

## 5. Hallazgos clave

### 5.1 El código `01` mezcla Civil y Sanitaria

El código `01` tiene 60 ingenieros, pero esos 60 se reparten entre:
- Capítulo **02 = CIVIL** (42 ingenieros)
- Capítulo **09 = SANITARIA** (18 ingenieros)

**El código `01` NO distingue entre Civil y Sanitaria.** La distinción real está en el **capítulo**.

### 5.2 Cuatro códigos → una sola especialidad de tarifa

Los códigos `02`, `04`, `07`, `10` (35 ingenieros en total) **TODOS** mapean a la misma especialidad de tarifa: **Eléctrica/Mecánica**. El CIP los distingue (mecánica vs eléctrica), pero para el cálculo de tarifa son UNO solo.

### 5.3 La relación correcta es por CAPÍTULO, no por código

| Especialidad de tarifa | Capítulo | Códigos involucrados |
|------------------------|----------|---------------------|
| **Civil** | 02 | 01 (parcial) |
| **Sanitaria** | 09 | 01 (parcial) |
| **Eléctrica/Mecánica** | 05 y 15 | 02, 04, 07, 10 |

## 6. Implicaciones para la migración de tablas

Si se separa `EspecialidadIngeniero` (perfil) de `Especialidad` (tarifa):

### Para la tabla `EspecialidadIngeniero` (perfil del ingeniero):
- Se llena desde el CIP: `codigo_especialidad` + `capitulo`
- Debe distinguir por CAPÍTULO (02=civil, 09=sanitaria, 05=mecánica, 15=eléctrica)
- El código `01` solo NO basta — necesita el capítulo para saber si es civil o sanitaria

### Para la tabla `Especialidad` (tarifa/liquidación):
- Solo 3 registros: Civil, Sanitaria, Eléctrica/Mecánica
- Mapeo desde ingeniero:
  - Capítulo 02 → Civil
  - Capítulo 09 → Sanitaria
  - Capítulos 05 y 15 → Eléctrica/Mecánica

### Regla de mapeo propuesta (de ingeniero a tarifa):

```python
MAPEO_ESPECIALIDAD_INGENIERO_A_TARIFA = {
    "02": "CIVIL",        # capitulo 02
    "09": "SANITARIA",    # capitulo 09
    "05": "ELECTRICA",    # capitulo 05
    "15": "ELECTRICA",    # capitulo 15
}
```

## 7. Inspectores (por categoría)

Del seed `inspectores_reales.json` (alpha):

| Dato | Valor |
|------|-------|
| Total inspectores | 124 |
| Total registros | 138 |
| Con múltiples categorías | 2 (CIP 117690, 117696 — cat 3 y 4) |
| Con múltiples tipos (EDIF+HU) | 14 |
| Distribución | cat 4: 64, cat 3: 40, cat 2: 15, cat 1: 7 |

## 8. Decisiones pendientes

1. ¿El código `01` se distingue por capítulo (02=civil, 09=sanitaria) o se asigna todo a una sola?
2. ¿`EspecialidadIngeniero` se llena con los códigos tal cual del CIP, o se normaliza?
3. ¿La tabla `Especialidad` (tarifa) mantiene solo 3 registros (Civil, Sanitaria, Eléctrica/Mecánica)?
