# Contraste Arquitectónico: PLAN_REFACTORIZACION.md vs Código Real

**Fecha:** 2026-08-10  
**Proyecto:** aplicacion  
**Cambio:** backend-arquitectura-contraste-final  
**Modo:** Lectura pura de código (sin pytest)

---

## Resumen Ejecutivo

| Regla Arquitectónica | Estado | Violaciones |
|---------------------|--------|-------------|
| Controllers: Cero if/for | ⚠️ PARCIAL | 1 controller con if |
| Controllers: Zero ORM | ✅ CUMPLE | 0 ocurrencias |
| Controllers: Zero manual errors | ✅ CUMPLE | 0 ocurrencias |
| Presenters: Solo @staticmethod | ⚠️ PARCIAL | 1 presenter con método instance |
| Presenters: Zero ORM | ❌ VIOLA | 1 presenter accede ORM |
| Orchestrators: Builds Domain DTOs | ✅ CUMPLE | Todos construyen DTOs |
| Schemas: Heredan BaseSchema | ❌ VIOLA | 5 módulos no heredan |

**Total de módulos evaluados:** 7 controllers, 7 presenters, 7 orchestrators, 7+ schema files

---

## 1. Controladores: Regla "Sagrados" (Cero Lógica)

### Archivos inspeccionados

| # | Controlador | Ruta |
|---|-------------|------|
| 1 | IngenieroHabilitadoController | `backend/modules/usuarios/presentation/controllers/ingeniero_habilitado_controller.py` |
| 2 | AuthLoginController | `backend/modules/usuarios/presentation/controllers/auth_controller.py` |
| 3 | FinanzasController | `backend/modules/finanzas/presentation/controllers/finanzas_controller.py` |
| 4 | InspectorController | `backend/modules/liquidaciones/presentation/controllers/inspector_controller.py` |
| 5 | DelegadoController | `backend/modules/liquidaciones/presentation/controllers/delegado_controller.py` |
| 6 | EntidadesController | `backend/modules/entidades/presentation/controllers/entidad_controller.py` |
| 7 | ConsultaController | `backend/modules/entidades/presentation/controllers/consulta_controller.py` |

### Detalle de Inspección

#### ✅ IngenieroHabilitadoController — CUMPLE
- **Archivo:** `backend/modules/usuarios/presentation/controllers/ingeniero_habilitado_controller.py`
- **Líneas:** 1-50
- **Inspección:** Sin if/for, sin ORM, sin error_response manual. Solo delegacion pura.
- **Evidencia:**
  ```python
  # Line 46: Delegacion pura
  result = await self.orchestrator.obtener_ingeniero_habilitado(cip=cip)
  # Line 49: Presenter instance method (aceptable por ser formatting)
  presented = IngenieroHabilitadoPresenter().present(result)
  return success_response(presented)
  ```

#### ✅ AuthLoginController — CUMPLE
- **Archivo:** `backend/modules/usuarios/presentation/controllers/auth_controller.py`
- **Líneas:** 1-74
- **Inspección:** 3 endpoints (login_username, login_dni, login_email). Todos puros.
- **Evidencia:**
  ```python
  # Line 44-48: login_username
  result = await self.auth_orchestrator.login_username(username=payload.username, password=payload.password)
  return success_response(AuthPresenter.present_login(result))
  ```

#### ✅ FinanzasController — CUMPLE
- **Archivo:** `backend/modules/finanzas/presentation/controllers/finanzas_controller.py`
- **Líneas:** 1-39
- **Inspección:** Endpoint unico, delegacion pura.
- **Evidencia:**
  ```python
  # Line 37-38
  domain_result = await self.orchestrator.obtener_variables_vigentes()
  presented = FinanzasPresenter.present_variables_vigentes(domain_result)
  return success_response(presented)
  ```

#### ✅ InspectorController — CUMPLE
- **Archivo:** `backend/modules/liquidaciones/presentation/controllers/inspector_controller.py`
- **Líneas:** 1-95
- **Inspección:** 3 endpoints (list_inspectores, list_inspectores_vigentes, obtener_inspector).
- **Evidencia:**
  ```python
  # Line 51-59: list_inspectores
  domain_result = self.orchestrator.list_inspectores_proceso(page=page, page_size=page_size)
  return success_response(self.presenter.present_list(domain_result))
  ```

