"use client";

import {
  AlertCircle,
  Calendar,
  ChevronDown,
  FileText,
  MapPin,
  Ruler,
  Truck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { LiquidacionNoEdificacionListItem } from "../types/liquidacion-no-edificacion.types";

interface LiquidacionImpactoVialCardProps {
  item: LiquidacionNoEdificacionListItem;
  onVerDetalle?: (item: LiquidacionNoEdificacionListItem) => void;
}

/** Format currency: 1234.56 -> "S/ 1,234.56" */
const formatCurrency = (value: number): string => {
  return `S/ ${value.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

/** Format date: ISO string -> "dd MMM yyyy" */
const formatDate = (isoString: string): string => {
  if (!isoString) return "—";
  try {
    return new Date(isoString).toLocaleDateString("es-PE", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
};

/** Estado badge using theme variables */
const getEstadoBadgeClass = (estado: string): string => {
  switch (estado) {
    case "PAGADO":
      return "bg-emerald-500/10 text-secondary-foreground border-emerald-500/20";
    case "PENDIENTE":
      return "bg-amber-500/10 text-amber-600 border-amber-500/20";
    case "ANULADO":
      return "bg-destructive/10 text-destructive border-destructive/20";
    default:
      return "bg-muted text-muted-foreground border-border";
  }
};

/** Section card with icon header and visible border */
function SectionCard({
  icon,
  title,
  children,
  className,
}: {
  icon: React.ReactNode;
  title: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-card shadow-sm overflow-hidden",
        className,
      )}
    >
      <div className="flex items-center gap-2 px-4 py-2.5 border-b bg-muted/30">
        <span className="text-muted-foreground/70">{icon}</span>
        <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
          {title}
        </h4>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

/** Label + value row */
function LabelValue({
  label,
  value,
  className,
}: {
  label: string;
  value: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col", className)}>
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
        {label}
      </span>
      <span className="text-sm font-medium text-foreground">{value}</span>
    </div>
  );
}

/**
 * LiquidacionImpactoVialCard — concrete card for Impacto Vial.
 * Shows área (m²), proyecto, municipalidad, expediente, observación, and totales.
 */
export function LiquidacionImpactoVialCard({
  item,
  onVerDetalle,
}: LiquidacionImpactoVialCardProps) {
  const {
    id,
    public_id,
    estado,
    fecha_registro,
    municipalidad_nombre,
    valor_caracteristico,
    proyecto_denominacion,
    expediente,
    observacion,
    totales,
  } = item;

  return (
    <Collapsible className="group bg-card rounded-2xl border shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* HEADER */}
      <CollapsibleTrigger className="w-full px-5 py-4 bg-gradient-to-r from-muted/40 via-muted/20 to-transparent border-b border-border/60 text-left hover:bg-muted/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
          {/* Left: Icon + IDs */}
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 group-hover:bg-primary/15 transition-colors">
              <Truck className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              {/* Primary: Liquidación ID + Status */}
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-lg font-black text-foreground tracking-tight">
                  {public_id}
                </h3>
                <span
                  className={cn(
                    "shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                    getEstadoBadgeClass(estado),
                  )}
                >
                  {estado}
                </span>
              </div>

              {/* Secondary: Project name */}
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                {proyecto_denominacion && (
                  <>
                    <span className="text-xs text-muted-foreground truncate max-w-[280px]">
                      {proyecto_denominacion}
                    </span>
                    <span className="text-xs text-muted-foreground/60 hidden sm:inline">
                      •
                    </span>
                  </>
                )}
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground-foreground">
                  Impacto Vial
                </span>
                {expediente && (
                  <span className="text-xs text-muted-foreground font-mono hidden md:inline">
                    Exp: {expediente}
                  </span>
                )}
              </div>

              {/* Tertiary: Date + ID */}
              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground/70">
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>{formatDate(fecha_registro)}</span>
                </div>
                <span className="hidden sm:inline text-muted-foreground/30">|</span>
                <span className="font-mono hidden md:inline">ID: {id}</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/8 border border-primary/15 text-xs font-bold text-primary">
                  <Ruler className="h-3 w-3" />
                  {valor_caracteristico.toLocaleString("es-PE")} m²
                </span>
              </div>
            </div>
          </div>

          {/* Right: Valor + Chevron */}
          <div className="flex flex-col gap-2 lg:items-end">
            <div className="bg-primary/5 border border-primary/10 rounded-xl px-4 py-2.5 flex items-center gap-3">
              <div className="text-right">
                <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                  Total a Pagar
                </p>
                <p className="text-xl font-black text-primary tracking-tight">
                  {formatCurrency(Number(totales.total_a_pagar))}
                </p>
              </div>
              <ChevronDown className="h-4 w-4 text-primary/40 group-data-[state=open]:rotate-180 transition-transform" />
            </div>
            {onVerDetalle && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onVerDetalle(item);
                }}
                className="h-8 rounded-lg gap-1.5 text-xs font-semibold border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50 w-full lg:w-auto"
              >
                Ver detalle
              </Button>
            )}
          </div>
        </div>
      </CollapsibleTrigger>

      {/* BODY */}
      <CollapsibleContent className="p-5 space-y-4 border-t border-border/40 bg-muted/10">
        {/* Two-column grid: Liquidación + Proyecto */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Liquidación Card */}
          <SectionCard
            icon={<FileText className="h-3.5 w-3.5" />}
            title="Liquidación"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue
                label="Tipo"
                value="Impacto Vial"
              />
              <LabelValue
                label="Área"
                value={`${valor_caracteristico.toLocaleString("es-PE")} m²`}
              />
              {municipalidad_nombre && (
                <LabelValue label="Municipalidad" value={municipalidad_nombre} />
              )}
              {expediente && <LabelValue label="Expediente" value={expediente} />}
            </div>
          </SectionCard>

          {/* Proyecto Card */}
          <SectionCard
            icon={<Truck className="h-3.5 w-3.5" />}
            title="Proyecto"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              {proyecto_denominacion ? (
                <>
                  <LabelValue label="Denominación" value={proyecto_denominacion} />
                  {municipalidad_nombre && (
                    <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                      <span>{municipalidad_nombre}</span>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-xs text-muted-foreground/60 italic">
                  Sin proyecto asociado
                </p>
              )}
            </div>
          </SectionCard>
        </div>

        {/* Totales Card (full width) */}
        <SectionCard
          icon={<Ruler className="h-3.5 w-3.5" />}
          title="Totales"
          className="border-border/60"
        >
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="flex flex-col">
              <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                Subtotal
              </span>
              <span className="text-sm font-bold text-foreground">
                {formatCurrency(Number(totales.subtotal))}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                IGV
              </span>
              <span className="text-sm font-bold text-foreground">
                {formatCurrency(Number(totales.igv))}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                Total
              </span>
              <span className="text-sm font-bold text-foreground">
                {formatCurrency(Number(totales.total))}
              </span>
            </div>
            <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 -my-0.5">
              <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">
                Total a Pagar
              </span>
              <span className="text-base font-black text-primary">
                {formatCurrency(Number(totales.total_a_pagar))}
              </span>
            </div>
          </div>
        </SectionCard>

        {/* Observación (if present) */}
        {observacion && (
          <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
            <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">
                Observación
              </span>
              <p className="text-sm text-amber-700/90 font-medium leading-relaxed mt-0.5">
                {observacion}
              </p>
            </div>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
