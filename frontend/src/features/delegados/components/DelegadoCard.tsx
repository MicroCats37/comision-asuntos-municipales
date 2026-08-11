"use client";

/**
 * DelegadoCard — Card para un delegado profesional.
 * Muestra CIP, DNI, nombre completo, correo e iniciales.
 */
import { BadgeCheck, IdCard, Mail, User } from "lucide-react";

export interface DelegadoCardItem {
  id: string;
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

export function DelegadoCard({ item }: DelegadoCardProps) {
  const perfil = item.perfil_ingeniero;
  const correo = perfil.correo_personal ?? perfil.correo_institucional;

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
            <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 border border-green-500/20 px-2 py-0.5 text-[10px] font-bold text-green-600 uppercase tracking-wider">
              <BadgeCheck className="h-3 w-3" />
              Delegado
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
