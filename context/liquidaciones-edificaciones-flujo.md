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

### 2.2 Relaciones

- `LiquidacionEdificaciones.revisiones` es **M2M** a `EdificacionesRevision`.
- Las especialidades disponibles se obtienen de `EdificacionesRevision` vigente (no existe tabla `EspecialidadesHabilitadasEdificaciones`).

### 2.3 Atributos por Modelo

| Modelo | Atributos clave |
|--------|----------------|
| `EdificacionesRevision` (tarifa) | `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit` — pertenecen a la tarifa/revisión, NO a un bloque global |
| `LiquidacionEdificaciones` | Referencia M2M a revisiones seleccionadas |

### 2.4 Creación de Instancias

- `LiquidacionEdificaciones` se crea **junto con** `LiquidacionGeneral` desde endpoints específicos.
- **NO** por pasos separados manuales.

---

## 3. Reglas Financieras y de Revisión

### 3.1 Variables Financieras (IGV/UIT)

- IGV/UIT se **muestran** al formulario por endpoint de finanzas (solo para mostrar).
- Al crear liquidación, el backend los **resuelve internamente** con el service de finanzas vigente.
- **El frontend NO envía IGV/UIT.**

### 3.2 Primera Revisión

- Según `docs/tarifas.md`: **0.15% del valor de obra declarada**.

### 3.3 Nueva Revisión

- Se crea desde `liquidacion_previa_id`.
- Se calcula `numero_revision = previa + 1`.
- **Máximo 7 revisiones** (1 primera + 6 nuevas).

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

- Identificado por: `cip`, `dni`, `cap` (**NO** `capitulo`).
- `cip` y `dni` son únicos.
- `cap` máximo **6 dígitos**.

### 4.5 Liquidaciones Edificaciones (NO CRUD genérico)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/liquidaciones/edificaciones/primera-revision` | Crear primera revisión |
| `GET` | `/liquidaciones/edificaciones/nueva-revision` | Preparar formulario por liquidación previa |
| `POST` | `/liquidaciones/edificaciones/nueva-revision` | Crear nueva revisión |
| `GET` | `/liquidaciones/edificaciones/{id}` | Snapshot/detalle de liquidación |

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
    "valor_proyecto": 500000.00,
    "expediente": "EXP-2026-001",
    "observacion": "Observación opcional"
  }
}
```

> **Nota**: NO se envía `liquidacion_previa_id` en primera revisión.

### 6.2 Nueva Revisión

```json
{
  "liquidacion": {
    "liquidacion_previa_id": 123,
    "valor_proyecto": 500000.00,
    "expediente": "EXP-2026-002",
    "observacion": "Observación opcional"
  },
  "edificaciones": {
    "revisiones": [1, 2, 3]
  }
}
```

> **Nota**: NO se envía IGV/UIT desde frontend.

---

## 7. JSON de Respuesta/Snapshot Correcto

### 7.1 Estructura del Snapshot

```json
{
  "liquidacion": {
    "id": 123,
    "numero_liquidacion": "LIQ-EDIF-2026-00001",
    "estado": "PENDIENTE",
    "fecha_creacion": "2026-01-15T10:30:00Z",
    "proyecto": {
      "id": 456,
      "public_id": "PROY-2026-00001",
      "nombre": "Edificio Residencial Los Andes",
      "direccion": "Av. Principal 123, Lima",
      "valor_proyecto": 500000.00,
      "entidad": {
        "id": 789,
        "tipo": "INSTITUCION",
        "nombre": "Constructora Los Andes S.A.C.",
        "ruc": "20456789012"
      },
      "proyectista": {
        "id": 101,
        "cip": "CIP-12345",
        "dni": "12345678",
        "cap": "123456",
        "nombres": "Juan",
        "apellidos": "Pérez García"
      }
    },
    "expediente": "EXP-2026-001",
    "observacion": "Observación opcional"
  },
  "edificaciones": {
    "revisiones": [
      {
        "id": 1,
        "numero_revision": 1,
        "especialidad": "ARQUITECTURA",
        "tarifa": {
          "id": 10,
          "derecho_minimo": 100.00,
          "derecho_maximo": 5000.00,
          "porcentaje_minimo_uit": 0.15
        },
        "monto_base": 750.00,
        "cobra": true
      },
      {
        "id": 2,
        "numero_revision": 2,
        "especialidad": "ESTRUCTURAS",
        "tarifa": {
          "id": 11,
          "derecho_minimo": 150.00,
          "derecho_maximo": 6000.00,
          "porcentaje_minimo_uit": 0.15
        },
        "monto_base": 0,
        "cobra": false
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
- `edificaciones` contiene `revisiones[]`.
- Cada revisión contiene su `tarifa` con `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit`.
- `totales` contiene: subtotal, IGV, total, liquidación total, total a pagar.
- Esta estructura se guarda en `LiquidacionSnapshot.data` **por ahora** porque campos finales pueden cambiar.

---

## 8. Preguntas Pendientes

| # | Pregunta | Estado |
|---|----------|--------|
| 1 | Nombre exacto de endpoints de nueva revisión | ⏳ Pendiente |
| 2 | Definir shape final de snapshot con cliente | ⏳ Pendiente |
| 3 | Confirmar valores enum exactos de clasificación | ⏳ Pendiente |
| 4 | Definir formato/algoritmo de `public_id` de Proyecto | ⏳ Pendiente |

---

## 9. Notas Importantes de Estilo

### 9.1 Orden de Objetos

Mantener objetos ordenados por pertenencia:

| Parent | Child | Ejemplo |
|--------|-------|---------|
| `liquidacion` | `proyecto` | `liquidacion.proyecto` |
| `proyecto` | `entidad`, `proyectista` | `proyecto.entidad`, `proyecto.proyectista` |
| `tarifa` / `revision` | `derecho_minimo` | `revision.tarifa.derecho_minimo` |

### 9.2 Datos

- **NO mezclar datos globales inventados**.
- Usar datos coherentes con el dominio.
- Los ejemplos JSON son ilustrativos y bien ordenados.

---

## 10. Referencias

- Contrato de arquitectura: `contract/django-app-architecture-contract.md`
- Tarifas: `docs/tarifas.md`
- Helper core: `esta_vigente` para validaciones de periodo

---

*Documento generado: 2026-06-16*
