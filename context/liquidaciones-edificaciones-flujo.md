# Liquidaciones Edificaciones — Arquitectura y Flujo

## 1. Resumen del Objetivo

Diseñar la lógica de negocio de Liquidaciones Edificaciones antes de implementar services/controllers.

> **Nota**: Usar contrato `contract/django-app-architecture-contract.md` cuando se implemente.

---

## 2. Decisiones de Modelo/Semántica Ya Tomadas

### 2.1 Estructura de Modelos

| Modelo | Rol |
|--------|-----|
| `LiquidacionGeneral` | Cabecera/base operacional de toda liquidación |
| `LiquidacionEdificaciones` | Cabecera específica de edificaciones; se crea junto con `LiquidacionGeneral` desde endpoints específicos |
| `EdificacionesRevision` | Revisión/tarifa por especialidad; tiene campo `habilitada` por periodo (usa helper core `esta_vigente`) |
| `EdificacionesEspecialidades` | Define el grupo de especialidades vigentes para Liquidaciones de Edificaciones en un período determinado |
| `Proyectista` | Vinculado a `PerfilIngeniero` (source of truth para CIP/habilitación); NO duplica campos CIP/DNI/CAP/Nombres/Apellidos |

### 2.2 Relaciones

- `LiquidacionEdificaciones.revisiones` es **M2M** a `EdificacionesRevision`.
- `EdificacionesRevision.especialidades` es **M2M** a `Especialidad` (no FK singular).
- `EdificacionesEspecialidades.especialidades` es **M2M** a `Especialidad`.
- `Proyectista` tiene FK a `PerfilIngeniero` y FK a `Especialidad` (NO campos duplicados de identidad).

### 2.3 Atributos por Modelo

| Modelo | Atributos clave |
|--------|----------------|
| `EdificacionesRevision` (tarifa) | `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit` — pertenecen a la tarifa/revisión, NO a un bloque global. Tiene M2M a `especialidades`. |
| `LiquidacionEdificaciones` | Referencia M2M a revisiones seleccionadas. `revisiones_ids` en API permite múltiples pero cálculo es 1 fila = 1 cargo. |
| `EdificacionesEspecialidades` | `periodo_inicio`, `periodo_fin` (nullable), M2M a `especialidades`. `habilitada` es propiedad computada (no almacenada). |
| `Proyectista` | FK `perfil_ingeniero`, FK `especialidad`, `descripcion` (opcional). Unique constraint en `(perfil_ingeniero, especialidad)`. |

### 2.4 Creación de Instancias

- `LiquidacionEdificaciones` se crea **junto con** `LiquidacionGeneral` desde endpoints específicos.
- **NO** por pasos separados manuales.

### 2.5 Proyectista — Modelo Limpio

`Proyectista` **NO almacena** campos duplicados de `PerfilIngeniero`:
- ❌ NO `nombres`, `apellidos`, `cip`, `dni`, `cap`
- ✅ SÍ `perfil_ingeniero = ForeignKey(PerfilIngeniero)` y `especialidad = ForeignKey(Especialidad)`
- Unique constraint en `(perfil_ingeniero, especialidad)`
- La identidad del ingeniero se obtiene via `PerfilIngeniero` referenciado

---

## 3. Reglas Financieras y de Revisión

### 3.1 Variables Financieras (IGV/UIT)

- IGV/UIT se **muestran** al formulario por endpoint de finanzas (solo para mostrar).
- Al crear liquidación, el backend los **resuelve internamente** con el service de finanzas vigente.
- **El frontend NO envía IGV/UIT.**

### 3.2 Primera Revisión

- Según `docs/tarifas.md`: **0.15% del valor de obra declarada**.
- **Validación de conjunto exacto de especialidades**:
  - Se busca `EdificacionesEspecialidades` vigente para la fecha actual.
  - Si no existe, se lanza `EspecialidadesGrupoNoEncontradoError`.
  - Las especialidades de las `EdificacionesRevision` seleccionadas deben coincidir **exactamente** con el conjunto del grupo vigente.
  - Si no coincide, se lanza `EspecialidadesSetInvalidoError`.

### 3.3 Nueva Revisión

- Se crea desde `liquidacion_previa_id`.
- Se calcula `numero_revision = previa + 1`.
- **Máximo 7 revisiones** (1 primera + 6 nuevas).
- **Exactamente UNA revisión por nueva revisión** (validación en schema y flujo).
  - Si se envían más de 1, se lanza `RevisionesMultipleError`.

### 3.4 Cobro por Número de Revisión

| Número | Cobra? |
|--------|--------|
| 1 | ✅ Sí |
| 2 | ❌ No |
| 3 | ✅ Sí |
| 4 | ❌ No |
| 5 | ✅ Sí |
| 6 | ❌ No |
| 7 | ✅ Sí |

### 3.5 Conservación de Revisiones

- Aunque una revisión (2,4,6) **no cobre**, debe conservar las `revisiones` seleccionadas en el M2M.

