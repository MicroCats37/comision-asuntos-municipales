# SDD Explore — Mapeo completo de modelos Django para admin.py

## 1. Estado Actual

El proyecto `comision-asuntos-municipales` tiene **4 módulos Django** registrados como `LOCAL_APPS`:
- `modules.entidades`
- `modules.usuarios`
- `modules.finanzas`
- `modules.liquidaciones`

**No existen admin.py en ningún módulo.** Solo existe `core/admin.py` que personaliza el app_label de `LiquidacionGeneral`.

Todos los modelos heredan de:
- `core.models.BaseModel` (UUID + timestamps, abstract)
- `core.models.UUIDModel` (solo UUID, abstract)
- `core_application.models.VigenciaModel` (periodo_inicio/periodo_fin, abstract)
- `core_application.models.AutoNumeroModel` (numero auto-incremental, abstract)
- `django.contrib.auth.models.AbstractBaseUser` + `PermissionsMixin` (solo en `Usuario`)

**Todos los modelos concretos tienen `HistoricalRecords` (django-simple-history).** Los modelos `Historical*` resultantes **NO se registran en admin.**

### Convenciones detectadas
- Los módulos usan arquitectura hexagonal: `domain/models/`, `infrastructure/`, `presentation/`
- `domain/models/` tiene archivos por entidad (`usuario.py`, `perfil_ingeniero.py`, etc.)
- `models.py` en la raíz del módulo re-exporta desde `domain/models/`
- Los modelos "específicos" de liquidaciones (Edificación, HU, MS, etc.) son **OneToOne extensions** de `LiquidacionGeneral`, NO tablas separadas independientes
- `MunicipalidadProvincial` y `MunicipalidadDistrital` son **proxy models** de `Municipalidad` — NO se registran standalone
- `ProyectoEmpresarial` y `ProyectoPersonaNatural` son **proxy models** de `Proyecto` — NO se registran standalone
- `Usuario` es custom user model con `AbstractBaseUser` — requiere `UserAdmin` extendido

---

## 2. Tabla Maestra de Modelos

### MÓDULO: usuarios

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `Usuario` | `usuarios_usuario` | BaseModel + DjangoAuthMixin | **STANDALONE** | — | Custom user model. Requiere UserAdmin extendido. Hereda `is_staff` de DjangoAuthMixin. |
| `PerfilIngeniero` | `usuarios_perfilingeniero` | BaseModel + HistoricalRecords | **STANDALONE** | — | OneToOne con Usuario. Datos profesionales CIP. |
| `Capitulo` | `usuarios_capitulo` | BaseModel + HistoricalRecords | **STANDALONE** | — | Catálogo de capítulos profesionales CIP. |
| `EspecialidadIngeniero` | `usuarios_especialidadingeniero` | BaseModel + HistoricalRecords | **STANDALONE** | — | Especialidad profesional vinculada a Capítulo. Combinación (codigo, capitulo) única. |
| `EspecialidadRevision` | `usuarios_especialidadrevision` | BaseModel + HistoricalRecords | **STANDALONE** | — | Solo 3 registros: Civil, Sanitaria, Eléctrica/Mecánica. Para tarifas de liquidación. |
| `IngenieroHabilitacion` | `usuarios_ingenierohabilitacion` | BaseModel + HistoricalRecords | **STANDALONE** | PerfilIngeniero? | Historial de habilitaciones CIP por fecha. Un FK a PerfilIngeniero. No es hijo inline — tiene sentido standalone para ver histórico. |

