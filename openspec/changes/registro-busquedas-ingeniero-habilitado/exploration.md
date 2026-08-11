# Exploration v2: Registro de Búsquedas de Ingeniero Habilitado (Alcance Total)

## Status

**success** — Exploration completa del alcance total de cambios para el registro de búsquedas de ingeniero habilitado, con mapa de schemas, cadena de flujo, y decisiones pendientes.

---

## Mapa de Schemas del Endpoint

### Schema de Respuesta HTTP

**`IngenieroHabilitadoOut`** — `backend/modules/usuarios/presentation/schemas/ingeniero_habilitado_schemas.py:9`

```python
class IngenieroHabilitadoOut(BaseSchema):
    cip: str = Field(..., description="Número de CIP (6 dígitos)")
    nombres: str = Field(..., description="Nombres completos")
    apellidos: str = Field(..., description="Apellidos completos")
    habilitado: bool = Field(..., description="True si condicion == '1'")
    capitulo: Optional[str] = Field(None, description="Descripción del capítulo profesional")
```

| Aspecto | Detalle |
|---------|---------|
| Hereda de | `BaseSchema` → `ninja.Schema` (Pydantic) |
| Cómo se autogenera | Django Ninja genera automáticamente el OpenAPI schema a partir del modelo Pydantic |
| `BaseSchema` config | `model_config = {"arbitrary_types_allowed": True}` + validador `sanitize_strings` que convierte strings vacíos en `None` |
| Campos de fecha | **No tiene campos de fecha en la respuesta** — `IngenieroHabilitadoOut` es un schema SIMPLIFICADO que solo expone `cip, nombres, apellidos, habilitado, capitulo` |
| Serialización de fechas | No aplica — este schema no expone fechas |

### Schema de Dominio

**`IngenieroHabilitadoResult`** — `backend/modules/usuarios/domain/schemas/ingeniero_habilitado_schemas.py:65`

```python
class IngenieroHabilitadoResult(BaseModel):  # Pydantic BaseModel
    cip: str
    paterno: str
    materno: str
    nombre1: str
    nombre2: Optional[str] = ""
    dni: str
    fechaNacimiento: Optional[date] = None  # <-- date, no datetime
    # ... más campos ...
    habilitado: bool
```

| Aspecto | Detalle |
|---------|---------|
| Tipo | `pydantic.BaseModel` (NO Django model — DTO puro) |
| Serialización `date` → `str` | Pydantic serializa `date` automáticamente a ISO 8601 string (`"YYYY-MM-DD"`), que es lo mismo que `str(date_obj)` — formato `"%Y-%m-%d"` |
| `fechaNacimiento` parsing | `datetime.strptime(data.fechaNacimiento, "%Y-%m-%d").date()` en `from_cip_data()` — asume que el CIP externo retorna `YYYY-MM-DD` |
| NO se persiste en BD | Es un DTO volátil, no toca la base de datos |

### Schema Intermedio (Raw del CIP)

**`CipColegiadoData`** — `backend/modules/usuarios/domain/schemas/ingeniero_habilitado_schemas.py:18`

```python
class CipColegiadoData(BaseModel):
    cip: str
    fechaNacimiento: Optional[str] = None  # <-- string, NO date (raw del API)
    condicion: str
    # ...
```

| Aspecto | Detalle |
|---------|---------|
| `fechaNacimiento` tipo | `str` (el string crudo del API externo) |
| `habilitado` property | `return self.condicion == "1"` — bool calculado, no persiste |

### Schema de Entrada (Endpoint)

El endpoint `GET /ingenieros/habilitados/{cip}` recibe únicamente:
- **`cip: str`** — path param en la URL, validado como string por Ninja
- **No hay query params de fecha** — la fecha se genera internamente en el servidor
- **No hay request body**

### Cadena de Serialización de Fechas (entrada → dominio → salida)

```
CIP API response (string "YYYY-MM-DD")
  → CipColegiadoData.fechaNacimiento: str
    → IngenieroHabilitadoResult.from_cip_data(): date (via datetime.strptime)
      → Presenter: Solo extrae cip, nombres, apellidos, habilitado, capitulo
        → IngenieroHabilitadoOut: SIN campo de fecha (schema simplificado)
          → HTTP response JSON: sin campo de fecha
```

