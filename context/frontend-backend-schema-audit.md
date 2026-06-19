# Frontend-Backend Schema Audit

**Fecha**: 2026-06-17
**Proyecto**: CIP/CAM

---

## Resumen Ejecutivo

| Endpoint | Estado | Problemas |
|----------|--------|-----------|
| `POST /liquidaciones/edificaciones/primera-revision` | ⚠️ | Wrapper `{ liquidacion: ... }` en frontend vs plano en backend |
| `GET /liquidaciones/edificaciones` | ✅ | Alineado |
| `GET /finanzas/variables/vigentes` | ✅ | Alineado |
| `POST /proyectos/` | ⚠️ | Campo `distrito` vs `distrito_id` en backend |
| `GET /proyectos/buscar/{public_id}` | ⚠️ | Mismo problema distrito |
| `POST /entidades/instituciones` | ✅ | Alineado |
| `POST /entidades/personas-naturales` | ✅ | Alineado |
| `GET /entidades/buscar?numero_documento=` | ⚠️ | No hay hook/uso en frontend |

---

## 1. `POST /liquidaciones/edificaciones/primera-revision`

### Backend Request Schema
```python
# liquidacion_edificaciones_schemas.py
class PrimeraRevisionLiquidacionIn(Schema):
    proyecto_public_id: str
    valor_proyecto: float
    expediente: Optional[str]
    observacion: Optional[str]
    revisiones_ids: list[int]
```

### Frontend Request (via useCrearLiquidacion)
```typescript
// El hook envuelve: { liquidacion: payload }
// Donde payload = PrimeraRevisionFormData
```

**ISSUE**: El frontend envía `{ liquidacion: { ... } }` pero el backend espera directamente los campos planos.

**Verificado en código**:
- `useCrearLiquidacion.ts` línea 36: `mutation.mutate({ liquidacion: payload })`
- Controller espera `PrimeraRevisionLiquidacionIn` directamente (sin wrapper)

### Backend Response Schema
```python
class LiquidacionSnapshotOut(Schema):
    liquidacion: LiquidacionOut
    edificaciones: EdificacionesOut
    totales: TotalesOut
```

### Frontend Response Schema
```typescript
// liquidacion.schema.ts
liquidacionSnapshotResponseSchema: {
  data: {
    liquidacion: { ... },
    edificaciones: { ... },
    totales: { ... }
  }
}
```

**Desalineación detectada**: El schema frontend espera `proyecto.nombre` pero el presenter retorna `proyecto.nombre` (OK). El backend usa `nombre` no `denominacion`.

---

## 2. `GET /liquidaciones/edificaciones`

### Backend Response Schema
```python
class LiquidacionEdificacionesListItemOut(Schema):
    id: str
    numero_revision: int
    expediente: str
    estado: str
    valor_proyecto: float
    proyecto_public_id: str
    proyecto_denominacion: str
    fecha_registro: str
    total: float
```

### Frontend TypeScript
```typescript
// liquidacion-edificaciones.ts
interface LiquidacionListItem {
  id: string;
  numero_revision: number;
  expediente: string;
  estado: string;
  valor_proyecto: number;
  proyecto_public_id: string;
  proyecto_denominacion: string;
  fecha_registro: string;
  total: number;
}
```

**Estado**: ✅ Alineado

---

## 3. `GET /finanzas/variables/vigentes`

### Backend Response Schema
```python
class VariablesFinancierasOut(Schema):
    igv_valor: float
    igv_periodo_inicio: str
    uit_valor: float
    uit_periodo_inicio: str
```

### Frontend Schema
```typescript
// useVariablesFinancieras.ts
finanzasVariablesResponseSchema = {
  success, data: {
    igv_valor, igv_periodo_inicio, uit_valor, uit_periodo_inicio
  }, error
}
```

**Estado**: ✅ Alineado

---

## 4. `POST /proyectos/`

### Backend Request Schema
```python
class ProyectoIn(Schema):
    denominacion: str
    direccion: Optional[str]
    distrito_id: Optional[int]  # <-- ID, no nombre
    proyectista_id: Optional[int]
    entidad_id: Optional[int]
```

### Frontend Input
```typescript
// proyecto.service.ts
proyectoInputSchema = {
  denominacion, direccion,
  distrito_id: number | undefined,  // OK
  proyectista_id, entidad_id
}
```

**ISSUE**: El frontend define `distrito_id` correctamente, pero en `handleSubmit` de `ProyectoFormModal` envía `distrito` (nombre) en lugar de `distrito_id`:

```typescript
// ProyectoFormModal.tsx líneas 72-77
const result = await crearMutation.mutateAsync({
  denominacion: data.denominacion,
  direccion: data.direccion || undefined,
  proyectista_id: proyectista?.id,
  entidad_id: entidad?.id,
  // FALTA: distrito_id - el form solo tiene 'distrito' como string
});
```