### MÓDULO: entidades

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `Entidad` | `entidades_entidad` | BaseModel + HistoricalRecords | **STANDALONE** | — | Entidad maestra (RUC→institución, DNI→persona natural). Empresa=Entidad (backward compat). |
| `Banco` | `entidades_banco` | BaseModel + HistoricalRecords | **STANDALONE** | — | Catálogo de bancos. |
| `Contacto` | `entidades_contacto` | BaseModel + HistoricalRecords | **STANDALONE** | — | Contacto reutilizable para Entidad, Municipalidad, Banco. |
| `UbigeoDepartamento` | `entidades_ubigeodepartamento` | BaseModel | **STANDALONE** | — | Jerarquía ubigeo nivel 1. |
| `UbigeoProvincia` | `entidades_ubigeoprovincia` | BaseModel | **STANDALONE** | UbigeoDepartamento | FK a Departamento. |
| `UbigeoDistrito` | `entidades_ubigeodistrito` | BaseModel | **STANDALONE** | UbigeoProvincia | FK a Provincia, tiene código ubigeo 6 dígitos. |
| `Municipalidad` | `entidades_municipalidad` | BaseModel + HistoricalRecords | **STANDALONE** | — | Proxy: `MunicipalidadProvincial` y `MunicipalidadDistrital`. |
| `MunicipalidadProvincial` | (misma tabla) | Proxy de Municipalidad | **NO REGISTRAR** | Municipalidad | Mismo manager que filtra por provincia. |
| `MunicipalidadDistrital` | (misma tabla) | Proxy de Municipalidad | **NO REGISTRAR** | Municipalidad | Mismo manager que filtra por distrito. |
| `Alcalde` | `entidades_alcalde` | BaseModel + VigenciaModel + HistoricalRecords | **STANDALONE** | Municipalidad | Vigencia por periodos. Hijo natural de Municipalidad. |
| `GerenteUrbano` | `entidades_gerenteurbano` | BaseModel + VigenciaModel + HistoricalRecords | **STANDALONE** | Municipalidad | Vigencia por periodos. Hijo natural de Municipalidad. |
| `ContactoMunicipalidad` | `entidades_contactomunicipalidad` | BaseModel + HistoricalRecords | **INLINE** | Municipalidad | Tabla puente municipalidad↔contacto. Mostrar como inline dentro de Municipalidad. |
| `ContactoBanco` | `entidades_contactobanco` | BaseModel + HistoricalRecords | **INLINE** | Banco | Tabla puente banco↔contacto. Mostrar como inline dentro de Banco. |

### MÓDULO: finanzas

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `IGV` | `finanzas_igv` | BaseModel + VigenciaModel + HistoricalRecords | **STANDALONE** | — | Tasa IGV fraccionaria. Catálogo con vigencia. |
| `UIT` | `finanzas_uit` | BaseModel + VigenciaModel + HistoricalRecords | **STANDALONE** | — | Valor UIT en soles. Catálogo con vigencia. |

### MÓDULO: liquidaciones

#### Catálogos ( STANDALONE )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `TipoLiquidacion` | `liquidaciones_tipoliquidacion` | BaseModel | **STANDALONE** | — | Catálogo: Edificación, HU, MS, IV, Taludes, IO. |
| `Proyectista` | `liquidaciones_proyectista` | BaseModel + HistoricalRecords | **STANDALONE** | — | FK a PerfilIngeniero. Unique per perfil. |
| `Delegado` | `liquidaciones_delegado` | BaseModel + HistoricalRecords | **STANDALONE** | — | FK a PerfilIngeniero + FK a EspecialidadRevision. OneToOne. |
| `Inspector` | `liquidaciones_inspector` | BaseModel + HistoricalRecords | **STANDALONE** | — | FK a PerfilIngeniero + FK a EspecialidadRevision. Unique(perfil, especialidad). |
| `InspectorTipoLiquidacion` | `liquidaciones_inspectortipoliquidacion` | BaseModel + HistoricalRecords | **STANDALONE** | Inspector | Catálogo de inspectores por tipo de liquidacion. |
| `LiquidacionEspecialidadDisponibles` | `liquidaciones_liquidacionespecialidaddisponibles` | BaseModel + HistoricalRecords | **STANDALONE** | TipoLiquidacion | Especialidades disponibles por tipo de liquidación. |

