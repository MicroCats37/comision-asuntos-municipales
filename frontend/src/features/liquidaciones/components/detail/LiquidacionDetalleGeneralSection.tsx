"use client";

import {
  CheckCircle2,
  FileText,
  MapPin,
  Phone,
  User,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { LiquidacionGeneralOutput } from "../../schemas/liquidacion-base.schema";
import {
  formatCurrency,
  formatDate,
  getEstadoBadgeClass,
  LabelValue,
} from "../liquidacion-ui";

interface LiquidacionDetalleGeneralSectionProps {
  /** Full liquidacion general data from backend */
  liquidacionGeneral: LiquidacionGeneralOutput;
}

/**
 * Compact dense layout for liquidacion general data.
 * Two-row structure: primary info (expediente, entidad, proyecto, ubicación, fecha, totals)
 * then secondary compact row (contacto, creador, comprobante).
 * No full-width section boxes — groups share horizontal space.
 */
export function LiquidacionDetalleGeneralSection({
  liquidacionGeneral: lg,
}: LiquidacionDetalleGeneralSectionProps) {
  const distritoLabel = lg.proyecto.distrito
    ? [
        lg.proyecto.distrito.nombre,
        lg.proyecto.distrito.provincia?.nombre,
        lg.proyecto.distrito.departamento?.nombre,
      ]
        .filter(Boolean)
        .join(" - ")
    : "—";

  const municipalidadLabel = lg.municipalidad
    ? lg.municipalidad.codigo
      ? `${lg.municipalidad.codigo} - ${lg.municipalidad.nombre}`
      : lg.municipalidad.nombre
    : "—";

  const usuarioLabel = lg.usuario_creador
    ? [lg.usuario_creador.nombres, lg.usuario_creador.apellidos]
        .filter(Boolean)
        .join(" ") ||
      lg.usuario_creador.username ||
      "—"
    : "—";

  const contactoLabel = lg.contacto
    ? [lg.contacto.nombres, lg.contacto.apellidos].filter(Boolean).join(" ") ||
      "—"
    : "—";

  const comprobanteActivo =
    lg.comprobantes?.find((c) => c.activo) ?? null;

  const hasComprobanteOrMeta =
    comprobanteActivo || lg.codigo_cta || lg.legacy !== undefined;

  const hasContacto = lg.contacto != null;
  const hasCreador = lg.usuario_creador != null;

  return (
    <div className="space-y-4">
      {/* ── ROW 1: Primary — expediente, entidad, proyecto, ubicación, fecha, totales ─── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* Expediente + Revision */}
        <div className="rounded-lg border border-border/50 bg-card p-3">
          <LabelValue
            label="Expediente"
            value={lg.expediente || "—"}
            valueClassName="text-sm"
          />
          {lg.numero_revision && (
            <p className="text-[10px] text-muted-foreground mt-1">
              Rev. N° {lg.numero_revision}
            </p>
          )}
        </div>

        {/* Entidad / Administrado */}
        <div className="rounded-lg border border-border/50 bg-card p-3">
          {lg.proyecto.entidad ? (
            <>
              <LabelValue
                label="Entidad / Administrado"
                value={lg.proyecto.entidad.razon_social}
                valueClassName="text-xs leading-tight"
              />
              <p className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                {lg.proyecto.entidad.tipo_documento}{" "}
                {lg.proyecto.entidad.numero_documento}
              </p>
            </>
          ) : (
            <p className="text-xs text-muted-foreground italic">Sin entidad</p>
          )}
        </div>

        {/* Proyecto */}
        <div className="rounded-lg border border-border/50 bg-card p-3">
          <LabelValue
            label="Proyecto"
            value={lg.denominacion_de_proyecto}
            valueClassName="text-xs leading-tight"
          />
          {lg.proyecto.nombre_propietario && (
            <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
              {lg.proyecto.nombre_propietario}
            </p>
          )}
          {lg.proyecto.direccion && (
            <div className="flex items-start gap-1 mt-0.5">
              <MapPin className="h-2.5 w-2.5 shrink-0 mt-0.5 text-muted-foreground/60" />
              <span className="text-[10px] text-muted-foreground leading-tight truncate">
                {lg.proyecto.direccion}
              </span>
            </div>
          )}
        </div>

        {/* Ubicación */}
        <div className="rounded-lg border border-border/50 bg-card p-3">
          <LabelValue
            label="Municipalidad"
            value={municipalidadLabel}
            valueClassName="text-xs leading-tight"
          />
          <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
            {distritoLabel}
          </p>
        </div>

        {/* Fecha + IGV/UIT */}
        <div className="rounded-lg border border-border/50 bg-card p-3">
          <LabelValue
            label="Registro"
            value={formatDate(lg.fecha_registro)}
            valueClassName="text-xs"
          />
          <div className="flex items-center gap-2 mt-0.5">
            {lg.igv && (
              <span className="text-[10px] text-muted-foreground">
                IGV {lg.igv.valor}%
              </span>
            )}
            {lg.uit && (
              <span className="text-[10px] text-muted-foreground">
                UIT {formatCurrency(lg.uit.valor)}
              </span>
            )}
          </div>
        </div>

        {/* Totales */}
        <div className="rounded-lg border border-border/50 bg-card p-3">
          <LabelValue
            label="Subtotal"
            value={formatCurrency(lg.sub_total)}
            valueClassName="text-xs"
          />
          <LabelValue
            label="Total"
            value={formatCurrency(lg.total)}
            valueClassName="text-sm font-bold text-primary mt-0.5"
          />
        </div>
      </div>

      {/* ── Estado badge row ─── */}
      {lg.estado && (
        <div className="flex items-center gap-2 px-1">
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
              getEstadoBadgeClass(lg.estado),
            )}
          >
            {lg.estado}
          </span>
          {hasComprobanteOrMeta && (
            <>
              <span className="text-border/40">|</span>
              {/* Comprobante / Metadata inline */}
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                {lg.legacy !== undefined && (
                  <span className="text-[10px] text-muted-foreground">
                    Legacy:{" "}
                    <span
                      className={cn(
                        "font-semibold",
                        lg.legacy ? "text-amber-600" : "text-emerald-600",
                      )}
                    >
                      {lg.legacy ? "Sí" : "No"}
                    </span>
                  </span>
                )}
                {lg.codigo_cta && (
                  <span className="text-[10px] text-muted-foreground font-mono">
                    CTA {lg.codigo_cta}
                  </span>
                )}
                {comprobanteActivo ? (
                  <span className="flex items-center gap-1 text-[10px] text-emerald-700">
                    <CheckCircle2 className="h-2.5 w-2.5" />
                    {comprobanteActivo.tipo_comprobante}{" "}
                    {comprobanteActivo.serie}-{comprobanteActivo.numero}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-[10px] text-muted-foreground/50">
                    <XCircle className="h-2.5 w-2.5" />
                    Sin comprobante
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── ROW 2: Contacto + Creador (compact inline) ─── */}
      {(hasContacto || hasCreador) && (
        <div className="flex flex-wrap items-start gap-3 rounded-lg border border-border/50 bg-card p-3">
          {hasContacto && lg.contacto && (
            <div className="flex items-center gap-2">
              <Phone className="h-3 w-3 text-muted-foreground/60 shrink-0" />
              <span className="text-xs text-foreground">{contactoLabel}</span>
              {lg.contacto.dni && (
                <span className="text-[10px] text-muted-foreground">
                  · DNI {lg.contacto.dni}
                </span>
              )}
              {lg.contacto.cargo && (
                <span className="text-[10px] text-muted-foreground">
                  · {lg.contacto.cargo}
                </span>
              )}
              {lg.contacto.email && (
                <span className="text-[10px] text-muted-foreground truncate">
                  · {lg.contacto.email}
                </span>
              )}
              {(lg.contacto.telefono || lg.contacto.celular) && (
                <span className="text-[10px] text-muted-foreground">
                  · {lg.contacto.celular || lg.contacto.telefono}
                </span>
              )}
            </div>
          )}
          {hasContacto && hasCreador && (
            <span className="text-border/40">|</span>
          )}
          {hasCreador && (
            <div className="flex items-center gap-2">
              <User className="h-3 w-3 text-muted-foreground/60 shrink-0" />
              <span className="text-xs text-foreground">{usuarioLabel}</span>
              {lg.usuario_creador?.dni && (
                <span className="text-[10px] text-muted-foreground">
                  · DNI {lg.usuario_creador.dni}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Observación ─── */}
      {lg.observacion && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/15">
          <FileText className="h-3.5 w-3.5 text-amber-600 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-700/90 font-medium leading-relaxed">
            {lg.observacion}
          </p>
        </div>
      )}
    </div>
  );
}
