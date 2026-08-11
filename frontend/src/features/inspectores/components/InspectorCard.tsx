"use client";

/**
 * InspectorCard — Card para un inspector registrado.
 * Muestra CIP, DNI, nombre completo, tipo de liquidación y número de registro.
 */
import { BadgeCheck, IdCard, Mail, ShieldCheck, User } from "lucide-react";

export interface InspectorCardItem {
  id: string;
  tipo_liquidacion?: string | null;
  numero_registro?: string | null;
  telefono?: string | null;
  email?: string | null;
  perfil_ingeniero: {
    id: string;
    cip: string;
    dni: string;
    nombres?: string | null;
    apellido_paterno?: string | null;
    apellido_materno?: string | null;
    nombre_completo: string;
    correo_personal?: string | null;
    correo_institucional?: string | null;
  };
}

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

export function InspectorCard({ item }: InspectorCardProps) {
  const perfil = item.perfil_ingeniero;
  const correo = perfil.correo_personal ?? perfil.correo_institucional ?? item.email;

  return (
    <div className="rounded-2xl border bg-card shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      <div className="p-4 flex items-start gap-3">
        {/* Avatar */}
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary font-black text-lg">
          {initials(perfil.nombre_completo)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-base font-bold text-foreground tracking-tight truncate">
              {perfil.nombre_completo}
            </h3>
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-bold text-blue-600 uppercase tracking-wider">
              <ShieldCheck className="h-3 w-3" />
              Inspector
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <IdCard className="h-3.5 w-3.5 text-primary/60" />
              CIP: <span className="font-mono font-semibold text-foreground">{perfil.cip}</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <User className="h-3.5 w-3.5 text-primary/60" />
              DNI: <span className="font-mono font-semibold text-foreground">{perfil.dni}</span>
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5 text-xs text-muted-foreground">
            <span>Tipo: <span className="font-semibold text-foreground">{formatTipoLiquidacion(item.tipo_liquidacion)}</span></span>
            {item.numero_registro && (
              <span>Registro: <span className="font-mono font-semibold text-foreground">{item.numero_registro}</span></span>
            )}
          </div>

          {correo && (
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-muted-foreground">
              <Mail className="h-3.5 w-3.5 text-primary/60" />
              <span className="truncate">{correo}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