#### Modelos de Cálculo — Tarifas y Derechos ( STANDALONE )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `TarifaLiquidacionBase` | `liquidaciones_tarifaliquidacionbase` | BaseModel + VigenciaModel | **STANDALONE** | TipoLiquidacion | Tarifa base con vigencia. OneToOne con TarifaPorMetroCuadrado/TarifaPorcentajeObra. |
| `TarifaPorMetroCuadrado` | `liquidaciones_tarifaporcentajeliquidacion` | BaseModel + HistoricalRecords | **STANDALONE** | TarifaLiquidacionBase | OneToOne a TarifaLiquidacionBase. |
| `TarifaPorCategoriaVisitas` | `liquidaciones_tarifaporcategoriavisitas` | BaseModel + HistoricalRecords | **STANDALONE** | TarifaLiquidacionBase | FK a TarifaLiquidacionBase. |
| `TarifaPorcentajeObra` | `liquidaciones_tarifaporcentajeobra` | BaseModel + HistoricalRecords | **STANDALONE** | TarifaLiquidacionBase + EspecialidadRevision | FK a EspecialidadRevision para cálculo por especialidad. |
| `DerechoPorcentajeObra` | `liquidaciones_derechoporcentajeobra` | BaseModel + VigenciaModel + HistoricalRecords | **STANDALONE** | — | Derecho mínimo porcentual global. |
| `DerechoPorMetroCuadrado` | `liquidaciones_derechoporcentajeliquidacion` | BaseModel + VigenciaModel + HistoricalRecords | **STANDALONE** | — | Derecho mínimo M2 global. |

#### Modelo PRINCIPAL — Liquidación ( STANDALONE con INLINES )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `LiquidacionGeneral` | `liquidaciones_liquidaciongeneral` | BaseModel + HistoricalRecords | **STANDALONE** | — | Modelo central. M2M con EspecialidadRevision. FK a Proyecto, Municipalidad, TipoLiquidacion, IGV, UIT. |

#### Proyectos ( STANDALONE )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `Proyecto` | `liquidaciones_proyecto` | BaseModel + HistoricalRecords | **STANDALONE** | Entidad + UbigeoDistrito | FK a Entidad (PROTECT). Campos denormalizados de entidad. Proxy: `ProyectoEmpresarial`, `ProyectoPersonaNatural`. |
| `ProyectoEmpresarial` | (misma tabla) | Proxy de Proyecto | **NO REGISTRAR** | Proyecto | Filtra por entidad RUC. |
| `ProyectoPersonaNatural` | (misma tabla) | Proxy de Proyecto | **NO REGISTRAR** | Proyecto | Filtra por entidad DNI. |

#### Modelos de Asignación ( padre→hijo )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `DelegadoMunicipalidad` | `liquidaciones_delegadomunicipalidad` | BaseModel + HistoricalRecords | **INLINE** | Delegado | Asignación de distritos a delegado. Unique(delegado, municipalidad, tipo). MUESTRA inline dentro de Delegado. |
| `DelegadoMunicipalidadPeriodo` | `liquidaciones_delegadomunicipalidadperiodo` | BaseModel + VigenciaModel + HistoricalRecords | **INLINE** | DelegadoMunicipalidad | Vigencia del periodo. MUESTRA inline dentro de DelegadoMunicipalidad. |
| `InspectorAsignacionPeriodo` | `liquidaciones_inspectorasignacionperiodo` | BaseModel + VigenciaModel + HistoricalRecords | **INLINE** | InspectorTipoLiquidacion | Vigencia del periodo. MUESTRA inline dentro de InspectorTipoLiquidacion. |

#### Modelos de Vínculo a Liquidación ( INLINES dentro de LiquidacionGeneral )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `LiquidacionDelegado` | `liquidaciones_liquidaciondelegado` | BaseModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | Vínculo delegado↔liquidación. Inline dentro de LiquidacionGeneral. |
| `LiquidacionInspector` | `liquidaciones_liquidacioninspector` | BaseModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | Vínculo inspector↔liquidación. Inline dentro de LiquidacionGeneral. |
| `LiquidacionProyectista` | `liquidaciones_liquidacionproyectista` | BaseModel | **INLINE** | LiquidacionGeneral | Vínculo proyectista↔liquidación. Inline dentro de LiquidacionGeneral. |
| `LiquidacionContacto` | `liquidaciones_liquidacioncontacto` | BaseModel | **INLINE** | LiquidacionGeneral | Tabla puente contacto. Inline dentro de LiquidacionGeneral. |
| `LiquidacionDocumentos` | `liquidaciones_liquidaciondocumentos` | BaseModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | Documentos subidos. Inline dentro de LiquidacionGeneral. |
| `LiquidacionCodigo` | `liquidaciones_liquidacioncodigo` | BaseModel | **STANDALONE**? | — | Códigos de cuenta por tipo de liquidación. Catálogo independiente. |