**Nota: `IngenieroHabilitadoOut` NO incluye `fechaNacimiento`** — es un schema minimalista. Si el frontend necesita la fecha de nacimiento, hay que agregarla al presenter y al schema de salida.

---

## Configuración de Timezone

### Settings Django

**`backend/config/settings/base.py:111-113`**

```python
TIME_ZONE = "America/Lima"   # PET: UTC-5 sin DST
USE_TZ = True               # Django maneja TZ internamente
```

### Cómo se Guardan las Fechas

| Campo | Tipo | Cómo se Guarda | Timezone en BD |
|-------|------|---------------|----------------|
| `created_at` (TimestampedModel) | `DateTimeField` | `auto_now_add=True` | UTC (Django convierte) |
| `updated_at` (TimestampedModel) | `DateTimeField` | `auto_now=True` | UTC (Django convierte) |
| `fecha_nacimiento` (PerfilIngeniero) | `DateField` | Manual | **Naive** — `DateField` no tiene noción de TZ |

### Cómo se Serializan las Fechas en Schemas Pydantic

- `date` → Pydantic serializa automáticamente a ISO 8601 string (`"YYYY-MM-DD"`)
- `datetime` → ISO 8601 con TIME (`"YYYY-MM-DDTHH:MM:SS"`)
- **No hay timezone en la salida JSON** — Pydantic por defecto no incluye `Z` ni offset

### Helpers de Fecha Existentes

**`core/utils.py:114-131`** — `esta_vigente()` usa `timezone.localdate()`:

```python
def esta_vigente(periodo_inicio, periodo_fin, fecha=None):
    fecha = fecha or timezone.localdate()  # ← USA timezone.localdate()
    # ...
```

**`PerfilIngenieroCoreService`** (`perfil_ingeniero_core_service.py:9`) importa `django.utils.timezone` y usa `timezone.now()` para `_map_cip_data_to_perfil_fields`.

### Inercia de `date.today()` en el Proyecto

En `liquidaciones` se usa `date.today()` (naive, sin TZ) en varios lugares:
- `delegado_core_service.py:136`
- `delegado_orchestrator.py:154, 186, 228`
- `inspector_core_service.py:68`
- `inspector_orchestrator.py:155`

**Recomendación**: usar `timezone.localdate()` para el nuevo registro de búsqueda, para consistencia con `core/utils.py:esta_vigente()`.

---

## Cadena Completa del Flujo (con archivos y líneas)

### Paso 1 — Controller

**`backend/modules/usuarios/presentation/controllers/ingeniero_habilitado_controller.py:29-50`**

```python
@route.get("/habilitados/{cip}", response={200: ApiResponse[IngenieroHabilitadoOut]}, auth=None)
async def obtener_ingeniero_habilitado(self, cip: str):
    result = await self.orchestrator.obtener_ingeniero_habilitado(cip=cip)
    presented = IngenieroHabilitadoPresenter().present(result)
    return success_response(presented)
```

- **Firma**: `async def obtener_ingeniero_habilitado(self, cip: str) → dict`
- **Decorador**: `@route.get("/habilitados/{cip}")` — path param, no query params
- **Response schema**: `ApiResponse[IngenieroHabilitadoOut]` — `IngenieroHabilitadoOut` es el schema de respuesta
- **Auth**: `auth=None` — endpoint público

### Paso 2 — Orchestrator

**`backend/modules/usuarios/domain/services/orchestrators/ingeniero_habilitado_orchestrator.py:26-39`**

```python
async def obtener_ingeniero_habilitado(self, cip: str) -> IngenieroHabilitadoResult:
    return await self.flujo._proceso_obtener_ingeniero_habilitado(cip=cip)
```

- **Firma**: `async def obtener_ingeniero_habilitado(cip: str) → IngenieroHabilitadoResult`
- **Patrón**: Fachada thin — solo delega al flujo, sin lógica
- **Inyección**: `IngenieroHabilitadoFlujo` vía `__init__`

