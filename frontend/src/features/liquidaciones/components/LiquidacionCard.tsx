"use client";

import {
  AlertCircle,
  Banknote,
  Building2,
  Calendar,
  ChevronDown,
  FileText,
  HardHat,
  Hash,
  MapPin,
  Plus,
  Scale,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { LiquidacionSnapshotListItem } from "../types/liquidacion-edificaciones";

interface LiquidacionCardProps {
  item: LiquidacionSnapshotListItem;
  /** Callback when user clicks "Nueva revisión" — passes full snapshot item */
  onNuevaRevision?: (item: LiquidacionSnapshotListItem) => void;
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

const formatEnumLabel = (value: string | null | undefined): string => {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

/** Full enum labels for better UX */
const getTipoTramiteLabel = (value: string | null | undefined): string => {
  switch (value) {
    case "OBRA_NUEVA":
      return "Obra Nueva";
    case "DEMOLICION":
      return "Demolición";
    case "AMPLIACION":
      return "Ampliación";
    case "REMODELACION":
      return "Remodelación";
    case "MODIFICACION_LICENCIA":
      return "Modificación de Licencia";
    default:
      return formatEnumLabel(value);
  }
};

const getTramiteAccionLabel = (value: string | null | undefined): string => {
  switch (value) {
    case "PRIMERA_REVISION":
      return "1ra. Revisión";
    case "REVISION":
      return "Revisión";
    default:
      return formatEnumLabel(value);
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
  headerClassName,
}: {
  icon: React.ReactNode;
  title: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-card shadow-sm overflow-hidden",
        className,
      )}
    >
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-2.5 border-b bg-muted/30",
          headerClassName,
        )}
      >
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
  valueClassName,
}: {
  label: string;
  value: React.ReactNode;
  className?: string;
  valueClassName?: string;
}) {
  return (
    <div className={cn("flex flex-col", className)}>
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
        {label}
      </span>
      <span
        className={cn("text-sm font-medium text-foreground", valueClassName)}
      >
        {value}
      </span>
    </div>
  );
}

/**
 * LiquidacionCard — renders a Liquidacion at first level with an accordion
 * for Edificaciones details.
 *
 * The accordion shows the full Edificaciones breakdown (proyectistas,
 * especialidades/revisiones, and totales) that was previously shown flat.
 */
