# Edificaciones (PorcentajeObra) - Documentación Completa de Implementación

> **Versión**: 1.0
> **Fecha**: 2026-08-08
> **Estado**: Producción (commit 37be5e8)
> **Proyecto**: comision-asuntos-municipales
> **Rama**: betha

---

## 1. Resumen Ejecutivo

**Edificaciones** es un tipo de liquidación del módulo `liquidaciones` que usa el motor de cálculo **PorcentajeObra** (PO). A diferencia de Habilitación Urbana (HU) que usa metros cuadrados (M2) o Inspección de Obra (IO) que usa visitas, Edificaciones calcula el derecho a pagar aplicando uno o más porcentajes al `valor_declarado` del proyecto.

**Motor de cálculo**: `valor_declarado × sum(porcentaje_tarifas)`

**Características distintivas**:
- **Tarifas múltiples simultáneas**: Aplica N tarifas a la vez (Civil, Sanitaria, Eléctrica)
- **Resolución híbrida**: Array vacío = auto-fill con todas las vigentes; Array con elementos = validación explícita
- **Clamping agregado**: La regla de negocio (mínimo/máximo) aplica al TOTAL calculado, distribuido proporcionalmente
- **tipo_tramite = NULL**: Por ahora no se usa; future-state para cuando el frontend lo envíe

**Flujo simplificado**:
```
HTTP Request → Controller → Orchestrator (valida + clamping) → Flujo (@transaction.atomic) → Core (ORM + matemática) → DB
```

---

## 2. Arquitectura: Motor vs Liquidación Específica

### 2.1 Distinción Conceptual

El sistema de liquidaciones tiene **dos niveles** de abstracción:

| Nivel | Concepto | Ejemplo para Edificaciones |
|-------|----------|---------------------------|
| **Motor de cálculo** (Tipo) | "¿CÓMO se calcula?" | `LiquidacionPorcentajeObraCoreService` — matemática pura (valor × %) |
| **Liquidación específica** | "¿QUÉ trámite es?" | `LiquidacionEdificacionesOrchestrator` — coordinación + validación |

**Analogía**:
- **Motor** = el motor de un carro (no sabe si está en un Ferrari o Toyota)
- **Liquidación específica** = el carro completo (envuelve el motor con su lógica de negocio)

### 2.2 Nombres de las 4 Capas

```
Controller (Presentation)     → thin, delega nomás
    ↓
Orchestrator (Domain)         → validación + clamping + mapeo
    ↓
Flujo (Domain)                 → @transaction.atomic, coordinación
    ↓
Core (Infrastructure)         → ORM puro + aritmética
```

### 2.3 Los 3 Wrappers (Input/Output)

**Input (2 wrappers)**:
```python
{
  "liquidacion_general": { ... },     # Cabecera común (municipalidad, expediente, proyecto)
  "liquidacion_especifica": {         # Datos del motor
    "datos": { "valor_declarado": ... },
    "tarifas": [ ... ]                # Puede estar vacío (auto-fill)
  }
}
```

**Output (3 wrappers)**:
```python
{
  "liquidacion_general": { ... },     # Cabecera común con totales
  "liquidacion_especifica": { "id": ..., "numero": ... },  # Identidad
  "liquidacion_tipo": { ... }         # Motor: valor_declarado, porcentaje, detalles[]
}
```

---

## 3. Servicios Creados

### 3.1 Core (Pura ORM + Aritmética)

**Archivo**: `backend/modules/liquidaciones/domain/services/core/liquidacion_tipo/liquidacion_porcentaje_obra_core_service.py`

**Clase**: `LiquidacionPorcentajeObraCoreService`

#### Métodos:

##### `resolver_tarifas(payload_tarifas_ids: List[str])` → `List[TarifaPorcentajeObra]`

**Líneas**: 30-56

Resolución híbrida de tarifas:

```python
def resolver_tarifas(
    self,
    payload_tarifas_ids: List[str],
) -> List[TarifaPorcentajeObra]:
    if not payload_tarifas_ids:
        # Auto-fill: todas las vigentes para EDIFICACION
        bases = TarifaLiquidacionBase.objects.vigentes().filter(
            tipo_liquidacion=TipoLiquidacion.EDIFICACION
        )
        return list(
            TarifaPorcentajeObra.objects.filter(
                tarifa_base__in=bases
            ).select_related("tarifa_base", "especialidad")
        )
    else:
        # Explícito: solo las solicitadas
        return list(
            TarifaPorcentajeObra.objects.filter(
                id__in=payload_tarifas_ids
            ).select_related("tarifa_base", "especialidad")
        )
```

**Nota**: La validación de vigencia y tipo se hace en el Orchestrator, no aquí.

---

##### `get_derecho_porcentaje_vigente()` → `DerechoPorcentajeObra`

**Línea**: 58-60

```python
def get_derecho_porcentaje_vigente(self) -> DerechoPorcentajeObra:
    return DerechoPorcentajeObra.objects.vigentes().first()
```

---

##### `get_tarifas_porcentaje_vigentes()` → `List[TarifaPorcentajeObra]`

**Líneas**: 62-71

```python
def get_tarifas_porcentaje_vigentes(self) -> List[TarifaPorcentajeObra]:
    bases = TarifaLiquidacionBase.objects.vigentes().filter(
        tipo_liquidacion=TipoLiquidacion.EDIFICACION
    )
    return list(
        TarifaPorcentajeObra.objects.filter(
            tarifa_base__in=bases
        ).select_related("tarifa_base", "especialidad")
    )
```

---

##### `calcular_cotizacion_po(...)` → `CotizacionPorcentajeObraData`

**Líneas**: 73-146

Matemática pura del motor PorcentajeObra:

