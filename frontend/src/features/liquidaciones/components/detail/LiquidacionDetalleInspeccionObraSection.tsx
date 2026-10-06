"use client";

import { ClipboardCheck, Receipt, User } from "lucide-react";
import type {
  RegistroPagoOut,
  VisitasDatosOut,
} from "../../schemas/liquidacion-visitas.schema";
import { formatEnumLabel } from "../liquidacion-ui";

interface LiquidacionDetalleInspeccionObraSectionProps {
  /** Visitas data (liquidacion_tipo) */
  liquidacionTipo: VisitasDatosOut;
}

/**
 * Compact Inspección de Obra-specific (Visitas) data for the detail modal.
 * Mirrors the compact layout of LiquidacionDetalleEdificacionesSection.
 * Shows categoria, cantidad_visitas, porcentaje_uit, and inspectores.
 */
export function LiquidacionDetalleInspeccionObraSection({
  liquidacionTipo: lt,
}: LiquidacionDetalleInspeccionObraSectionProps) {
  return (
    <div className="space-y-3">
      {/* ── Section title ─── */}
      <div className="flex items-center gap-2">
        <ClipboardCheck className="h-3.5 w-3.5 text-primary/60" />
        <h3 className="text-xs font-bold text-foreground uppercase tracking-wide">
          Detalle técnico de Inspección de Obra
        </h3>
        <div className="flex-1 h-px bg-border/40" />
      </div>

      {/* ── Params strip: Liquidación params ─── */}
      <div className="flex flex-wrap items-start gap-3 min-w-0">
        {/* Liquidación params */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-lg border border-border/50 bg-card px-3 py-2">
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Categoría
            </span>
            <span className="text-xs font-medium text-foreground">
              {formatEnumLabel(lt.categoria) ?? "—"}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Cant. Visitas
            </span>
            <span className="text-xs font-medium text-foreground">
              {lt.cantidad_visitas ?? 0}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              % UIT
            </span>
            <span className="text-xs font-medium text-foreground">
              {lt.porcentaje_uit ?? 0}%
            </span>
          </div>
        </div>
      </div>

      {/* ── Inspectores table — compact ─── */}
      <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border/40 bg-muted/20">
          <User className="h-3 w-3 text-muted-foreground/70" />
          <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
            Inspectores asignados
          </h4>
          <span className="ml-1 inline-flex items-center justify-center h-3.5 w-3.5 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
            {lt.inspectores?.length ?? 0}
          </span>
        </div>
        {(lt.inspectores?.length ?? 0) > 0 ? (
          <div className="divide-y divide-border/20">
            {/* Table header */}
            <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-3 py-1.5 bg-muted/15 min-w-0">
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                Nombre
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[4rem]">
                CIP
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[5rem]">
                Categoría
              </span>
            </div>
            {/* Table rows */}
            {lt.inspectores?.map((inspector) => (
              <div
                key={inspector.id}
                className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-3 py-2 hover:bg-muted/8 transition-colors min-w-0"
              >
                <span className="text-xs text-foreground truncate">
                  {inspector.perfil_ingeniero.nombre_completo}
                </span>
                <span className="text-xs font-medium text-primary text-right min-w-[4rem]">
                  {inspector.perfil_ingeniero.cip}
                </span>
                <span className="text-xs text-muted-foreground text-right min-w-[5rem]">
                  {inspector.categoria ?? "—"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-3 py-2 text-xs text-muted-foreground/60 italic">
            Sin inspectores asignados
          </p>
        )}
      </div>

      {/* ── Registros de pago table — compact ─── */}
      <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border/40 bg-muted/20">
          <Receipt className="h-3 w-3 text-muted-foreground/70" />
          <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
            Registros de pago
          </h4>
          <span className="ml-1 inline-flex items-center justify-center h-3.5 w-3.5 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
            {lt.registros_pago?.length ?? 0}
          </span>
        </div>
        {(lt.registros_pago?.length ?? 0) > 0 ? (
          <div className="divide-y divide-border/20">
            {/* Table header */}
            <div className="grid grid-cols-[auto_auto_1fr_auto] gap-x-4 px-3 py-1.5 bg-muted/15 min-w-0">
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider min-w-[3.5rem]">
                Periodo
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider min-w-[3.5rem]">
                Mes
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                Inspecciones pagadas
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[5rem]">
                Fecha registro
              </span>
            </div>
            {/* Table rows — sorted by fecha_registro desc */}
            {(
              [...(lt.registros_pago ?? [])].sort((a, b) => {
                const dateA = a.fecha_registro
                  ? new Date(a.fecha_registro).getTime()
                  : 0;
                const dateB = b.fecha_registro
                  ? new Date(b.fecha_registro).getTime()
                  : 0;
                return dateB - dateA;
              }) as RegistroPagoOut[]
            ).map((registro) => (
              <div
                key={registro.id}
                className="grid grid-cols-[auto_auto_1fr_auto] gap-x-4 px-3 py-2 hover:bg-muted/8 transition-colors min-w-0"
              >
                <span className="text-xs text-foreground min-w-[3.5rem]">
                  {registro.periodo ?? "—"}
                </span>
                <span className="text-xs text-foreground min-w-[3.5rem]">
                  {registro.mes ?? "—"}
                </span>
                <span className="text-xs font-medium text-primary">
                  {registro.inspecciones_pagadas ?? 0}
                </span>
                <span className="text-xs text-muted-foreground text-right min-w-[5rem]">
                  {registro.fecha_registro
                    ? new Date(registro.fecha_registro).toLocaleDateString(
                        "es-PE",
                        {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                        },
                      )
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-3 py-2 text-xs text-muted-foreground/60 italic">
            Sin registros de pago
          </p>
        )}
      </div>
    </div>
  );
}