### Paso 3 — Flujo

**`backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py:35-79`**

```python
async def _proceso_obtener_ingeniero_habilitado(self, cip: str) -> IngenieroHabilitadoResult:
    normalized_cip = self._normalizar_cip(cip)              # línea 60
    if not normalized_cip:
        raise NotFoundError(f"CIP inválido: {cip}")       # línea 62-63
    try:
        raw_data = await sync_to_async(self._cip_client.get_colegiado)(normalized_cip)  # línea 67
    except CipServiceUnavailableError:
        raise                                             # línea 68-69
    if raw_data is None:
        raise CipNotFoundError(cip=normalized_cip)       # línea 72-73
    cip_data = CipColegiadoData(**raw_data)              # línea 76
    return IngenieroHabilitadoResult.from_cip_data(cip_data)  # línea 79
```

- **Validación de CIP inválido**: `_normalizar_cip` retorna `""` si no es válido → `NotFoundError`
- **Respuesta None del CIP**: `CipNotFoundError` (el CIP no existe en el servicio externo)
- **Inyección**: `ICipClient` + `PerfilIngenieroCoreService` (solo para `_normalizar_cip`)

### Paso 4 — Normalización de CIP

**`backend/modules/usuarios/domain/services/core/perfil_ingeniero_core_service.py:20-27`**

```python
def _normalizar_cip(self, cip: str) -> str:
    if not cip:
        return ""
    cip = str(cip).strip().replace('-', '').replace(' ', '')
    if not cip.isdigit():
        return ""
    return cip.zfill(6)[:6]
```

### Paso 5 — Cliente CIP (Servicio Externo)

**`backend/modules/usuarios/infrastructure/services.py:44-90`** (`RealCipClient`)

```python
BASE_URL = "http://172.16.93.83:9001/api/v1"
TIMEOUT = 10.0

def get_colegiado(self, cip: str) -> Optional[dict]:
    url = f"{self.base_url}/colegiado/{cip}"
    response = httpx.get(url, timeout=self.timeout)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        return None
    else:
        raise CipServiceUnavailableError(...)
```

- **URL**: `http://172.16.93.83:9001/api/v1/colegiado/{cip}`
- **Timeout**: 10 segundos
- **404**: retorna `None` (no existe el CIP)
- **Otro error**: `CipServiceUnavailableError`
- **Simulador**: `CipClientSimulator` retorna dict mockeado para CIPs `000001`, `000002`, `000003`

### Paso 6 — Presenter

**`backend/modules/usuarios/presentation/presenters/ingeniero_habilitado_presenter.py:49-77`**

```python
def present(result: IngenieroHabilitadoResult) -> IngenieroHabilitadoOut:
    capitulo_desc = result.capitulo.descripcion if ... else None
    return IngenieroHabilitadoOut(
        cip=result.cip,
        nombres=self._build_nombres(result.nombre1, result.nombre2),
        apellidos=self._build_apellidos(result.paterno, result.materno),
        habilitado=result.habilitado,
        capitulo=capitulo_desc,
    )
```

- **Mapeo**: `IngenieroHabilitadoResult` (dominio completo) → `IngenieroHabilitadoOut` (respuesta HTTP simplificada)
- **NO incluye**: `fechaNacimiento`, `dni`, ni ningún otro campo del resultado de dominio
- **Presenter usado en**: `controller:49` — `IngenieroHabilitadoPresenter().present(result)`

### Paso 7 — Response Envelope

**`backend/core/responses.py:41-43`**

```python
def success_response(data: Any = None) -> dict:
    return {"success": True, "data": data, "error": None}
```

---

## Modelo `IngenieroHabilitacion` (Modelo Existente)

**`backend/modules/usuarios/domain/models/perfil_ingeniero.py:172-198`**

```python
class IngenieroHabilitacion(BaseModel):  # Hereda UUID + TimestampedModel
    perfil_ingeniero = models.ForeignKey("PerfilIngeniero", ...)
    ultimo_periodo_pagado_cip = models.CharField(max_length=20, null=True)
    condicion_cip = models.CharField(max_length=10, null=True)
```