#### Modelos de Detalle por Tipo de Liquidación ( INLINES / ONE-TO-ONE EXTENSIONS )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `LiquidacionEdificacion` | `liquidaciones_liquidacionedificacion` | BaseModel + AutoNumeroModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | OneToOne. Extensión para régimen de edificaciones. |
| `LiquidacionHabilitacionUrbana` | `liquidaciones_liquidacionhabilitacionurbana` | BaseModel + AutoNumeroModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | OneToOne. Extensión para HU. |
| `LiquidacionMecanicaSuelos` | `liquidaciones_liquidacionmecanicasuelos` | BaseModel + AutoNumeroModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | OneToOne. Extensión para MS. |
| `LiquidacionTaludes` | `liquidaciones_liquidaciontaludes` | BaseModel + AutoNumeroModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | OneToOne. Extensión para Taludes. |
| `LiquidacionInspeccionObra` | `liquidaciones_liquidacioninspeccionobra` | BaseModel + AutoNumeroModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | OneToOne. Extensión para Inspección de Obra. |
| `LiquidacionImpactoVial` | `liquidaciones_liquidacionimpactovial` | BaseModel + AutoNumeroModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | OneToOne. Extensión para Impacto Vial. |

#### Modelos de Cálculo por Liquidación ( INLINES dentro de LiquidacionGeneral )

| Modelo | Tabla DB | Tipo | Categoría | Parent | Notas |
|--------|----------|------|-----------|--------|-------|
| `LiquidacionPorMetroCuadrado` | `liquidaciones_liquidacionporcentajeliquidacion` | BaseModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | Cálculo M2. FK a TarifaPorMetroCuadrado + DerechoPorMetroCuadrado. |
| `LiquidacionPorCategoriaVisitas` | `liquidaciones_liquidacionporcategoriavisitas` | BaseModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | Cálculo por visitas. FK a TarifaPorCategoriaVisitas. |
| `LiquidacionPorcentajeObra` | `liquidaciones_liquidacionporcentajeobra` | BaseModel + HistoricalRecords | **INLINE** | LiquidacionGeneral | OneToOne. Cálculo porcentual. M2M through a TarifaPorcentajeObra. |
| `LiquidacionPorcentajeObraDetalle` | `liquidaciones_liquidacionporcentajeobradetalle` | BaseModel + HistoricalRecords | **INLINE** | LiquidacionPorcentajeObra | Breakdown por especialidad. FK a TarifaPorcentajeObra + EspecialidadRevision. |

---

## 3. Mapa de Inlines Recomendados

### LiquidacionGeneral (Padre principal)
```
LiquidacionGeneral
├── LiquidacionDelegado (TabularInline) — delegados asignados a esta liquidación
├── LiquidacionInspector (TabularInline) — inspectores asignados a esta liquidación
├── LiquidacionProyectista (TabularInline) — proyectistas de esta liquidación
├── LiquidacionContacto (TabularInline) — contactos de esta liquidación
├── LiquidacionDocumentos (TabularInline) — documentos subidos
├── LiquidacionEdificacion (StackedInline) — ONE-TO-ONE si tipo=EDIFICACION
├── LiquidacionHabilitacionUrbana (StackedInline) — ONE-TO-ONE si tipo=HABILITACION_URBANA
├── LiquidacionMecanicaSuelos (StackedInline) — ONE-TO-ONE si tipo=MECANICA_SUELOS
├── LiquidacionTaludes (StackedInline) — ONE-TO-ONE si tipo=TALUDES
├── LiquidacionInspeccionObra (StackedInline) — ONE-TO-ONE si tipo=INSPECCION_OBRA
├── LiquidacionImpactoVial (StackedInline) — ONE-TO-ONE si tipo=IMPACTO_VIAL
├── LiquidacionPorMetroCuadrado (TabularInline) — cálculo M2 (HU, MS, IV, Taludes)
├── LiquidacionPorCategoriaVisitas (TabularInline) — cálculo visitas (IO)
└── LiquidacionPorcentajeObra (StackedInline) — ONE-TO-ONE — cálculo porcentual (Edificaciones)
    └── LiquidacionPorcentajeObraDetalle (TabularInline) — desglose por especialidad
```

