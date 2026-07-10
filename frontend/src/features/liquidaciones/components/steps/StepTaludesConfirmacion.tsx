/**
 * Step: Confirmación para Taludes.
 * Confirmation step specific to Taludes.
 *
 * Arquitectura de sub-componentes Taludes-específicos:
 * - TaludesConfirmacionCard: tarjeta envolvente reutilizable
 * - TaludesDataRow: fila label/valor
 */
"use client";

import {
  BadgeCheck,
  Building2,
  Banknote,
  Users,
  Phone,
  Calculator,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { useTaludesStepperStore, type CachedProyecto } from "../../store";
import type { CotizacionTaludesResponse } from "../../types/liquidacion-taludes.types";

// ── Sub-componentes Taludes-específicos ──

interface TaludesConfirmacionCardProps {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  className?: string;
  actions?: Array<{ label: string; onClick: () => void }>;
}

function TaludesConfirmacionCard({
  title,
  icon: Icon,
  children,
  className,
  actions,
}: TaludesConfirmacionCardProps) {
  return (
    <div className={`rounded-xl border border-border bg-card overflow-hidden ${className ?? ""}`}>
      <div className="flex items-center justify-between px-4 py-3 bg-muted/40 border-b border-border">
        <div className="flex items-center gap-2">
          {Icon && (
            <div className="p-1.5 bg-primary/10 rounded-md text-primary">
              <Icon className="h-3.5 w-3.5" />
            </div>
          )}
          <h4 className="text-sm font-semibold text-foreground">{title}</h4>
        </div>
        {actions && actions.length > 0 && (
          <div className="flex gap-1">
            {actions.map((action) => (
              <Button
                key={action.label}
                type="button"
                variant="ghost"
                size="sm"
                onClick={action.onClick}
                className="h-7 px-2 gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

interface TaludesDataRowProps {
  label: string;
  children: React.ReactNode;
  className?: string;
}

function TaludesDataRow({ label, children, className = "" }: TaludesDataRowProps) {
  return (
    <div className={`space-y-0.5 min-w-0 ${className}`}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="text-sm font-medium text-foreground truncate">{children}</div>
    </div>
  );
}

// ── Props para el paso de confirmación Taludes ─────────────────────────────────

export type LiquidacionDisplayItem = {
  label: string;
  value: string | number | null | undefined;
  highlight?: boolean;
};

export interface StepTaludesConfirmacionProps {
  methods: UseFormReturn<FieldValues>;
  isActive: boolean;
  /** Label del tipo de liquidación (ej: "Taludes") */
  tipoLabel: string;
  /** Items de la sección Liquidación */
  liquidacionItems: LiquidacionDisplayItem[];
  municipalidades?: Array<{ id: string; nombre: string }>;
  /** Cotización desde el store - Taludes-specific type */
  quote: CotizacionTaludesResponse | null;
}

// ── Paso de Confirmación Taludes ───────────────────────────────────────────────────

export function StepTaludesConfirmacion({
  methods,
  isActive,
  tipoLabel,
  liquidacionItems,
  municipalidades = [],
  quote,
}: StepTaludesConfirmacionProps) {
  const {
    selectedProyecto,
    proyectoInline,
    selectedProyectistas,
    selectedContactos,
    selectedTarifasIds,
    goToStep,
  } = useTaludesStepperStore();

  const { watch } = methods;
  const watchedMunicipalidadId = watch("municipalidad_id");
  const municipalidad = municipalidades.find((m) => m.id === watchedMunicipalidadId);

  const formatSoles = (value: number) =>
    `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;

  if (!isActive) return null;

  const hasProyecto = !!selectedProyecto || !!proyectoInline;

  return (
    <div className="space-y-6 min-w-0 max-w-full">
      {/* Header summary */}
      <div className="flex items-center gap-4 p-4 rounded-xl bg-primary/5 border border-primary/20">
        <div className="p-2.5 bg-primary/15 rounded-lg text-primary shadow-sm">
          <BadgeCheck className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-bold text-foreground leading-tight">Revisión final</h3>
          <p className="text-sm text-muted-foreground mt-0.5">
            Verifica que toda la información sea correcta antes de crear la liquidación
          </p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 min-w-0">
        {/* Left column: Proyecto + Liquidación */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Proyecto */}
          <TaludesConfirmacionCard
            title="Proyecto"
            icon={Building2}
            actions={[{ label: "Editar", onClick: () => goToStep(0) }]}
          >
            <TaludesProyectoDisplay
              selectedProyecto={selectedProyecto}
              proyectoInline={proyectoInline}
              hasProyecto={hasProyecto}
            />
          </TaludesConfirmacionCard>

          {/* Liquidación */}
          <TaludesConfirmacionCard
            title="Liquidación"
            icon={Banknote}
            actions={[{ label: "Editar", onClick: () => goToStep(0) }]}
          >
            <div className="space-y-3 min-w-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <TaludesDataRow label="Tipo">{tipoLabel}</TaludesDataRow>
                <TaludesDataRow label="Municipalidad">{municipalidad?.nombre ?? "—"}</TaludesDataRow>
                {liquidacionItems.map((item) => (
                  <TaludesDataRow
                    key={item.label}
                    label={item.label}
                    className={item.highlight ? "text-primary" : ""}
                  >
                    {item.highlight && typeof item.value === "number"
                      ? `${item.value.toLocaleString("es-PE")} m²`
                      : item.value ?? "—"}
                  </TaludesDataRow>
                ))}
                {/* Tarifas seleccionadas */}
                <TaludesDataRow label="Tarifas" className="sm:col-span-2">
                  {selectedTarifasIds.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {selectedTarifasIds.map((id) => (
                        <Badge key={id} variant="outline" className="text-xs font-mono">
                          {id.slice(0, 8)}...
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <span className="text-muted-foreground italic">Sin tarifas</span>
                  )}
                </TaludesDataRow>
              </div>
            </div>
          </TaludesConfirmacionCard>
        </div>

        {/* Center column: Proyectistas + Contactos */}
        <div className="flex-[2] min-w-0 space-y-4">
          <TaludesConfirmacionCard
            title={`Proyectistas (${selectedProyectistas.length})`}
            icon={Users}
            actions={[{ label: "Editar", onClick: () => goToStep(2) }]}
          >
            <TaludesPersonasDisplay
              personas={selectedProyectistas.map((p) => ({
                cip: p.cip,
                label: p.nombres && p.apellidos ? `${p.nombres} ${p.apellidos}` : `CIP ${p.cip}`,
                especialidad: p.especialidad_id,
                descripcion: p.descripcion,
              }))}
              emptyMessage="Sin proyectistas agregados"
            />
          </TaludesConfirmacionCard>

          <TaludesConfirmacionCard
            title={`Contactos (${selectedContactos.length})`}
            icon={Phone}
            actions={[{ label: "Editar", onClick: () => goToStep(2) }]}
          >
            <TaludesPersonasDisplay
              personas={selectedContactos.map((c, i) => ({
                cip: c.localId ?? `contacto-${i}`,
                label: `${c.nombres} ${c.apellidos}`,
                cargo: c.cargo,
                telefono: c.telefono ?? c.celular,
                email: c.email,
                principal: c.principal,
              }))}
              emptyMessage="Sin contactos agregados"
              showCargo
              showTelefono
              showEmail
            />
          </TaludesConfirmacionCard>
        </div>

        {/* Right column: Cotización */}
        <div className="flex-1 min-w-0">
          <TaludesConfirmacionCard
            title="Cotización"
            icon={Calculator}
            actions={quote ? [{ label: "Recalcular", onClick: () => goToStep(0) }] : undefined}
          >
            <TaludesCotizacionDisplay quote={quote} formatSoles={formatSoles} />
          </TaludesConfirmacionCard>
        </div>
      </div>
    </div>
  );
}

// ── Sub-componentes internos de visualización ─────────────────────────────────

interface TaludesPersonaDisplayItem {
  cip: string;
  label: string;
  especialidad?: string;
  descripcion?: string;
  cargo?: string | null;
  telefono?: string | null;
  email?: string | null;
  principal?: boolean;
}

interface TaludesPersonasDisplayProps {
  personas: TaludesPersonaDisplayItem[];
  emptyMessage: string;
  showCargo?: boolean;
  showTelefono?: boolean;
  showEmail?: boolean;
}

function TaludesPersonasDisplay({
  personas,
  emptyMessage,
  showCargo,
  showTelefono,
  showEmail,
}: TaludesPersonasDisplayProps) {
  if (personas.length === 0) {
    return <p className="text-sm text-muted-foreground italic">{emptyMessage}</p>;
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {personas.map((p) => (
        <div
          key={p.cip}
          className="flex items-start gap-3 p-3 rounded-lg border border-border bg-card/50"
        >
          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
            <span className="text-xs font-bold text-primary">
              {p.label.slice(0, 2).toUpperCase()}
            </span>
          </div>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-medium truncate">{p.label}</p>
              {p.principal && (
                <Badge className="text-[10px] bg-primary/10 text-primary">Principal</Badge>
              )}
            </div>
            <div className="flex flex-wrap gap-1">
              <Badge variant="outline" className="text-[10px]">
                {p.especialidad ?? p.cip}
              </Badge>
            </div>
            {showCargo && p.cargo && <p className="text-xs text-muted-foreground">{p.cargo}</p>}
            {showTelefono && p.telefono && (
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Phone className="h-3 w-3" />
                {p.telefono}
              </p>
            )}
            {showEmail && p.email && (
              <p className="text-xs text-muted-foreground truncate">{p.email}</p>
            )}
            {p.descripcion && (
              <p className="text-xs text-muted-foreground line-clamp-2">{p.descripcion}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function TaludesCotizacionDisplay({
  quote,
  formatSoles,
}: {
  quote: CotizacionTaludesResponse | null;
  formatSoles: (v: number) => string;
}) {
  if (!quote) {
    return <p className="text-sm text-muted-foreground italic">Sin cotización calculada</p>;
  }
  return (
    <div className="space-y-4 min-w-0">
      <div className="space-y-2 text-sm">
        <div className="flex justify-between gap-2">
          <span className="text-muted-foreground">Subtotal</span>
          <span className="font-medium">{formatSoles(quote.totales.subtotal)}</span>
        </div>
      </div>
      <div className="rounded-lg border border-primary bg-primary/5 p-4 space-y-2">
        <span className="flex items-center gap-1.5 text-sm font-semibold text-primary">
          <BadgeCheck className="h-4 w-4" />
          Total a Pagar
        </span>
        <span className="text-2xl font-bold text-primary">{formatSoles(quote.totales.total_a_pagar)}</span>
      </div>
      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        Revisión #{quote.numero_revision} · UIT {formatSoles(quote._metadata.uit_valor)}
      </div>
    </div>
  );
}

interface TaludesProyectoDisplayProps {
  selectedProyecto: CachedProyecto | null;
  proyectoInline: {
    denominacion: string;
    direccion?: string;
    nombre_propietario?: string;
    entidad?: { razon_social: string; tipo_documento: string; numero_documento: string };
  } | null;
  hasProyecto: boolean;
}

function TaludesProyectoDisplay({
  selectedProyecto,
  proyectoInline,
  hasProyecto,
}: TaludesProyectoDisplayProps) {
  if (!hasProyecto) {
    return <p className="text-sm text-muted-foreground italic">Sin proyecto seleccionado</p>;
  }
  if (selectedProyecto) {
    return (
      <div className="space-y-3 min-w-0">
        <TaludesDataRow label="Denominación">{selectedProyecto.denominacion}</TaludesDataRow>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <TaludesDataRow label="Código">{selectedProyecto.public_id}</TaludesDataRow>
          {selectedProyecto.direccion && <TaludesDataRow label="Dirección">{selectedProyecto.direccion}</TaludesDataRow>}
          {selectedProyecto.distrito && <TaludesDataRow label="Distrito">{selectedProyecto.distrito}</TaludesDataRow>}
        </div>
        {selectedProyecto.entidad?.nombre && (
          <TaludesDataRow label="Entidad">{selectedProyecto.entidad.nombre}</TaludesDataRow>
        )}
      </div>
    );
  }
  return (
    <div className="space-y-3 min-w-0">
      <TaludesDataRow label="Denominación">{proyectoInline?.denominacion}</TaludesDataRow>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {proyectoInline?.direccion && <TaludesDataRow label="Dirección">{proyectoInline.direccion}</TaludesDataRow>}
        {proyectoInline?.nombre_propietario && (
          <TaludesDataRow label="Propietario">{proyectoInline.nombre_propietario}</TaludesDataRow>
        )}
      </div>
      {proyectoInline?.entidad && (
        <TaludesDataRow label="Entidad">
          {proyectoInline.entidad.razon_social} ({proyectoInline.entidad.tipo_documento}:{" "}
          {proyectoInline.entidad.numero_documento})
        </TaludesDataRow>
      )}
    </div>
  );
}