- **No es un log de búsquedas** — es un snapshot histórico de la habilitación
- **No tiene campo de fecha de búsqueda** — solo tiene `created_at` del `TimestampedModel`
- **No sirve para deduplicación diaria** — no hay forma de saber si ya se buscó el CIP "hoy"

---

## Lista Exhaustiva de Archivos a Cambiar

| Archivo | Qué cambia | Tipo de cambio | Riesgo |
|---------|-----------|----------------|--------|
| `backend/modules/usuarios/domain/models/perfil_ingeniero.py` | Agregar clase `IngenieroBusquedaRegistro` al final del archivo | **Nuevo modelo** | Bajo — no toca código existente |
| `backend/modules/usuarios/domain/services/core/ingeniero_busqueda_registro_core_service.py` | **NUEVO ARCHIVO** — CoreService con `_registrar_busqueda(cip, fecha)` usando `get_or_create` + constraint único | Creación | N/A (archivo nuevo) |
| `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py` | Agregar llamada `sync_to_async(core_reg._registrar_busqueda)(normalized_cip, timezone.localdate())` después de obtener datos del CIP exitosamente (línea 79, antes del `return`) | Modificación | **Medio** — hay que agregar `IngenieroBusquedaRegistroCoreService` como dependencia del flujo |
| `backend/modules/usuarios/di.py` | Agregar binding de `IngenieroBusquedaRegistroCoreService` en `UsuariosModule.configure()` | Modificación | Bajo — solo wiring de DI |
| `backend/modules/usuarios/presentation/controllers/ingeniero_habilitado_controller.py` | **Sin cambios** — la firma del endpoint no cambia | N/A | N/A |
| `backend/modules/usuarios/domain/services/orchestrators/ingeniero_habilitado_orchestrator.py` | **Sin cambios** — el orquestador es fachada thin | N/A | N/A |
| `backend/modules/usuarios/presentation/schemas/ingeniero_habilitado_schemas.py` | **Sin cambios** — `IngenieroHabilitadoOut` no cambia | N/A | N/A |
| `backend/modules/usuarios/presentation/presenters/ingeniero_habilitado_presenter.py` | **Sin cambios** | N/A | N/A |
| `backend/config/api.py` | Verificar que el controller esté registrado (ya está según codegraph) | N/A | N/A |
| `migrations/` | Generar migration para `IngenieroBusquedaRegistro` | Migration Django | Bajo — makemigrations lo genera automáticamente |

---

## Decisiones Pendientes (para confirmar con el usuario)

### 1. ¿Qué campos guarda el registro?

**Opción A — Solo cip + fecha de búsqueda** (mínimo)
```python
class IngenieroBusquedaRegistro(BaseModel):
    cip = models.CharField(max_length=6, db_index=True)
    fecha_busqueda = models.DateField()
```
→ Ventaja: simple, mínimo personal information
→ Desventaja: no queda registro de quién hizo la búsqueda ni resultado

**Opción B — cip + fecha + resultado (completo)**
```python
class IngenieroBusquedaRegistro(BaseModel):
    cip = models.CharField(max_length=6, db_index=True)
    fecha_busqueda = models.DateField()
    cip_existente = models.BooleanField()  # None si CIP inválido/error
    habilitado = models.BooleanField(null=True)
    paterno = models.CharField(max_length=100, blank=True)
    # ... más campos del resultado CIP
```
→ Ventaja: auditoría completa, posible para reportes
→ Desventaja: más campos, más complejidad

**Recomendación**: Opción A (mínimo) — la deduplicación es el objetivo, guardar toda la respuesta es un extra.

---

### 2. ¿La respuesta del endpoint cambia?

**Situación actual**: El endpoint retorna `IngenieroHabilitadoOut` con `cip, nombres, apellidos, habilitado, capitulo`.

**Pregunta**: ¿El frontend necesita saber si "esta búsqueda ya fue hecha hoy"?

- **Si SÍ**: Agregar campo `ya_buscado_hoy: bool` a `IngenieroHabilitadoOut` — requiere cambiar el presenter
- **Si NO**: El registro es transparente al usuario — efecto secundario interno

