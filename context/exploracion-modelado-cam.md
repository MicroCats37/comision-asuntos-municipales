# Exploración de Modelado CAM — Análisis y Recomendaciones

**Proyecto:** aplicacion  
**Fecha:** 2026-06-12  
**Alcance:** Modelos Django bajo `core` y `modules` (entidades, usuarios, liquidaciones)

---

## 1. Flujo Real/Ideal de una Comisión de Asuntos Municipales (CAM)

El flujo de trabajo real de un expediente en una CAM es:

```
1. INGRESO DEL EXPEDIENTE
   ├── Un ciudadano/entidad presenta un proyecto ante la municipalidad
   ├── El proyecto puede provenir de:
   │   ├── Una Empresa (con RUC)
   │   ├── Una Persona Natural (con DNI)
   │   └── La propia Municipalidades (auto-proyecto edil)
   └── Se asigna un número de expediente único y fecha de ingreso

2. ETAPA DE PROYECTISTA / ORIGEN
   ├── Se registra el profesional proyectista responsable (vinculado a CIP)
   ├── Se registra la entidad originante (empresa, persona natural, municipalidad)
   └── Puede haber múltiples proyectistas en un mismo expediente

3. REVISIONES POR ESPECIALIDAD
   ├── El expediente es derivado a una o más especialidades técnicas
   ├── Cada especialidad puede:
   │   ├── Aprobar sin observaciones
   │   ├── Emitir OBSERVACIONES (requieren subsanación)
   │   └── Solicitar SUBSANACIONES / levantamientos
   └── Las observaciones tienen estado: abierta, subsanada, no subsanada

4. ETAPA DE DOCUMENTOS
   ├── Documentos adjuntos al expediente (planos, memorias, certificados)
   ├── Documentos de subsanación
   └── Informes técnicos de cada especialidad

5. DICTÁMENES / INFORMES DE COMISIÓN
   ├── Cada especialidad emite un DICTAMEN o INFORME
   ├── El dictamen puede ser: favorable, desfavorable, observado
   └── Finalmente la Comisión emite una DECISIÓN

6. ESTADOS Y HISTORIAL
   ├── El expediente transita por estados: Ingresado, EnRevisión, Observado,
   │   Subsanado, ConDictamen, Aprobado, Desaprobado, Archivado
   └── Cada cambio de estado se registra con fecha, usuario y motivo

7. PARTICIPANTES
   ├── Miembros de la Comisión (con roles: presidente, vocal, secretario)
   ├── Delegados por municipalidad (ingenieros)
   └── Personal administrativo de soporte
```

---

## 2. Modelo Actual vs. Flujo Real — Comparación

### 2.1 Lo que existe actualmente

| Modelo | Ubicación | Descripción |
|--------|-----------|-------------|
| `Empresa` | entidades | RUC, razón social, dirección |
| `PersonaNatural` | entidades | DNI, nombres, apellidos |
| `Contacto` | entidades | Contacto reutilizable (puente) |
| `ContactoEmpresa` | entidades | Puente Empresa→Contacto |
| `ContactoMunicipalidad` | entidades | Puente Municipalidad→Contacto |
| `Municipalidad` | entidades | Provincial o Distrital (XOR) |
| `Alcalde` | entidades | Histórico de alcaldías |
| `GerenteUrbano` | entidades | Histórico de gerentes urbanos |
| `Usuario` | usuarios | Usuario custom con DNI |
| `PerfilIngeniero` | usuarios | Perfil profesional (CIP, capítulo) |
| `Capitulo` | usuarios | Capítulo profesional |
| `Delegado` | liquidaciones | Ingeniero delegado + especialidad |
| `MunicipalidadDelegado` | liquidaciones | Distritos asignados a delegado |
| `PeriodoDelegado` | liquidaciones | Períodos asignados a delegado |
| `Especialidad` | liquidaciones | Nombre de especialidad |
| `EspecialidadPeriodo` | liquidaciones | Especialidad habilitada por período |
| `Proyectista` | liquidaciones | Nombres/apellidos (aislado) |
| `Proyecto` | liquidaciones | Vinculado a Proyectista + (Empresa XOR PersonaNatural) |
| `ProyectoEmpresarial` | liquidaciones | Proxy de Proyecto (empresa) |
| `ProyectoPersonaNatural` | liquidaciones | Proxy de Proyecto (persona natural) |
| `ContactoProyecto` | liquidaciones | Puente Proyecto→Contacto |
| `Revision` | liquidaciones | Revisión de Liquidación por delegado |
| `RevisionDelegado` | liquidaciones | Puente N:M Revision→Delegado |
| `Liquidacion` | liquidaciones | Liquidación de un Proyecto |
| `IGV`, `UIT`, `DerechoMinimo`, `PorcentajeLiquidacion` | liquidaciones | Parámetros fiscales |

