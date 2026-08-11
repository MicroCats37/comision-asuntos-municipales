# Estrategia de Arquitectura: Cards de Liquidaciones

## 1. El Olor Arquitectónico (Code Smell)

Actualmente, las vistas dependen de `LiquidacionGeneralCard`, un componente de 533 líneas que actúa como un "God Object". Recibe cualquier tipo de liquidación y usa declaraciones `switch` y ternarios para decidir qué mostrar:
```tsx
// MAL PATRÓN ACTUAL:
tipoLiquidacion === "inspeccion-obra" ? (mostrar_visitas) :
tipoLiquidacion === "edificacion" ? (mostrar_porcentajes) :
(mostrar_m2) 
```
Esto viola el principio Abierto/Cerrado (OCP) de SOLID.

Además, la UI de **Paginación** (los botones y el contador de páginas) está duplicada manualmente en las 6 vistas.

## 2. La Solución (Patrón de Composición)

Aplicaremos un patrón de composición estricto. Construiremos **1 Base** y **6 Wrappers**.

### A. La Base (UI Tonta)
Crearemos `LiquidacionBaseCard.tsx`. Solo sabrá dibujar el contenedor, el encabezado (expediente, fecha, estado, total) y manejar el acordeón (abrir/cerrar). No tendrá idea de qué tipo de liquidación está mostrando.

```tsx
interface LiquidacionBaseCardProps {
  expediente: string;
  fecha_registro: string;
  total: number;
  estado: string;
  children: React.ReactNode; // Aquí se inyecta la magia específica
}
```

### B. Los 6 Wrappers de Dominio (Smart Cards)
Cada tipo de liquidación tendrá su propia tarjeta (ej. `LiquidacionEdificacionesCard.tsx`). Esta tarjeta recibirá el tipo de dato exacto de su API, llamará a la Base para pintarse, y le pasará sus datos específicos como `children`.

```tsx
// Ejemplo: LiquidacionHabilitacionUrbanaCard.tsx
export const LiquidacionHUCard = ({ item }: { item: LiquidacionHUOutput }) => {
  return (
    <LiquidacionBaseCard expediente={item.expediente} total={item.total} ...>
      {/* Contenido 100% específico de HU sin switches */}
      <div className="grid">
        <span>Área: {item.area_m2} m2</span>
        <span>Costo por m2: {item.costo_m2}</span>
      </div>
    </LiquidacionBaseCard>
  );
}
```

### C. Abstracción de Paginación
Crearemos `src/components/ui/LiquidacionPagination.tsx`.
Recibirá las props de tu hook actual (`page`, `pageSize`, `total`, `totalPages`, `setPage`) y dibujará los botones. Las vistas pasarán de tener 40 líneas de código de paginación a solo 1.

## 3. Plan de Acción

1. **Crear `LiquidacionBaseCard` y `LiquidacionPagination`**.
2. **Crear la Card específica para Edificaciones** (`LiquidacionEdificacionesCard`) y conectarla a la vista `LiquidacionesEdificacionesView` usando los nuevos endpoints del backend.
3. **Replicar** el patrón para las otras 5 vistas (HU, MS, IV, Taludes, IO).
4. **Eliminar** el monstruo `LiquidacionGeneralCard`.