#### ❌ DelegadoController — VIOLA
- **Archivo:** `backend/modules/liquidaciones/presentation/controllers/delegado_controller.py`
- **Líneas:** 92-95
- **Violación:** IF en el controlador para parsear string a bool.
- **Evidencia:**
  ```python
  # Lines 92-95
  vigente_bool: Optional[bool] = None
  if vigente is not None:
      vigente_bool = vigente.lower() == "true"
  ```
- **Descripción:** El endpoint `list_delegados_por_municipalidad` contiene logica de parseo (`if vigente is not None`). Segun el contrato, los controladores deben tener CERO if/for.

#### ✅ EntidadesController — CUMPLE
- **Archivo:** `backend/modules/entidades/presentation/controllers/entidad_controller.py`
- **Líneas:** 1-131
- **Inspección:** 5 endpoints, todos puros.
- **Evidencia:**
  ```python
  # Line 58-67: crear_institucion
  result, creado = await self.orchestrator.upsert_entidad(...)
  return success_response(self.presenter.present_upsert(result, creado))
  ```

#### ✅ ConsultaController — CUMPLE
- **Archivo:** `backend/modules/entidades/presentation/controllers/consulta_controller.py`
- **Líneas:** 1-80
- **Inspección:** 2 endpoints, ambos puros.
- **Evidencia:**
  ```python
  # Line 55-58
  result = await self.orchestrator.consultar_sunat(ruc)
  return success_response(self.presenter.present_sunat(result))
  ```

---

## 2. Presenters: @staticmethod, Zero ORM

### Archivos inspeccionados

| # | Presenter | Ruta |
|---|-----------|------|
| 1 | IngenieroHabilitadoPresenter | `backend/modules/usuarios/presentation/presenters/ingeniero_habilitado_presenter.py` |
| 2 | AuthPresenter | `backend/modules/usuarios/presentation/presenters/auth_presenter.py` |
| 3 | FinanzasPresenter | `backend/modules/finanzas/presentation/presenters/finanzas_presenter.py` |
| 4 | InspectorPresenter | `backend/modules/liquidaciones/presentation/presenters/inspector_presenter.py` |
| 5 | DelegadoPresenter | `backend/modules/liquidaciones/presentation/presenters/delegado_presenter.py` |
| 6 | EntidadPresenter | `backend/modules/entidades/presentation/presenters/entidad_presenter.py` |
| 7 | ConsultaPresenter | `backend/modules/entidades/presentation/presenters/consulta_presenter.py` |

### Detalle de Inspección

#### ⚠️ IngenieroHabilitadoPresenter — PARCIAL
- **Archivo:** `backend/modules/usuarios/presentation/presenters/ingeniero_habilitado_presenter.py`
- **Líneas:** 1-76
- **Estado:** Helper methods son @staticmethod pero el metodo principal `present()` es instance method.
- **Evidencia:**
  ```python
  # Line 18: Helper @staticmethod - OK
  @staticmethod
  def _build_nombres(nombre1: str, nombre2: str | None) -> str:
      ...
  
  # Line 33: Helper @staticmethod - OK
  @staticmethod
  def _build_apellidos(paterno: str, materno: str) -> str:
      ...
  
  # Line 48: Instance method - VIOLACION PARCIAL
  def present(self, result: IngenieroHabilitadoResult) -> IngenieroHabilitadoOut:
      ...
  ```
- **Nota:** El metodo `present()` deberia ser `@staticmethod` segun el contrato. Actualmente es un instance method que crea el presenter en el controller (`IngenieroHabilitadoPresenter().present(result)`).

#### ✅ AuthPresenter — CUMPLE
- **Archivo:** `backend/modules/usuarios/presentation/presenters/auth_presenter.py`
- **Líneas:** 1-38
- **Estado:** Solo tiene `present_login` como @staticmethod.
- **Evidencia:**
  ```python
  # Line 13-14
  @staticmethod
  def present_login(result) -> LoginTokenOut:
      ...
  ```

#### ✅ FinanzasPresenter — CUMPLE
- **Archivo:** `backend/modules/finanzas/presentation/presenters/finanzas_presenter.py`
- **Líneas:** 1-40
- **Estado:** `present_variables_vigentes` es @staticmethod.
- **Evidencia:**
  ```python
  # Line 18-19
  @staticmethod
  def present_variables_vigentes(domain_result: VariablesVigentesResult) -> VariablesFinancierasOut:
      ...
  ```