### 2.2 Conceptos FALTANTES críticos

| Concepto faltante | Impacto |
|-------------------|---------|
| **Expediente** | No hay entidad que agrupe proyectos relacionados y su flujo活着 |
| **EstadoExpediente / HistorialEstado** | No hay tracking de estados ni auditoría de cambios |
| **Observacion / Subsanacion** | No se modelan las observaciones de especialidades ni su ciclo de vida |
| **Dictamen / Informe** | No existen dictámenes por especialidad ni decisión de comisión |
| **Documento** | No hay modelo para documentos adjuntos (planos, certificados, informes) |
| **MiembroComision** | No se modelan los miembros de la comisión con roles |
| **EntidadOriginante (polimórfico)** | No se puede modelar que el proyecto viene de una municipalidad |
| **EspecialidadRevision** | No hay vínculo entre revisión y especialidad específica |
| **ObservacionRespuesta** | No hay forma de rastrear la subsanación de una observación |

---

## 3. Qué Funciona Bien

1. **BaseModel con UUID** (`core/models/BaseModel`): UUID como PK protege contra enumeración. Bien diseñado.

2. **Patrón XOR con proxy models** en `Proyecto` (empresa vs. persona_natural) y `Municipalidad` (provincia vs. distrito): La validación en `clean()` y los managers personalizados son un patrón correcto.

3. **Tablas puente explícitas con `principal`**: `ContactoEmpresa`, `ContactoMunicipalidad`, `ContactoProyecto` siguen un buen patrón donde se puede marcar un contacto como principal y agregar notas específicas de la relación.

4. **Modelo `Contacto` reutilizable**: En lugar de GenericForeignKey, se usan FK explícitas en cada puente. Esto mantiene la integridad referencial.

5. **Histórico con `simple_history`**: Todos los modelos relevantes tienen `HistoricalRecords` para auditoría.

6. **Parámetros fiscales con vigencia**: `IGV`, `UIT`, `DerechoMinimo`, `PorcentajeLiquidacion` tienen `periodo_inicio`/`periodo_fin` para manejar vigencia temporal. Esto es correcto.

7. **`Delegado` vinculado a `PerfilIngeniero`**: Un delegado es un ingeniero con perfil profesional. Relación correcta.

8. **`Especialidad` y `EspecialidadPeriodo`**: Separa la definición de especialidad de su habilitación por período. Bien diseñado.

---

## 4. Qué Se Ve Odd o Arriesgado

### 4.1 `Proyectista` es un modelo AISLADO sin vínculo a `PerfilIngeniero`

```python
# liquidaciones/domain/models/proyecto.py
class Proyectista(BaseModel):
    nombres = models.CharField(max_length=255)
    apellidos = models.CharField(max_length=255)
```

Un proyectista es un ingeniero, pero no está vinculado a `PerfilIngeniero`. Esto significa:
- Se duplica información (nombres/apellidos ya existen en `PerfilIngeniero`)
- No hay forma de verificar que el proyectista tiene CIP válido
- No hay vínculo con el capítulo profesional

**Riesgo:** Datos inconsistentes y sin validación de profesionales real.

### 4.2 `nombre_propietario` como campo desnormalizado en `Proyecto`

```python
class Proyecto(BaseModel):
    ...
    nombre_propietario = models.CharField(max_length=255)
```

Este campo es texto libre. Debería ser una FK a `Empresa` o `PersonaNatural`. Esto causa:
- No hay integridad referencial
- Si cambia el nombre del propietario, no se actualiza automáticamente
- No se puede consultar proyectos por propietario de forma eficiente

### 4.3 `Proyecto` no puede pertenecer a una `Municipalidad`

El modelo actual permite que un proyecto pertenezca a `Empresa` O a `PersonaNatural`, pero **no a una municipalidad**. En el flujo real CAM, una municipalidad puede generar sus propios proyectos (autogestión edil). Esto es un gap funcional importante.