```python
def calcular_cotizacion_po(
    self,
    valor_declarado: Decimal,
    tarifas: List[TarifaPorcentajeObra],
    igv_porcentaje: Decimal,
    derecho: DerechoPorcentajeObra,
) -> CotizacionPorcentajeObraData:
    if not tarifas:
        raise ValueError("At least one tarifa is required")

    # Step 1: Per-detalle RAW (sin clamping)
    detalles_raw: List[DetallePorcentajeObraData] = []
    for tarifa in tarifas:
        subtotal = valor_declarado * tarifa.porcentaje_liquidacion
        detalles_raw.append(
            DetallePorcentajeObraData(
                tarifa_aplicada=TarifaPorcentajeObraAplicada(...),
                porcentaje_aplicado=tarifa.porcentaje_liquidacion,
                subtotal=subtotal,
                igv=subtotal * igv_porcentaje,
                uit=valor_declarado * derecho.porcentaje_minimo_uit,
                total=subtotal + (subtotal * igv_porcentaje),
            )
        )

    # Step 2: Agregar
    porcentaje_liquidacion = sum(t.porcentaje_liquidacion for t in tarifas, Decimal("0"))
    total_calculado = sum(d.subtotal for d in detalles_raw, Decimal("0"))

    # Step 3: Clamping al TOTAL
    detalles_finales = detalles_raw
    if total_calculado < derecho.derecho_minimo:
        factor = derecho.derecho_minimo / total_calculado
        detalles_finales = self._distribute_clamp(detalles_raw, factor, igv_porcentaje, valor_declarado, derecho)
    elif derecho.derecho_maximo is not None and total_calculado > derecho.derecho_maximo:
        factor = derecho.derecho_maximo / total_calculado
        detalles_finales = self._distribute_clamp(detalles_raw, factor, igv_porcentaje, valor_declarado, derecho)

    total_subtotal = sum(d.subtotal for d in detalles_finales, Decimal("0"))
    total = sum(d.total for d in detalles_finales, Decimal("0"))

    return CotizacionPorcentajeObraData(...)
```

---

##### `_distribute_clamp(...)` → `List[DetallePorcentajeObraData]`

**Líneas**: 148-171

Distribución proporcional del factor de clamping:

```python
def _distribute_clamp(
    self,
    detalles_raw: List[DetallePorcentajeObraData],
    factor: Decimal,
    igv_porcentaje: Decimal,
    valor_declarado: Decimal,
    derecho: DerechoPorcentajeObra,
) -> List[DetallePorcentajeObraData]:
    result = []
    for d in detalles_raw:
        new_subtotal = d.subtotal * factor
        new_igv = new_subtotal * igv_porcentaje
        result.append(
            DetallePorcentajeObraData(
                tarifa_aplicada=d.tarifa_aplicada,
                porcentaje_aplicado=d.porcentaje_aplicado,
                subtotal=new_subtotal,
                igv=new_igv,
                uit=valor_declarado * derecho.porcentaje_minimo_uit,
                total=new_subtotal + new_igv,
            )
        )
    return result
```

---

##### `create_liquidacion_porcentaje_obra(...)` → `LiquidacionPorcentajeObra`

**Líneas**: 173-206

Crea el registro en DB + todos los detalles:

```python
def create_liquidacion_porcentaje_obra(
    self,
    liquidacion_general,
    cotizacion: CotizacionPorcentajeObraData,
    derecho: DerechoPorcentajeObra,
) -> LiquidacionPorcentajeObra:
    liquidacion_po = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion_general,
        tipo_tramite=None,  # FUTURE: activate
        valor_declarado=cotizacion.valor_declarado,
        porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
        derecho_minimo=derecho.derecho_minimo,
        derecho_maximo=derecho.derecho_maximo,
        porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
        derecho_aplicado=derecho,
    )
    for detalle in cotizacion.detalles:
        tarifa = TarifaPorcentajeObra.objects.get(id=detalle.tarifa_aplicada.tarifa_id)
        LiquidacionPorcentajeObraDetalle.objects.create(
            liquidacion_porcentaje=liquidacion_po,
            tarifa_aplicada=tarifa,
            especialidad=tarifa.especialidad,
            porcentaje_aplicado=detalle.porcentaje_aplicado,
            subtotal=detalle.subtotal,
            igv=detalle.igv,
            uit=detalle.uit,
            total=detalle.total,
        )
    return liquidacion_po
```

---

### 3.2 Orchestrator (Validación + Coordinación)

**Archivo**: `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_edificaciones_orchestrator.py`

**Clase**: `LiquidacionEdificacionesOrchestrator`

#### Métodos:

##### `_validar_tarifa_explicita(tarifa)` → `None` / `HttpError`

**Líneas**: 56-72

Valida que una tarifa explícitamente enviada por el usuario esté vigente y sea de EDIFICACION:

```python
def _validar_tarifa_explicita(self, tarifa) -> None:
    today = timezone.now().date()
    is_vigente = (
        tarifa.tarifa_base.periodo_inicio <= today
        and (
            tarifa.tarifa_base.periodo_fin is None
            or tarifa.tarifa_base.periodo_fin >= today
        )
    )
    if not is_vigente:
        raise HttpError(400, f"Tarifa {tarifa.id} no está vigente")
    if tarifa.tarifa_base.tipo_liquidacion != TipoLiquidacion.EDIFICACION:
        raise HttpError(400, f"Tarifa {tarifa.id} no es de edificaciones")
```

---

##### `crear_primera_revision_proceso(usuario_id, payload_in)` → `EdificacionesPrimeraRevisionResult`

**Líneas**: 85-172

Flujo completo de validación y creación:

```python
def crear_primera_revision_proceso(
    self,
    usuario_id: int,
    payload_in,
) -> EdificacionesPrimeraRevisionResult:
    # Step 1: Validar valor_declarado
    valor_declarado = payload_in.liquidacion_especifica.datos.valor_declarado
    if valor_declarado <= 0:
        raise HttpError(400, "valor_declarado debe ser mayor a 0")

    # Step 2: Resolución híbrida
    payload_tarifas_ids = [str(t.tarifa_porcentaje_obra_id) for t in payload_in.liquidacion_especifica.tarifas]
    tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids)

    # Validar solo en modo explícito
    if payload_tarifas_ids:
        for tarifa in tarifas:
            self._validar_tarifa_explicita(tarifa)

    if not tarifas:
        raise HttpError(400, "No hay tarifas vigentes para edificaciones")

    # Step 3: Obtener IGV/UIT/Derecho vigentes
    igv_vigente = self.general_core.get_igv_vigente()
    uit_vigente = self.general_core.get_uit_vigente()
    if not igv_vigente or not uit_vigente:
        raise HttpError(400, "No hay IGV o UIT vigente configurado")

    derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
    if not derecho:
        raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

    # Step 4: Construir DTO de dominio
    domain_data = EdificacionesPrimeraRevisionData(...)

    # Step 5: Delegar al Flujo
    return self.flujo.ejecutar_primera_revision(
        usuario_id=usuario_id,
        data=domain_data,
        igv_porcentaje=Decimal(str(igv_vigente.valor)),
        derecho=derecho,
    )
```

