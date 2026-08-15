"use client";

/**
 * InspectorCard — Card para un inspector registrado.
 * Distribución balanceada: header (avatar + nombre + badge),
 * grid 2 columnas (CIP/DNI | Tipo/Registro).
 */
import { BadgeCheck, IdCard, Mail, ShieldCheck, User } from "lucide-react";
import type { InspectorListItem } from "../types/inspectores.types";

export type InspectorCardItem = InspectorListItem;

interface InspectorCardProps {
  item: InspectorCardItem;
}

function initials(nombre: string): string {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

function formatTipoLiquidacion(value?: string | null): string {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" ");
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

export function InspectorCard({ item }: InspectorCardProps) {
  const perfil = item.perfil_ingeniero;
  const correo =
    perfil.correo_personal ?? perfil.correo_institucional ?? item.email;

  return (
    <div className="rounded-2xl border bg-card shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* Header: avatar + nombre + badge */}
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
        <span className="shrink-0 inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2.5 py-1 text-[10px] font-bold text-blue-600 uppercase tracking-wider">
          <ShieldCheck className="h-3 w-3" />
          Inspector
        </span>
      </div>

      {/* Body: grid 2 columnas */}
      <div className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <InfoItem icon={IdCard} label="CIP" value={perfil.cip} />
          <InfoItem icon={User} label="DNI" value={perfil.dni} />
          <InfoItem
            icon={ShieldCheck}
            label="Tipo"
            value={formatTipoLiquidacion(item.tipo_liquidacion)}
          />
          <InfoItem
            icon={BadgeCheck}
            label="Registro"
            value={item.numero_registro}
          />
        </div>

        {correo && (
          <div className="mt-4 pt-3 border-t border-border/50 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Mail className="h-3.5 w-3.5 text-primary/60" />
            <span className="truncate">{correo}</span>
          </div>
        )}
      </div>
    </div>
  );
}
