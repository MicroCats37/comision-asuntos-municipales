"use client";

import { Building2, MapPin, User } from "lucide-react";
import type { LiquidacionGeneralOutput } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { DetalleField, DetalleSection } from "./DetalleSection";

interface Props {
  lg: LiquidacionGeneralOutput;
}

const formatDocumento = (tipo: string | null, numero: string | null) => {
  if (!tipo && !numero) return null;
  return [tipo, numero].filter(Boolean).join(" ");
};

export function DetalleProyectoSection({ lg }: Props) {
  const proyecto = lg.proyecto;
  const distrito = proyecto.distrito;
  const distritoLabel = distrito
    ? [
        distrito.nombre,
        distrito.provincia?.nombre,
        distrito.departamento?.nombre,
      ]
        .filter(Boolean)
        .join(" - ")
    : "";
  const municipalidad = lg.municipalidad;
  const muniLabel = municipalidad
    ? municipalidad.codigo
      ? `${municipalidad.codigo} - ${municipalidad.nombre}`
      : municipalidad.nombre
    : "";
  const entidad = proyecto.entidad;
  const entidadDoc = formatDocumento(
    entidad?.tipo_documento ?? null,
    entidad?.numero_documento ?? null,
  );
  const administrado = proyecto.nombre_propietario;

  return (
    <DetalleSection title="Proyecto" icon={Building2} className="lg:col-span-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
        {entidad ? (
          <DetalleField label="Entidad">
            <span className="font-semibold text-foreground">
              {entidad.razon_social}
            </span>
          </DetalleField>
        ) : null}
        {entidadDoc ? (
          <DetalleField label="Documento" mono>
            {entidadDoc}
          </DetalleField>
        ) : null}
        {administrado ? (
          <DetalleField label="Administrado">
            <span className="inline-flex items-center gap-1.5">
              <User className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
              {administrado}
            </span>
          </DetalleField>
        ) : null}
        {lg.denominacion_de_proyecto ? (
          <DetalleField label="Proyecto">
            <span className="text-foreground font-semibold">
              {lg.denominacion_de_proyecto}
            </span>
          </DetalleField>
        ) : null}
        {proyecto.direccion ? (
          <DetalleField label="Direccion">
            <span className="inline-flex items-baseline gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
              <span>{proyecto.direccion}</span>
              {proyecto.urbanizacion ? (
                <span className="text-[10px] text-muted-foreground/70 italic">
                  Urb. {proyecto.urbanizacion}
                </span>
              ) : null}
            </span>
          </DetalleField>
        ) : null}
        {distritoLabel ? (
          <DetalleField label="Distrito">
            <span className="text-muted-foreground">{distritoLabel}</span>
          </DetalleField>
        ) : null}
        {muniLabel ? (
          <DetalleField label="Municipalidad">
            <span className="font-mono text-foreground/90">{muniLabel}</span>
          </DetalleField>
        ) : null}
      </div>
    </DetalleSection>
  );
}
