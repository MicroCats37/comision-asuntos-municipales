# SDD Apply Progress: separar-especialidades

## Status: ✅ COMPLETE — 208/208 tests integration pasando

## Qué se implementó

Separación de la tabla única `usuarios_especialidad` (modelo `Especialidad`) en DOS modelos:

### EspecialidadIngeniero (perfil del ingeniero)
- Campos: `codigo` (CharField 4) + `nombre` (CharField 100) + `capitulo` (FK al modelo `Capitulo` EXISTENTE — sin duplicar nombre)
- `UniqueConstraint(codigo, capitulo)` — permite código 01 con Civil (cap 02) y Sanitaria (cap 09)
- Seed 6 registros desde Excel SACDLIMA: 01/cap02/ING. CIVIL, 01/cap09/ING. SANITARIA, 02/cap05/ING. MECÁNICO ELECTRICISTA, 04/cap15/ING. ELECTRICISTA, 07/cap15/ING. EN ELECTRICIDAD, 10/cap15/ING. ELECTRICO

### EspecialidadRevision (tarifa/cálculo)
- Campos: `codigo` + `slug` (unique) + `nombre`
- Seed 3 registros: 01/civil/Ingeniería Civil, 02/sanitaria/Ingeniería Sanitaria, 03/electrica-mecanica/Eléctrica/Mecánica

## Migrations

- usuarios: `0003_especialidadrevision_especialidadingeniero_and_more.py`, `0003_1_copy_especialidad_data.py`, `0004_delete_especialidad.py`
- liquidaciones: `0017_historicalinspectortipoliquidacion_and_more.py` (refactor inspectores previo), `0018_alter_historicalliquidacionespecialidaddisponibles_especialidad_and_more.py`

## FKs repuntadas

- `PerfilIngeniero.especialidad` → `EspecialidadIngeniero`
- `TarifaPorcentajeObra.especialidad`, `LiquidacionPorcentajeObraDetalle.especialidad`, `LiquidacionEspecialidadDisponibles.especialidad`, `LiquidacionGeneral.especialidades_revisadas` (M2M) → `EspecialidadRevision`

## 5 imports rotos corregidos

`seed_tarifas_all.py`, `seed_tarifas_edificacion.py`, `load_delegados_reales.py`, `cleanup_especialidad_duplicates.py`, `diagnostic.py` — ahora importan desde `modules.usuarios.domain.models.perfil_ingeniero`.

## Tests ajustados

Fixtures de tests liquidaciones cambiados a `EspecialidadRevision` + slug: `test_hu_detail.py`, `test_edificaciones_tarifas_vigentes.py`, `test_edificaciones_nueva_revision.py`, `test_edificaciones_nueva_liquidacion.py`, `test_tarifas_historicas.py`, `test_iv_detail.py`, `test_iv_list.py`, `test_taludes_detail.py`, `test_taludes_list.py`, `test_inspectores.py`, `conftest.py`.

## Resultado

- 208/208 tests integration pasando
- ~50+ archivos modificados (models, core services, flujos, orquestadores, presenters, schemas, seeds, tests)
- API `/delegados/` mantenida (`EspecialidadOut` id/codigo/nombre) — contrato público no roto

## Nota

El agente apply no persistió este artifact; lo registró el orquestador post-hoc con la información verificada del working tree.
