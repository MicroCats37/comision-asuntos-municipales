# Estrategia: Endpoints de Listado (GET) para Liquidaciones

## 1. Objetivo
Implementar un endpoint `GET /` en cada uno de los 6 controladores de liquidaciones específicos (Edificaciones, Habilitación Urbana, etc.) que devuelva una lista paginada utilizando el componente `PaginatedData`. 
**Regla estricta:** El schema de salida de cada item en la lista debe ser exactamente el mismo schema detallado que se usa como respuesta al crear la liquidación.

## 2. El Problema de N+1 Consultas

Dado que vamos a devolver el schema completo, necesitamos cargar **todas** las relaciones de la liquidación en la base de datos de un solo golpe. Si no lo hacemos, el ORM hará una consulta extra por cada proyecto, por cada entidad, por cada tarifa y por cada especialidad (miles de queries).

### Solución por Tipo de Liquidación:

**A. Para Edificaciones (Porcentaje de Obra):**
Al hacer el query en Django/ORM, usaremos esta cadena exacta:
```python
LiquidacionGeneral.objects.filter(
    tipo_liquidacion=TipoLiquidacion.EDIFICACION
).select_related(
    'proyecto',
    'proyecto__entidad',
    'municipalidad',
    'usuario_creador',
).prefetch_related(
    'liquidacion_porcentaje_obra',
    'liquidacion_porcentaje_obra__detalles',
    'liquidacion_porcentaje_obra__detalles__tarifa_aplicada',
    'liquidacion_porcentaje_obra__detalles__especialidad',
    'liquidacion_porcentaje_obra__derecho_aplicado',
)
```

**B. Para Habilitación Urbana, Mecánica de Suelos, Taludes, Impacto Vial (M2):**
```python
LiquidacionGeneral.objects.filter(
    tipo_liquidacion=TIPO_CORRESPONDIENTE
).select_related(
    'proyecto', 'proyecto__entidad', 'municipalidad', 'usuario_creador'
).prefetch_related(
    'liquidacion_m2',
    'liquidacion_m2__tarifa_aplicada',
    'liquidacion_m2__derecho',
)
```

**C. Para Inspección de Obra (Visitas):**
```python
LiquidacionGeneral.objects.filter(
    tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA
).select_related(
    'proyecto', 'proyecto__entidad', 'municipalidad', 'usuario_creador'
).prefetch_related(
    'liquidacion_visitas',
    'liquidacion_visitas__tarifa_aplicada',
)
```

## 3. Patrón de Arquitectura (Capas a tocar)

Para implementar esto en cada módulo (ej. Edificaciones), modificaremos 4 capas:

1. **Core Service (`LiquidacionGeneralCoreService`):**
   - Agregaremos un método genérico que acepte el tipo de liquidación y los parámetros de paginación (`page`, `page_size`), aplique los `select_related`/`prefetch_related` correspondientes y devuelva los datos crudos.

2. **Orchestrator (`LiquidacionEdificacionesOrchestrator`):**
   - Agregaremos el método `listar_liquidaciones(page, page_size)`.

3. **Presenter (`LiquidacionEdificacionesPresenter`):**
   - Crearemos un método estático `present_list(liquidaciones, total, page, page_size)`.
   - Iterará sobre las liquidaciones llamando al método `present_primera_revision` existente para reutilizar la misma salida exacta.
   - Envolverá el resultado en `PaginatedData`.

4. **Controller (`LiquidacionEdificacionesController`):**
   - Expondremos la ruta `@router.get("/", response_model=ApiResponse[PaginatedData[LiquidacionEdificacionesOutput]])`.

## 4. Riesgos Asumidos
Reutilizar el schema de creación (`LiquidacionEdificacionesOutput`) para un listado significa que estamos enviando **muchos datos** al frontend (incluyendo el desglose completo de tarifas y especialidades para cada ítem de la lista). 
Esto cumple con tu requerimiento de reutilizar el mismo componente y simplifica el frontend, pero a nivel de red el payload será pesado. Al usar paginación (ej. 10 por página), este impacto es aceptable.