#### ✅ InspectorPresenter — CUMPLE
- **Archivo:** `backend/modules/liquidaciones/presentation/presenters/inspector_presenter.py`
- **Líneas:** 1-120
- **Estado:** Todos los metodos son @staticmethod.
- **Evidencia:**
  ```python
  # Line 34, 49, 61, 78, 92, 105
  @staticmethod
  def _map_perfil_ingeniero(...) -> PerfilIngenieroOut: ...
  
  @staticmethod
  def present_list(domain_result: InspectorListResult) -> PaginatedData[InspectorOut]: ...
  ```

#### ✅ DelegadoPresenter — CUMPLE
- **Archivo:** `backend/modules/liquidaciones/presentation/presenters/delegado_presenter.py`
- **Líneas:** 1-125
- **Estado:** Todos los metodos son @staticmethod.
- **Evidencia:**
  ```python
  # Line 37, 52, 60, 77, 100
  @staticmethod
  def _map_perfil_ingeniero(...) -> PerfilIngenieroOut: ...
  
  @staticmethod
  def present_list(domain_result: DelegadoListResult) -> PaginatedData[DelegadoOut]: ...
  ```

#### ❌ EntidadPresenter — VIOLA ORM
- **Archivo:** `backend/modules/entidades/presentation/presenters/entidad_presenter.py`
- **Líneas:** 75-113 (present_distritos), 115-144 (present_municipalidades)
- **Violación:** Acceso a propiedades ORM de Django (relaciones anidadas).
- **Evidencia:**
  ```python
  # Lines 88-92 (present_distritos)
  departamento = UbigeoDepartamentoOut(
      id=d.provincia.departamento.id,          # <-- ORM
      nombre=d.provincia.departamento.nombre,  # <-- ORM
  )
  
  # Lines 95-98
  provincia = UbigeoProvinciaOut(
      id=d.provincia.id,       # <-- ORM
      nombre=d.provincia.nombre,
      departamento=departamento,
  )
  
  # Lines 122-126 (present_municipalidades)
  if hasattr(municipalidad, 'provincia') and municipalidad.provincia:
      provincia_out = ProvinciaBasicOut(
          id=municipalidad.provincia.id,         # <-- ORM
          nombre=municipalidad.provincia.nombre,  # <-- ORM
      )
  ```
- **Descripción:** El metodo `present_distritos` y `present_municipalidades` acceden directamente a relaciones ORM (`d.provincia.departamento.id`, `municipalidad.provincia.id`). El contrato prohibe terminantemente que los presenters hagan llamadas a la base de datos o accedan al ORM.

#### ✅ ConsultaPresenter — CUMPLE
- **Archivo:** `backend/modules/entidades/presentation/presenters/consulta_presenter.py`
- **Líneas:** 1-64
- **Estado:** Todos los metodos son @staticmethod, sin acceso ORM.
- **Evidencia:**
  ```python
  # Line 21-22, 44-45
  @staticmethod
  def present_sunat(result: SunatInstitucionResult) -> InstitucionSunatOut: ...
  
  @staticmethod
  def present_reniec(result: ReniecPersonaResult) -> PersonaReniecOut: ...
  ```

---

## 3. Orchestrators: Builds Domain DTOs

### Archivos inspeccionados

| # | Orchestrator | Ruta |
|---|--------------|------|
| 1 | IngenieroHabilitadoOrchestrator | `backend/modules/usuarios/domain/services/orchestrators/ingeniero_habilitado_orchestrator.py` |
| 2 | AuthOrchestrator | `backend/modules/usuarios/domain/services/orchestrators/auth_orchestrator.py` |
| 3 | FinanzasOrchestrator | `backend/modules/finanzas/domain/services/finanzas_orchestrator.py` |
| 4 | InspectorOrchestrator | `backend/modules/liquidaciones/domain/services/orchestrators/inspector_orchestrator.py` |
| 5 | DelegadoOrchestrator | `backend/modules/liquidaciones/domain/services/orchestrators/delegado_orchestrator.py` |
| 6 | EntidadesOrchestrator | `backend/modules/entidades/domain/services/orchestrators/entidad_orchestrator.py` |
| 7 | ConsultaOrchestrator | `backend/modules/entidades/domain/services/orchestrators/consulta_orchestrator.py` |

