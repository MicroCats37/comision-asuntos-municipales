# SDD Exploration: Nueva Sección "Recibo de Honorario"

## Metadata

- **Change name**: `recibo-honorario-seccion`
- **Project**: `comision-asuntos-municipales`
- **Explored at**: 2026-08-14
- **Status**: success

---

## 1. Modelo ReciboHonorarioDelegado

### Ubicación
`backend/modules/finanzas/domain/models/recibo_honorario.py:26`

### Campos exactos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | PK heredado de BaseModel |
| `liquidacion_delegado` | FK OneToOne → `LiquidacionDelegado` | Asignación liquidación+delegado+especialidad. `on_delete=PROTECT` |
| `sub_total` | Decimal(12,2) | Snapshot del sub_total de LiquidacionGeneral |
| `imp_bruto` | Decimal(12,2) | Importe bruto (subtotal del LiquidacionPorcentajeObraDetalle) |
| `renta_cip` | Decimal(12,2) | `imp_bruto × 0.25` |
| `aporte_codemu` | Decimal(12,2) | `imp_bruto × 0.05` |
| `fondo_comun` | Decimal(12,2) | `imp_bruto × 0.10` |
| `neto_honorario` | Decimal(12,2) | `imp_bruto − renta_cip − aporte_codemu − fondo_comun` |
| `honorario` | Decimal(12,2) | Igual a `neto_honorario` |
| `created_at` | DateTime | Auditoría |
| `updated_at` | DateTime | Auditoría |

### Rates fijos (constantes de módulo)
```python
TASA_RENTA_CIP = Decimal("0.25")     # 25%
TASA_APORTE_CODEMU = Decimal("0.05") # 5%
TASA_FONDO_COMUN = Decimal("0.10")    # 10%
```

### Relaciones
- **OneToOne** con `LiquidacionDelegado` (`related_name="recibo_honorario"`)
- `LiquidacionDelegado` tiene FK a `LiquidacionGeneral`, `Delegado`, `EspecialidadRevision`

### Constraints
- Unique constraint implícita por OneToOne: un recibo por `liquidacion_delegado`
- `ordering = ["-created_at"]`

### Estado actual del backend
**Ya existe la API completa:**
- `backend/modules/finanzas/presentation/controllers/finanzas_controller.py:51-67` — `POST /finanzas/recibos-honorarios` (crear)
- `backend/modules/finanzas/presentation/controllers/finanzas_controller.py:69-97` — `GET /finanzas/recibos-honorarios` (listar con paginación y filtros `delegado_id`, `liquidacion_id`)

**Schemas ya definidos** (`backend/modules/finanzas/presentation/schemas/finanzas_schemas.py`):
- `ReciboHonorarioCrearIn` — solo `liquidacion_delegado_id: UUID`
- `ReciboHonorarioDelegadoOut` — con todos los montos + `liquidacion_general`, `delegado`, `especialidad` anidados

**Servicios existentes:**
- `FinanzasOrchestrator.crear_recibo_proceso()` — resuelve `imp_bruto` desde el detalle de la liquidación según tipo
- `FinanzasOrchestrator.listar_recibos_proceso()` — paginación y filtros
- `FinanzasCoreService.crear_recibo()` — `get_or_create` idempotente
- `ReciboHonorarioFlujo` — flujo transaccional con `@transaction.atomic`

**Tests existentes:**
- `backend/modules/finanzas/tests/integration/test_recibo_honorario.py` — tests de cálculo, creación, y paginación (modelo + presenter)

---

## 2. LiquidacionDelegado

### Ubicación
`backend/modules/liquidaciones/domain/models/delegado.py:122`

### Campos
| Campo | Tipo |
|-------|------|
| `liquidacion` | FK → `LiquidacionGeneral` |
| `delegado` | FK → `Delegado` |
| `especialidad_revision` | FK → `EspecialidadRevision` |
| `periodo` | CharField (nullable) |
| `dictamen_revision` | CharField (choices) |
| `fecha_presentacion` | DateField (nullable) |
| `fecha_revision` | DateField (nullable) |

