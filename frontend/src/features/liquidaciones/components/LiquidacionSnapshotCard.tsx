"use client";

import {
  FileText,
  Building2,
  MapPin,
  User,
  Award,
  CreditCard,
  Calendar,
  Banknote,
  Percent,
  Hash,
  AlertCircle,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { LiquidacionSnapshotListItem } from "../types/liquidacion-edificaciones";

interface LiquidacionSnapshotCardProps {
  item: LiquidacionSnapshotListItem;
}

/** Format currency: 1234.56 -> "S/ 1,234.56" */
const formatCurrency = (value: number): string => {
  return `S/ ${value.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

/** Format date: ISO string -> "dd/MM/yyyy" */
const formatDate = (isoString: string): string => {
  if (!isoString) return "—";
  try {
    return new Date(isoString).toLocaleDateString("es-PE");
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

/** Estado badge usando solo variables de tema */
const getEstadoBadgeClass = (estado: string): string => {
  switch (estado) {
    case "PAGADO":
      return "bg-emerald-500/10 text-emerald-600 border-emerald-500/20";
    case "PENDIENTE":
      return "bg-amber-500/10 text-amber-600 border-amber-500/20";
    case "ANULADO":
      return "bg-destructive/10 text-destructive border-destructive/20";
    default:
      return "bg-muted text-muted-foreground border-border";
  }
};

/** Compact stat chip */
function StatChip({
  icon,
  label,
  value,
  highlight = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg",
        highlight
          ? "bg-primary/5 border border-primary/10"
          : "bg-muted/50 border border-border/50"
      )}
    >
      <span className="text-muted-foreground">{icon}</span>
      <div className="flex flex-col">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          {label}
        </span>
        <span
          className={cn(
            "text-sm font-bold",
            highlight ? "text-primary" : "text-foreground"
          )}
        >
          {value}
        </span>
      </div>
    </div>
  );
}

export function LiquidacionSnapshotCard({ item }: LiquidacionSnapshotCardProps) {
  const {
    numero_liquidacion,
    public_id,
    estado,
    fecha_registro,
    municipalidad_nombre,
    observacion,
    proyecto,
    edificaciones,
    totales,
  } = item;

  return (
    <div className="group bg-card rounded-2xl border shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* ─── TOP SECTION: Identity & Status ─── */}
      <div className="px-6 py-5 border-b border-border/60 bg-gradient-to-r from-muted/30 to-transparent">
        <div className="flex items-start justify-between gap-4">
          {/* Left: Icon + IDs */}
          <div className="flex items-start gap-4 min-w-0 flex-1">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 group-hover:bg-primary/15 transition-colors">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-3 flex-wrap">
                <h3 className="text-lg font-bold text-foreground tracking-tight">
                  {public_id || numero_liquidacion}
                </h3>
                <span
                  className={cn(
                    "shrink-0 inline-flex items-center rounded-full border px-3 py-0.5 text-[11px] font-bold uppercase tracking-wider",
                    getEstadoBadgeClass(estado)
                  )}
                >
                  {estado}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-1 truncate font-medium">
                {proyecto.nombre}
              </p>
              {public_id && numero_liquidacion && public_id !== numero_liquidacion && (
                <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                  {numero_liquidacion}
                </p>
              )}
            </div>
          </div>

          {/* Right: Date */}
          <div className="hidden sm:flex items-center gap-2 text-muted-foreground shrink-0">
            <Calendar className="h-4 w-4" />
            <span className="text-xs font-medium">{formatDate(fecha_registro)}</span>
          </div>
        </div>
      </div>

      {/* ─── MIDDLE SECTION: Key Info Grid ─── */}
      <div className="px-6 py-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Proyectistas */}
          {edificaciones.proyectistas && edificaciones.proyectistas.length > 0 && (
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
                <User className="h-4 w-4 text-secondary-foreground" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Proyectista{edificaciones.proyectistas.length > 1 ? "s" : ""}
                </p>
                {edificaciones.proyectistas.map((proj, idx) => (
                  <p key={proj.id} className="text-sm font-semibold text-foreground truncate">
                    {proj.nombres} {proj.apellidos}
                    {proj.cip && <span className="text-xs text-muted-foreground"> (CIP: {proj.cip})</span>}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Entidad */}
          {proyecto.entidad && (
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
                <CreditCard className="h-4 w-4 text-secondary-foreground" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Entidad
                </p>
                <p className="text-sm font-semibold text-foreground truncate">
                  {proyecto.entidad.nombre}
                </p>
                <p className="text-xs text-muted-foreground">
                  {proyecto.entidad.tipo}: {proyecto.entidad.ruc}
                </p>
              </div>
            </div>
          )}

          {/* Dirección */}
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
              <MapPin className="h-4 w-4 text-secondary-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Dirección
              </p>
              <p className="text-sm font-medium text-foreground truncate">
                {proyecto.direccion || "—"}
              </p>
            </div>
          </div>

          {/* Revisión */}
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
              <Hash className="h-4 w-4 text-secondary-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Revisión
              </p>
              <p className="text-sm font-semibold text-foreground">
                {edificaciones.numero_revision}
              </p>
            </div>
          </div>

          {/* Municipalidad */}
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
              <Building2 className="h-4 w-4 text-secondary-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Municipalidad
              </p>
              <p className="text-sm font-semibold text-foreground truncate">
                {municipalidad_nombre || "—"}
              </p>
            </div>
          </div>

          {/* Trámite */}
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
              <FileText className="h-4 w-4 text-secondary-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Trámite
              </p>
              <p className="text-sm font-semibold text-foreground truncate">
                {formatEnumLabel(edificaciones.tipo_tramite)}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatEnumLabel(edificaciones.tramite_accion)}
              </p>
            </div>
          </div>

          {/* Especialidades count */}
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
              <Building2 className="h-4 w-4 text-secondary-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Especialidades
              </p>
              <p className="text-sm font-semibold text-foreground">
                {edificaciones.revisiones.length}{" "}
                {edificaciones.revisiones.length === 1 ? "especialidad" : "especialidades"}
              </p>
            </div>
          </div>

          {/* Mobile date */}
          <div className="flex items-start gap-3 sm:hidden">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary/50">
              <Calendar className="h-4 w-4 text-secondary-foreground" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Fecha
              </p>
              <p className="text-sm font-semibold text-foreground">
                {formatDate(fecha_registro)}
              </p>
            </div>
          </div>
        </div>

        {/* ─── EDIFICACIONES / ESPECIALIDADES ─── */}
        {edificaciones.revisiones.length > 0 && (
          <div className="mt-5 pt-5 border-t border-border/50">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">
              Especialidades ({edificaciones.revisiones.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {edificaciones.revisiones.map((edif) => (
                <div
                  key={edif.id}
                  className="group/chip inline-flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-secondary/40 border border-border/60 hover:bg-secondary/70 hover:border-primary/20 transition-all"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 group-hover/chip:bg-primary/15 transition-colors">
                    <Building2 className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-foreground leading-tight">
                      {edif.especialidad}
                    </span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-muted-foreground">
                        Tarifa: {Number(edif.tarifa.porcentaje_minimo_uit).toFixed(4)} UIT
                      </span>
                      {edif.tarifa.derecho_maximo && (
                        <span className="text-[10px] text-muted-foreground">
                          (max {formatCurrency(Number(edif.tarifa.derecho_maximo))})
                        </span>
                      )}
                      <span className="text-[10px] font-bold text-primary">
                        {formatCurrency(edif.monto_base)}
                      </span>
                    </div>
                  </div>
                  {edif.cobra ? (
                    <span className="ml-1 inline-flex h-2 w-2 rounded-full bg-emerald-500" title="Cobra" />
                  ) : (
                    <span className="ml-1 inline-flex h-2 w-2 rounded-full bg-muted-foreground/30" title="No cobra" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {edificaciones.revisiones.length === 0 && (
          <div className="mt-5 pt-5 border-t border-border/50">
            <div className="flex items-center gap-2 text-muted-foreground/60">
              <Building2 className="h-4 w-4" />
              <span className="text-xs font-medium">Sin especialidades registradas</span>
            </div>
          </div>
        )}

        {/* ─── FINANCIAL SUMMARY ─── */}
        <div className="mt-5 pt-5 border-t border-border/50">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatChip
                icon={<Banknote className="h-3.5 w-3.5" />}
                label="Subtotal"
                value={formatCurrency(totales.subtotal)}
              />
              <StatChip
                icon={<Percent className="h-3.5 w-3.5" />}
                label="IGV"
                value={formatCurrency(totales.igv)}
              />
            </div>
            <div className="flex items-center gap-3 bg-primary/5 border border-primary/10 rounded-xl px-5 py-3">
              <div className="text-right">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Total a Pagar
                </p>
                <p className="text-xl font-black text-primary tracking-tight">
                  {formatCurrency(totales.total_a_pagar)}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-primary/40" />
            </div>
          </div>
        </div>

        {/* ─── OBSERVACIÓN ─── */}
        {observacion && (
          <div className="mt-4 flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10">
            <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <span className="text-xs text-amber-700 font-medium leading-relaxed">
              {observacion}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