### 3.6 Cálculo: Una Revisión = Un Cargo

- **Una fila de `EdificacionesRevision` = una línea de cargo/cálculo**.
- NO se expande por cada especialidad de la revisión (aunque tenga M2M especialidades).
- El subtotal es la suma de derechos de cada revisión.

### 3.7 LiquidacionGeneral — Campos Operativos

- `valor_base_calculo`: Se setea con `valor_proyecto` si no se proporciona explícitamente.
- `sub_total`: Se llena después del cálculo de la liquidación.

---

## 4. Controllers/Endpoints Semánticamente Separados

### 4.1 Finanzas

- `GET /finanzas/variables-vigentes` — devuelve IGV/UIT **solo para mostrar** en formulario.

### 4.2 Entidades

- `POST /entidades` — crear/upsert entidad.
- Dos schemas de entrada:
  - **Institución**: datos de institución.
  - **Persona natural**: datos de persona.

### 4.3 Proyectos

- `POST /proyectos` — crear proyecto.
- El proyecto tendrá `public_id`.
- Se crea desde **modal** y devuelve:
  - `id` / `public_id`
  - Resumen completo del proyecto.

### 4.4 Proyectista

- Identificado por `(perfil_ingeniero_id, especialidad_id)`.
- Upsert: busca por `(perfil_ingeniero, especialidad)`, si no existe crea.
- **NO** requiere campos de identidad (CIP, DNI, etc.) — se obtienen de `PerfilIngeniero`.

### 4.5 Liquidaciones Edificaciones (NO CRUD genérico)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/liquidaciones/edificaciones/primera-revision` | Crear primera revisión |
| `GET` | `/liquidaciones/edificaciones/nueva-revision/formulario` | Preparar formulario por liquidación previa |
| `POST` | `/liquidaciones/edificaciones/nueva-revision` | Crear nueva revisión |
| `GET` | `/liquidaciones/edificaciones/{id}` | Snapshot/detalle de liquidación |
| `POST` | `/liquidaciones/edificaciones/cotizar/primera-revision` | Cotizar primera revisión (sin guardar) |
| `POST` | `/liquidaciones/edificaciones/cotizar/nueva-revision` | Cotizar nueva revisión (sin guardar) |
| `GET` | `/liquidaciones/edificaciones/revisiones-vigentes` | Lista de revisiones vigentes |
| `GET` | `/liquidaciones/edificaciones/snapshots` | Lista paginada de snapshots |

---

## 5. Flujo Frontend/Modal

```
┌──────────────────────────────────────────────────────────────┐
│                    FORMULARIO LIQUIDACIÓN                      │
│  1. Carga variables financieras (IGV/UIT) de finanzas        │
│  2. [Botón] Buscar/Crear Proyecto → Modal Proyecto           │
│                                                              │
│     ┌─────────────────────────────────────┐                  │
│     │         MODAL PROYECTO              │                  │
│     │  - Crear proyecto nuevo              │                  │
│     │  - Buscar proyecto existente        │                  │
│     │  - [Botón] Buscar/Crear Proyectista  │                  │
│     │                                       │                  │
│     │     ┌──────────────────────┐          │                  │
│     │     │ MODAL PROYECTISTA    │          │                  │
│     │     │ - Crear/Buscar       │          │                  │
│     │     │ (por perfil+esp)     │          │                  │
│     │     └──────────────────────┘          │                  │
│     │  - [Botón] Buscar/Crear Entidad       │                  │
│     │                                       │                  │
│     │     ┌──────────────────────┐          │                  │
│     │     │   MODAL ENTIDAD      │          │                  │
│     │     │ - Upsert institución │          │                  │
│     │     │ - Upsert persona     │          │                  │
│     │     └──────────────────────┘          │                  │
│     └─────────────────────────────────────┘                  │
│                                                              │
│  3. Seleccionar revisiones (especialidades)                   │
│  4. [Botón] Guardar → Backend calcula totales internamente  │
└──────────────────────────────────────────────────────────────┘
```

### 5.1 Notas del Flujo

- Entidad luego podrá integrarse con **RENIEC/SUNAT** o servicio externo por documento.
- El backend resuelve IGV/UIT internamente al guardar.

---

## 6. JSON de Entrada Correcto

### 6.1 Primera Revisión

```json
{
  "liquidacion": {
    "proyecto_public_id": "PROY-2026-00001",
    "municipalidad_id": "uuid-de-municipalidad",
    "tipo_tramite": "OBRA_NUEVA",
    "valor_proyecto": 500000.00,
    "observacion": "Observación opcional",
    "revisiones_ids": ["uuid-revision-1", "uuid-revision-2"],
    "proyectistas_ids": ["uuid-proyectista-1"]
  }
}
```

> **Nota**: NO se envía `liquidacion_previa_id` en primera revisión.
> Las revisiones seleccionadas deben representar exactamente el conjunto de especialidades del grupo vigente.

