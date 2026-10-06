/**
 * CalculoDetail — Bloque de detalle de cálculo específico por motor.
 *
 * Cada tipo de liquidación tiene su propio sub-componente que se renderiza
 * dentro del `delegadosSlot` del LiquidacionCardShell:
 * - PorcentajeObra (Edif/Taludes/IV) → Valor declarado + % + Especialidades
 * - M2 (HU/MS) → Área + Costo por m²
 * - Visitas (IO) → Cantidad + Categoría + Inspector + CIP
 *
 * Layout grid 4-col con título coloreado a la izquierda.
 */
import {
  Banknote,
  Calculator,
  CheckCircle2,
  MapPin,
  Receipt,
  User,
} from "lucide-react";

export interface CalculoPorcentajeProps {
  motor: "porcentaje";
  valorDeclarado?: number | null;
  porcentajeLiquidacion?: number | null;
  derechoMinimo?: number | null;
  especialidades?: string[];
  formatCurrency: (v: number | null | undefined) => string;
  formatDecimalPercent: (v: number | null | undefined) => string;
}

export function CalculoPorcentaje({
  valorDeclarado,
  porcentajeLiquidacion,
  derechoMinimo,
  especialidades,
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
      label: "Porcentaje de liquidación",
      value: formatDecimalPercent(porcentajeLiquidacion),
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
      icon={<Calculator />}
      titulo="Tarifas aplicadas"
      subtitulo="Resumen del cálculo"
      items={items}
      especialidades={especialidades}
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
  especialidades?: string[];
}

function CalculoDetailLayout({
  icon,
  titulo,
  subtitulo,
  items,
  especialidades,
}: CalculoDetailLayoutProps) {
  return (
    <section
      className="grid items-stretch"
      style={{
        marginTop: "14px",
        gridTemplateColumns:
          "minmax(180px, 1.15fr) repeat(2, 1fr) minmax(220px, 1.5fr)",
        border: "1px solid #eadedf",
        backgroundColor: "#fffafa",
        borderRadius: "11px",
        overflow: "hidden",
      }}
    >
      {/* Col 1: heading */}
      <div
        className="p-3.5 grid"
        style={{
          gridTemplateColumns: "auto 1fr",
          columnGap: "7px",
          alignContent: "center",
          color: "#a90c24",
          backgroundColor: "#fff4f3",
        }}
      >
        <span style={{ color: "#a90c24", width: "18px", height: "18px" }}>
          {icon}
        </span>
        <div>
          <strong className="text-[12px] uppercase tracking-wider font-bold">
            {titulo}
          </strong>
          <span className="text-[10px] text-neutral-500 block mt-0.5">
            {subtitulo}
          </span>
        </div>
      </div>

      {/* Items del cálculo */}
      {items.map((item, i) => (
        <div
          key={item.label}
          className="p-3.5 flex flex-col justify-center"
          style={{ borderLeft: "1px solid #eadedf" }}
        >
          <span className="block uppercase text-[10px] font-bold tracking-wider text-neutral-500">
            {item.label}
          </span>
          <strong className="block mt-1 text-[12px] font-bold text-neutral-900">
            {item.value}
          </strong>
        </div>
      ))}

      {/* Último slot: Especialidades (chips) o vacío */}
      <div
        className="p-3.5 flex flex-col justify-center min-w-0"
        style={{ borderLeft: "1px solid #eadedf" }}
      >
        <span className="block uppercase text-[10px] font-bold tracking-wider text-neutral-500 flex items-center gap-1">
          <Receipt className="h-3 w-3" />
          Especialidades
        </span>
        {especialidades && especialidades.length > 0 ? (
          <div className="flex flex-wrap gap-1 mt-1">
            {especialidades.map((esp) => (
              <span
                key={esp}
                className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-white border text-[11px] leading-tight"
                style={{
                  maxWidth: "100%",
                  borderColor: "#e5c5c6",
                  color: "#272124",
                  whiteSpace: "normal",
                }}
              >
                {esp}
              </span>
            ))}
          </div>
        ) : (
          <span className="block mt-1 text-[11px] italic text-neutral-500">
            Sin especialidades
          </span>
        )}
      </div>
    </section>
  );
}
