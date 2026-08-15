"use client";

/**
 * DelegadoCard — Card para un delegado profesional.
 * Distribución balanceada: header (avatar + nombre + estado),
 * luego grid 2 columnas (CIP/DNI | Especialidad/Capítulo),
 * y abajo municipalidades asignadas.
 */
import {
  BadgeCheck,
  Building2,
  IdCard,
  Landmark,
  Layers,
  User,
} from "lucide-react";
import type { DelegadoOut } from "../types/delegados.types";

export type DelegadoCardItem = DelegadoOut;

interface DelegadoCardProps {
  item: DelegadoCardItem;
}

function initials(nombre: string): string {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

function estadoConfig(estado?: string | null): {
  label: string;
  className: string;
} {
  switch (estado) {
    case "vigente":
      return {
        label: "Vigente",
        className: "bg-green-500/10 border-green-500/20 text-green-600",
      };
    case "sin_vigencia":
      return {
        label: "Sin Vigencia",
        className: "bg-amber-500/10 border-amber-500/20 text-amber-600",
      };
    case "sin_asignaciones":
      return {
        label: "Sin Asignaciones",
        className: "bg-muted border-border text-muted-foreground",
      };
    default:
      return {
        label: estado ?? "—",
        className: "bg-muted border-border text-muted-foreground",
      };
  }
}

function InfoItem({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value?: string | null;
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon className="h-3.5 w-3.5 text-primary/60 shrink-0 mt-0.5" />
      <div className="min-w-0">
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          {label}
        </p>
        <p className="text-sm font-semibold text-foreground truncate">
          {value || "—"}
        </p>
      </div>
    </div>
  );
}

export function DelegadoCard({ item }: DelegadoCardProps) {
  const perfil = item.perfil_ingeniero;
  const vigentes = (item.municipalidades || []).filter((m) => m.es_vigente);
  const municipiosMostrar =
    vigentes.length > 0 ? vigentes : item.municipalidades || [];
  const estado = estadoConfig(item.estado);

  return (
    <div className="rounded-2xl border bg-card shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* Header: avatar + nombre + estado */}
      <div className="px-4 py-3 bg-gradient-to-r from-muted/40 via-muted/20 to-transparent border-b border-border/60 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary font-black text-lg">
            {initials(perfil.nombre_completo)}
          </div>
          <div className="min-w-0">
            <h3 className="text-base font-bold text-foreground tracking-tight truncate">
              {perfil.nombre_completo}
            </h3>
            <p className="text-[11px] text-muted-foreground">
              {[
                perfil.nombres,
                perfil.apellido_paterno,
                perfil.apellido_materno,
              ]
                .filter(Boolean)
                .join(" ") || "—"}
            </p>
          </div>
        </div>
        <span
          className={`shrink-0 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${estado.className}`}
        >
          <BadgeCheck className="h-3 w-3" />
          {estado.label}
        </span>
      </div>

      {/* Body: grid 2 columnas */}
      <div className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <InfoItem icon={IdCard} label="CIP" value={perfil.cip} />
          <InfoItem icon={User} label="DNI" value={perfil.dni} />
          <InfoItem
            icon={Layers}
            label="Especialidad"
            value={perfil.especialidad?.nombre}
          />
          <InfoItem
            icon={Landmark}
            label="Capítulo"
            value={perfil.capitulo?.abreviacion ?? perfil.capitulo?.nombre}
          />
        </div>

        {/* Municipalidades */}
        {municipiosMostrar.length > 0 && (
          <div className="mt-4 pt-3 border-t border-border/50">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1 mb-2">
              <Building2 className="h-3 w-3 text-primary/60" />
              Municipalidades asignadas
            </p>
            <div className="flex flex-wrap gap-1.5">
              {municipiosMostrar.map((m) => (
                <span
                  key={m.id}
                  className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/20 px-2 py-1 text-[11px]"
                >
                  {m.municipalidad?.codigo
                    ? `${m.municipalidad.codigo} - `
                    : ""}
                  {m.municipalidad?.nombre ?? "—"}
                  {m.categoria && (
                    <span className="text-muted-foreground">
                      ({m.categoria})
                    </span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
