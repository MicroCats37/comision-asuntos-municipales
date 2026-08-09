"use client";

import { useState } from "react";
import {
  AlertCircle,
  Banknote,
  Building2,
  Calendar,
  ChevronDown,
  FileText,
  Hash,
  HardHat,
  MapPin,
  Pen,
  Phone,
  Plus,
  Scale,
  User,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type {
  LiquidacionEdificacionOut,
  ContactoOut,
  DelegadoOut,
  ProyectistaOut,
  RevisionOut,
} from "../types/liquidacion-edificaciones";
import { GestionarDelegadosModal } from "./GestionarDelegadosModal";

interface LiquidacionListCardProps {
  item: LiquidacionEdificacionOut;
  onNuevaRevision?: (item: LiquidacionEdificacionOut) => void;
}

/** Format currency: 1234.56 -> "S/ 1,234.56" */
const formatCurrency = (value: number | string): string => {
  return `S/ ${Number(value).toLocaleString("es-PE", {
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
    case "REINTEGRO":
      return "Reintegro";
    case "PROYECTO_CON_PLANTAS_TIPICAS":
      return "Proyecto con Plantas Típicas";
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
      <span className={cn("text-sm font-medium text-foreground", className)}>
        {value}
      </span>
    </div>
  );
}

/** Proyectista chip */
function ProyectistaChip({ proj }: { proj: ProyectistaOut }) {
  const nombre = [
    proj.perfil_ingeniero_nombres,
    proj.perfil_ingeniero_apellidos,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-secondary/40 border border-border/60">
      <HardHat className="h-3 w-3 text-primary shrink-0" />
      <div className="flex flex-col min-w-0">
        <span className="text-xs font-semibold text-foreground truncate max-w-[160px]">
          {nombre || "Sin nombre"}
        </span>
        {proj.perfil_ingeniero_cip && (
          <span className="text-[10px] text-muted-foreground">
            CIP: {proj.perfil_ingeniero_cip}
          </span>
        )}
      </div>
    </div>
  );
}

/** Delegado chip */
function DelegadoChip({ del }: { del: DelegadoOut }) {
  const nombre = [del.perfil_ingeniero_nombres, del.perfil_ingeniero_apellidos]
    .filter(Boolean)
    .join(" ");
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-secondary/40 border border-border/60">
      <User className="h-3 w-3 text-muted-foreground shrink-0" />
      <div className="flex flex-col min-w-0">
        <span className="text-xs font-semibold text-foreground truncate max-w-[160px]">
          {nombre || "—"}
        </span>
        {del.perfil_ingeniero_cip && (
          <span className="text-[10px] text-muted-foreground">
            CIP: {del.perfil_ingeniero_cip}
          </span>
        )}
      </div>
    </div>
  );
}

/** Contacto chip */
function ContactoChip({ contacto }: { contacto: ContactoOut }) {
  const nombre = [contacto.nombres, contacto.apellidos]
    .filter(Boolean)
    .join(" ");
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-secondary/40 border border-border/60">
      <Phone className="h-3 w-3 text-muted-foreground shrink-0" />
      <div className="flex flex-col min-w-0">
        <span className="text-xs font-semibold text-foreground truncate max-w-[140px]">
          {nombre || "Sin nombre"}
        </span>
        {contacto.cargo && (
          <span className="text-[10px] text-muted-foreground truncate max-w-[140px]">
            {contacto.cargo}
          </span>
        )}
      </div>
    </div>
  );
}

/** Revision chip */
function RevisionChip({ rev }: { rev: RevisionOut }) {
  const especialidadesLabel = rev.especialidades
    .map((e) => e.nombre)
    .join(", ");
  return (
    <div className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-secondary/40 border border-border/60">
      <Building2 className="h-3 w-3 text-primary shrink-0" />
      <div className="flex flex-col min-w-0">
        <span
          className="text-xs font-semibold text-foreground truncate max-w-[120px]"
          title={especialidadesLabel}
        >
          {especialidadesLabel || "Sin especialidad"}
        </span>
        <span className="text-[10px] text-muted-foreground">
          {Number(rev.tarifa.porcentaje_minimo_uit).toFixed(4)} UIT
        </span>
      </div>
      <div className="flex flex-col items-end gap-0.5 ml-1">
        <span className="text-xs font-bold text-primary">
          {formatCurrency(Number(rev.monto_base))}
        </span>
      </div>
    </div>
  );
}

/**
 * LiquidacionListCard — renders an Edificaciones Liquidacion from the list endpoint
 * (GET /liquidaciones/edificaciones).
 *
 * Uses LiquidacionEdificacionOut fields which include rich nested data:
 * proyecto, municipalidad, valores, proyectistas, delegados, contactos, revisiones.
 *
 * Shows all available key fields in an expandable accordion layout.
 */
export function LiquidacionListCard({
  item,
  onNuevaRevision,
}: LiquidacionListCardProps) {
  const {
    id,
    public_id,
    numero_revision,
    estado,
    tipo_tramite,
    tramite_accion,
    fecha_registro,
    expediente,
    observacion,
    proyecto,
    entidad,
    municipalidad,
    valores,
    proyectistas,
    delegados,
    contactos,
    revisiones,
    // Campos financieros directos
    subtotal,
    igv,
    total,
    total_a_pagar,
  } = item;

  // Build location string for municipalidad
  const municipalidadLocation = [
    municipalidad.distrito?.nombre,
    municipalidad.provincia?.nombre,
  ]
    .filter(Boolean)
    .join(", ");

  // Build location string for proyecto
  const proyectoLocation = [proyecto.direccion, proyecto.entidad?.nombre]
    .filter(Boolean)
    .join(" · ");

  const total_display = valores?.total_a_pagar ?? total_a_pagar;

  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);

  return (
    <>
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

                {/* Secondary: Project name + Expediente */}
                <div className="flex items-center gap-3 mt-1 flex-wrap">
                  {proyecto.nombre && (
                    <span className="text-xs text-muted-foreground truncate max-w-[280px]">
                      {proyecto.nombre}
                    </span>
                  )}
                  {expediente && (
                    <>
                      <span className="text-xs text-muted-foreground/60 hidden sm:inline">
                        •
                      </span>
                      <span className="text-xs text-muted-foreground font-mono hidden md:inline">
                        Exp: {expediente}
                      </span>
                    </>
                  )}
                </div>

                {/* Tertiary: Date + ID + Trámite badges */}
                <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground/70">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>{formatDate(fecha_registro)}</span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground-foreground">
                      <Scale className="h-3 w-3" />
                      {getTipoTramiteLabel(tipo_tramite)}
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground-foreground">
                      {getTramiteAccionLabel(tramite_accion)}
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/8 border border-primary/15 text-xs font-bold text-primary">
                      Rev. N° {numero_revision}
                    </span>
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
                      className="h-7 rounded-lg gap-1 text-[11px] font-semibold border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50"
                    >
                      <Plus className="h-3 w-3" />
                      Nueva revisión
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {/* Right: Total prominently displayed + counts badges + Chevron */}
            <div className="flex flex-col gap-2 lg:items-end">
              <div className="bg-primary/5 border border-primary/10 rounded-xl px-4 py-2.5 flex items-center gap-3">
                <div className="text-right">
                  <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                    Total
                  </p>
                  <p className="text-xl font-black text-primary tracking-tight">
                    {formatCurrency(Number(total_display))}
                  </p>
                </div>
                <ChevronDown className="h-4 w-4 text-primary/40 group-data-[state=open]:rotate-180 transition-transform" />
              </div>
              {/* Quick counts */}
              <div className="flex flex-wrap gap-1.5 justify-end">
                {proyectistas.length > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-[10px] font-semibold text-secondary-foreground-foreground">
                    <HardHat className="h-2.5 w-2.5" />
                    {proyectistas.length}
                  </span>
                )}
                {delegados.length > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-[10px] font-semibold text-secondary-foreground-foreground">
                    <Users className="h-2.5 w-2.5" />
                    {delegados.length}
                  </span>
                )}
                {contactos.length > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-[10px] font-semibold text-secondary-foreground-foreground">
                    <Phone className="h-2.5 w-2.5" />
                    {contactos.length}
                  </span>
                )}
                {revisiones.length > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/8 border border-primary/15 text-[10px] font-bold text-primary">
                    <Building2 className="h-2.5 w-2.5" />
                    {revisiones.length}
                  </span>
                )}
              </div>
            </div>
          </div>
        </CollapsibleTrigger>

        {/* Action bar — always visible, outside the trigger */}
        <div className="flex items-center gap-2 px-5 py-2 bg-muted/20 border-b border-border/40">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setDelegadosModalOpen(true)}
            className="h-7 rounded-lg gap-1.5 text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
          >
            <Pen className="h-3 w-3" />
            Gestionar delegados
          </Button>
        </div>

        {/* ════════════════════════════════════════════════════════════════════
          BODY: Rich Accordion Content
      ════════════════════════════════════════════════════════════════════ */}
        <CollapsibleContent className="p-5 space-y-4 border-t border-border/40 bg-muted/10">
          {/* Three-column grid: Proyecto + Municipalidad + Liquidación Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Proyecto Card */}
            <SectionCard
              icon={<Hash className="h-3.5 w-3.5" />}
              title="Proyecto"
              className="border-border/60"
            >
              <div className="space-y-2">
                <LabelValue
                  label="Denominación"
                  value={proyecto.nombre || "—"}
                />
                {proyecto.valor_proyecto != null && (
                  <LabelValue
                    label="Valor del Proyecto"
                    value={formatCurrency(Number(proyecto.valor_proyecto))}
                  />
                )}
                {entidad && (
                  <>
                    <LabelValue label="Entidad" value={entidad.nombre || "—"} />
                    {entidad.ruc && (
                      <LabelValue
                        label="RUC"
                        value={`${entidad.tipo || ""} ${entidad.ruc}`.trim()}
                      />
                    )}
                  </>
                )}
                {proyectoLocation && (
                  <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                    <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{proyectoLocation}</span>
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
              <div className="space-y-2">
                <LabelValue
                  label="Nombre"
                  value={municipalidad.nombre || "—"}
                />
                {municipalidad.codigo && (
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

            {/* Liquidación Info Card */}
            <SectionCard
              icon={<FileText className="h-3.5 w-3.5" />}
              title="Liquidación"
              className="border-border/60"
            >
              <div className="space-y-2">
                <LabelValue
                  label="Trámite"
                  value={getTipoTramiteLabel(tipo_tramite)}
                />
                <LabelValue
                  label="Acción"
                  value={getTramiteAccionLabel(tramite_accion)}
                />
                <LabelValue
                  label="Revisión N°"
                  value={String(numero_revision)}
                />
                {expediente && (
                  <LabelValue label="Expediente" value={expediente} />
                )}
              </div>
            </SectionCard>
          </div>

          {/* Proyectistas + Delegados row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Proyectistas Card */}
            <SectionCard
              icon={<HardHat className="h-3.5 w-3.5" />}
              title={
                proyectistas.length > 1
                  ? `Proyectistas (${proyectistas.length})`
                  : "Proyectista"
              }
              className="border-border/60"
            >
              {proyectistas.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {proyectistas.map((proj) => (
                    <ProyectistaChip key={proj.id} proj={proj} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground/60 italic">
                  Sin proyectistas registrados
                </p>
              )}
            </SectionCard>

            {/* Delegados Card */}
            <SectionCard
              icon={<User className="h-3.5 w-3.5" />}
              title={
                delegados.length > 1
                  ? `Delegados (${delegados.length})`
                  : delegados.length === 1
                    ? "Delegado"
                    : "Delegados"
              }
              className="border-border/60"
            >
              {delegados.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {delegados.map((del) => (
                    <DelegadoChip key={del.id} del={del} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground/60 italic">
                  Sin delegados registrados
                </p>
              )}
              <div className="mt-3">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDelegadosModalOpen(true);
                  }}
                  className="h-7 rounded-lg gap-1.5 text-[11px] font-semibold text-muted-foreground hover:text-primary hover:bg-primary/5"
                >
                  <Pen className="h-3 w-3" />
                  Gestionar delegados
                </Button>
              </div>
            </SectionCard>
          </div>

          {/* Contactos + Revisiones row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Contactos Card */}
            <SectionCard
              icon={<Phone className="h-3.5 w-3.5" />}
              title={
                contactos.length > 1
                  ? `Contactos (${contactos.length})`
                  : contactos.length === 1
                    ? "Contacto"
                    : "Contactos"
              }
              className="border-border/60"
            >
              {contactos.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {contactos.map((contacto) => (
                    <ContactoChip key={contacto.id} contacto={contacto} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground/60 italic">
                  Sin contactos registrados
                </p>
              )}
            </SectionCard>

            {/* Revisiones / Especialidades Card */}
            <SectionCard
              icon={<Building2 className="h-3.5 w-3.5" />}
              title={
                <span className="flex items-center gap-1.5">
                  Especialidades
                  <span className="ml-1 inline-flex items-center justify-center h-4 w-4 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
                    {revisiones.length}
                  </span>
                </span>
              }
              className="border-border/60"
            >
              {revisiones.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {revisiones.map((rev) => (
                    <RevisionChip key={rev.id} rev={rev} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground/60 italic">
                  Sin especialidades registradas
                </p>
              )}
            </SectionCard>
          </div>

          {/* Totales Card (full width) */}
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
                  {formatCurrency(Number(subtotal ?? valores?.subtotal ?? 0))}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                  IGV
                </span>
                <span className="text-sm font-bold text-foreground">
                  {formatCurrency(Number(igv ?? valores?.igv ?? 0))}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                  Total
                </span>
                <span className="text-sm font-bold text-foreground">
                  {formatCurrency(Number(total ?? valores?.total ?? 0))}
                </span>
              </div>
              <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 -my-0.5">
                <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">
                  Total a Pagar
                </span>
                <span className="text-base font-black text-primary">
                  {formatCurrency(
                    Number(total_a_pagar ?? valores?.total_a_pagar ?? 0),
                  )}
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

      <GestionarDelegadosModal
        open={delegadosModalOpen}
        onOpenChange={setDelegadosModalOpen}
        liquidacionId={id}
        municipalidadId={municipalidad.id}
        tipoLiquidacion="edificacion"
        revisionIds={revisiones.map((r) => r.id)}
        delegadosActuales={delegados}
      />
    </>
  );
}