### Unique constraint
```python
UniqueConstraint(fields=["liquidacion", "delegado"], name="unique_liquidacion_delegado")
```

### Relación con LiquidacionGeneral y Delegado
```
LiquidacionDelegado
  ├── liquidacion FK → LiquidacionGeneral
  ├── delegado FK → Delegado
  │     └── perfil_ingeniero FK → PerfilIngeniero
  └── especialidad_revision FK → EspecialidadRevision
```

### API de LiquidacionDelegado
`backend/modules/liquidaciones/presentation/controllers/liquidacion_delegado_controller.py:36`

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/liquidaciones/delegados/vigentes` | GET | Lista delegados vigentes filtrados por `municipalidad_id`, `tipo_liquidacion` |
| `/liquidaciones/delegados-asignaciones` | GET | Lista asignaciones con paginación. Filtros: `cip`, `liquidacion_id` |
| `/liquidaciones/{liquidacion_id}/delegados` | PATCH | Batch create/update/delete |

**El endpoint `GET /liquidaciones/delegados-asignaciones`** es el más relevante para el buscador del modal de creación de recibo. Soporta filtro por `cip` y paginación.

---

## 3. Patrón Modal Buscador (Nueva Revisión)

### Archivo de referencia
`frontend/src/features/liquidaciones/components/forms/SeleccionarPreviaModal.tsx:31`

### Estructura exacta

**Props** (`SeleccionarPreviaModalProps`):
```typescript
interface SeleccionarPreviaModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tiposPermitidos?: string[];       // códigos de tipo_liquidacion permitidos
  title?: string;
  description?: string;
  onSelect: (previa: LiquidacionGeneralItem) => void;
}
```

**Comportamiento:**
1. **Input de búsqueda**: Documento (RUC/DNI), 8 o 11 dígitos
2. **Validación**: `isDocumentoValid = documento.trim().length === 8 || documento.trim().length === 11`
3. **Búsqueda**: `useLiquidacionesGenerales({ documento, soloUltimasRevisiones: true, enabled: searched && open })`
4. **Resultados**: Lista de cards con datos de proyecto y tipo de liquidación
5. **Selección**: Click en card → `onSelect(item)` → cierra modal implícitamente
6. **Paginación**: `Pagination` component al pie si `total > pageSize`

**Componentes usados:**
- `GenericModal` (componente base genérico de modal)
- `Pagination` de `@/components/genericPagination/Pagination`
- `useLiquidacionesGenerales` hook

**Integración en vista** (`LiquidacionesInspeccionObraView.tsx`):
```typescript
<SeleccionarPreviaModal
  open={showPreviaModal}
  onOpenChange={setShowPreviaModal}
  tiposPermitidos={["INSPECCION_OBRA"]}
  title="Nueva Revisión"
  description="Busca la liquidación previa para crear una nueva revisión"
  onSelect={(previa) => { /* handler */ }}
/>
```

### Patrón clave para replicar
Para el modal de **Recibo de Honorario**, el buscador debe buscar **LiquidacionDelegado** (asignaciones), no LiquidacionGeneral. El endpoint `/liquidaciones/delegados-asignaciones` es el correcto, con filtro `cip` para buscar por número de CIP del delegado.

---

## 4. Sidebar

### Archivo
`frontend/src/components-app/sidebar/ProtectedSidebar.tsx:87`

### Grupos actuales
```typescript
const liquidacionesGroup = {
  title: "Liquidación",
  icon: FileText,
  children: [/* 6 items de tipos de liquidación */]
};

const operativaGroup = {
  title: "Operativa",
  icon: Users,
  children: [Delegados, Inspectores]
};