---

##### `cotizar_proceso(valor_declarado, payload_tarifas_ids)` → `CotizacionPorcentajeObraResult`

**Líneas**: 181-245

Cotización sin persistir (mismo flujo que crear pero sin DB):

```python
def cotizar_proceso(
    self,
    valor_declarado: Decimal,
    payload_tarifas_ids: List[str],
) -> CotizacionPorcentajeObraResult:
    # Step 1: Validación
    if valor_declarado <= 0:
        raise HttpError(400, "valor_declarado debe ser mayor a 0")

    # Step 2: Resolución híbrida
    tarifas = self.porcentaje.core.resolver_tarifas(payload_tarifas_ids)
    if payload_tarifas_ids:
        for tarifa in tarifas:
            self._validar_tarifa_explicita(tarifa)
    if not tarifas:
        raise HttpError(400, "No hay tarifas vigentes para edificaciones")

    # Step 3: Obtener IGV y Derecho
    igv_vigente = self.general_core.get_igv_vigente()
    if not igv_vigente:
        raise HttpError(400, "No hay IGV vigente")
    derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
    if not derecho:
        raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

    # Step 4: Calcular
    cotizacion = self.porcentaje_core.calcular_cotizacion_po(
        valor_declarado=valor_declarado,
        tarifas=tarifas,
        igv_porcentaje=Decimal(str(igv_vigente.valor)),
        derecho=derecho,
    )

    # Step 5: Construir Result
    return CotizacionPorcentajeObraResult(...)
```

---

### 3.3 Flujo (Transaccional)

**Archivo**: `backend/modules/liquidaciones/domain/services/flujos/liquidacion_especifico/liquidacion_edificaciones_flujo.py`

**Clase**: `LiquidacionEdificacionesFlujo`

#### Métodos:

##### `ejecutar_primera_revision(...)` → `EdificacionesPrimeraRevisionResult`

**Líneas**: 62-69

Wrapper síncrono que delega al método con `@transaction.atomic`:

```python
def ejecutar_primera_revision(
    self,
    usuario_id: int,
    data: EdificacionesPrimeraRevisionData,
    igv_porcentaje: Decimal,
    derecho,
) -> EdificacionesPrimeraRevisionResult:
    return self._ejecutar_primera_revision_sync(usuario_id, data, igv_porcentaje, derecho)
```

---

##### `_ejecutar_primera_revision_sync(...)` → `EdificacionesPrimeraRevisionResult`

**Líneas**: 71-156

Orquestación transaccional de todas las operaciones de DB:

```python
@transaction.atomic()
def _ejecutar_primera_revision_sync(
    self,
    usuario_id: int,
    data: EdificacionesPrimeraRevisionData,
    igv_porcentaje: Decimal,
    derecho,
) -> EdificacionesPrimeraRevisionResult:
    gen_data = data.liquidacion_general
    po_data = data.liquidacion_especifica

    # Paso 1: Entidad (upsert por documento)
    entidad = self.general_core.create_entidad(
        tipo_documento=gen_data.proyecto.entidad.tipo_documento,
        numero_documento=gen_data.proyecto.entidad.numero_documento,
    )

    # Paso 2: Proyecto
    proyecto_data = {...}
    proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

    # Paso 3: LiquidacionGeneral (sub_total=0, total=0 inicialmente)
    liquidacion_general = self.general_core.create_liquidacion_general(
        municipalidad_id=gen_data.municipalidad_id,
        expediente=gen_data.expediente,
        observacion=gen_data.observacion,
        proyecto=proyecto,
        tipo_liquidacion=TipoLiquidacion.EDIFICACION,
        numero_revision=1,
    )

    # Asignar FKs de IGV/UIT y guardar
    igv_vigente = self.general_core.get_igv_vigente()
    uit_vigente = self.general_core.get_uit_vigente()
    liquidacion_general.igv_id = igv_vigente
    liquidacion_general.uit_id = uit_vigente
    liquidacion_general.usuario_creador_id = usuario_id

    # Paso 4: Calcular PorcentajeObra
    tarifas_orm = [TarifaPorcentajeObra.objects.get(id=t.tarifa_id) for t in po_data.tarifas]
    cotizacion = self.porcentaje_core.calcular_cotizacion_po(
        valor_declarado=po_data.datos.valor_declarado,
        tarifas=tarifas_orm,
        igv_porcentaje=igv_porcentaje,
        derecho=derecho,
    )

    # Actualizar totales de LiquidacionGeneral
    liquidacion_general.sub_total = cotizacion.total_subtotal
    liquidacion_general.total = cotizacion.total
    liquidacion_general.save()

    # Paso 5: Crear LiquidacionPorcentajeObra + detalles
    liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
        liquidacion_general=liquidacion_general,
        cotizacion=cotizacion,
        derecho=derecho,
    )

    # Paso 6: LiquidacionEdificacion (wrapper de identidad)
    edificacion = LiquidacionEdificacion.objects.create(
        liquidacion=liquidacion_general
    )

    # Build Result
    return self._build_result(liquidacion_general, edificacion, liquidacion_po, usuario_id)
```

**Orden de operaciones en DB**:
```
1. Entidad (upsert)
2. Proyecto
3. LiquidacionGeneral (totales=0)
4. IGV/UIT FKs asignados → save()
5. LiquidacionPorcentajeObra + Detalles
6. LiquidacionEdificacion (identidad)
```

---

##### `_build_result(...)` → `EdificacionesPrimeraRevisionResult`

**Líneas**: 158-235

Mapeo de objetos ORM → Result (Pydantic puro):

