"use client";

import {
  AlertCircle,
  Banknote,
  Building2,
  FileDown,
  FileText,
  Hash,
  MapPin,
  Pen,
  User,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { LiquidacionCardBase } from "./LiquidacionDetalleCompleta";
import { LiquidacionCardHeader } from "./LiquidacionCardHeader";
import { GestionarDelegadosModal } from "./GestionarDelegadosModal";
import { printLiquidacionDocument } from "@/features_deprecated/liquidaciones/components/LiquidacionPDFModal";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { useState } from "react";

export function kindLabel(tipo_liquidacion: string | null | undefined): string {
  if (!tipo_liquidacion) return "Liquidación";
  const KIND_LABEL: Record<string, string> = {
    "habilitacion-urbana": "Habilitación Urbana",
    "mecanica-suelos": "Mecánica de Suelos",
    "impacto-vial": "Impacto Vial",
    "taludes": "Taludes",
    "inspeccion-obra": "Inspección de Obra",
  };
  return KIND_LABEL[tipo_liquidacion] ?? tipo_liquidacion.replace(/[-_]/g, " ");
}

export const formatCurrency = (value: number | string): string => {
  const numValue = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(numValue)) return "—";
  return `S/ ${numValue.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const formatDate = (isoString: string): string => {
  if (!isoString) return "—";
  try {
    return new Date(isoString).toLocaleDateString("es-PE", {
      day: "2-digit", month: "short", year: "numeric",
    });
  } catch { return "—"; }
};

function SectionCard({ icon, title, children, className }: {
  icon: React.ReactNode; title: React.ReactNode; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={cn("rounded-xl border bg-card shadow-sm overflow-hidden", className)}>
      <div className="flex items-center gap-2 px-4 py-2.5 border-b bg-muted/30">
        <span className="text-muted-foreground/70">{icon}</span>
        <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{title}</h4>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function LabelValue({ label, value, className, valueClassName }: {
  label: string; value: React.ReactNode; className?: string; valueClassName?: string;
}) {
  return (
    <div className={cn("flex flex-col", className)}>
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">{label}</span>
      <span className={cn("text-sm font-medium text-foreground", valueClassName)}>{value}</span>
    </div>
  );
}

interface Props {
  item: LiquidacionCardBase;
  typeLabel: string;
  typeSpecificSummary?: React.ReactNode;
}

export function LiquidacionDetalleCard({ item, typeLabel, typeSpecificSummary }: Props) {
  const {
    public_id,
    estado,
    fecha_registro,
    municipalidad,
    proyecto,
    entidad,
    valores,
    delegados,
    contactos,
    revisiones,
    expediente,
    observacion,
    tipo_liquidacion,
  } = item;

  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);
  const tipoLiquidacion = tipo_liquidacion || "edificacion";
  const currentUser = useAuthStore((state) => state.user);
  const pdfUser = currentUser ? { nombres: currentUser.nombres, apellidos: currentUser.apellidos } : undefined;

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <div className="bg-card rounded-xl border shadow-sm overflow-hidden">
        <LiquidacionCardHeader
          data={{
            public_id,
            estado,
            fecha_registro,
            proyectoNombre: proyecto?.nombre ?? "",
            kindBadge: kindLabel(tipoLiquidacion),
            expediente,
            total: valores.total_a_pagar,
          }}
          rightSlotChildren={
            <div className="flex items-center gap-2">
              <span
                role="button" tabIndex={0}
                onClick={() => { void printLiquidacionDocument(item, pdfUser); }}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") void printLiquidacionDocument(item, pdfUser); }}
                className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold text-muted-foreground hover:text-primary hover:bg-primary/5 cursor-pointer select-none transition-colors"
              >
                <FileDown className="h-3 w-3" />
                PDF
              </span>
              <span
                role="button" tabIndex={0}
                onClick={() => setDelegadosModalOpen(true)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setDelegadosModalOpen(true); }}
                className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
              >
                <Pen className="h-3 w-3" />
                Delegados
              </span>
            </div>
          }
        />
      </div>

      {/* Type-specific Summary */}
      <SectionCard icon={<FileText className="h-3.5 w-3.5" />} title={typeLabel} className="border-border/60">
        {typeSpecificSummary ?? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LabelValue label="Tipo" value={kindLabel(tipoLiquidacion)} />
            <LabelValue label="Revisión" value={`N° ${item.numero_revision}`} />
            <LabelValue label="Expediente" value={expediente || "—"} />
          </div>
        )}
      </SectionCard>

      {/* Three-column: Proyecto + Municipalidad + Valores */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SectionCard icon={<Hash className="h-3.5 w-3.5" />} title="Proyecto" className="border-border/60">
          <div className="space-y-2.5">
            <LabelValue label="Código" value={<span className="font-mono text-primary font-semibold">{proyecto.public_id}</span>} />
            <LabelValue label="Nombre" value={proyecto.nombre} />
            {proyecto.entidad && (
              <>
                <LabelValue label="Entidad" value={proyecto.entidad.nombre} />
                <LabelValue label="RUC" value={`${proyecto.entidad.tipo} ${proyecto.entidad.ruc}`} />
              </>
            )}
            {proyecto.direccion && (
              <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{proyecto.direccion}</span>
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard icon={<Building2 className="h-3.5 w-3.5" />} title="Municipalidad" className="border-border/60">
          <div className="space-y-2.5">
            <LabelValue label="Nombre" value={municipalidad?.nombre || "—"} />
            {municipalidad?.codigo && <LabelValue label="Código" value={municipalidad.codigo} />}
            {entidad && (
              <LabelValue label="Entidad" value={entidad.nombre} />
            )}
          </div>
        </SectionCard>

        <SectionCard icon={<Banknote className="h-3.5 w-3.5" />} title="Valores" className="border-border/60">
          <div className="space-y-2.5">
            <LabelValue label="Subtotal" value={formatCurrency(valores.subtotal)} />
            <LabelValue label="Total a Pagar" value={formatCurrency(valores.total_a_pagar)} valueClassName="text-primary font-bold" />
          </div>
        </SectionCard>
      </div>

      {/* Revisiones */}
      <div className="grid grid-cols-1 gap-4">
        <SectionCard
          icon={<Building2 className="h-3.5 w-3.5" />}
          title={<span className="flex items-center gap-1.5">Revisiones<span className="ml-1 inline-flex items-center justify-center h-4 w-4 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">{revisiones.length}</span></span>}
          className="border-border/60"
        >
          {revisiones.length > 0 ? (
            <div className="space-y-3">
              {/* Specialty chips */}
              <div className="flex flex-wrap gap-2">
                {(() => {
                  const seen = new Set<string>();
                  const uniqueEspecialidades = revisiones.flatMap((rev) =>
                    rev.especialidades.filter((esp) => {
                      if (seen.has(esp.id)) return false;
                      seen.add(esp.id);
                      return true;
                    })
                  );
                  return uniqueEspecialidades.map((esp) => (
                    <div
                      key={esp.id}
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <Building2 className="h-3.5 w-3.5 text-primary" />
                      </div>
                      <span className="text-xs font-bold text-foreground">{esp.nombre}</span>
                    </div>
                  ));
                })()}
              </div>
              {/* Tariff data per revision */}
              <div className="space-y-2">
                {revisiones.map((rev, idx) => (
                  <div key={rev.id} className="rounded-lg border border-border/40 bg-muted/20 p-2.5">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                        Revisión {idx + 1}
                      </span>
                    </div>
                    {tipoLiquidacion === "inspeccion-obra" ? (
                      <div className="grid grid-cols-3 gap-2">
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Costo/Visita
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.costo_por_visita != null
                              ? formatCurrency(rev.tarifa.costo_por_visita)
                              : "—"}
                          </span>
                        </div>
                        <div className="flex flex-col">
                        <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                          Cant. Visitas
                        </span>
                        <span className="text-xs font-medium text-foreground">
                          {rev.tarifa?.cantidad_visitas ?? "—"}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Categoría
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.categoria ?? "—"}
                          </span>
                        </div>
                      </div>
                    ) : tipoLiquidacion === "edificacion" ? (
                      <div className="grid grid-cols-3 gap-2">
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            % Liquidación
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.porcentaje_liquidacion != null
                              ? `${(rev.tarifa.porcentaje_liquidacion * 100).toFixed(2)}%`
                              : "—"}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Derecho Mín.
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.derecho_minimo != null
                              ? formatCurrency(rev.tarifa.derecho_minimo)
                              : "—"}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Derecho Máx.
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.derecho_maximo != null
                              ? formatCurrency(rev.tarifa.derecho_maximo)
                              : "—"}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="grid grid-cols-3 gap-2">
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Costo (S/ m²)
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.costo_por_m2 != null
                              ? formatCurrency(rev.tarifa.costo_por_m2)
                              : "—"}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Derecho Mín.
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.derecho_minimo != null
                              ? formatCurrency(rev.tarifa.derecho_minimo)
                              : "—"}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[8px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Derecho Máx.
                          </span>
                          <span className="text-xs font-medium text-foreground">
                            {rev.tarifa?.derecho_maximo != null
                              ? formatCurrency(rev.tarifa.derecho_maximo)
                              : "—"}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground/60 italic">Sin revisiones registradas</p>
          )}
        </SectionCard>
      </div>

      {/* Delegados */}
      <SectionCard icon={<Users className="h-3.5 w-3.5" />} title={`Delegados${delegados.length > 0 ? ` (${delegados.length})` : ""}`} className="border-border/60">
        {delegados.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {delegados.map((d) => (
              <div key={d.id} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <User className="h-3.5 w-3.5 text-muted-foreground" />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">
                    {[d.perfil_ingeniero_nombres, d.perfil_ingeniero_apellidos].filter(Boolean).join(" ") || "—"}
                  </span>
                  {d.perfil_ingeniero_cip && (
                    <span className="text-[10px] text-muted-foreground">CIP: {d.perfil_ingeniero_cip}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground/60 italic">Sin delegados registrados</p>
        )}
        <div className="mt-3">
          <Button
            type="button" variant="ghost" size="sm"
            onClick={() => setDelegadosModalOpen(true)}
            className="h-7 rounded-lg gap-1.5 text-[11px] font-semibold text-muted-foreground hover:text-primary hover:bg-primary/5"
          >
            <Pen className="h-3 w-3" />
            Gestionar delegados
          </Button>
        </div>
      </SectionCard>

      {/* Contactos */}
      {contactos.length > 0 && (
        <SectionCard icon={<Users className="h-3.5 w-3.5" />} title={`Contactos (${contactos.length})`} className="border-border/60">
          <div className="flex flex-wrap gap-2">
            {contactos.map((c) => (
              <div key={c.id} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary/40 border border-border/60">
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-foreground">
                    {[c.nombres, c.apellidos].filter(Boolean).join(" ") || "—"}
                  </span>
                  {c.cargo && <span className="text-[10px] text-muted-foreground">{c.cargo}</span>}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Totales */}
      <SectionCard icon={<Banknote className="h-3.5 w-3.5" />} title="Totales" className="border-border/60">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <LabelValue label="Subtotal" value={formatCurrency(valores.subtotal)} />
          {"igv" in valores && valores.igv != null && (
            <LabelValue label="IGV" value={formatCurrency(valores.igv)} />
          )}
          {"total" in valores && valores.total != null && (
            <LabelValue label="Total" value={formatCurrency(valores.total)} />
          )}
          <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 -my-0.5">
            <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">Total a Pagar</span>
            <span className="text-base font-black text-primary">{formatCurrency(valores.total_a_pagar)}</span>
          </div>
        </div>
      </SectionCard>

      {observacion && (
        <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
          <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Observación</span>
            <p className="text-sm text-amber-700/90 font-medium leading-relaxed mt-0.5">{observacion}</p>
          </div>
        </div>
      )}

      <GestionarDelegadosModal
        open={delegadosModalOpen}
        onOpenChange={setDelegadosModalOpen}
        liquidacionId={item.id}
        municipalidadId={municipalidad.id}
        tipoLiquidacion={tipoLiquidacion}
        revisionIds={revisiones.map((r) => r.id)}
        delegadosActuales={delegados}
      />
    </div>
  );
}