### 4.4 No hay modelo de `Expediente` — se salta un nivel de abstracción

`Liquidacion` se vincula directamente a `Proyecto`. En el flujo real:
- Un **Expediente** ingresa a la CAM
- Un Expediente puede contener **múltiples Proyectos**
- Cada Proyecto genera una Liquidación

Sin `Expediente`, no se puede:
- Agrupar proyectos relacionados
- Modelar el flujo de revisión por especialidad a nivel expediente
- Registrar una decisión de comisión que abarca múltiples proyectos

### 4.5 `Revision` está acoplada a `Liquidacion`, no a `Proyecto` o `Expediente`

```python
class Revision(BaseModel):
    liquidacion = models.ForeignKey("Liquidacion", ...)
```

Pero en el flujo real, las revisiones son por **especialidad** sobre el proyecto, no sobre la liquidación. La revisión debería ser:
- Sobre el `Proyecto` (o `Expediente`)
- Con una `Especialidad` asignada
- Con estado de observación/subsanación

### 4.6 No hay modelo de `Observacion` ni `Subsanacion`

Las observaciones son centrales en el flujo CAM. No existen como entidades. Esto significa:
- No se puede registrar qué observaciones hizo cada especialidad
- No hay ciclo de vida (abierta → subsanada → verificada)
- No hay forma de adjuntar documentos de subsanación

### 4.7 No hay `Dictamen` ni `Decision`

Cada especialidad emite un dictamen. La comisión toma decisiones. Ninguno de estos existe como modelo.

### 4.8 `distrito` y `provincia` en `Empresa`, `PersonaNatural`, `Municipalidad` son texto libre

Deberían ser FK a `UbigeoDistrito` / `UbigeoProvincia` para:
- Validación de existencia real
- Consultas geográficas
- Integridad referencial

### 4.9 `Usuario` usa `email` como `USERNAME_FIELD`

```python
USERNAME_FIELD = "email"
```

Esto puede causar problemas si el email cambia. Muchos sistemas prefieren usar un identifier interno (DNI) como username y permitir email como campo alternativo.

---

## 5. Modelo de Datos Actual — Diagrama Simplificado

```
                    ┌─────────────────┐
                    │   Municipalidad │
                    │  (Provincial/   │
                    │   Distrital)    │
                    └───────┬─────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
   ┌────────────┐   ┌────────────┐    ┌────────────┐
   │  Empresa   │   │  Banco    │    │  Contacto  │◄──── Tabla puente
   └─────┬──────┘   └────────────┘    └────────────┘      (ContactoEmpresa,
         │                                        ContactoMunicipalidad,
         │                                        ContactoBanco)
         ▼
   ┌────────────┐      ┌────────────┐
   │PersonaNatu.│      │ Proyectista│ (AISLADO - sin FK a PerfilIngeniero)
   └─────┬──────┘      └─────┬──────┘
         │                   │
         │   ┌───────────────┴───────────────┐
         │   │                               │
         ▼   ▼                               ▼
   ┌──────────────────┐            ┌──────────────────┐
   │    Proyecto      │            │    Revision      │
   │ (Empresa XOR     │            │  (liquidacion    │
   │  PersonaNatural) │            │   FK)            │
   └────────┬─────────┘            └────────┬─────────┘
            │                               │
            ▼                               ▼
   ┌──────────────────┐            ┌──────────────────┐
   │   Liquidacion    │            │ RevisionDelegado  │
   │  (proyecto FK)   │            │  (puente N:M)    │
   └──────────────────┘            └──────────────────┘
```

---

## 6. Recomendaciones de Modelado — Pasos Prácticos y Ordenados

### Fase 1: Correcciones FUNDAMENTALES (sin las cuales el sistema no funciona bien)

| # | Acción | Por qué |
|---|--------|---------|
| 1.1 | Crear modelo `Expediente` con `numero`, `fecha_ingreso`, `estado`, `municipalidad_origen` | Agrupa proyectos y modela el flujo real |
| 1.2 | Agregar `Expediente` como FK en `Proyecto` (`proyecto.expediente`) | Un proyecto pertenece a un expediente |
| 1.3 | Vincular `Proyectista` a `PerfilIngeniero` (FK) o eliminar y usar `PerfilIngeniero` directamente | Elimina duplicación y valida CIP |
| 1.4 | Eliminar `nombre_propietario` desnormalizado; usar `empresa` o `persona_natural` directamente | Integridad referencial |
| 1.5 | Crear modelo `EntidadOriginante` (abstracto) o usar GenericForeignKey para permitir que un proyecto venga de Empresa, PersonaNatural o Municipalidades | Modela el origen real del proyecto |