```python
def _build_result(
    self,
    liquidacion_general,
    edificacion,
    liquidacion_po,
    usuario_id: int,
) -> EdificacionesPrimeraRevisionResult:
    liquidacion_general.refresh_from_db()

    # Build EntidadResult
    entidad_result = EntidadResult(
        razon_social=proyecto.entidad_razon_social,
        tipo_documento=getattr(proyecto, 'entidad_tipo_documento', None) or "",
        numero_documento=getattr(proyecto, 'entidad_numero_documento', None) or "",
    )

    # Build ProyectoResult
    proyecto = liquidacion_general.proyecto
    proyecto_result = ProyectoResult(...)

    return EdificacionesPrimeraRevisionResult(
        liquidacion_general=LiquidacionGeneralResult(
            id=str(liquidacion_general.id),
            municipalidad_id=str(liquidacion_general.municipalidad_id),
            usuario_creador=UsuarioCreadorResult(id=str(usuario_id)),
            fecha_registro=liquidacion_general.created_at.isoformat(),
            expediente=liquidacion_general.expediente,
            observacion=liquidacion_general.observacion,
            numero_revision=liquidacion_general.numero_revision,
            sub_total=float(liquidacion_general.sub_total),
            total=float(liquidacion_general.total),
            igv_id=str(liquidacion_general.igv_id.id) if liquidacion_general.igv_id else None,
            uit_id=str(liquidacion_general.uit_id.id) if liquidacion_general.uit_id else None,
            proyecto=proyecto_result,
        ),
        liquidacion_especifica=LiquidacionEspecificaEdificacionesResult(
            id=str(edificacion.id),
            numero=edificacion.numero,
        ),
        liquidacion_tipo=LiquidacionPorcentajeObraResult(
            id=str(liquidacion_po.id),
            liquidacion_general_id=str(liquidacion_po.liquidacion_general_id),
            tipo_tramite=liquidacion_po.tipo_tramite,  # NULL
            valor_declarado=liquidacion_po.valor_declarado,
            porcentaje_liquidacion=liquidacion_po.porcentaje_liquidacion,
            derecho_minimo=liquidacion_po.derecho_minimo,
            derecho_maximo=liquidacion_po.derecho_maximo,
            porcentaje_minimo_uit=liquidacion_po.porcentaje_minimo_uit,
            derecho_aplicado_id=str(liquidacion_po.derecho_aplicado_id),
            detalles=[
                DetallePorcentajeObraResult(
                    id=str(d.id),
                    tarifa_aplicada_id=str(d.tarifa_aplicada_id),
                    especialidad_id=str(d.especialidad_id),
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                    igv=d.igv,
                    uit=d.uit,
                    total=d.total,
                )
                for d in liquidacion_po.detalles.all()
            ],
        ),
    )
```

---

### 3.4 Presentation Layer

#### 3.4.1 Schemas (Input/Output)

**Archivo**: `backend/modules/liquidaciones/presentation/schemas/liquidacion_tipo/porcentaje_schemas.py`

Schemas del motor (shared, no solo Edificaciones):

```python
# Input (líneas 13-31)
class LiquidacionPorcentajeObraDatosIn(BaseSchema):
    valor_declarado: Decimal

class LiquidacionPorcentajeObraTarifaIn(BaseSchema):
    tarifa_porcentaje_obra_id: uuid.UUID

class LiquidacionPorcentajeObraIn(BaseSchema):
    """Si `tarifas` está vacío → auto-fill. Si tiene elementos → validación explícita."""
    datos: LiquidacionPorcentajeObraDatosIn
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = []

# Output (líneas 34-59)
class LiquidacionPorcentajeObraDetalleOut(BaseSchema):
    id: uuid.UUID
    tarifa_aplicada_id: uuid.UUID
    especialidad_id: uuid.UUID
    porcentaje_aplicado: Decimal
    subtotal: Decimal
    igv: Decimal
    uit: Decimal
    total: Decimal

class LiquidacionPorcentajeObraDatosOut(BaseSchema):
    id: uuid.UUID
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal
    tipo_tramite: Optional[str] = None  # NULL por ahora
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: uuid.UUID
    detalles: List[LiquidacionPorcentajeObraDetalleOut]
```

---

**Archivo**: `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_edificaciones_schemas.py`

Schemas específicos de Edificaciones (wrappers):

```python
# Líneas 22-25: Output de identidad
class LiquidacionTipoOutput(BaseSchema):
    id: uuid.UUID
    numero: int

# Líneas 28-31: Input completo
class LiquidacionEdificacionesInput(BaseSchema):
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn

# Líneas 34-38: Output completo (3 wrappers)
class LiquidacionEdificacionesOutput(BaseSchema):
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput  # Identidad
    liquidacion_tipo: LiquidacionPorcentajeObraDatosOut  # Cálculo

# Líneas 41-77: Cotizar
class LiquidacionEdificacionesCotizarInput(BaseSchema):
    liquidacion_especifica: LiquidacionPorcentajeObraIn

class LiquidacionEdificacionesCotizarOutput(BaseSchema):
    valor_declarado: Decimal
    porcentaje_liquidacion: Decimal
    derecho_minimo: Decimal
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Decimal
    derecho_aplicado_id: uuid.UUID
    detalles: List[LiquidacionEdificacionesCotizarDetalleOut]
    total_subtotal: Decimal
    total: Decimal
```

---

#### 3.4.2 Presenter

**Archivo**: `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_edificaciones_presenter.py`

**Clase**: `LiquidacionEdificacionesPresenter`

```python
# Líneas 28-92
@staticmethod
def present_primera_revision(domain_result: EdificacionesPrimeraRevisionResult) -> LiquidacionEdificacionesOutput:
    general = domain_result.liquidacion_general
    tipo = domain_result.liquidacion_tipo
    especifica = domain_result.liquidacion_especifica

    general_out = LiquidacionGeneralOutput(
        id=uuid.UUID(general.id),
        municipalidad_id=uuid.UUID(general.municipalidad_id),
        usuario_creador=UsuarioCreadorOutput(id=uuid.UUID(general.usuario_creador.id)),
        fecha_registro=general.fecha_registro,
        expediente=general.expediente,
        observacion=general.observacion,
        numero_revision=general.numero_revision,
        sub_total=general.sub_total,
        total=general.total,
        igv_id=uuid.UUID(general.igv_id) if general.igv_id else None,
        uit_id=uuid.UUID(general.uit_id) if general.uit_id else None,
        proyecto=ProyectoOutput(...),
    )

    tipo_out = LiquidacionTipoOutput(
        id=uuid.UUID(especifica.id),
        numero=especifica.numero,
    )

    tipo_datos_out = LiquidacionPorcentajeObraDatosOut(
        id=uuid.UUID(tipo.id),
        valor_declarado=tipo.valor_declarado,
        porcentaje_liquidacion=tipo.porcentaje_liquidacion,
        tipo_tramite=tipo.tipo_tramite,  # NULL
        derecho_minimo=tipo.derecho_minimo,
        derecho_maximo=tipo.derecho_maximo,
        porcentaje_minimo_uit=tipo.porcentaje_minimo_uit,
        derecho_aplicado_id=uuid.UUID(tipo.derecho_aplicado_id),
        detalles=[
            LiquidacionPorcentajeObraDetalleOut(
                id=uuid.UUID(d.id),
                tarifa_aplicada_id=uuid.UUID(d.tarifa_aplicada_id),
                especialidad_id=uuid.UUID(d.especialidad_id),
                porcentaje_aplicado=d.porcentaje_aplicado,
                subtotal=d.subtotal,
                igv=d.igv,
                uit=d.uit,
                total=d.total,
            )
            for d in tipo.detalles
        ],
    )

    return LiquidacionEdificacionesOutput(
        liquidacion_general=general_out,
        liquidacion_especifica=tipo_out,
        liquidacion_tipo=tipo_datos_out,
    )
```