**Nota:** Para los OneToOne de tipo específico, se recomienda usar `get_exclude` condicional basado en `tipo_liquidacion` o un solo `StackedInline` genérico que maneje todos.

### Delegado (Hijo de PerfilIngeniero, pero registrado standalone)
```
Delegado
├── DelegadoMunicipalidad (TabularInline) — distritos asignados
│   └── DelegadoMunicipalidadPeriodo (TabularInline) — periodos de vigencia
```

### Inspector (Hijo de PerfilIngeniero, pero registrado standalone)
```
Inspector
└── InspectorTipoLiquidacion (TabularInline) — tipos de liquidación asignados
    └── InspectorAsignacionPeriodo (TabularInline) — periodos de vigencia
```

### Municipalidad
```
Municipalidad
├── ContactoMunicipalidad (TabularInline) — contactos asignados
├── Alcalde (TabularInline) — historial de alcalдель
└── GerenteUrbano (TabularInline) — historial de gerentes urbanos
```

### Banco
```
Banco
└── ContactoBanco (TabularInline) — contactos asignados
```

### TarifaLiquidacionBase
```
TarifaLiquidacionBase
├── TarifaPorMetroCuadrado (StackedInline) — detalle M2 (OneToOne)
├── TarifaPorCategoriaVisitas (TabularInline) — detalle visitas
└── TarifaPorcentajeObra (TabularInline) — detalle porcentual por especialidad
```

### LiquidacionPorcentajeObra
```
LiquidacionPorcentajeObra
└── LiquidacionPorcentajeObraDetalle (TabularInline) — desglose por especialidad
```

---

## 4. Estructura Admin por Módulo

### `modules/usuarios/admin.py`
**Modelos a registrar:**
1. `Usuario` — extender `UserAdmin` existente
2. `PerfilIngeniero` — standalone
3. `Capitulo` — standalone
4. `EspecialidadIngeniero` — standalone
5. `EspecialidadRevision` — standalone
6. `IngenieroHabilitacion` — standalone (histórico, no inline)

**Inlines:** Ninguno (los hijos son independientes)

### `modules/entidades/admin.py`
**Modelos a registrar:**
1. `Entidad` — standalone
2. `Banco` — standalone
3. `Contacto` — standalone
4. `UbigeoDepartamento` — standalone
5. `UbigeoProvincia` — standalone
6. `UbigeoDistrito` — standalone
7. `Municipalidad` — standalone (no proxy)
8. `Alcalde` — standalone (también inline en Municipalidad)
9. `GerenteUrbano` — standalone (también inline en Municipalidad)

**Inlines:**
- `BancoAdmin`: `ContactoBancoInline` (TabularInline)
- `MunicipalidadAdmin`: `ContactoMunicipalidadInline` (TabularInline), `AlcaldeInline` (TabularInline), `GerenteUrbanoInline` (TabularInline)

### `modules/finanzas/admin.py`
**Modelos a registrar:**
1. `IGV` — standalone
2. `UIT` — standalone

**Inlines:** Ninguno