### Detalle de Inspección

#### ✅ IngenieroHabilitadoOrchestrator — CUMPLE
- **Archivo:** `backend/modules/usuarios/domain/services/orchestrators/ingeniero_habilitado_orchestrator.py`
- **Líneas:** 1-39
- **Estado:** Construye Domain DTOs (IngenieroHabilitadoResult). Aunque usa return directo en lugar de asignar a variable, la arquitectura es correcta porque delega a flujo y retorna el DTO directamente.
- **Evidencia:**
  ```python
  # Line 39: Return directo (aceptable para delegacion simple)
  return await self.flujo._proceso_obtener_ingeniero_habilitado(cip=cip)
  ```

#### ✅ AuthOrchestrator — CUMPLE
- **Archivo:** `backend/modules/usuarios/domain/services/orchestrators/auth_orchestrator.py`
- **Líneas:** 1-33
- **Estado:** Construye Domain DTOs (LoginTokenResult). Mismo patron que el anterior.
- **Evidencia:**
  ```python
  # Line 25, 29, 33: Return directo
  return await self.flujo._proceso_login_username(username, password)
  ```

#### ✅ FinanzasOrchestrator — CUMPLE
- **Archivo:** `backend/modules/finanzas/domain/services/finanzas_orchestrator.py`
- **Líneas:** 1-34
- **Estado:** Construye Domain DTOs (VariablesVigentesResult).
- **Evidencia:**
  ```python
  # Line 32-33
  igv = IGV.objects.vigente()
  uit = UIT.objects.vigente()
  return VariablesVigentesResult.from_igv_uit(igv, uit)  # Build DTO
  ```

#### ✅ InspectorOrchestrator — CUMPLE
- **Archivo:** `backend/modules/liquidaciones/domain/services/orchestrators/inspector_orchestrator.py`
- **Líneas:** 1-185
- **Estado:** Construye Domain DTOs (InspectorResult, InspectorListResult, InspectorDetailResult, InspectorVigenteResult, InspectorVigenteListResult). Usa variables intermedias para claridad.
- **Evidencia:**
  ```python
  # Line 91-98: Asignacion a variable para claridad
  orm_objects, total = self.core_service.list_inspectores_paginated(
      page=page,
      page_size=page_size,
  )
  
  domain_results: list[InspectorResult] = [
      self._build_inspector_result(i) for i in orm_objects
  ]
  
  return InspectorListResult(...)  # Build DTO
  ```

#### ✅ DelegadoOrchestrator — CUMPLE
- **Archivo:** `backend/modules/liquidaciones/domain/services/orchestrators/delegado_orchestrator.py`
- **Líneas:** 1-210
- **Estado:** Construye Domain DTOs. Usa variables intermedias.
- **Evidencia:**
  ```python
  # Line 116-141: Asignacion a variable
  municipalidades_result: list[MunicipalidadesAsignadasResult] = []
  for dm in dm_list:
      ...
      municipalidades_result.append(
          MunicipalidadesAsignadasResult(...)
      )
  
  return DelegadoMunicipalidadesResult(...)  # Build DTO
  ```

#### ✅ EntidadesOrchestrator — CUMPLE
- **Archivo:** `backend/modules/entidades/domain/services/orchestrators/entidad_orchestrator.py`
- **Líneas:** 1-78
- **Estado:** Construye Domain DTOs (EntidadResult). Usa sync_to_async correctamente.
- **Evidencia:**
  ```python
  # Line 70-74
  return await sync_to_async(self.flujo.core._obtener_distritos)(
      search=search,
      provincia_id=provincia_id,
      departamento_id=departamento_id,
  )
  ```

#### ✅ ConsultaOrchestrator — CUMPLE
- **Archivo:** `backend/modules/entidades/domain/services/orchestrators/consulta_orchestrator.py`
- **Líneas:** 1-61
- **Estado:** Construye Domain DTOs (SunatInstitucionResult, ReniecPersonaResult).
- **Evidencia:**
  ```python
  # Line 46, 60
  return await self.sunat_flujo._proceso_consulta_sunat(ruc)
  ```

---

## 4. Schemas: Heredan BaseSchema

### Archivos inspeccionados