---

#### 3.4.3 Controller

**Archivo**: `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_edificaciones_controller.py`

**Clase**: `LiquidacionEdificacionesController`

Endpoints disponibles (líneas 33-110):

```python
@api_controller("/liquidaciones/edificaciones", tags=["Edificaciones"], permissions=[AllowAny])
class LiquidacionEdificacionesController:

    # GET /liquidaciones/edificaciones/tarifas/vigentes
    @route.get("/tarifas/vigentes", response={200: ApiResponse[dict]}, auth=None)
    def get_tarifas_vigentes(self):
        tarifas = self.orchestrator.obtener_tarifas_vigentes_proceso()
        return success_response({
            "tarifas": [
                {
                    "id": str(t.id),
                    "especialidad": t.especialidad.nombre,
                    "porcentaje_liquidacion": float(t.porcentaje_liquidacion),
                }
                for t in tarifas
            ],
        })

    # POST /liquidaciones/edificaciones/nueva-liquidacion/primera-revision
    @route.post("/nueva-liquidacion/primera-revision",
                response={200: ApiResponse[LiquidacionEdificacionesOutput]})
    def crear_primera_revision(self, request, payload: LiquidacionEdificacionesInput):
        usuario_id = self.auth_core_service.get_authenticated_user_id(request)
        domain_result = self.orchestrator.crear_primera_revision_proceso(
            usuario_id=usuario_id,
            payload_in=payload,
        )
        result = self.presenter.present_primera_revision(domain_result)
        return success_response(result)

    # POST /liquidaciones/edificaciones/cotizar
    @route.post("/cotizar", response={200: ApiResponse[LiquidacionEdificacionesCotizarOutput]}, auth=None)
    def cotizar(self, payload: LiquidacionEdificacionesCotizarInput):
        le = payload.liquidacion_especifica
        valor_declarado = le.datos.valor_declarado
        payload_tarifas_ids = [str(t.tarifa_porcentaje_obra_id) for t in le.tarifas]
        domain_result = self.orchestrator.cotizar_proceso(
            valor_declarado=valor_declarado,
            payload_tarifas_ids=payload_tarifas_ids,
        )
        return success_response(domain_result)
```

---

## 4. Flujo Completo (Input → DB → Output)

### 4.1 Input JSON

**Modo A: Auto-fill** (array vacío → backend auto-rellena):

```json
{
  "liquidacion_general": {
    "municipalidad_id": "uuid-municipalidad",
    "expediente": "EXP-2026-00123",
    "observacion": "Primera revisión de habilitación",
    "proyecto": {
      "denominacion": "Edificio Residencial Los Jardines",
      "nombre_propietario": "Carlos Mendoza Pérez",
      "direccion": "Av. Arequipa 1234, Lima",
      "distrito_id": "uuid-distrito",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20456789012",
        "razon_social": "Inmobiliaria Los Jardines S.A.C."
      }
    }
  },
  "liquidacion_especifica": {
    "datos": {
      "valor_declarado": 100000.00
    },
    "tarifas": []
  }
}
```

**Modo B: Explícito** (array con IDs → validación):

```json
{
  "liquidacion_especifica": {
    "datos": {
      "valor_declarado": 100000.00
    },
    "tarifas": [
      { "tarifa_porcentaje_obra_id": "uuid-civil" },
      { "tarifa_porcentaje_obra_id": "uuid-sanitaria" },
      { "tarifa_porcentaje_obra_id": "uuid-electrica" }
    ]
  }
}
```

---

### 4.2 Validación en Orchestrator

```
crear_primera_revision_proceso()
│
├─ 1. valor_declarado > 0 ?
│     └─ HttpError(400) si no
│
├─ 2. Resolver tarifas (híbrido)
│     ├─ Si array vacío → auto-fill con vigentes
│     └─ Si array con IDs → fetch + validar
│
├─ 3. Validar cada tarifa (solo explícito)
│     ├─ ¿Vigente? → HttpError(400) si no
│     └─ ¿TipoLiquidacion = EDIFICACION? → HttpError(400) si no
│
├─ 4. IGV vigente existe? → HttpError(400) si no
├─ 5. UIT vigente existe? → HttpError(400) si no
└─ 6. DerechoPorcentajeObra vigente existe? → HttpError(400) si no
```

---

### 4.3 Resolución Híbrida de Tarifas

**Dos modos en el mismo endpoint**:

| Modo | `tarifas` | Comportamiento | Validación |
|------|-----------|----------------|------------|
| **Auto-fill** | `[]` (vacío) | Backend toma TODAS las vigentes de EDIFICACION | No se valida nada |
| **Explícito** | `[{tarifa_id: uuid}, ...]` | Solo se usan las especificadas | Vigencia + tipo |

**Código en Orchestrator**:

```python
# Líneas 106-118
payload_tarifas_ids = [str(t.tarifa_porcentaje_obra_id) for t in payload_in.liquidacion_especifica.tarifas]
tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids)

if payload_tarifas_ids:  # Solo si explicit mode
    for tarifa in tarifas:
        self._validar_tarifa_explicita(tarifa)

if not tarifas:
    raise HttpError(400, "No hay tarifas vigentes para edificaciones")
```

**Código en Core (resolver_tarifas)**:

```python
# Líneas 40-56
if not payload_tarifas_ids:  # AUTO-FILL
    bases = TarifaLiquidacionBase.objects.vigentes().filter(
        tipo_liquidacion=TipoLiquidacion.EDIFICACION
    )
    return list(TarifaPorcentajeObra.objects.filter(tarifa_base__in=bases)...)
else:  # EXPLÍCITO
    return list(TarifaPorcentajeObra.objects.filter(id__in=payload_tarifas_ids)...)
```

---

### 4.4 Cálculo en Core

**Fórmula por detalle**:

```
subtotal_i   = valor_declarado × tarifa_i.porcentaje_liquidacion
igv_i        = subtotal_i × igv_porcentaje
uit_i        = valor_declarado × derecho.porcentaje_minimo_uit
total_i      = subtotal_i + igv_i
```

**Fórmula agregada**:

```
porcentaje_liquidacion = Σ(tarifa_i.porcentaje_liquidacion)
total_calculado       = Σ(subtotal_i)
```

**Clamping** (aplicado al TOTAL, no a cada detalle):

```
SI total_calculado < derecho.derecho_minimo:
    factor = derecho.derecho_minimo / total_calculado
    PARA CADA detalle:
        detalle.subtotal = detalle.subtotal × factor
        detalle.igv      = detalle.subtotal × igv_porcentaje
        detalle.total    = detalle.subtotal + detalle.igv

SI derecho.derecho_maximo EXISTE Y total_calculado > derecho.derecho_maximo:
    factor = derecho.derecho_maximo / total_calculado
    PARA CADA detalle:
        detalle.subtotal = detalle.subtotal × factor
        detalle.igv      = detalle.subtotal × igv_porcentaje
        detalle.total    = detalle.subtotal + detalle.igv
```

**Ejemplo numérico (sin clamping)**:
- `valor_declarado = 100,000`
- 3 tarifas × 0.0015 (0.15%)
- IGV = 18%

```
Civil:      subtotal=150.00, igv=27.00, uit=110.00, total=177.00
Sanitaria:  subtotal=150.00, igv=27.00, uit=110.00, total=177.00
Electrica:  subtotal=150.00, igv=27.00, uit=110.00, total=177.00

porcentaje_liquidacion = 0.0045
sub_total = 450.00
total = 531.00
```

**Ejemplo numérico (con clamping mínimo)**:
- `valor_declarado = 10,000`
- 3 tarifas × 0.0015
- `derecho_minimo = 129.80`

```
Calculado:  45.00 (suma de 3 × 15)
Aplicar min: 129.80 / 45.00 = 2.8844...
factor = 2.8844

Civil:      subtotal=43.27, igv=7.79, total=51.06
Sanitaria:  subtotal=43.27, igv=7.79, total=51.06
Electrica:  subtotal=43.27, igv=7.79, total=51.06

sub_total = 129.80
total = 153.16
```

---

### 4.5 Operaciones en DB

**Orden transaccional (dentro de `@transaction.atomic`)**:

```
BEGIN TRANSACTION
│
├─ 1. [General Core] create_entidad(tipo_documento, numero_documento)
│     └─ INSERT INTO entidades ... ON CONFLICT ... RETURNING id
│
├─ 2. [General Core] create_proyecto(proyecto_data, entidad)
│     └─ INSERT INTO proyectos ... RETURNING id
│
├─ 3. [General Core] create_liquidacion_general(...)
│     └─ INSERT INTO liquidaciones_general (sub_total=0, total=0)
│
├─ 4. [Flujo] Asignar igv_id, uit_id, usuario_creador_id → save()
│     └─ UPDATE liquidaciones_general SET igv_id=..., uit_id=..., ...
│
├─ 5. [Core] calcular_cotizacion_po(...) → CotizacionPorcentajeObraData
│     └─ Sin DB (aritmética pura)
│
├─ 6. [Flujo] Actualizar totales de LiquidacionGeneral
│     └─ UPDATE liquidaciones_general SET sub_total=..., total=...
│
├─ 7. [Core] create_liquidacion_porcentaje_obra(liquidacion_general, cotizacion, derecho)
│     ├─ INSERT INTO liquidaciones_porcentaje_obra (...)
│     └─ INSERT INTO liquidaciones_porcentaje_obra_detalles (N inserts)
│
└─ 8. [Flujo] LiquidacionEdificacion.objects.create(liquidacion=liquidacion_general)
    └─ INSERT INTO liquidaciones_edificaciones (...)

COMMIT
```

---

### 4.6 Output JSON

```json
{
  "liquidacion_general": {
    "id": "uuid",
    "municipalidad_id": "uuid",
    "usuario_creador": { "id": "uuid" },
    "fecha_registro": "2026-08-08T10:30:00",
    "expediente": "EXP-2026-00123",
    "observacion": "Primera revisión de habilitación",
    "numero_revision": 1,
    "sub_total": 450.00,
    "total": 531.00,
    "igv_id": "uuid-igv",
    "uit_id": "uuid-uit",
    "proyecto": {
      "id": "uuid",
      "denominacion": "Edificio Residencial Los Jardines",
      "nombre_propietario": "Carlos Mendoza Pérez",
      "direccion": "Av. Arequipa 1234, Lima",
      "distrito_id": "uuid-distrito",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20456789012",
        "razon_social": "Inmobiliaria Los Jardines S.A.C."
      }
    }
  },
  "liquidacion_especifica": {
    "id": "uuid",
    "numero": 1
  },
  "liquidacion_tipo": {
    "id": "uuid",
    "valor_declarado": 100000.00,
    "porcentaje_liquidacion": 0.0045,
    "tipo_tramite": null,
    "derecho_minimo": 129.80,
    "derecho_maximo": null,
    "porcentaje_minimo_uit": 0.02,
    "derecho_aplicado_id": "uuid-derecho",
    "detalles": [
      {
        "id": "uuid",
        "tarifa_aplicada_id": "uuid-civil",
        "especialidad_id": "uuid-civil-especialidad",
        "porcentaje_aplicado": 0.0015,
        "subtotal": 150.00,
        "igv": 27.00,
        "uit": 110.00,
        "total": 177.00
      },
      {
        "id": "uuid",
        "tarifa_aplicada_id": "uuid-sanitaria",
        "especialidad_id": "uuid-sanitaria-especialidad",
        "porcentaje_aplicado": 0.0015,
        "subtotal": 150.00,
        "igv": 27.00,
        "uit": 110.00,
        "total": 177.00
      },
      {
        "id": "uuid",
        "tarifa_aplicada_id": "uuid-electrica",
        "especialidad_id": "uuid-electrica-especialidad",
        "porcentaje_aplicado": 0.0015,
        "subtotal": 150.00,
        "igv": 27.00,
        "uit": 110.00,
        "total": 177.00
      }
    ]
  }
}
```