### 6.2 Nueva Revisión

```json
{
  "liquidacion_previa_id": "uuid-liquidacion-previa",
  "revisiones_ids": ["uuid-una-sola-revision"],
  "observacion": "Observación opcional",
  "proyectistas_ids": []
}
```

> **Nota**: `revisiones_ids` debe contener exactamente UNA revisión.
> Si `proyectistas_ids` está vacío, se heredan de la liquidación previa.

---

## 7. JSON de Respuesta/Snapshot Correcto

### 7.1 Estructura del Snapshot

```json
{
  "liquidacion": {
    "id": "uuid",
    "public_id": "LIQ-2026-00001",
    "numero_liquidacion": "LIQ-EDIF-1",
    "estado": "PENDIENTE",
    "fecha_creacion": "2026-01-15T10:30:00Z",
    "proyecto": {
      "id": "uuid",
      "public_id": "PROY-2026-00001",
      "nombre": "Edificio Residencial Los Andes",
      "direccion": "Av. Principal 123, Lima",
      "valor_proyecto": 500000.00,
      "entidad": {
        "id": "uuid",
        "tipo": "INSTITUCION",
        "nombre": "Constructora Los Andes S.A.C.",
        "ruc": "20456789012"
      }
    },
    "municipalidad": {
      "id": "uuid",
      "nombre": "Municipalidad de Lima",
      "codigo": "MUN-LIMA",
      "provincia": { "id": "uuid", "nombre": "Lima" },
      "distrito": { "id": "uuid", "nombre": "Lima" }
    },
    "observacion": "Observación opcional"
  },
  "edificaciones": {
    "public_id": "LIQ-EDIF-2026-00001",
    "numero_revision": 1,
    "tipo_tramite": "OBRA_NUEVA",
    "tramite_accion": "PRIMERA_REVISION",
    "proyectistas": [
      {
        "id": "uuid",
        "perfil_ingeniero_id": "uuid",
        "perfil_ingeniero_nombres": "Juan",
        "perfil_ingeniero_apellidos": "Pérez García",
        "perfil_ingeniero_cip": "CIP-12345",
        "especialidad_id": "uuid",
        "especialidad_nombre": "Arquitectura",
        "descripcion": null
      }
    ],
    "revisiones": [
      {
        "id": "uuid",
        "especialidad": "Arquitectura",
        "tarifa": {
          "id": "uuid",
          "derecho_minimo": "100.00",
          "derecho_maximo": "5000.00",
          "porcentaje_minimo_uit": "0.1500"
        },
        "monto_base": 750.00,
        "cobra": true,
        "derecho": 750.00
      },
      {
        "id": "uuid",
        "especialidad": "Estructuras",
        "tarifa": {
          "id": "uuid",
          "derecho_minimo": "150.00",
          "derecho_maximo": "6000.00",
          "porcentaje_minimo_uit": "0.1500"
        },
        "monto_base": 0,
        "cobra": false,
        "derecho": 0
      }
    ]
  },
  "totales": {
    "subtotal": 750.00,
    "igv": 142.50,
    "total": 892.50,
    "liquidacion_total": 892.50,
    "total_a_pagar": 892.50
  }
}
```

### 7.2 Notas Importantes

- `liquidacion` contiene `proyecto` **dentro** (anidado).
- `edificaciones` contiene `proyectistas` (vía M2M) y `revisiones[]`.
- Cada revisión contiene su `tarifa` con `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit`.
- `totales` contiene: subtotal, IGV, total, liquidación total, total a pagar.
- `proyectistas` ahora muestra datos del `PerfilIngeniero` referenciado, no campos duplicados.
- **Una revisión = una línea de cargo** (no se expande por especialidad aunque tenga M2M especialidades).

---

## 8. Errores de Validación

| Error | Excepción | Descripción |
|-------|-----------|-------------|
| Grupo de especialidades no vigente | `EspecialidadesGrupoNoEncontradoError` | No existe `EdificacionesEspecialidades` vigente para la fecha actual |
| Conjunto de especialidades no coincide | `EspecialidadesSetInvalidoError` | Las especialidades de las revisiones seleccionadas no coinciden exactamente con el grupo vigente |
| Múltiples revisiones en nueva revisión | `RevisionesMultipleError` | Se envió más de una revisión para nueva revisión (se requiere exactamente 1) |
| Revisión no habilitada | `RevisionNoHabilitadaError` | Una de las revisiones seleccionadas no está vigente/habilitada |

---

## 9. Referencias

- Contrato de arquitectura: `contract/django-app-architecture-contract.md`
- Tarifas: `docs/tarifas.md`
- Helper core: `esta_vigente` para validaciones de periodo

---

*Documento generado: 2026-06-24*
*Última actualización: Agregada documentación sobre modelo Proyectista limpio, validación de conjunto exacto de especialidades, y cálculo 1 revisión = 1 cargo.*