### Fase 2: Modelar el flujo de revisión

| # | Acción | Por qué |
|---|--------|---------|
| 2.1 | Crear modelo `EspecialidadRevision` vinculando `Proyecto` + `Especialidad` + `Delegado` | Quién revisó qué especialidad |
| 2.2 | Crear modelo `Observacion` con `EspecialidadRevision`, `descripcion`, `estado` (abierta/subsanada/cerrada), `fecha` | Ciclo de observaciones |
| 2.3 | Crear modelo `Subsanacion` vinculada a `Observacion` con `documentos` adjuntos | Respuesta a observación |
| 2.4 | Crear modelo `Dictamen` por `EspecialidadRevision` con `tipo` (favorable/desfavorable/observado), `descripcion`, `fecha` | Resultado por especialidad |

### Fase 3: Decisiones y documentos

| # | Acción | Por qué |
|---|--------|---------|
| 3.1 | Crear modelo `DecisionComision` vinculada a `Expediente` con `tipo` (aprobado/desaprobado/observado), `fecha`, `descripcion` | Decisión oficial |
| 3.2 | Crear modelo `Documento` con `expediente` FK, `tipo` (plano/certificado/informe), `archivo`, `fecha` | Documentos adjuntos |
| 3.3 | Crear modelo `MiembroComision` con `usuario`, `rol` (presidente/vocal/secundario), `periodo` | Miembros de la comisión |

### Fase 4: Historial y estados

| # | Acción | Por qué |
|---|--------|---------|
| 4.1 | Crear modelo `EstadoExpediente` con `expediente`, `estado`, `fecha`, `usuario`, `observacion` | Tracking de estados |
| 4.2 | Definir choices para estados: `INGRESADO`, `EN_REVISION`, `OBSERVADO`, `SUBSANADO`, `CON_DICTAMEN`, `APROBADO`, `DESAPROBADO`, `ARCHIVADO` | Máquina de estados |
| 4.3 | Reemplazar `distrito`/`provincia` texto con FK a `Ubigeo*` en `Empresa`, `PersonaNatural`, `Municipalidad` | Integridad geográfica |

---

## 7. Resumen de Gap más Crítico

El sistema actual modela **liquidaciones**, no **expedientes CAM**.

- Lo que existe: `Proyecto` → `Liquidacion` → `Revision`
- Lo que falta: `Expediente` → `Proyecto` → `EspecialidadRevision` → `Observacion` → `Dictamen` → `Decision`

**Empezar por crear `Expediente`** como entidad central. Sin esto, todo lo demás está desorganizado.

---

## 8. Archivos Relevantes Inspectados

| Archivo | Relevancia |
|---------|------------|
| `modules/entidades/domain/models/empresa.py` | Empresa, PersonaNatural, ContactoEmpresa |
| `modules/entidades/domain/models/municipalidad.py` | Municipalidad,Alcalde,GerenteUrbano,ContactoMunicipalidad |
| `modules/entidades/domain/models/contacto.py` | Contacto reutilizable |
| `modules/usuarios/domain/models/usuario.py` | Usuario custom |
| `modules/usuarios/domain/models/perfil_ingeniero.py` | PerfilIngeniero, Capitulo |
| `modules/liquidaciones/domain/models/proyecto.py` | Proyectista, Proyecto, ContactoProyecto |
| `modules/liquidaciones/domain/models/delegado.py` | Delegado, MunicipalidadDelegado, PeriodoDelegado |
| `modules/liquidaciones/domain/models/revision.py` | Revision |
| `modules/liquidaciones/domain/models/revision_delegado.py` | RevisionDelegado (puente) |
| `modules/liquidaciones/domain/models/liquidacion.py` | Liquidacion, PorcentajeLiquidacion |
| `modules/liquidaciones/domain/models/especialidades.py` | Especialidad, EspecialidadPeriodo |
| `modules/liquidaciones/domain/models/impuestos.py` | IGV, UIT, DerechoMinimo |
| `core/models/__init__.py` | BaseModel, UUIDModel, TimestampedModel |