const finanzasGroup = {
  title: "Finanzas",
  icon: DollarSign,
  children: [Tarifas]
};
```

### Cómo agregar "Recibo de Honorario"
Se agregaría como nuevo ítem dentro del grupo `finanzasGroup`:

```typescript
const finanzasGroup = {
  title: "Finanzas",
  icon: DollarSign,
  children: [
    { title: "Tarifas", href: "/liquidaciones/finanzas" },
    { title: "Recibo de Honorario", href: "/liquidaciones/recibos-honorario" }, // NUEVO
  ],
};
```

**Icono sugerido**: `Receipt` de lucide-react (o `FileText` que ya se usa)

### Ruta
La ruta sería `/liquidaciones/recibos-honorario` siguiendo el patrón de `/liquidaciones/finanzas`.

---

## 5. Patrón de Vista con Tabla (Liquidaciones)

### Estructura de archivos
```
frontend/src/features/liquidaciones/
  ├── views/
  │   ├── LiquidacionesEdificacionesView.tsx
  │   ├── LiquidacionesHabilitacionUrbanaView.tsx
  │   └── ...
  ├── hooks/
  │   └── useLiquidacionesGenerales.ts  (hook genérico de listado)
  └── components/
      └── forms/
          └── SeleccionarPreviaModal.tsx
```

### Hook de listado (`useLiquidacionesGenerales`)
- Props: `page`, `pageSize`, `documento`, `tipo`, `enabled`, `soloUltimasRevisiones`
- Retorna: `{ items, total, totalPages, pageSize, isLoading, isError, refetch }`

### Vista típica con filtros
1. Filtros en la parte superior (inputs para `documento`, `fecha`, etc.)
2. Tabla de resultados con columnas
3. Paginación al pie
4. Modal de creación/edición

---

## 6. API de Delegados para el Buscador

### Endpoint principal para el buscador
`GET /liquidaciones/delegados-asignaciones`

**Params:**
- `page: int` (default 1)
- `page_size: int` (default 10, max 100)
- `cip: Optional[str]` — filtro por CIP del delegado
- `liquidacion_id: Optional[UUID]` — filtro por liquidación

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [{
      "id": "uuid",
      "liquidacion": { "id": "uuid", "expediente": "...", ... },
      "delegado": { "id": "uuid", "nombre_completo": "...", "cip": "...", ... },
      "especialidad_revision": { "id": "uuid", "codigo": "...", "nombre": "...", ... },
      "periodo": "2026-01",
      "dictamen_revision": "...",
      "fecha_presentacion": "...",
      "fecha_revision": "..."
    }],
    "total": 100,
    "page": 1,
    "page_size": 10,
    "total_pages": 10
  }
}
```

Este endpoint es el que debe consumirse desde el modal buscador para seleccionar la `liquidacion_delegado` antes de crear el recibo.

---

## 7. Recomendación de Diseño

### Frontend

#### Página de consulta (`/liquidaciones/recibos-honorario`)
```
ReciboHonorariosView/
├── components/
│   ├── ReciboHonorariosTable.tsx      # Tabla con columnas: creado, delegado, liquidación, montos
│   ├── ReciboHonorariosFilters.tsx    # Filtros: CIP delegado, ID liquidación, rango de fechas
│   └── CrearReciboModal.tsx           # Modal de creación con buscador
├── hooks/
│   └── useReciboHonorarios.ts         # Hook de listado (GET /finanzas/recibos-honorarios)
└── index.tsx
```

#### Modal de creación
- **Trigger**: botón "Nuevo Recibo" en la vista
- **Buscador**: Similar a `SeleccionarPreviaModal` pero consume `/liquidaciones/delegados-asignaciones?cip={cip}`
- **Al seleccionar**: Muestra el detalle de la asignación (liquidación, delegado, especialidad)
- **Confirmación**: Botón "Crear Recibo" → `POST /finanzas/recibos-honorarios` con `{ liquidacion_delegado_id }`
- **Respuesta**: Muestra los montos calculados del recibo creado

### Backend

**Ya está implementado:**
- `POST /finanzas/recibos-honorarios` ✅
- `GET /finanzas/recibos-honorarios` ✅ (con filtros `delegado_id`, `liquidacion_id`)

**Posibles mejoras necesarias:**
- El endpoint de listado actual filtra por `delegado_id` y `liquidacion_id` a nivel UUID — verificar que sea suficiente para los filtros de la UI
- La creación (`crear_recibo_proceso`) internamente resuelve el `imp_bruto` desde el detalle de la liquidación — no requiere input adicional del usuario

---

## 8. Decisiones Pendientes (para el usuario)