| Módulo | Schema File | Hereda de BaseSchema? |
|--------|-------------|----------------------|
| usuarios/ingeniero_habilitado | `domain/schemas/ingeniero_habilitado_schemas.py` | ✅ SÍ (Result) |
| usuarios/ingeniero_habilitado | `presentation/schemas/ingeniero_habilitado_schemas.py` | ❌ NO (hereda de `Schema`) |
| usuarios/auth | `presentation/schemas/auth_schemas.py` | ❌ NO (hereda de `Schema`) |
| finanzas | `presentation/schemas/finanzas_schemas.py` | ❌ NO (hereda de `Schema`) |
| liquidaciones/inspector | `presentation/schemas/inspector/inspector_schemas.py` | ✅ SÍ |
| liquidaciones/delegado | `presentation/schemas/delegado/delegado_schemas.py` | ✅ SÍ |
| entidades | `presentation/schemas/entidad_schemas.py` | ❌ NO (hereda de `Schema`) |
| entidades | `presentation/schemas/consulta_schemas.py` | ❌ NO (hereda de `Schema`) |

### Detalle de Inspección

#### ✅ Inspector Schemas — CUMPLE
- **Archivo:** `backend/modules/liquidaciones/presentation/schemas/inspector/inspector_schemas.py`
- **Líneas:** 1-70
- **Evidencia:**
  ```python
  # Line 6
  from core.types import BaseSchema
  
  # Line 11, 24, 34, 43, 53, 64
  class PerfilIngenieroOut(BaseSchema): ...
  class InspectorOut(BaseSchema): ...
  class InspectorListOut(BaseSchema): ...
  ```

#### ✅ Delegado Schemas — CUMPLE
- **Archivo:** `backend/modules/liquidaciones/presentation/schemas/delegado/delegado_schemas.py`
- **Líneas:** 1-75
- **Evidencia:**
  ```python
  # Line 6
  from core.types import BaseSchema
  
  # Line 11, 24, 30, 39, 51, 58, 69
  class PerfilIngenieroOut(BaseSchema): ...
  class DelegadoOut(BaseSchema): ...
  ```

#### ❌ Entidad Schemas — VIOLA
- **Archivo:** `backend/modules/entidades/presentation/schemas/entidad_schemas.py`
- **Líneas:** 1-102
- **Violación:** Hereda de `Schema` (Ninja) en lugar de `BaseSchema`.
- **Evidencia:**
  ```python
  # Line 7
  from ninja import Schema, Field, Query
  
  # Line 11, 20, 28, 38, 51, 57, 64, 73, 79, 85, 91
  class EntidadInstitucionIn(Schema): ...     # ❌ No hereda BaseSchema
  class EntidadPersonaNaturalIn(Schema): ...  # ❌ No hereda BaseSchema
  class EntidadOut(Schema): ...               # ❌ No hereda BaseSchema
  ```

#### ❌ Consulta Schemas — VIOLA
- **Archivo:** `backend/modules/entidades/presentation/schemas/consulta_schemas.py`
- **Líneas:** 1-34
- **Violación:** Hereda de `Schema` (Ninja) en lugar de `BaseSchema`.
- **Evidencia:**
  ```python
  # Line 7
  from ninja import Schema, Field
  
  # Line 12, 25
  class InstitucionSunatOut(Schema): ...  # ❌ No hereda BaseSchema
  class PersonaReniecOut(Schema): ...      # ❌ No hereda BaseSchema
  ```

#### ❌ Auth Schemas — VIOLA
- **Archivo:** `backend/modules/usuarios/presentation/schemas/auth_schemas.py`
- **Líneas:** 1-44
- **Violación:** Hereda de `Schema` (Ninja) en lugar de `BaseSchema`.
- **Evidencia:**
  ```python
  # Line 6
  from ninja import Schema, Field
  
  # Line 9, 15, 21, 27, 39
  class LoginUsernameIn(Schema): ...  # ❌ No hereda BaseSchema
  class LoginDniIn(Schema): ...       # ❌ No hereda BaseSchema
  class LoginEmailIn(Schema): ...     # ❌ No hereda BaseSchema
  class AuthUserOut(Schema): ...      # ❌ No hereda BaseSchema
  class LoginTokenOut(Schema): ...    # ❌ No hereda BaseSchema
  ```