El schema del form solo tiene `distrito: string` (nombre), no `distrito_id`.

### Backend Response Schema
```python
class ProyectoOut(Schema):
    id: int
    public_id: str
    denominacion: str
    direccion: Optional[str]
    distrito: Optional[str]  # <-- Nombre del distrito, no ID
    proyectista_id: Optional[int]
    entidad_id: Optional[int]
```

### Frontend Response Schema
```typescript
// proyecto.service.ts
data: {
  id, public_id, denominacion, direccion: nullable,
  distrito: nullable,  // OK
  proyectista_id, entidad_id
}
```

**Estado**: ⚠️ Parcialmente alineado - el form no captura `distrito_id` correctamente.

---

## 5. `GET /proyectos/buscar/{public_id}`

### Backend Response Schema
Usa `ProyectoUpsertResponseOut` (mismo que crear).

### Frontend
```typescript
// proyecto.service.ts
buscarProyecto(publicId) → proyectoResponseSchema.parse(response.data)
```

**Estado**: ⚠️ Mismo problema que POST /proyectos/ con `distrito_id`.

---

## 6. `POST /entidades/instituciones`

### Backend Request Schema
```python
class EntidadInstitucionIn(Schema):
    tipo_documento: str = "RUC"
    numero_documento: str
    razon_social: str
    nombre_comercial: Optional[str]
    direccion: Optional[str]
    distrito_id: Optional[int]
```

### Frontend Request
```typescript
// useEntidad.ts / EntidadFormModal.tsx
payload = {
  tipo_documento: "RUC",
  numero_documento, razon_social, nombre_comercial, direccion
  // distrito_id no se envía (el form no lo tiene)
}
```

**ISSUE**: El backend acepta `distrito_id` pero el frontend no lo envía.

### Backend Response Schema
```python
class EntidadUpsertResponseOut(Schema):
    id, tipo_documento, numero_documento,
    razon_social, nombres, apellidos, nombre_completo,
    direccion, distrito_id, activo, creado
```

### Frontend Response Schema
```typescript
// useEntidad.ts
data: { id, tipo_documento, numero_documento, razon_social,
        nombres, apellidos, nombre_completo, direccion,
        distrito_id, activo, creado }
```

**Estado**: ✅ Tipos alineados (salvo distrito_id no enviado por frontend)

---

## 7. `POST /entidades/personas-naturales`

### Backend Request Schema
```python
class EntidadPersonaNaturalIn(Schema):
    tipo_documento: str = "DNI"
    numero_documento: str
    nombres: str
    apellidos: str
    direccion: Optional[str]
    distrito_id: Optional[int]
```

### Frontend Request
```typescript
// EntidadFormModal.tsx
payload = {
  tipo_documento: "DNI",
  numero_documento, nombres, apellidos, direccion
}
```

**ISSUE**: Mismo - `distrito_id` no enviado.

**Estado**: ⚠️ Igual que instituciones.

---

## 8. `GET /entidades/buscar?numero_documento=`

### Backend
- Endpoint existe: `GET /entidades/buscar?numero_documento=...`
- Retorna `ApiResponse[EntidadOut]`

### Frontend
- **No hay hook de frontend** para este endpoint.
- No se usa en ningún formulario.

**Estado**: ⚠️ Endpoint existe pero no se consume.

---

## Problemas Detectados

### CRITICAL

Ninguno que impida el funcionamiento básico.

### WARNING

1. **Liquidación primera-revision**: Frontend envía `{ liquidacion: payload }` pero el backend espera directamente `PrimeraRevisionLiquidacionIn`. Esto podría causar error 422 si el backend valida strict.

2. **ProyectoFormModal**: El campo `distrito` del form es un string (nombre) pero debería ser `distrito_id` (int) para enviar al backend.

3. **EntidadFormModal**: `distrito_id` no se captura ni se envía.

### SUGGESTION

1. Crear hook `useEntidadBuscar` para el endpoint `GET /entidades/buscar`.
2. Agregar campo `distrito_id` a los formularios de Entidad y Proyecto.

---

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `frontend/src/features/liquidaciones/components/LiquidacionEdificacionFormModal.tsx` | Corregido validación de submit sin proyecto usando `setError` + `useFormContext` |

---

## Verificaciones

- ✅ TypeScript (`npx tsc --noEmit`): Sin errores
- ✅ ModalShell no encontrado en formularios de liquidaciones/auth
- ✅ Sincronización `proyecto_public_id` verificada (línea 114-116)
- ✅ Bloqueo submit implementado con `setError` (línea 47-54)