export function LiquidacionCard({
  item,
  onNuevaRevision,
}: LiquidacionCardProps) {
  const {
    liquidacion_id,
    numero_liquidacion,
    public_id,
    estado,
    fecha_registro,
    municipalidad,
    observacion,
    proyecto,
    edificaciones,
    totales,
  } = item;

  // Build location string for proyecto
  const proyectoLocation = [
    proyecto.distrito?.nombre,
    proyecto.distrito?.provincia?.nombre,
  ]
    .filter(Boolean)
    .join(", ");

  // Build location string for municipalidad
  const municipalidadLocation = [
    municipalidad.distrito?.nombre,
    municipalidad.provincia?.nombre,
  ]
    .filter(Boolean)
    .join(", ");

  const hasMultipleProyectistas = edificaciones.proyectistas.length > 1;

  return (
    <Collapsible className="group bg-card rounded-2xl border shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* ════════════════════════════════════════════════════════════════════
          HEADER: Identity & Status + Total (CollapsibleTrigger)
      ════════════════════════════════════════════════════════════════════ */}
      <CollapsibleTrigger className="w-full px-5 py-4 bg-gradient-to-r from-muted/40 via-muted/20 to-transparent border-b border-border/60 text-left hover:bg-muted/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
          {/* Left: Icon + IDs */}
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 group-hover:bg-primary/15 transition-colors">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              {/* Primary: Liquidación ID + Status */}
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-lg font-black text-foreground tracking-tight">
                  {public_id || numero_liquidacion}
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

              {/* Secondary: Internal ID + Project name */}
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                {public_id &&
                  numero_liquidacion &&
                  public_id !== numero_liquidacion && (
                    <span className="text-xs text-muted-foreground font-mono">
                      N° {numero_liquidacion}
                    </span>
                  )}
                <span className="text-xs text-muted-foreground/60 hidden sm:inline">
                  •
                </span>
                <span className="text-xs text-muted-foreground truncate max-w-[280px]">
                  {proyecto.nombre}
                </span>
              </div>

              {/* Tertiary: Date + ID + Trámite badges */}
              <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground/70">
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>{formatDate(fecha_registro)}</span>
                </div>
                <span className="hidden sm:inline text-muted-foreground/30">
                  |
                </span>
                <span className="font-mono hidden md:inline">
                  ID: {liquidacion_id}
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground-foreground">
                    <Scale className="h-3 w-3" />
                    {getTipoTramiteLabel(edificaciones.tipo_tramite)}
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground-foreground">
                    {getTramiteAccionLabel(edificaciones.tramite_accion)}
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/8 border border-primary/15 text-xs font-bold text-primary">
                    Rev. N° {edificaciones.numero_revision}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Total prominently displayed + Nueva Revision button + Chevron */}
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
            {onNuevaRevision && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onNuevaRevision(item);
                }}
                className="h-8 rounded-lg gap-1.5 text-xs font-semibold border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50 w-full lg:w-auto"
              >
                <Plus className="h-3.5 w-3.5" />
                Nueva revisión
              </Button>
            )}
          </div>
        </div>
      </CollapsibleTrigger>

      {/* ════════════════════════════════════════════════════════════════════
          BODY: Edificaciones Accordion Content
      ════════════════════════════════════════════════════════════════════ */}
      <CollapsibleContent className="p-5 space-y-4 border-t border-border/40 bg-muted/10">
        {/* ─── Three-column grid: Proyecto + Municipalidad + Edificación ─── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Proyecto Card */}
          <SectionCard
            icon={<Hash className="h-3.5 w-3.5" />}
            title="Proyecto"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue
                label="Código"
                value={
                  <span className="font-mono text-primary font-semibold">
                    {proyecto.public_id}
                  </span>
                }
              />
              <LabelValue label="Nombre" value={proyecto.nombre} />
              {proyecto.entidad && (
                <>
                  <LabelValue label="Entidad" value={proyecto.entidad.nombre} />
                  <LabelValue
                    label="RUC"
                    value={`${proyecto.entidad.tipo} ${proyecto.entidad.ruc}`}
                  />
                </>
              )}
              {proyecto.direccion && (
                <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">
                    {proyecto.direccion}
                    {proyectoLocation && ` · ${proyectoLocation}`}
                  </span>
                </div>
              )}
            </div>
          </SectionCard>

          {/* Municipalidad Card */}
          <SectionCard
            icon={<Building2 className="h-3.5 w-3.5" />}
            title="Municipalidad"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue label="Nombre" value={municipalidad?.nombre || "—"} />
              {municipalidad?.codigo && (
                <LabelValue label="Código" value={municipalidad.codigo} />
              )}
              {municipalidadLocation && (
                <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                  <span>{municipalidadLocation}</span>
                </div>
              )}
            </div>
          </SectionCard>

          {/* Edificación Card */}
          <SectionCard
            icon={<FileText className="h-3.5 w-3.5" />}
            title="Edificación"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue
                label="Código"
                value={
                  <span className="font-mono text-primary font-semibold">
                    {edificaciones.public_id}
                  </span>
                }
              />
              <LabelValue
                label="Valor del Proyecto"
                value={formatCurrency(Number(proyecto.valor_proyecto))}
              />
            </div>
          </SectionCard>
        </div>

        {/* ─── Two-column grid: Proyectistas + Especialidades ─── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Proyectistas Card */}
          <SectionCard
            icon={<User className="h-3.5 w-3.5" />}
            title={hasMultipleProyectistas ? "Proyectistas" : "Proyectista"}
            className="border-border/60"
          >
            {edificaciones.proyectistas &&
            edificaciones.proyectistas.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {edificaciones.proyectistas.map((proj) => (
                  <div
                    key={proj.id}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60 hover:bg-secondary/60 hover:border-primary/20 transition-all"
                  >
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                      <HardHat className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-foreground">
                        {[
                          proj.perfil_ingeniero_nombres,
                          proj.perfil_ingeniero_apellidos,
                        ]
                          .filter(Boolean)
                          .join(" ") || "Sin nombre"}
                      </span>
                      {proj.perfil_ingeniero_cip && (
                        <span className="text-[10px] text-muted-foreground">
                          CIP: {proj.perfil_ingeniero_cip}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/60 italic">
                Sin proyectistas registrados
              </p>
            )}
          </SectionCard>

          {/* Especialidades Card */}
          <SectionCard
            icon={<Building2 className="h-3.5 w-3.5" />}
            title={
              <span className="flex items-center gap-1.5">
                Especialidades
                <span className="ml-1 inline-flex items-center justify-center h-4 w-4 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
                  {edificaciones.revisiones.length}
                </span>
              </span>
            }
            className="border-border/60"
          >
            {edificaciones.revisiones.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {edificaciones.revisiones.map((edif) => (
                  <div
                    key={edif.id}
                    className="group/chip inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60 hover:bg-secondary/60 hover:border-primary/20 transition-all"
                  >
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 group-hover/chip:bg-primary/15 transition-colors">
                      <Building2 className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs font-bold text-foreground leading-tight truncate max-w-[120px]">
                        {edif.especialidades
                          .map((e: { nombre: string }) => e.nombre)
                          .join(", ")}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {Number(edif.tarifa.porcentaje_minimo_uit).toFixed(4)}{" "}
                        UIT
                      </span>
                    </div>
                    <div className="ml-1 flex flex-col items-end gap-0.5">
                      <span className="text-xs font-black text-primary">
                        {formatCurrency(Number(edif.monto_base))}
                      </span>
                      {edif.cobra ? (
                        <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-secondary-foreground">
                          <span className="inline-flex h-1 w-1 rounded-full bg-emerald-500" />
                          Cobra
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-muted-foreground/50">
                          <span className="inline-flex h-1 w-1 rounded-full bg-muted-foreground/30" />
                          No cobra
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/60 italic">
                Sin especialidades registradas
              </p>
            )}
          </SectionCard>
        </div>

        {/* ─── Delegados (only if present) ─── */}
        {edificaciones.delegados && edificaciones.delegados.length > 0 && (
          <SectionCard
            icon={<User className="h-3.5 w-3.5" />}
            title={`Delegados (${edificaciones.delegados.length})`}
            className="border-border/60"
          >
            <div className="flex flex-wrap gap-2">
              {edificaciones.delegados.map((d) => (
                <div
                  key={(d as Record<string, unknown>).id as string}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted">
                    <User className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-foreground">
                      {[
                        (d as Record<string, unknown>).perfil_ingeniero_nombres,
                        (d as Record<string, unknown>).perfil_ingeniero_apellidos,
                      ]
                        .filter(Boolean)
                        .join(" ") || "—"}
                    </span>
                    {(d as Record<string, unknown>).perfil_ingeniero_cip as boolean && (
                      <span className="text-[10px] text-muted-foreground">
                        CIP: {(d as Record<string, unknown>).perfil_ingeniero_cip as string}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {/* ─── Totales Card (full width) ─── */}
        <SectionCard
          icon={<Banknote className="h-3.5 w-3.5" />}
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

        {/* ─── Observación (if present) ─── */}
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
