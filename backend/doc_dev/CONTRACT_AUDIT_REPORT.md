# Reporte de Auditoría de Contratos: Backend vs `PLAN_REFACTORIZACION.md`

## Resultado General
Los schemas de salida (Pydantic) cumplen al 100% con la herencia de `BaseSchema`, y las respuestas son exactas. **Sin embargo, a nivel de capas internas, ninguno de los 6 módulos cumple al 100% las reglas arquitectónicas del plan.**

## Infracciones Arquitectónicas Detectadas

### Infracción 1: Lógica en el Controlador (Regla §1-A)
- **Regla:** Los controladores son "sagrados" y tienen CERO lógica (prohibido usar `if`, `for`).
- **Problema:** En los 6 controladores, dentro del endpoint `GET /`, el agente metió lógica de validación manual:
  ```python
  if page < 1: page = 1
  if page_size > 100: page_size = 100
  ```
- **Solución:** Esta lógica debe extraerse a un utilitario de paginación de Ninja o moverse al Orquestador.

### Infracción 2: Llamadas a Base de Datos en el Presentador (Regla §3-A)
- **Regla:** PROHIBIDO llamar a la base de datos en los Presentadores.
- **Problema:** En todos los métodos `present_detalle`, el código hace llamadas perezosas (lazy queries) al ORM de Django:
  - `lg.liquidacion_m2.all()[0]` (en HU y MS)
  - `lpo.detalles.all()` (en Edificaciones, Taludes, Vial)
  - `lg.liquidacion_visitas.first()` (en IO)
- **Solución:** Aunque hicimos `prefetch_related`, usar `.all()` o `.first()` sigue siendo una evaluación de QuerySet. El Presentador solo debería mapear datos planos, no lidiar con la API del ORM.

### Infracción 3: El Presentador asume el rol del Orquestador (Regla §3-C)
- **Regla:** El flujo debe ser: Orquestador retorna `Domain Result` -> Presentador mapea `Domain Result` a `Output Schema`.
- **Problema:** Actualmente, el Orquestador está devolviendo objetos crudos del ORM (`LiquidacionGeneral`). Es el Presentador el que está armando el objeto de dominio (`EdificacionesPrimeraRevisionResult`) iterando sobre el ORM. Esto acopla el Presentador a la estructura de la base de datos.
- **Solución:** El Orquestador debe ser quien mapee el modelo del ORM hacia el `Result` de dominio.

### Infracción 4: Fallback falso de UUID en Inspección de Obra (Regla §1-C)
- **Regla:** Usar `BaseSchema` para mantener consistencia con los `null`.
- **Problema:** En `LiquidacionInspeccionObraPresenter`, si no hay IGV o UIT, el código inventa un UUID falso: `uuid.uuid4()`. Esto pervierte el contrato.
- **Solución:** Debe retornar `None` de forma honesta, igual que hacen los otros 5 presentadores.