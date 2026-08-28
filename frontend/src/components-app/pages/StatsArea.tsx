"use client";

import { ShieldCheck, Users } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatsAreaProps {
  familiaresCount: number;
  conocidosCount: number;
  cupos?: { permitidos: number; activos: number };
}

// Stats card with decorative background circle and icon
function StatCard({
  children,
  className,
  bgColor = "bg-primary",
  iconBg = "bg-primary",
  iconColor = "text-primary-foreground",
  icon,
  decorativeIcon,
  isDarkBg = false,
}: {
  children: React.ReactNode;
  className?: string;
  bgColor?: string;
  iconBg?: string;
  iconColor?: string;
  icon?: React.ReactNode;
  decorativeIcon?: React.ReactNode;
  /** When true, uses white/20 border for visibility on dark backgrounds */
  isDarkBg?: boolean;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden group min-h-[160px] flex flex-col justify-center p-6 rounded-[32px] border shadow-sm",
        // Card 1 (bg-card white): use full opacity border for proper card definition
        // Cards 2 and 3 (solid dark backgrounds): use white/20 border for visibility on dark bg
        isDarkBg ? "border-white/20" : "border-border",
        className,
      )}
    >
      {/* Decorative background circle - top right */}
      <div
        className={cn(
          "absolute top-0 right-0 w-48 h-48 rounded-full -mr-24 -mt-24 transition-transform duration-1000 group-hover:scale-110",
          bgColor,
          "opacity-20",
        )}
      />

      {/* Decorative background icon - bottom right */}
      {decorativeIcon && (
        <div className="absolute -bottom-6 -right-6 opacity-10 transition-transform duration-700 group-hover:scale-110">
          {decorativeIcon}
        </div>
      )}

      {/* Content */}
      <div className="relative z-10 flex items-start gap-5">
        {icon && (
          <div
            className={cn(
              "h-12 w-12 rounded-2xl flex items-center justify-center shadow-lg shrink-0",
              iconBg,
              iconColor,
            )}
          >
            {icon}
          </div>
        )}
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}

export function StatsArea({
  familiaresCount,
  conocidosCount,
  cupos,
}: StatsAreaProps) {
  const cuposUsados = cupos?.activos ?? 0;
  const cuposTotales = cupos?.permitidos ?? 0;
  const cuposDisponibles = Math.max(0, cuposTotales - cuposUsados);
  const cuposPorcentaje =
    cuposTotales > 0 ? (cuposUsados / cuposTotales) * 100 : 0;
  const beneficiariosActivos = cupos?.activos ?? 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
      {/* Main stat card - Gestión de Beneficiarios */}
      <StatCard
        className="lg:col-span-6 bg-card"
        bgColor="bg-emerald-100"
        iconBg="bg-emerald-500"
        iconColor="text-white"
        icon={<ShieldCheck className="h-6 w-6" />}
        decorativeIcon={
          <ShieldCheck className="h-20 w-20 text-secondary-foreground" />
        }
      >
        <div>
          <h3 className="text-lg font-black text-foreground mb-1 tracking-tight">
            Gestión de Beneficiarios
          </h3>
          <p className="text-xs text-muted-foreground font-medium leading-relaxed max-w-sm">
            Tus familiares nucleares pueden disfrutar de{" "}
            <span className="text-secondary-foreground font-bold uppercase tracking-tighter text-[10px]">
              ingreso libre (S/ 0.00)
            </span>{" "}
            en todas nuestras sedes.
          </p>
        </div>
      </StatCard>

      {/* Beneficiarios stat */}
      <StatCard
        className="lg:col-span-3 bg-blue-600"
        bgColor="bg-blue-600"
        iconBg="bg-white/20"
        iconColor="text-white"
        isDarkBg
        decorativeIcon={<Users className="h-20 w-20 text-white" />}
      >
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1 w-4 bg-white/30 rounded-full" />
            <span className="text-[9px] font-black uppercase tracking-[0.15em] text-white/70">
              Beneficiarios
            </span>
          </div>
          <h2 className="text-4xl font-black tracking-tighter text-white">
            {beneficiariosActivos}
            <span className="text-lg font-normal text-white/60">
              {" "}
              de {cuposTotales}
            </span>
          </h2>
          <p className="text-white/50 font-medium text-[10px] uppercase tracking-wider mt-1">
            Cupos Totales
          </p>
        </div>
      </StatCard>

      {/* Pases Libres stat */}
      <StatCard
        className="lg:col-span-3 bg-primary"
        bgColor="bg-primary"
        iconBg="bg-white/20"
        iconColor="text-white"
        isDarkBg
        decorativeIcon={<ShieldCheck className="h-20 w-20 text-white" />}
      >
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1 w-4 bg-emerald-400/50 rounded-full animate-pulse" />
            <span className="text-[9px] font-black uppercase tracking-[0.15em] text-emerald-300">
              Pases Libres
            </span>
          </div>
          <h2 className="text-4xl font-black tracking-tighter text-white">
            {cuposDisponibles}
          </h2>
          <p className="text-white/50 font-medium text-[10px] uppercase tracking-wider mt-1">
            Disponibles este mes
          </p>
        </div>
      </StatCard>
    </div>
  );
}
