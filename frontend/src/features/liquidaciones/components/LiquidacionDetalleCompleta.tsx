"use client";

import {
  AlertCircle,
  ArrowLeft,
  FileDown,
  Home,
  type LucideIcon,
  MapPin,
  Pen,
  Phone,
  User,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type {
  ContactoOutput,
  DelegadoOperativoMinOutput,
  LiquidacionGeneralOutput,
  LiquidacionTipoOutput,
} from "../schemas/liquidacion-base.schema";
import type { LiquidacionDetalleItem } from "../schemas/liquidacion-detail.schemas";
import { formatPublicId } from "../utils/formatPublicId";

// ── Helpers ───────────────────────────────────────────────────────────────────

export function kindLabel(tipo_liquidacion: string | null | undefined): string {
  if (!tipo_liquidacion) return "Liquidación";
  const KIND_LABEL: Record<string, string> = {
    "habilitacion-urbana": "Habilitación Urbana",
    "mecanica-suelos": "Mecánica de Suelos",
    "impacto-vial": "Impacto Vial",
    taludes: "Taludes",
    "inspeccion-obra": "Inspección de Obra",
    edificacion: "Edificación",
    edificaciones: "Edificación",
  };
  return KIND_LABEL[tipo_liquidacion] ?? tipo_liquidacion.replace(/[-_]/g, " ");
}

export const formatCurrency = (
  value: number | string | null | undefined,
): string => {
  if (value == null) return "—";
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "—";
  return `S/ ${numValue.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const formatDate = (isoString: string | null | undefined): string => {
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

// ── Sub-components ────────────────────────────────────────────────────────────

function PageSection({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <section className={className}>{children}</section>;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-2">
      {children}
    </h3>
  );
}

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
    <div className={className}>
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
        {label}
      </span>
      <span className={valueClassName ?? "text-sm font-medium text-foreground"}>
        {value}
      </span>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="bg-card rounded-xl border shadow-sm h-48 animate-pulse"
        />
      ))}
    </div>
  );
}

function ErrorState({
  message = "Error al cargar los detalles de la liquidación",
}: {
  message?: string;
}) {
  return (
    <div className="flex items-center justify-center p-8 text-destructive">
      <AlertCircle className="h-5 w-5 mr-2" />
      {message}
    </div>
  );
}

function EmptyState({
  message = "No se encontró la liquidación",
}: {
  message?: string;
}) {
  return (
    <div className="flex items-center justify-center p-8 text-muted-foreground">
      {message}
    </div>
  );
}

// ── Revisión Section ───────────────────────────────────────────────────────────

function RevisionesSection({
  revisiones,
}: {
  revisiones: LiquidacionGeneralOutput["revisiones_previas"];
}) {
  if (revisiones.length === 0) {
    return (
      <p className="text-xs text-muted-foreground/60 italic">
        Sin revisiones registradas
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {revisiones.map((rev) => (
        <div
          key={rev.id}
          className="rounded-lg border border-border/40 bg-muted/20 p-3"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
              Revisión {rev.numero_revision}
            </span>
          </div>
          {rev.expediente && (
            <div className="flex flex-col">
              <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                Expediente
              </span>
              <span className="text-xs font-medium text-foreground">
                {rev.expediente}
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Delegados Section ───────────────────────────────────────────────────────────

function DelegadosSection({
  delegados,
}: {
  delegados: DelegadoOperativoMinOutput[];
}) {
  if (delegados.length === 0) {
    return (
      <p className="text-xs text-muted-foreground/60 italic">
        Sin delegados registrados
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {delegados.map((d) => (
        <div
          key={d.id}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60"
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted">
            <User className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-bold text-foreground">
              {d.colegiado.nombre_completo || "—"}
            </span>
            <div className="flex items-center gap-2">
              {d.colegiado.cip && (
                <span className="text-[10px] text-muted-foreground">
                  CIP: {d.colegiado.cip}
                </span>
              )}
              {d.colegiado.especialidad?.nombre && (
                <span className="text-[10px] text-primary/70">
                  • {d.colegiado.especialidad.nombre}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Contactos Section ───────────────────────────────────────────────────────────

function ContactosSection({
  contacto,
}: {
  contacto: ContactoOutput | null | undefined;
}) {
  if (!contacto) {
    return (
      <p className="text-xs text-muted-foreground/60 italic">
        Sin contactos registrados
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      <div className="inline-flex items-center gap-3 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60 min-w-[200px]">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-bold text-foreground">
            {[contacto.nombres, contacto.apellidos].filter(Boolean).join(" ") ||
              "—"}
          </span>
          {contacto.dni && (
            <span className="text-[10px] text-muted-foreground">
              DNI: {contacto.dni}
            </span>
          )}
          <div className="flex flex-wrap items-center gap-2">
            {(contacto.telefono || contacto.celular) && (
              <span className="text-[10px] text-primary/70 flex items-center gap-1">
                <Phone className="h-2.5 w-2.5" />
                {contacto.telefono || contacto.celular}
              </span>
            )}
            {contacto.email && (
              <span className="text-[10px] text-primary/70">
                {contacto.email}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

interface LiquidacionDetalleCompletaProps {
  item: LiquidacionDetalleItem | null;
  isLoading?: boolean;
  isError?: boolean;
  onBack?: () => void;
  kindLabel: string;
  kindIcon?: LucideIcon;
  backLabel?: string;
  showPdfButton?: boolean;
  showDelegadosButton?: boolean;
  pdfModalContent?: React.ReactNode;
  delegadosModalContent?: React.ReactNode;
}

export function LiquidacionDetalleCompleta({
  item,
  isLoading = false,
  isError = false,
  onBack,
  kindLabel: typeLabel,
  kindIcon: KindIcon = Home,
  backLabel = "Volver",
  showPdfButton = false,
  showDelegadosButton = false,
  pdfModalContent,
  delegadosModalContent,
}: LiquidacionDetalleCompletaProps) {
  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);
  const [pdfModalOpen, setPdfModalOpen] = useState(false);
  const tipoLiquidacion =
    item?.liquidacion_general?.tipo_liquidacion?.codigo || "edificacion";
  const hasIgv = item?.liquidacion_general?.igv?.valor != null;

  if (isLoading) return <LoadingSkeleton />;
  if (isError) return <ErrorState />;
  if (!item) return <EmptyState />;

  return (
    <div className="space-y-0">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <PageSection className="pb-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            {onBack && (
              <Button
                variant="outline"
                size="sm"
                onClick={onBack}
                className="h-8 px-3 gap-1 shrink-0"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                <KindIcon className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-black tracking-tight">
                  {typeLabel}
                </h1>
                <p className="text-sm text-muted-foreground font-mono">
                  {formatPublicId(
                    tipoLiquidacion,
                    item.liquidacion_general.fecha_registro,
                    item.liquidacion_especifica.numero,
                  )}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs text-muted-foreground">
              N° {item.liquidacion_general.numero_revision}
            </span>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground">
              {formatDate(item.liquidacion_general.fecha_registro)}
            </span>
            {showPdfButton && (
              <span
                role="button"
                tabIndex={0}
                onClick={() => setPdfModalOpen(true)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") setPdfModalOpen(true);
                }}
                className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold text-muted-foreground hover:text-primary hover:bg-primary/5 cursor-pointer select-none transition-colors border border-border/60"
              >
                <FileDown className="h-3 w-3" />
                PDF
              </span>
            )}
            {showDelegadosButton && (
              <span
                role="button"
                tabIndex={0}
                onClick={() => setDelegadosModalOpen(true)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ")
                    setDelegadosModalOpen(true);
                }}
                className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border border-border/60 text-xs font-semibold text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
              >
                <Pen className="h-3 w-3" />
                Delegados
              </span>
            )}
          </div>
        </div>
      </PageSection>

      <hr className="border-border" />

      {/* ── Proyecto ───────────────────────────────────────────────────────── */}
      <PageSection className="py-4">
        <SectionLabel>Proyecto</SectionLabel>
        <div className="grid grid-auto-fill-sm gap-x-6 gap-y-2">
          <div>
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Código
            </span>
            <span className="text-sm font-medium text-foreground font-mono ml-2">
              {item.liquidacion_general.proyecto.id}
            </span>
          </div>
          <div>
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Nombre
            </span>
            <span className="text-sm font-medium text-foreground ml-2">
              {item.liquidacion_general.proyecto.denominacion}
            </span>
          </div>
          {item.liquidacion_general.proyecto.direccion && (
            <div className="flex items-start gap-1.5">
              <MapPin className="h-3 w-3 shrink-0 mt-0.5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground leading-relaxed">
                {item.liquidacion_general.proyecto.direccion}
              </span>
            </div>
          )}
          {item.liquidacion_general.proyecto.entidad && (
            <>
              <div>
                <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Entidad
                </span>
                <span className="text-sm font-medium text-foreground ml-2">
                  {item.liquidacion_general.proyecto.entidad.razon_social ??
                    "—"}
                </span>
              </div>
              {item.liquidacion_general.proyecto.entidad.numero_documento && (
                <div>
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                    RUC
                  </span>
                  <span className="text-sm font-medium text-foreground ml-2">
                    {item.liquidacion_general.proyecto.entidad.tipo_documento ??
                      ""}{" "}
                    {item.liquidacion_general.proyecto.entidad.numero_documento}
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </PageSection>

      <hr className="border-border" />

      {/* ── Municipalidad ──────────────────────────────────────────────────── */}
      <PageSection className="py-4">
        <SectionLabel>Municipalidad</SectionLabel>
        <div className="grid grid-auto-fill-sm gap-x-6 gap-y-2">
          <div>
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Nombre
            </span>
            <span className="text-sm font-medium text-foreground ml-2">
              {item.liquidacion_general.municipalidad?.nombre || "—"}
            </span>
          </div>
          {item.liquidacion_general.municipalidad?.codigo && (
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Código
              </span>
              <span className="text-sm font-medium text-foreground ml-2">
                {item.liquidacion_general.municipalidad.codigo}
              </span>
            </div>
          )}
          {item.liquidacion_general.proyecto.distrito && (
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Distrito
              </span>
              <span className="text-sm font-medium text-foreground ml-2">
                {item.liquidacion_general.proyecto.distrito.nombre}
              </span>
            </div>
          )}
          {item.liquidacion_general.proyecto.distrito?.provincia && (
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Provincia
              </span>
              <span className="text-sm font-medium text-foreground ml-2">
                {item.liquidacion_general.proyecto.distrito.provincia.nombre}
              </span>
            </div>
          )}
        </div>
      </PageSection>

      <hr className="border-border" />

      {/* ── Valores ────────────────────────────────────────────────────────── */}
      <PageSection className="py-4">
        <SectionLabel>Valores</SectionLabel>
        <div className="grid grid-auto-fill-sm gap-x-6 gap-y-2">
          <div>
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Subtotal
            </span>
            <span className="text-sm font-medium text-foreground ml-2">
              {formatCurrency(item.liquidacion_general.sub_total)}
            </span>
          </div>
          {hasIgv && (
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                IGV
              </span>
              <span className="text-sm font-medium text-foreground ml-2">
                {formatCurrency(
                  item.liquidacion_general.total -
                    item.liquidacion_general.sub_total,
                )}
              </span>
            </div>
          )}
          {hasIgv && (
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Total
              </span>
              <span className="text-sm font-medium text-foreground ml-2">
                {formatCurrency(item.liquidacion_general.total)}
              </span>
            </div>
          )}
          <div>
            <span className="text-[10px] font-semibold text-primary uppercase tracking-wider">
              Total a Pagar
            </span>
            <span className="text-lg font-black text-primary ml-2">
              {formatCurrency(item.liquidacion_general.total)}
            </span>
          </div>
        </div>
      </PageSection>

      <hr className="border-border" />

      {/* ── Revisiones ─────────────────────────────────────────────────────── */}
      <PageSection className="py-4">
        <div className="flex items-center gap-2 mb-3">
          <SectionLabel>Revisiones</SectionLabel>
          <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-primary/10 text-xs font-bold text-primary">
            {item.liquidacion_general.revisiones_previas.length}
          </span>
          <span className="text-xs text-muted-foreground">
            ({item.liquidacion_general.revisiones_previas.length}{" "}
            {item.liquidacion_general.revisiones_previas.length === 1
              ? "revisión"
              : "revisiones"}
            )
          </span>
        </div>
        <RevisionesSection
          revisiones={item.liquidacion_general.revisiones_previas}
        />
      </PageSection>

      <hr className="border-border" />

      {/* ── Delegados ──────────────────────────────────────────────────────── */}
      <PageSection className="py-4">
        <div className="flex items-center gap-2 mb-2">
          <SectionLabel>Delegados</SectionLabel>
          {item.liquidacion_general.delegados.length > 0 && (
            <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
              {item.liquidacion_general.delegados.length}
            </span>
          )}
        </div>
        <DelegadosSection delegados={item.liquidacion_general.delegados} />
      </PageSection>

      <hr className="border-border" />

      {/* ── Contactos ─────────────────────────────────────────────────────── */}
      <PageSection className="py-4">
        <div className="flex items-center gap-2 mb-2">
          <SectionLabel>Contactos</SectionLabel>
          {item.liquidacion_general.contacto && (
            <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
              1
            </span>
          )}
        </div>
        <ContactosSection contacto={item.liquidacion_general.contacto} />
      </PageSection>

      {/* ── Observación ────────────────────────────────────────────────────── */}
      {item.liquidacion_general.observacion && (
        <>
          <hr className="border-border" />
          <PageSection className="py-4">
            <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-500/5 border border-amber-500/15">
              <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">
                  Observación
                </span>
                <p className="text-sm text-amber-700/90 font-medium leading-relaxed mt-0.5">
                  {item.liquidacion_general.observacion}
                </p>
              </div>
            </div>
          </PageSection>
        </>
      )}

      {/* ── Expediente (if present) ───────────────────────────────────────── */}
      {item.liquidacion_general.expediente && (
        <>
          <hr className="border-border" />
          <PageSection className="py-4">
            <SectionLabel>Expediente</SectionLabel>
            <span className="text-sm font-medium text-foreground">
              {item.liquidacion_general.expediente}
            </span>
          </PageSection>
        </>
      )}

      {/* Modals */}
      {showDelegadosButton && delegadosModalContent && (
        <div>{delegadosModalContent}</div>
      )}
      {showPdfButton && pdfModalContent && <div>{pdfModalContent}</div>}
    </div>
  );
}