**Recomendación**: No cambiar la respuesta — el registro es un efecto secundario invisible. Si en el futuro se necesita, se agrega en una versión posterior.

---

### 3. ¿Usar `timezone.localdate()` para la fecha de deduplicación?

**Respuesta confirmada por el usuario**: "Django maneja las zonas internamente, pero para afuera y para adentro tengo que parsear esas zonas."

- **Entrada** (CIP API → `fechaNacimiento`): el API externo retorna `YYYY-MM-DD` como string, se parsea con `datetime.strptime(..., "%Y-%m-%d").date()` — **correcto**
- **Salida** (serialización HTTP): Pydantic serializa `date` a ISO string automáticamente — **correcto**
- **Registro de búsqueda**: usar `timezone.localdate()` (de `django.utils.timezone`) para la fecha de deduplicación

**Decisión**: Usar `timezone.localdate()` en el CoreService — confirmado.

---

### 4. ¿EI CIP inválido (no existe en el servicio CIP) se registra?

**Situación**: Si el CIP es válido格式 pero no existe en el servicio CIP externo (404), el flujo lanza `CipNotFoundError`. El registro de búsqueda NO se ejecuta actualmente.

**Opciones**:
- **Opción A — Registrar solo búsquedas exitosas** (CIP encontrado): el registro solo se crea cuando `raw_data is not None` → solo búsquedas que encontraron el ingeniero
- **Opción B — Registrar todas las búsquedas intentadas**: incluir CIPs que no existen (para auditoría, para saber que alguien buscó ese CIP)

**Recomendación**: Opción A (solo exitosas) — el propósito es deduplicar consultas al servicio CIP externo; si el CIP no existe, no hay consulta que deduplicar.

---

### 5. ¿El modelo usa `UniqueConstraint` a nivel DB?

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["cip", "fecha_busqueda"],
            name="unique_cip_fecha_busqueda"
        )
    ]
```

**Decisión**: Sí — es la forma correcta de garantizar la deduplicación a nivel de base de datos. Django `get_or_create` con el constraint único garantiza exactly-one.

---

## Risks Descubiertos

1. **Campo `fechaNacimiento` no expuesto en respuesta HTTP**: `IngenieroHabilitadoOut` no incluye `fechaNacimiento`. Si el frontend lo necesita, hay que agregarlo al presenter y al schema.

2. **Discrepancia modelo/servicio en `PerfilIngenieroCoreService`**: `_map_cip_data_to_perfil_fields()` referencia `habilitado_cip`, `condicion_cip`, `fecha_validacion_cip` — estos campos **no existen** en `PerfilIngeniero`. Si se llama `_upsert_perfil_from_cip`, fallará con `AttributeError`. (No afecta el flujo actual porque es de solo lectura.)

3. **Inercia de `date.today()`**: En `liquidaciones` se usa `date.today()` naive en lugar de `timezone.localdate()`. Si se copia ese patrón por error, la deduplicación fallará en la frontera de timezone de Perú.

4. **No hay tests de integración** para el endpoint `GET /ingenieros/habilitados/{cip}`. La nueva funcionalidad parte sin cobertura.

5. **Riesgo de sincronización en `get_or_create`**: Si dos requests concurrentes para el mismo CIP+fecha llegan simultáneamente, el segundo `get_or_create` puede causar un `IntegrityError` si no se usa el wrapper correcto. La solución es el patrón Django estándar que maneja esto internamente.

---

## Siguiente Recomendado

**apply** — La exploración v2 es exhaustiva. Los riesgos son manejables. Las decisiones pendientes son preguntas claras al usuario. La fase de diseño e implementación puede proceder una vez confirmadas las decisiones pendientes.

---

## Skill Resolution

- `sdd-explore/SKILL.md` — cargado desde `C:\Users\Usuario\.claude\skills\sdd-explore\SKILL.md`
- `_shared/sdd-phase-common.md` — cargado desde `C:\Users\Usuario\.config\opencode\skills\_shared\sdd-phase-common.md`
- `_shared/openspec-convention.md` — cargado desde `C:\Users\Usuario\.config\opencode\skills\_shared\openspec-convention.md`
