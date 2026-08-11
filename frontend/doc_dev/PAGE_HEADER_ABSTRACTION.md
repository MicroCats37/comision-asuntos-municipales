# Abstracción de Vistas: PageHeader

## El Problema de Duplicación

Al analizar las vistas de la carpeta deprecada (ej. `LiquidacionesEdificacionesView`, `LiquidacionesImpactoVialView`, etc.), se detectó que todas repiten exactamente el mismo bloque de ~40 líneas de código Tailwind para construir la cabecera de la página:

```tsx
<div className="space-y-4">
  <div className="flex items-center gap-3">
    <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
      <Icono className="h-6 w-6 text-primary" />
    </div>
    <div>
      <h1 className="text-3xl font-black tracking-tight">Título</h1>
      <p className="text-sm text-muted-foreground">Descripción</p>
    </div>
  </div>
  <div className="flex flex-wrap items-center gap-3">
    {/* Botones de acción hardcodeados aquí */}
  </div>
</div>
```

## La Solución Propuesta

Para nuestra nueva arquitectura en `components-app`, crearemos un componente unificado llamado `PageHeader`.

**Ubicación:** `frontend/src/components-app/pages/PageHeader.tsx`

**Interfaz (Contrato):**
```tsx
import type { LucideIcon } from "lucide-react";

interface PageHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  actionNodes?: React.ReactNode; // Permite inyectar cualquier cantidad de botones
}
```

### Cómo se verá el código de las nuevas Vistas

En lugar de 40 líneas de HTML, cada página de dominio (ej. Edificaciones) solo necesitará esto:

```tsx
<PageHeader
  title="Liquidaciones de Edificaciones"
  description="Gestiona las liquidaciones de proyectos de edificación"
  icon={FileText}
  actionNodes={
    <>
      <Button onClick={() => setStepperOpen(true)}>Nueva Liquidación</Button>
      <Button variant="outline">Consultar Ingeniero</Button>
    </>
  }
/>
```

## Beneficios
1. **DRY (Don't Repeat Yourself):** Eliminamos cientos de líneas de código duplicado.
2. **Consistencia Visual:** Si mañana queremos que el título sea más pequeño o el ícono sea cuadrado, cambiamos un solo archivo y las 7 páginas se actualizan automáticamente.
3. **Vistas Limpias:** Cumplimos la regla de que las Vistas (`Views`) deben ser "tontas" y dedicarse solo a componer componentes, no a escribir HTML crudo.