### `modules/liquidaciones/admin.py`
**Modelos a registrar:**
1. `TipoLiquidacion` — standalone
2. `Proyectista` — standalone
3. `Delegado` — standalone (con inline de DelegadoMunicipalidad)
4. `Inspector` — standalone (con inline de InspectorTipoLiquidacion)
5. `LiquidacionEspecialidadDisponibles` — standalone (catálogo)
6. `TarifaLiquidacionBase` — standalone (con inlines de tarifas)
7. `TarifaPorMetroCuadrado` — standalone (o inline de TarifaLiquidacionBase)
8. `TarifaPorCategoriaVisitas` — standalone (o inline de TarifaLiquidacionBase)
9. `TarifaPorcentajeObra` — standalone
10. `DerechoPorcentajeObra` — standalone
11. `DerechoPorMetroCuadrado` — standalone
12. `LiquidacionGeneral` — standalone (con TODOS los inlines de vínculos y cálculo)
13. `LiquidacionCodigo` — standalone (catálogo de códigos por tipo)

**Inlines:**
- `DelegadoAdmin`: `DelegadoMunicipalidadInline` → `DelegadoMunicipalidadPeriodoInline`
- `InspectorAdmin`: `InspectorTipoLiquidacionInline` → `InspectorAsignacionPeriodoInline`
- `LiquidacionGeneralAdmin`:
  - `LiquidacionDelegadoInline`
  - `LiquidacionInspectorInline`
  - `LiquidacionProyectistaInline`
  - `LiquidacionContactoInline`
  - `LiquidacionDocumentosInline`
  - `LiquidacionEdificacionInline`
  - `LiquidacionHabilitacionUrbanaInline`
  - `LiquidacionMecanicaSuelosInline`
  - `LiquidacionTaludesInline`
  - `LiquidacionInspeccionObraInline`
  - `LiquidacionImpactoVialInline`
  - `LiquidacionPorMetroCuadradoInline`
  - `LiquidacionPorCategoriaVisitasInline`
  - `LiquidacionPorcentajeObraInline` → `LiquidacionPorcentajeObraDetalleInline`

---

## 5. Campos Sugeridos

### Usuario
```python
list_display = ['username', 'dni', 'email', 'nombres', 'apellidos', 'is_staff', 'is_active']
search_fields = ['username', 'dni', 'email', 'nombres', 'apellidos']
list_filter = ['is_staff', 'is_active', 'is_superuser']
```

### PerfilIngeniero
```python
list_display = ['cip', 'nombre_completo', 'dni', 'especialidad', 'capitulo', 'correo_institucional']
search_fields = ['cip', 'dni', 'nombres', 'apellido_paterno', 'apellido_materno', 'correo_personal', 'correo_institucional']
list_filter = ['especialidad', 'capitulo', 'genero']
```

### Entidad
```python
list_display = ['numero_documento', 'tipo_documento', 'nombre_completo']
search_fields = ['numero_documento']
list_filter = ['tipo_documento']
```

### Municipalidad
```python
list_display = ['codigo', 'nombre', 'provincia', 'distrito']
search_fields = ['codigo', 'nombre']
list_filter = [('provincia', RelatedOnlyDropdownFilter), ('distrito', RelatedOnlyDropdownFilter)]
```

### LiquidacionGeneral
```python
list_display = ['id', 'proyecto', 'municipalidad', 'tipo_liquidacion', 'estado', 'total', 'fecha_registro']
search_fields = ['proyecto__denominacion', 'expediente', 'proyecto__entidad_numero_documento']
list_filter = ['estado', 'tipo_liquidacion', 'municipalidad', 'fecha_registro']
readonly_fields = ['total', 'sub_total', 'fecha_registro', 'igv_snapshot', 'uit_snapshot']
```

### Delegado
```python
list_display = ['perfil_ingeniero', 'especialidad_revision']
search_fields = ['perfil_ingeniero__nombres', 'perfil_ingeniero__apellido_paterno', 'perfil_ingeniero__cip']
list_filter = ['especialidad_revision']
```

### Inspector
```python
list_display = ['perfil_ingeniero', 'especialidad_revision']
search_fields = ['perfil_ingeniero__nombres', 'perfil_ingeniero__apellido_paterno', 'perfil_ingeniero__cip']
list_filter = ['especialidad_revision']
```

### TarifaLiquidacionBase
```python
list_display = ['tipo_liquidacion', 'periodo_inicio', 'periodo_fin']
search_fields = ['tipo_liquidacion__nombre']
list_filter = ['tipo_liquidacion']
```