---

## 5. Reglas de Negocio Implementadas

### 5.1 Cálculo Por Detalle

Para cada tarifa en `tarifas[]`:

```python
detalle.subtotal = valor_declarado × tarifa.porcentaje_liquidacion
detalle.igv     = detalle.subtotal × igv_porcentaje
detalle.uit     = valor_declarado × derecho.porcentaje_minimo_uit
detalle.total   = detalle.subtotal + detalle.igv
```

**Nota**: `uit` es informativo (no se suma al total).

### 5.2 Cálculo Agregado

```python
porcentaje_liquidacion = Σ(tarifa.porcentaje_liquidacion)
total_subtotal        = Σ(detalle.subtotal)
total                 = Σ(detalle.total)
```

### 5.3 Clamping

**Pregunta clave**: ¿A qué se aplica el clamping?

**Respuesta**: Al **TOTAL** (sub_total + IGV), con distribución **proporcional** por detalle.

**Razonamiento**: La regla de negocio dice "el cobro total no puede ser menor al derecho mínimo". Aplicar clamping per-detalle sería incorrecto porque cambiaría el porcentaje efectivo de cada tarifa.

**Implementación**:

```python
# Core (líneas 119-130)
if total_calculado < derecho.derecho_minimo:
    factor = derecho.derecho_minimo / total_calculado
    detalles_finales = self._distribute_clamp(detalles_raw, factor, ...)
elif derecho.derecho_maximo is not None and total_calculado > derecho.derecho_maximo:
    factor = derecho.derecho_maximo / total_calculado
    detalles_finales = self._distribute_clamp(detalles_raw, factor, ...)
```

**Distribución proporcional** (líneas 148-171):

```python
for d in detalles_raw:
    new_subtotal = d.subtotal * factor
    new_igv = new_subtotal * igv_porcentaje
    # ...
```

### 5.4 tipo_tramite = NULL

**Estado actual**: `tipo_tramite` es NULL en todos los registros.

**Por qué**: El frontend aún no lo envía. La implementación está lista para cuando se active:

```python
# En Orchestrator (línea 162)
liquidacion_especifica=LiquidacionPorcentajeObraData(
    datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
    tarifas=tarifas_aplicadas,
    tipo_tramite=None,  # FUTURE: activate when frontend sends it
),

# En Flujo (línea 183)
liquidacion_po = LiquidacionPorcentajeObra.objects.create(
    ...
    tipo_tramite=None,  # FUTURE: activate when frontend sends it
    ...
)
```

**Cuándo se activará**: Cuando el frontend necesite distinguir entre tipos de trámite (OBRA_NUEVA, AMPLIACION, REMODELACION, etc.) para reglas de negocio específicas.

---

## 6. Reglas de Validación

### 6.1 En Orchestrator (HttpError 400 si falla)

| Validación | Condición | Mensaje |
|------------|-----------|---------|
| `valor_declarado > 0` | `valor_declarado <= 0` | "valor_declarado debe ser mayor a 0" |
| Tarifas existentes | `not tarifas` | "No hay tarifas vigentes para edificaciones" |
| Tarifa vigente (explícito) | `not is_vigente` | "Tarifa {id} no está vigente" |
| Tarifa de EDIFICACION | `tipo != EDIFICACION` | "Tarifa {id} no es de edificaciones" |
| IGV vigente | `not igv_vigente` | "No hay IGV vigente" |
| UIT vigente | `not uit_vigente` | "No hay UIT vigente configurado" |
| Derecho vigente | `not derecho` | "No hay DerechoPorcentajeObra vigente" |

### 6.2 En Cotizar (mismas validaciones)

El endpoint `/cotizar` tiene las mismas validaciones pero **no persiste**.

### 6.3 En Core (ValueError, no HttpError)

| Validación | Condición | Excepción |
|------------|-----------|-----------|
| Al menos 1 tarifa | `not tarifas` | `ValueError("At least one tarifa is required")` |

---

## 7. Configuración

### 7.1 DI Bindings

**Archivo**: `backend/modules/liquidaciones/di.py`

Bindings agregados (líneas 78-88):

```python
# Líneas 78-79: Core service — Tipo PorcentajeObra
binder.bind(LiquidacionPorcentajeObraCoreService, to=LiquidacionPorcentajeObraCoreService)

# Líneas 81-82: Flujo — Edificaciones
binder.bind(LiquidacionEdificacionesFlujo, to=LiquidacionEdificacionesFlujo)

# Líneas 84-85: Orchestrator — Edificaciones
binder.bind(LiquidacionEdificacionesOrchestrator, to=LiquidacionEdificacionesOrchestrator)

# Líneas 87-88: Presenter — Edificaciones
binder.bind(LiquidacionEdificacionesPresenter, to=LiquidacionEdificacionesPresenter)
```

### 7.2 API Registration

**Archivo**: `backend/config/api.py`

Controller registrado (línea 87):

```python
from modules.liquidaciones.presentation.controllers.liquidacion_especifico.liquidacion_edificaciones_controller import (
    LiquidacionEdificacionesController,
)

# Línea 87:
api.register_controllers(LiquidacionEdificacionesController)
```

---

## 8. Tests

### 8.1 Archivos de Test

| Archivo | Cobertura |
|---------|-----------|
| `backend/modules/liquidaciones/tests/integration/test_edificaciones_nueva_liquidacion.py` | Creación completa, clamping, auto-fill, explícito |
| `backend/modules/liquidaciones/tests/integration/test_edificaciones_tarifas_vigentes.py` | GET tarifas, listado |

### 8.2 Escenarios de Test Cubiertos

