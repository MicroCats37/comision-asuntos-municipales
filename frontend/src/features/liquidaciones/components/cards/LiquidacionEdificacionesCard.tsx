"use client";

import {
  Banknote,
  Building2,
  FileDown,
  FileText,
  Hash,
  MapPin,
  Percent,
  Phone,
  Scale,
  User,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
/**
 * LiquidacionEdificacionesCard — Card de Edificaciones (PorcentajeObra)
 * rediseñada para mostrar TODA la data rica del backend:
 *  - liquidacion_general: municipalidad, usuario_creador, distrito, igv, uit, contacto
 *  - liquidacion_tipo: valor_declarado, % liquidación, derechos, detalles[]
 *
 * Arquitectura: LiquidacionBaseCard (shell) + SectionCard/LabelValue (composición).
 */
import { useState } from "react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacion } from "../../pdf/printLiquidacion";
import type { LiquidacionEdificacionesListItem } from "../../schemas/liquidacion-edificaciones.schema";
import { formatPublicId } from "../../utils/formatPublicId";
import { GestionarDelegadosModal } from "../GestionarDelegadosModal";
import {
  LiquidacionCardHeader,
  type LiquidacionCardHeaderData,
} from "../LiquidacionCardHeader";
import {
  formatCurrency,
  formatDate,
  formatEnumLabel,
  LabelValue,
  SectionCard,
} from "../liquidacion-ui";
import { LiquidacionBaseCard } from "./LiquidacionBaseCard";

interface LiquidacionEdificacionesCardProps {
  item: LiquidacionEdificacionesListItem;
}

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

export function LiquidacionEdificacionesCard({
  item,
}: LiquidacionEdificacionesCardProps) {
  const router = useRouter();
  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);

  const lg = item.liquidacion_general;
  const lt = item.liquidacion_tipo;

  // Convertir item al tipo que el PDF espera
  const pdfItem: PdfLiquidacionItem = {
    liquidacion_general: lg as PdfLiquidacionItem["liquidacion_general"],
    liquidacion_especifica:
      item.liquidacion_especifica as PdfLiquidacionItem["liquidacion_especifica"],
    liquidacion_tipo: lt as PdfLiquidacionItem["liquidacion_tipo"],
  };

  const handlePrint = () => {
    printLiquidacion(pdfItem, "edificacion");
  };

  const headerData: LiquidacionCardHeaderData = {
    public_id: formatPublicId(
      "edificacion",
      lg.fecha_registro,
      item.liquidacion_especifica.numero,
    ),
    fecha_registro: lg.fecha_registro,
    proyectoNombre: lg.proyecto.denominacion,
    kindBadge: "Edificación",
    expediente: lg.expediente,
    total: lg.total,
  };

  const handleVerDetalle = () => {
    router.push(`/liquidaciones/edificaciones/${lg.id}`);
  };

  const rightSlotActions = (
    <div className="flex items-center gap-2">
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation();
          setDelegadosModalOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.stopPropagation();
            setDelegadosModalOpen(true);
          }
        }}
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
      >
        <Users className="h-3 w-3" />
        Delegados
      </span>
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation();
          handlePrint();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.stopPropagation();
            handlePrint();
          }
        }}
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
      >
        <FileDown className="h-3 w-3" />
        PDF
      </span>
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation();
          handleVerDetalle();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.stopPropagation();
            handleVerDetalle();
          }
        }}
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50 cursor-pointer select-none transition-colors"
      >
        Ver detalle
      </span>
    </div>
  );

  // ── Data helpers ─────────────────────────────────────────────────────────
  const distritoLabel = lg.proyecto.distrito
    ? [
        lg.proyecto.distrito.nombre,
        lg.proyecto.distrito.provincia?.nombre,
        lg.proyecto.distrito.departamento?.nombre,
      ]
        .filter(Boolean)
        .join(" - ")
    : "—";
  const usuarioLabel = lg.usuario_creador
    ? [lg.usuario_creador.nombres, lg.usuario_creador.apellidos]
        .filter(Boolean)
        .join(" ") ||
      lg.usuario_creador.username ||
      "—"
    : "—";
  const municipalidadLabel = lg.municipalidad
    ? lg.municipalidad.codigo
      ? `${lg.municipalidad.codigo} - ${lg.municipalidad.nombre}`
      : lg.municipalidad.nombre
    : "—";

  return (
    <>
      <LiquidacionBaseCard
        data={headerData}
        rightSlotChildren={rightSlotActions}
      >
        {/* ─── Fila 1: Trámite + Municipalidad + Usuario + Fecha ─── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SectionCard
            icon={<FileText className="h-3.5 w-3.5" />}
            title="Trámite"
            className="border-border/60"
          >
            <div className="space-y-2">
              <LabelValue
                label="Tipo"
                value={getTipoTramiteLabel(lt.tipo_tramite)}
              />
              <LabelValue label="Revisión" value={`N° ${lg.numero_revision}`} />
              <LabelValue label="Expediente" value={lg.expediente || "—"} />
            </div>
          </SectionCard>

          <SectionCard
            icon={<Building2 className="h-3.5 w-3.5" />}
            title="Municipalidad"
            className="border-border/60"
          >
            <div className="space-y-2">
              <LabelValue label="Nombre" value={municipalidadLabel} />
              <LabelValue label="Distrito" value={distritoLabel} />
            </div>
          </SectionCard>

          <SectionCard
            icon={<User className="h-3.5 w-3.5" />}
            title="Creador"
            className="border-border/60"
          >
            <div className="space-y-2">
              <LabelValue label="Usuario" value={usuarioLabel} />
              {lg.usuario_creador?.dni && (
                <LabelValue label="DNI" value={lg.usuario_creador.dni} />
              )}
              {lg.usuario_creador?.email && (
                <LabelValue label="Email" value={lg.usuario_creador.email} />
              )}
            </div>
          </SectionCard>

          <SectionCard
            icon={<Scale className="h-3.5 w-3.5" />}
            title="Fecha"
            className="border-border/60"
          >
            <div className="space-y-2">
              <LabelValue
                label="Registro"
                value={formatDate(lg.fecha_registro)}
              />
              <LabelValue
                label="IGV"
                value={lg.igv ? `${formatDecimalPercent(lg.igv.valor)}` : "—"}
              />
              <LabelValue
                label="UIT"
                value={lg.uit ? formatCurrency(lg.uit.valor) : "—"}
              />
            </div>
          </SectionCard>
        </div>

        {/* ─── Fila 2: Proyecto + Entidad + Valores ─── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SectionCard
            icon={<Hash className="h-3.5 w-3.5" />}
            title="Proyecto"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue
                label="Denominación"
                value={lg.proyecto.denominacion}
              />
              {lg.proyecto.nombre_propietario && (
                <LabelValue
                  label="Propietario"
                  value={lg.proyecto.nombre_propietario}
                />
              )}
              {lg.proyecto.direccion && (
                <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">
                    {lg.proyecto.direccion}
                  </span>
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard
            icon={<Building2 className="h-3.5 w-3.5" />}
            title="Entidad"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              {lg.proyecto.entidad ? (
                <>
                  <LabelValue
                    label="Razón Social"
                    value={lg.proyecto.entidad.razon_social}
                  />
                  <LabelValue
                    label="Documento"
                    value={`${lg.proyecto.entidad.tipo_documento} ${lg.proyecto.entidad.numero_documento}`}
                  />
                </>
              ) : (
                <p className="text-xs text-muted-foreground/60 italic">
                  Sin entidad
                </p>
              )}
            </div>
          </SectionCard>

          <SectionCard
            icon={<Percent className="h-3.5 w-3.5" />}
            title="Liquidación"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue
                label="Valor Declarado"
                value={formatCurrency(lt.valor_declarado ?? 0)}
              />
              <LabelValue
                label="% Liquidación"
                value={formatDecimalPercent(lt.porcentaje_liquidacion ?? 0)}
              />
              {lt.derecho_minimo != null && (
                <LabelValue
                  label="Derecho Mín."
                  value={formatCurrency(lt.derecho_minimo)}
                />
              )}
              {lt.derecho_maximo != null && (
                <LabelValue
                  label="Derecho Máx."
                  value={formatCurrency(lt.derecho_maximo)}
                />
              )}
            </div>
          </SectionCard>
        </div>

        {/* ─── Fila 3: Contacto + Totales ─── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SectionCard
            icon={<Phone className="h-3.5 w-3.5" />}
            title="Contacto"
            className="border-border/60"
          >
            {lg.contacto ? (
              <div className="space-y-2">
                <LabelValue
                  label="Nombre"
                  value={
                    [lg.contacto.nombres, lg.contacto.apellidos]
                      .filter(Boolean)
                      .join(" ") || "—"
                  }
                />
                {lg.contacto.cargo && (
                  <LabelValue label="Cargo" value={lg.contacto.cargo} />
                )}
                {lg.contacto.email && (
                  <LabelValue label="Email" value={lg.contacto.email} />
                )}
                {(lg.contacto.telefono || lg.contacto.celular) && (
                  <LabelValue
                    label="Teléfono"
                    value={lg.contacto.celular || lg.contacto.telefono || "—"}
                  />
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/60 italic">
                Sin contacto registrado
              </p>
            )}
          </SectionCard>

          <SectionCard
            icon={<Banknote className="h-3.5 w-3.5" />}
            title="Totales"
            className="border-border/60"
          >
            <div className="grid grid-cols-2 gap-3">
              <LabelValue
                label="Subtotal"
                value={formatCurrency(lg.sub_total)}
              />
              <LabelValue label="Total" value={formatCurrency(lg.total)} />
              <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2">
                <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">
                  Total a Pagar
                </span>
                <span className="text-base font-black text-primary">
                  {formatCurrency(lg.total)}
                </span>
              </div>
            </div>
          </SectionCard>
        </div>

        {/* ─── Tarifas / Detalles ─── */}
        <SectionCard
          icon={<Scale className="h-3.5 w-3.5" />}
          title={
            <span className="flex items-center gap-1.5">
              Tarifas
              <span className="ml-1 inline-flex items-center justify-center h-4 w-4 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
                {lt.detalles?.length ?? 0}
              </span>
            </span>
          }
          className="border-border/60"
        >
          {(lt.detalles?.length ?? 0) > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {lt.detalles?.map((detalle) => (
                <div
                  key={detalle.id}
                  className="rounded-lg border border-border/40 bg-muted/20 p-3"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                      Detalle
                    </span>
                    <span className="text-[10px] font-bold text-primary">
                      {formatDecimalPercent(detalle.porcentaje_aplicado)}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    <div className="flex flex-col">
                      <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Subtotal Parcial
                      </span>
                      <span className="text-sm font-bold">
                        {formatCurrency(detalle.subtotal)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground/60 italic">
              Sin tarifas registradas
            </p>
          )}
        </SectionCard>

        {/* ─── Observación ─── */}
        {lg.observacion && (
          <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
            <FileText className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">
                Observación
              </span>
              <p className="text-sm text-amber-700/90 font-medium leading-relaxed mt-0.5">
                {lg.observacion}
              </p>
            </div>
          </div>
        )}
      </LiquidacionBaseCard>

      <GestionarDelegadosModal
        open={delegadosModalOpen}
        onOpenChange={setDelegadosModalOpen}
        liquidacionId={lg.id}
        municipalidadId={lg.municipalidad?.id ?? ""}
        tipoLiquidacion="edificacion"
        delegadosActuales={(lg.delegados ?? []).map((d) => ({ id: d.id }))}
      />
    </>
  );
}