### TipoLiquidacion
```python
list_display = ['codigo', 'nombre']
search_fields = ['codigo', 'nombre']
```

### IGV / UIT
```python
list_display = ['valor', 'periodo_inicio', 'periodo_fin', 'vigente']
search_fields = []
list_filter = ['periodo_inicio']
```

---

## 6. Advertencias Importantes

### NO REGISTRAR

1. **`Historical*` (automatic models from django-simple-history)** — todos los modelos con `history = HistoricalRecords()` generan un modelo `HistoricalModelName` paralelo. Estos son de solo lectura para auditoría y **NO deben registrarse en admin**.

2. **Proxy models:**
   - `MunicipalidadProvincial` → herencia de `Municipalidad` (misma tabla)
   - `MunicipalidadDistrital` → herencia de `Municipalidad` (misma tabla)
   - `ProyectoEmpresarial` → herencia de `Proyecto` (misma tabla)
   - `ProyectoPersonaNatural` → herencia de `Proyecto` (misma tabla)

3. **Modelos abstractos:** `BaseModel`, `UUIDModel`, `TimestampedModel`, `VigenciaModel`, `AutoNumeroModel`, `DjangoAuthMixin` — no son modelos concretos, no se registran.

4. **`Usuario` con UserAdmin:** El custom user model requiere extender `django.contrib.auth.admin.UserAdmin` para que los campos de autenticación funcionen correctamente en el admin.

5. **Modelos de infraestructura vacíos:** `modules/usuarios/infrastructure/models.py` y `modules/entidades/infrastructure/models.py` están vacíos (solo comentarios placeholder). No registran nada.

6. **M2M through tables implícitas:** `LiquidacionPorcentajeObra.tarifas_aplicadas` usa `through= LiquidacionPorcentajeObraDetalle` — esta tabla intermedia se gestiona a través del inline, no como modelo standalone.

7. **`LiquidacionGeneral.especialidades_revisadas`** es ManyToMany con `EspecialidadRevision`. El admin de Django maneja M2M nativamente con el widget `filter_horizontal`/`filter_vertical` — no requiere tabla intermedia explícita.

8. **`LiquidacionGeneral.liquidaciones_previas`** es M2M self-referential — también manejado nativamente por Django.

---

## 7. Riesgos

1. **Sobrecarga del admin de `LiquidacionGeneral`**: Tiene ~15 inlines posibles. En la práctica, solo 1-3 aplican según `tipo_liquidacion`. Se recomienda usar `get_inlines` condicional para mostrar solo los relevantes.

2. **`LiquidacionEdificacion` y similares son OneToOne**: Se crearon como extensión de `LiquidacionGeneral`. En admin, mostrarlos como `StackedInline` funciona, pero hay que tener cuidado con el `get_exclude` o `get_inlines` condicional para evitar que todos aparezcan siempre.

3. **`core/admin.py` ya tiene personalización**: Hay un wrapper `get_app_list` que promueve `LiquidacionGeneral` al top. Al crear `modules/liquidaciones/admin.py`, hay que respetar esa personalización.

4. **`DelegadoMunicipalidad` tiene `unique_together`**: `(delegado, municipalidad, liquidacion_revision)` — el inline debe manejar la adición múltiple correctamente.

5. **`Inspector` tiene `unique_together`**: `(perfil_ingeniero, especialidad_revision)` — implica que un ingeniero puede ser inspector para múltiples especialidades solo si son distintas.

6. **`IngenieroHabilitacion`**: No es inline de `PerfilIngeniero` porque tiene sentido standalone para ver el histórico de habilitaciones por fecha. Se recomienda registrarlo independiente.

---

## 8. Próximo Paso Recomendado

**`sdd-propose`**: Dado que este es un trabajo de creación de archivos admin.py (no un cambio en la lógica de negocio), la fase de propuesta puede ser breve — básicamente confirmar la estructura propuesta y proceder directamente a `sdd-tasks` → `sdd-apply`.

Alternativamente, dado que el objetivo es crear archivos admin.py siguiendo patrones conocidos, se puede saltar directamente a `sdd-apply` con los tasks de crear cada admin.py por módulo.
