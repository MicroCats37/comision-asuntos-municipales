/**
 * CalculoDetail — Bloque de detalle de cálculo específico por motor.
 *
 * Cada tipo de liquidación tiene su propio sub-componente que se renderiza
 * dentro del `calculoSlot` del LiquidacionCardShell:
 * - PorcentajeObra (Edif/Taludes/IV) → Valor declarado + % + Derecho mínimo
 *   + UIT + % Mín. UIT
 * - M2 (HU/MS) → Área + Costo por m²
 * - Visitas (IO) → Cantidad + Categoría + Inspector + CIP
 *
 * Las ESPECIALIDADES no se renderizan aquí: viven en `DelegadosListBySpecialty`
 * (mismo bloque que los delegados) para evitar duplicar el nombre de la
 * especialidad como chip + sub-header.
 *
 * Layout: heading full-width + grid responsivo cuyo número de columnas escala
 * con la cantidad de items y el viewport (`calculoGridCols(N)`).
 */
import { Calculator, MapPin, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { calculoGridCols } from "../../utils/calculoGridCols";

export interface CalculoPorcentajeProps {
  motor: "porcentaje";
  valorDeclarado?: number | null;
  porcentajeLiquidacion?: number | null;
  derechoMinimo?: number | null;
  /** Valor de la UIT vigente al registro (S/). Viene de `lg.uit.valor`. */
  uit?: number | null;
  /** % mínimo sobre la UIT configurado para esta liquidación (decimal 0-100). */
  porcentajeMinimoUit?: number | null;
  formatCurrency: (v: number | null | undefined) => string;
  formatDecimalPercent: (v: number | null | undefined) => string;
}

export function CalculoPorcentaje({
  valorDeclarado,
  porcentajeLiquidacion,
  derechoMinimo,
  uit,
  porcentajeMinimoUit,
  formatCurrency,
  formatDecimalPercent,
}: CalculoPorcentajeProps) {
  const items: Array<{ label: string; value: string }> = [];
  if (valorDeclarado != null && valorDeclarado > 0) {
    items.push({
      label: "Valor declarado",
      value: formatCurrency(valorDeclarado),
    });
  }
  if (porcentajeLiquidacion != null) {
    items.push({
      label: "% Liq.",
      value: formatDecimalPercent(porcentajeLiquidacion),
    });
  }
  if (derechoMinimo != null && derechoMinimo > 0) {
    items.push({
      label: "Der. Mín.",
      value: formatCurrency(derechoMinimo),
    });
  }
  if (uit != null && uit > 0) {
    items.push({
      label: "UIT",
      value: formatCurrency(uit),
    });
  }
  if (porcentajeMinimoUit != null) {
    items.push({
      label: "% Mín. UIT",
      value: formatDecimalPercent(porcentajeMinimoUit),
    });
  }

  return (
    <CalculoDetailLayout
      icon={<Calculator />}
      titulo="Tarifas aplicadas"
      subtitulo="Resumen del cálculo"
      items={items}
    />
  );
}

export interface CalculoM2Props {
  motor: "m2";
  areaM2?: number | null;
  costoPorM2?: number | null;
  derechoMinimo?: number | null;
  formatCurrency: (v: number | null | undefined) => string;
}

export function CalculoM2({
  areaM2,
  costoPorM2,
  derechoMinimo,
  formatCurrency,
}: CalculoM2Props) {
  const items: Array<{ label: string; value: string }> = [];
  if (areaM2 != null && areaM2 > 0) {
    items.push({
      label: "Área",
      value: `${areaM2.toLocaleString("es-PE")} m²`,
    });
  }
  if (costoPorM2 != null && costoPorM2 > 0) {
    items.push({
      label: "Costo por m²",
      value: formatCurrency(costoPorM2),
    });
  }
  if (derechoMinimo != null && derechoMinimo > 0) {
    items.push({
      label: "Derecho mínimo",
      value: formatCurrency(derechoMinimo),
    });
  }

  return (
    <CalculoDetailLayout
      icon={<MapPin />}
      titulo="Cálculo por m²"
      subtitulo="Área y tarifa aplicada"
      items={items}
    />
  );
}

export interface CalculoVisitasProps {
  motor: "visitas";
  cantidadVisitas?: number | null;
  categoria?: string | null;
  inspectores?: Array<{
    perfil_ingeniero?: { nombre_completo?: string; cip?: string };
  }>;
  formatCurrency: (v: number | null | undefined) => string;
}

export function CalculoVisitas({
  cantidadVisitas,
  categoria,
  inspectores,
}: CalculoVisitasProps) {
  const items: Array<{ label: string; value: string }> = [];
  if (cantidadVisitas != null) {
    items.push({
      label: "Cantidad de visitas",
      value: `${cantidadVisitas}`,
    });
  }
  if (categoria) {
    items.push({ label: "Categoría", value: categoria });
  }
  const inspector = inspectores?.[0]?.perfil_ingeniero;
  if (inspector?.nombre_completo) {
    items.push({ label: "Inspector", value: inspector.nombre_completo });
  }
  if (inspector?.cip) {
    items.push({ label: "CIP", value: inspector.cip });
  }

  return (
    <CalculoDetailLayout
      icon={<User />}
      titulo="Cálculo de visitas"
      subtitulo="Inspección de obra"
      items={items}
    />
  );
}

// ── Layout compartido ────────────────────────────────────────────────

interface CalculoDetailLayoutProps {
  icon: React.ReactNode;
  titulo: string;
  subtitulo: string;
  items: Array<{ label: string; value: string }>;
}

/**
 * Responsivo: el número de columnas crece con la cantidad de items y el
 * viewport, manteniendo los bloques homogéneos (mismo ancho de celda) en
 * cada breakpoint sin filas desbalanceadas.
 *
 * `calculoGridCols` lives in `utils/calculoGridCols.ts` so the detail
 * modal can reuse the same distribution.
 */

function CalculoDetailLayout({
  icon,
  titulo,
  subtitulo,
  items,
}: CalculoDetailLayoutProps) {
  return (
    <section
      className={cn(
        "grid items-stretch overflow-hidden rounded-xl border border-rose-100 bg-rose-50/40 mt-3.5",
        calculoGridCols(items.length),
      )}
    >
      {/* Heading full-width */}
      <div
        className="grid items-center gap-2 px-3.5 py-3 text-primary"
        style={{
          gridColumn: "1 / -1",
          gridTemplateColumns: "auto 1fr",
          columnGap: "8px",
          backgroundColor: "var(--color-rose-50, #fff4f3)",
          borderBottom: "1px solid #edcfd1",
        }}
      >
        <span
          aria-hidden
          className="inline-flex items-center justify-center text-primary"
          style={{ width: "18px", height: "18px" }}
        >
          {icon}
        </span>
        <div className="min-w-0">
          <strong className="block text-[12px] uppercase tracking-wider font-bold leading-tight">
            {titulo}
          </strong>
          <span className="block text-[10px] text-muted-foreground mt-0.5">
            {subtitulo}
          </span>
        </div>
      </div>

      {/* Items del cálculo */}
      {items.length === 0 ? (
        <div
          className="px-3.5 py-3 text-[11px] italic text-muted-foreground"
          style={{ gridColumn: "1 / -1" }}
        >
          Sin datos de cálculo registrados.
        </div>
      ) : (
        items.map((item, i) => (
          <div
            key={item.label}
            className="px-3.5 py-3 flex flex-col justify-center min-w-0"
            style={{
              borderLeft: i === 0 ? "none" : "1px solid #edcfd1",
            }}
          >
            <span className="block uppercase text-[10px] font-bold tracking-wider text-muted-foreground leading-tight">
              {item.label}
            </span>
            <strong className="block mt-1 text-[12px] font-bold text-neutral-900 leading-tight">
              {item.value}
            </strong>
          </div>
        ))
      )}
    </section>
  );
}