1. **Ubicación en sidebar**: ¿"Recibo de Honorario" va dentro del grupo "Finanzas" (como está propuesto) o en otro grupo (ej. "Operativa")?

2. **Filtros de la vista de consulta**: ¿Qué filtros necesita la tabla? Los básicos serían:
   - Por delegado (CIP o nombre)
   - Por liquidación (ID o expediente)
   - Rango de fechas de creación
   
   ¿Se necesita algún filtro adicional?

3. **¿Crear desde la misma vista de delegación?**: Actualmente la `LiquidacionDelegado` no tiene botón de "Generar Recibo". ¿Se quiere un acceso directo desde la vista de delegados/liquidaciones-delegado, o solo desde la nueva sección?

4. **Restricción de creación**: Un `ReciboHonorario` es OneToOne con `LiquidacionDelegado`. Si ya existe un recibo para esa asignación, `crear_recibo` hace update (idempotente). ¿Se debe mostrar un mensaje de "Ya existe un recibo para esta asignación"?

5. **Permisos**: ¿Los recibos de honorario tienen restricciones de acceso por rol?

---

## 9. Riesgos

1. **Resolución de `imp_bruto`**: El `crear_recibo_proceso` resuelve `imp_bruto` internamente desde `LiquidacionPorcentajeObraDetalle` (para tipo EDIFICACION) o desde `liquidacion.sub_total` (para tipo M2). Si no hay detalle coincidente con la especialidad del delegado, el test indica que se levanta un error (comentado en el test como BLOCKED). Necesita verificarse el comportamiento real.

2. **Endpoint `/liquidaciones/delegados-asignaciones`**: No está claro si este endpoint requiere autenticación o tiene los permisos correctos. En el controller tiene `auth=None` (AllowAny).

3. **Modelo migration**: La migration `finanzas.0003_add_recibo_honorario_delegado` ya se aplicó, pero el test de integración para el endpoint HTTP está comentado (BLOCKED) porque requiere fixtures de `liquidaciones` que no están listos.

4. **Frontend: `useLiquidacionesGenerales`**: Este hook busca por `documento` (RUC/DNI de la entidad). Para el buscador de `LiquidacionDelegado` se necesita buscar por CIP del delegado. Hay que verificar que el hook genérico sirva o si se necesita un hook específico.

---

## 10. Archivos Clave

### Backend
| Archivo | Relevancia |
|---------|------------|
| `backend/modules/finanzas/domain/models/recibo_honorario.py` | Modelo `ReciboHonorarioDelegado` |
| `backend/modules/finanzas/presentation/controllers/finanzas_controller.py` | Endpoints HTTP existentes |
| `backend/modules/finanzas/presentation/schemas/finanzas_schemas.py` | Schemas `ReciboHonorarioCrearIn`, `ReciboHonorarioDelegadoOut` |
| `backend/modules/finanzas/domain/services/finanzas_orchestrator.py` | `crear_recibo_proceso`, `listar_recibos_proceso` |
| `backend/modules/finanzas/domain/services/finanzas_core_service.py` | `crear_recibo`, `list_recibos_paginated` |
| `backend/modules/liquidaciones/domain/models/delegado.py:122` | Modelo `LiquidacionDelegado` |
| `backend/modules/liquidaciones/presentation/controllers/liquidacion_delegado_controller.py` | Endpoint `delegados-asignaciones` |
| `backend/modules/finanzas/tests/integration/test_recibo_honorario.py` | Tests de modelo yAPI |

### Frontend
| Archivo | Relevancia |
|---------|------------|
| `frontend/src/components-app/sidebar/ProtectedSidebar.tsx` | Sidebar, dónde agregar el ítem |
| `frontend/src/features/liquidaciones/components/forms/SeleccionarPreviaModal.tsx` | Patrón de modal buscador a replicar |
| `frontend/src/features/liquidaciones/hooks/useLiquidacionesGenerales.ts` | Hook de listado genérico |

---

## 11. next_recommended

`sdd-propose` — luego `sdd-spec` → `sdd-design` → `sdd-tasks` → `sdd-apply`
