# Flujo de Inspección de Obra (IO) — Documentación

## 1. Concepto

La Inspección de Obra (IO) es un tipo de liquidación **especial y autocontenido**:

- **Siempre es PRIMERA REVISIÓN** (`numero_revision=1`) — no tiene revisiones sucesivas.
- Es **una sola liquidación** por inspección — no se re-revisa.
- Se crea **basándose en una liquidación previa** de otro tipo (Edificaciones o Habilitación Urbana) para **heredar el proyecto**.
- Guarda la **referencia a su liquidación adjuntada** (la de origen).

## 2. Flujo de Creación

```
1. Usuario busca la ÚLTIMA REVISIÓN de un proyecto
   GET /liquidaciones/ultima-revision?tipo_liquidacion=EDIFICACION&proyecto_id=xxx
   → devuelve la liquidación con mayor numero_revision (ej. la revisión 5)

2. Usuario crea la IO
   POST /liquidaciones/inspeccion-obra/nueva-liquidacion/primera-revision
   {
     "liquidacion_previa_id": "<id de la revisión 5>",
     "cantidad_visitas": 3,
     "categoria": "A",
     "inspectores_ids": ["uuid"],
     "proyectistas": [...]
   }

3. Backend:
   a. Busca la liquidación previa por ID
   b. Deriva proyecto_id y municipalidad de esa previa
   c. Crea LiquidacionGeneral NUEVA con:
      - tipo_liquidacion = INSPECCION_OBRA
      - numero_revision = 1  (SIEMPRE)
      - proyecto = proyecto de la previa
      - municipalidad = municipalidad de la previa
   d. Guarda la relación con su liquidación adjuntada:
      - liquidacion_previa.liquidaciones_previas.add(nueva_io)
        (o la nueva_io guarda referencia a la previa en liquidaciones_previas)
   e. Crea el detalle de IO (visitas, categoría, inspectores)
```

## 3. Relación "Liquidación Adjuntada"

El modelo `LiquidacionGeneral` ya tiene:
```python
liquidaciones_previas = models.ManyToManyField(
    "self",
    symmetrical=False,
    related_name="revisiones",
    blank=True,
)
```

**Uso en IO:**
- La IO nueva guarda en `liquidaciones_previas` la referencia a la liquidación de origen (la revisión 5 de edificaciones).
- Esto permite rastrear: "esta IO vino de la revisión 5 del proyecto X".
- Es **independiente**: la liquidación de edificaciones sigue existiendo y puede tener otras liquidaciones/IO asociadas o ser trabajada por otra persona.

## 4. Por qué siempre es primera revisión

A diferencia de Edificaciones (que tiene revisiones 1, 3, 5 del MISMO proyecto), la IO es un **trámite puntual**: se inspecciona la obra una vez y se emite dictamen. No hay concepto de "re-revisar la inspección".

Por eso:
- `numero_revision = 1` siempre.
- No existe `POST /nueva-revision` para IO.
- El `tramite_accion` es `PRIMERA_REVISION`.

## 5. Diferencias clave vs Edificaciones

| Aspecto | Edificaciones | Inspección de Obra |
|---------|---------------|-------------------|
| Revisiones | 1, 3, 5 (impares, +2) | Solo 1 (primera) |
| Nueva revisión | Sí (`POST /nueva-revision`) | No aplica |
| Base para crear | Proyecto completo o previa | `liquidacion_previa_id` (deriva proyecto) |
| Liquidación adjuntada | Guarda previas en `liquidaciones_previas` | Guarda la previa de origen |
| Filtro por tipo | EDIFICACION | INSPECCION_OBRA (se crea) |

## 6. Pendiente de decisión

- ¿La IO guarda la previa en `liquidaciones_previas` de la IO nueva, o se guarda la IO en la lista `revisiones` de la previa? (es lo mismo por ser M2M simétrica, pero definir el semantic)
- ¿Se necesita mostrar la "liquidación adjuntada" en el output de la IO? (ej. un campo `liquidacion_previa` con el id/origen)