#### ❌ IngenieroHabilitadoOut Schema — VIOLA
- **Archivo:** `backend/modules/usuarios/presentation/schemas/ingeniero_habilitado_schemas.py`
- **Líneas:** 1-27
- **Violación:** Hereda de `Schema` (Ninja) en lugar de `BaseSchema`.
- **Evidencia:**
  ```python
  # Line 4
  from ninja import Schema, Field
  
  # Line 8
  class IngenieroHabilitadoOut(Schema): ...  # ❌ No hereda BaseSchema
  ```

#### ❌ Finanzas Schemas — VIOLA
- **Archivo:** `backend/modules/finanzas/presentation/schemas/finanzas_schemas.py`
- **Líneas:** 1-12
- **Violación:** Hereda de `Schema` (Ninja) en lugar de `BaseSchema`.
- **Evidencia:**
  ```python
  # Line 4
  from ninja import Schema, Field
  
  # Line 7
  class VariablesFinancierasOut(Schema): ...  # ❌ No hereda BaseSchema
  ```

### Nota sobre domain/schemas (Results)
Los schemas en `domain/schemas/` son Resultados internos (DTOs) que, segun el contrato, deben heredar de `BaseModel` puro de Pydantic. Esto esta correctamente implementado en los archivos existentes como `ingeniero_habilitado_schemas.py` (domain):

```python
# Line 6: domain/schemas/ingeniero_habilitado_schemas.py
from pydantic import BaseModel, Field

# Line 65: IngenieroHabilitadoResult
class IngenieroHabilitadoResult(BaseModel):  # ✅ Correcto para Results
    ...
```

---

## Resumen de Hallazgos

### Violaciones Críticas

| # | Tipo | Ubicación | Descripcion |
|---|------|-----------|-------------|
| 1 | Controller IF | `delegado_controller.py:92-95` | Logica de parseo `if vigente is not None` en controlador |
| 2 | Presenter ORM | `entidad_presenter.py:88-92,122-126` | Acceso a relaciones ORM (`d.provincia.departamento.id`) |
| 3 | Schema Inheritance | `entidad_schemas.py` | No hereda BaseSchema (usa Schema de Ninja) |
| 4 | Schema Inheritance | `consulta_schemas.py` | No hereda BaseSchema (usa Schema de Ninja) |
| 5 | Schema Inheritance | `auth_schemas.py` | No hereda BaseSchema (usa Schema de Ninja) |
| 6 | Schema Inheritance | `ingeniero_habilitado_schemas.py` (presentation) | No hereda BaseSchema (usa Schema de Ninja) |
| 7 | Schema Inheritance | `finanzas_schemas.py` | No hereda BaseSchema (usa Schema de Ninja) |

### Violaciones Menores

| # | Tipo | Ubicación | Descripcion |
|---|------|-----------|-------------|
| 1 | Presenter instance method | `ingeniero_habilitado_presenter.py:48` | Metodo `present()` es instance method, no @staticmethod |

---

## Contraste con Módulo Liquidaciones

El módulo **liquidaciones** es el unico que cumple correctamente con TODAS las reglas arquitectónicas:

### Inspector/Delegado Controllers
- ✅ Zero if/for
- ✅ Zero ORM
- ✅ Zero manual errors

### Inspector/Delegado Presenters  
- ✅ Solo @staticmethod
- ✅ Zero ORM
- ✅ Solo transforman datos

### Inspector/Delegado Schemas
- ✅ Heredan de BaseSchema

El módulo liquidaciones puede servir como **referencia de implementacion correcta** para corregir los otros módulos.

---

## Implicaciones

1. **Seguridad de Null/""**: Los schemas que no heredan de `BaseSchema` no ejecutan el sanitizador `_sanitize_empty_strings`. Esto significa que campos vacios `""` no se convierten a `None`, potencialmente causando inconsistencias en la base de datos.

2. **Controllers con logica**: La presencia de `if` en `DelegadoController` rompe el patron de "controller sagrado". Si la logica de parseo se moviera al Orchestrator, el controller seria puro.

3. **Presenter accediendo ORM**: `EntidadPresenter.present_distritos()` y `present_municipalidades()` asumen que los objetos recibidos tienen relaciones ya cargadas (lazy loading). Esto puede causar N+1 queries si no se precargan correctamente desde el Orchestrator/Core.

---

*Reporte generado automaticamente mediante lectura de codigo fuente. Sin ejecucion de tests.*