| Escenario | Archivo | Descripción |
|----------|---------|-------------|
| Primera revisión exitosa (auto-fill) | `test_edificaciones_nueva_liquidacion.py` | Array vacío → auto-fill con 3 tarifas |
| Primera revisión exitosa (explícito) | `test_edificaciones_nueva_liquidacion.py` | 3 tarifas explícitas → misma creación |
| Clamping mínimo | `test_edificaciones_nueva_liquidacion.py` | valor_declarado bajo → factor > 1 aplicado |
| Tarifas vigentes | `test_edificaciones_tarifas_vigentes.py` | GET retorna lista con especialidad |

---

## 9. Diferencias vs HU/MS

| Aspecto | HU/MS (M2) | Edificaciones (PO) |
|--------|------------|-------------------|
| **Motor** | `LiquidacionPorMetroCuadradoCoreService` | `LiquidacionPorcentajeObraCoreService` |
| **Input** | 1 tarifa por solicitud | N tarifas por solicitud |
| **Cálculo** | `area_m2 × costo_por_m2` | `valor_declarado × Σ(porcentaje_tarifas)` |
| **Clamping** | Por M2 individuales | Al TOTAL (distribuido proporcionalmente) |
| **tipo_tramite** | N/A | NULL por ahora (future-state) |
| **Modelo** | `LiquidacionPorMetroCuadrado` | `LiquidacionPorcentajeObra` + `LiquidacionPorcentajeObraDetalle` |
| **Detalle** | No existe (1:1) | Existe (1:N por especialidad) |

### 9.1 Similitudes con HU/MS

- Misma arquitectura de 4 capas
- Mismos wrappers de input/output
- Mismo patrón deOrchestrator → Flujo → Core
- Mismo `@transaction.atomic` en Flujo
- Misma validación en Orchestrator con `HttpError`

---

## 10. Modelo de Datos (DB)

### 10.1 Tablas Involucradas

```
liquidaciones_general
    │
    ├── liquidaciones_edificaciones (identidad: id + numero)
    │       │
    │       └── liquidaciones_porcentaje_obra (motor: valor, %)
    │               │
    │               └── liquidaciones_porcentaje_obra_detalles (N por especialidad)
    │
    ├── entidades (upsert por documento)
    ├── proyectos (FK → entidad)
    ├── vigentes_igv (FK snapshot)
    └── vigentes_uit (FK snapshot)
```

### 10.2 Modelo: LiquidacionPorcentajeObra

**Archivo**: `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/liquidacion_tipo.py`
**Líneas**: 151-236

```python
class LiquidacionPorcentajeObra(BaseModel):
    liquidacion_general = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_porcentaje_obra",
    )
    tipo_tramite = models.CharField(...)  # NULL por ahora
    valor_declarado = models.DecimalField(...)
    porcentaje_liquidacion = models.DecimalField(...)  # SUM de tarifas
    derecho_minimo = models.DecimalField(...)
    derecho_maximo = models.DecimalField(...)  # nullable
    porcentaje_minimo_uit = models.DecimalField(...)
    derecho_aplicado = models.ForeignKey("DerechoPorcentajeObra", ...)
```

### 10.3 Modelo: LiquidacionPorcentajeObraDetalle

**Archivo**: `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/liquidacion_tipo.py`
**Líneas**: 239-323

```python
class LiquidacionPorcentajeObraDetalle(BaseModel):
    liquidacion_porcentaje = models.ForeignKey("LiquidacionPorcentajeObra", related_name="detalles")
    tarifa_aplicada = models.ForeignKey("TarifaPorcentajeObra", ...)
    especialidad = models.ForeignKey("usuarios.Especialidad", ...)
    porcentaje_aplicado = models.DecimalField(...)
    subtotal = models.DecimalField(...)
    igv = models.DecimalField(...)
    uit = models.DecimalField(...)
    total = models.DecimalField(...)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion_porcentaje", "especialidad"],
                name="unique_liquidacion_porcentaje_detalle_especialidad",
            )
        ]
```

### 10.4 Modelo: LiquidacionEdificacion

**Archivo**: `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_especifico/liquidacion_edificaciones.py`
**Líneas**: 17-43

```python
class LiquidacionEdificacion(BaseModel, AutoNumeroModel):
    """Wrapper de identidad para Edificaciones."""
    liquidacion = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="edificaciones",
    )
    # numero viene de AutoNumeroModel (autoincremental)
```

---

## 11. Próximos Pasos

### 11.1 RE (Revisión de Expertos)

- Verificar que el clamping al TOTAL (no per-detalle) es correcto según la regla de negocio
- Confirmar que `tipo_tramite = NULL` es intencional por ahora

### 11.2 DE (Desarrollo)

- Activar `tipo_tramite` cuando el frontend lo envíe
- Agregar tests de clamping máximo (si `derecho_maximo` no es NULL)
- Tests de segunda revisión (incrementar `numero`)

### 11.3 MO (Mantenimiento)

- Monitorear que el auto-fill nodevuelva demasiadas tarifas en producción
- Considerar cache de tarifas vigentes (si perf es un problema)

---

## 12. Glosario

| Término | Definición |
|---------|-----------|
| **AutoNumeroModel** | Abstract model con campo `numero` autoincremental por save() |
| **Clamping** | Forzar un valor a un rango [min, max] multiplicando proporcionalmente |
| **Core** | Capa de ORM puro + aritmética (sin lógica de negocio) |
| **Cotización** | Cálculo sin persistencia (solo retorna valores) |
| **Detalle** | Breakdown por especialidad/tarifa (existe en PO, no en M2) |
| **Flujo** | Capa transaccional que coordina múltiples operaciones de Core |
| **Hybrid resolution** | Array vacío = auto-fill; array con elementos = explícito |
| **Orchestrator** | Capa de validación y coordinación (no hace ORM directo) |
| **PorcentajeObra** | Motor de cálculo: valor × sum(%) |
| **Snapshot** | Copia del valor al momento de crear (inmutable después) |
| **tipo_tramite** | Tipo de trámite Edificaciones (OBRA_NUEVA, AMPLIACION, etc.) — NULL por ahora |

---

## 13. Referencias

- **Contrato replicable**: `backend/docs/contracts/LIQUIDACIONES_REPLICABLE_CONTRACT.md`
- **Contrato Edificaciones**: `backend/docs/contracts/LIQUIDACIONES_EDIFICACIONES_CONTRACT.md`
- **Plan de refactorización**: `contract/PLAN_REFACTORIZACION.md`
- **Contrato de nombres**: `backend/doc_dev/EDIFICACIONES_NAMING.md`
