# Estrategia de Reconstrucción del Frontend (Clean Rebuild)

## 1. El Diagnóstico (Olores Arquitectónicos)

Tras auditar `frontend/src/`, estos son los problemas estructurales críticos que justifican una reconstrucción desde cero en lugar de un refactor:

1. **Componentes Masivos (God Objects):**
   - Archivos como `LiquidacionEdificacionesSingleFormModal.tsx` o `deprecadedForm.tsx` superan las 1000-1500 líneas.
   - Mezclan: renderizado UI, estado de formulario (React Hook Form), mutaciones API (React Query), lógica de modales hijos y CSS Grid hardcodeado.
2. **Manipulación Directa del DOM (Prints):**
   - Todos los archivos `*-print.ts` (`impacto-vial-print.ts`, etc.) construyen HTML inyectando nodos directamente (`document.createElement`, `appendChild`) saltándose el Virtual DOM de React.
   - Existe código duplicado en todos ellos para dar formato a monedas y fechas.
3. **Views que hacen demasiado:**
   - Archivos como `LiquidacionesEdificacionesView.tsx` controlan estados de modales, filtros, y lógica de negocio.
   - En una arquitectura limpia, una Vista (`View`) debe ser "tonta": solo recibe datos de un Hook y orquesta componentes.
4. **Tipos Mezclados:**
   - En `types/liquidacion-edificaciones.ts` conviven tipos de respuesta de API, DTOs de formularios, y tipos de tarjetas visuales. Deben estar separados.

## 2. Módulos Deprecados y a Eliminar

- **`features/auth/`**: A pedido, este módulo entero se marcará como **`[DEPRECADO]`**. Sus flujos (Zustand + Vistas de Login) se reconstruirán bajo la nueva arquitectura.
- **`deprecadedForm.tsx`**: Archivo de +1100 líneas sin uso real, con errores de TypeScript y lógica obsoleta. **Eliminación inmediata**.
- **`hooks/useCrearLiquidacion.ts`**: Obsoleto a favor de hooks específicos por tipo.

## 3. La Nueva Arquitectura Propuesta (Domain-Driven)

En lugar de tener carpetas gigantes de `components/`, `hooks/` y `types/` donde conviven todos los tipos de liquidaciones, separaremos por **Dominios**.

### Estructura de Carpetas Objetivo:
```text
frontend/src/features/
├── liquidaciones/
│   ├── domains/                      # 🏗️ NUEVO: Separación estricta
│   │   ├── edificaciones/            # Todo lo específico de Edificaciones
│   │   │   ├── hooks/                # (ej. useCrearEdificacion)
│   │   │   ├── components/           # (ej. EdificacionCotizacionForm)
│   │   │   ├── types/                
│   │   │   │   ├── api/              # Contratos de red
│   │   │   │   ├── form/             # Esquemas Zod (DTOs)
│   │   │   │   └── display/          # Props de UI
│   │   │   └── pages/                
│   │   ├── inspeccion-obra/          # Aislado de Edificaciones
│   │   └── mecanica-suelos/          # Aislado de Edificaciones
│   │
│   ├── shared/                       # ♻️ Reutilizable transversalmente
│   │   ├── components/               # (ej. LiquidacionGeneralCard)
│   │   ├── print/                    # NUEVO sistema de impresión sin tocar el DOM
│   │   └── types/                    # Tipos comunes (Entidad, Proyecto)
│   │
│   └── views/                        # Vistas delgadas que solo componen
```

## 4. Reglas Estrictas para la Reconstrucción

Al rearmar los componentes (ej. el formulario de Edificaciones) en la nueva carpeta `domains/`, seguiremos estas reglas inviolables:

1. **Vistas Delgadas (Thin Views):** Las carpetas `views/` y `pages/` **no** pueden tener lógica de negocio. Solo componen layouts llamando a Smart Fields.
2. **Formularios Basados en Smart Fields:** Ningún modal de formulario superará las 300 líneas. Si crece, la lógica compleja se extrae a un "Smart Field" (ver `SMART_FIELD_ARCHITECTURE.md`) que se inyecta vía `customFields`.
3. **Impresión Abstraída:** Todo el código espagueti de `document.createElement` se reemplazará por un generador de PDFs puro, llamado a través de un Hook genérico (`usePdfGenerator`).
4. **Hooks como única fuente de datos:** Un componente visual nunca llama a Axios ni a fetch directamente. Siempre consume un hook dentro de `domains/*/hooks/`.

## 5. Plan de Acción (Fase 1)

Para demostrar el modelo sin romper la app actual:
1. Crear la estructura `features/liquidaciones/domains/edificaciones/`.
2. Reconstruir **únicamente el flujo de Edificaciones** desde cero allí adentro.
3. Crear el nuevo sistema de Smart Fields acoplado a tu `GenericForm`.
4. Una vez validado, aplicar el mismo patrón a `auth` (reconstrucción completa) y al resto de liquidaciones (Taludes, Vial, etc.).
