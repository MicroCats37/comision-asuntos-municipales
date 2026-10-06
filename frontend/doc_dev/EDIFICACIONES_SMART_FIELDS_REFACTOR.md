# Refactorización: Formulario de Edificaciones a Smart Fields

## 1. El Problema Actual

El formulario actual (`LiquidacionEdificacionesSingleFormModal.tsx`) usa `GenericForm` pasándole un render prop (`children`) enorme. Dentro de ese render prop, hay un diseño en CSS grid (`grid-area-tramite` y `grid-area-proyecto`) donde están mezclados:
- Inputs genéricos
- Lógica de la tabla de revisiones (Zustand + Hooks de API)
- Lógica de cotización (Zustand + Mutations + Watchers de RHF)
- Un componente complejo de búsqueda de entidad (`EntidadLookupField`)
- Lógica de sincronización mediante `useEffect`

Esto va en contra de la arquitectura limpia de UI, ensuciando la vista del modal.

## 2. La Solución: Smart Fields vía `customFields`

`GenericForm` tiene una propiedad llamada `customFields`. Acepta un mapa de componentes y les inyecta el objeto `methods` (que contiene `control`, `watch`, `setValue`, etc. de React Hook Form).

La estrategia es extraer los bloques complejos de UI en sus propios componentes ("Smart Fields") que se conecten al estado del formulario por su cuenta, sin ensuciar el componente padre.

### A. Extrayendo la Tabla de Revisiones
Actualmente, la lógica de inicialización y selección de `RevisionesVigentesTable` está en el modal principal.

**El Smart Field:**
```tsx
import { useController, UseFormReturn } from "react-hook-form";
import { useEdificacionStepperStore } from "@/features/...";

export function RevisionesVigentesSmartField({ 
  methods 
}: { 
  methods: UseFormReturn<FormData> 
}) {
  const store = useEdificacionStepperStore();
  const { data: revisiones, isLoading } = useRevisionesVigentes({...});
  
  // Aquí encapsulamos la lógica de selección que antes ensuciaba el modal
  const handleSelect = (id: string) => {
    if (!store.lockedRevisionIds?.includes(id)) {
      store.setSelectedTarifasId(id);
      // Opcional: sincronizar con RHF si es necesario
      methods.setValue("revisiones_ids", [id]); 
    }
  };
  
  return (
    <RevisionesVigentesTable 
      revisiones={revisiones}
      selectedId={store.selectedTarifasIds}
      onSelectRevision={handleSelect}
      isLoading={isLoading}
    />
  );
}
```

### B. Extrayendo la Cotización
La cotización escucha (`watch`) los valores del proyecto y dispara mutaciones.

**El Smart Field:**
```tsx
export function CotizacionSmartField({ methods }: { methods: UseFormReturn<FormData> }) {
  const store = useEdificacionStepperStore();
  const cotizacionMutation = useCotizacionPrimeraRevision();
  
  // El Smart Field se suscribe localmente a lo que necesita, evitando re-renders del modal gigante
  const valorProyecto = methods.watch("valor_proyecto");
  const valorBaseCalculo = methods.watch("valor_base_calculo");
  
  const handleCotizar = async () => {
    // Toda la lógica de cotización se encapsula aquí
  };
  
  return (
    <CotizacionSection
      quote={store.cotizacion.quote}
      onCotizar={handleCotizar}
      isLoading={cotizacionMutation.isPending}
    />
  );
}
```

### C. El `EntidadLookupField`
Este componente ya está casi listo para ser un Smart Field porque acepta la prop `control`. Solo hay que pasárselo de manera limpia.

## 3. Estrategia de Migración (Fases)

### Fase 1: Extracción de Smart Fields (Manteniendo el Layout)
Dado que el modal actual tiene un layout muy específico (CSS Grid con 2 columnas asimétricas `tramite` y `proyecto`), **NO** es recomendable pasar a la configuración JSON (`formSections`/`fields`) de golpe, porque perderías el control del layout.

**Cómo queda el modal refactorizado (Fase 1):**

```tsx
<GenericForm
  formId="liquidacion-edificaciones-form"
  schema={formSchema}
  formMethods={formMethods}
  onSubmit={handleSubmit}
>
  {() => {
    // El modal ahora solo se encarga del LAYOUT, no de la lógica de negocio.
    return (
      <div className="grid grid-areas-liquidacion-modal">
        {/* REGIÓN TRÁMITE */}
        <div className="grid-in-tramite space-y-4">
          <GenericInput field={{ name: 'municipalidad_id', type: 'searchable-select' }} control={formMethods.control} />
          <GenericInput field={{ name: 'expediente', type: 'text' }} control={formMethods.control} />
          
          {/* Smart Fields Inyectados */}
          <RevisionesVigentesSmartField methods={formMethods} />
          <CotizacionSmartField methods={formMethods} />
        </div>

        {/* REGIÓN PROYECTO */}
        <div className="grid-in-proyecto space-y-4">
          {/* Este Smart Field internamente maneja 3 inputs (tipo, numero, razon social) */}
          <EntidadLookupField control={formMethods.control} />
          <ContactosSection contactos={store.contactos} />
        </div>
      </div>
    );
  }}
</GenericForm>
```

### Fase 2: Configuración Declarativa (Futuro)
Cuando los layouts sean más estandarizados en la app, podrías eliminar el render prop y usar la inyección automática:

```tsx
<GenericForm
  schema={formSchema}
  fields={[
    { name: 'expediente', type: 'text', label: 'Expediente' },
    // Slots fantasma para inyectar Smart Fields en la iteración automática
    { name: 'slot_revisiones', type: 'custom' },
    { name: 'slot_cotizacion', type: 'custom' }
  ]}
  customFields={{
    'slot_revisiones': (methods) => <RevisionesVigentesSmartField methods={methods} />,
    'slot_cotizacion': (methods) => <CotizacionSmartField methods={methods} />
  }}
/>
```

## 4. Resumen Arquitectónico

1. **El `GenericForm` nunca debe modificarse** para admitir casos raros de Edificaciones.
2. **El Modal no debe tener lógica de negocio** ni watchers de inputs. Solo layout.
3. **Los Smart Fields encapsulan el desorden**. Saben de Zustands, saben de mutaciones y saben a qué campos de React Hook Form conectarse mediante el objeto `methods`.