"use client";

import {
  Eye,
  FilePenLine,
  FileText,
  Link2,
  type LucideIcon,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type LiquidacionFormMode =
  | "create"
  | "edit"
  | "nueva-revision"
  | "relacionada";

interface LiquidacionFormHeaderProps {
  mode: LiquidacionFormMode;
  revisionNumber?: number;
  onVerDetalle?: () => void;
  verDetalleDisabled?: boolean;
  /** Subtotal de la liquidación previa — se muestra inline al lado del badge */
  previousSubtotal?: number;
  /** Total de la liquidación previa — se muestra inline al lado del badge */
  previousTotal?: number;
  className?: string;
}

const MODE_BADGE: Record<
  LiquidacionFormMode,
  { label: string; classes: string; icon: LucideIcon; titlePrefix: string }
> = {
  create: {
    label: "NUEVA",
    classes: "bg-primary/10 border-primary/30 text-primary",
    icon: FileText,
    titlePrefix: "Nueva Liquidación",
  },
  edit: {
    label: "EDITAR",
    classes: "bg-muted border-border text-muted-foreground",
    icon: FilePenLine,
    titlePrefix: "Editar Liquidación",
  },
  "nueva-revision": {
    label: "REVISIÓN",
    classes: "bg-warning/15 border-warning/40 text-warning",
    icon: RefreshCw,
    titlePrefix: "Nueva Revisión",
  },
  relacionada: {
    label: "RELACIONADA",
    classes:
      "bg-blue-500/15 border-blue-500/40 text-blue-700 dark:text-blue-300",
    icon: Link2,
    titlePrefix: "Liquidación Relacionada",
  },
};

const formatSolesCompact = (value: number | undefined): string =>
  value == null
    ? "—"
    : `S/ ${Number(value).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function LiquidacionFormHeader({
  mode,
  revisionNumber,
  onVerDetalle,
  verDetalleDisabled = false,
  previousSubtotal,
  previousTotal,
  className,
}: LiquidacionFormHeaderProps) {
  const config = MODE_BADGE[mode];
  const Icon = config.icon;
  const showVerDetalle =
    (mode === "nueva-revision" || mode === "relacionada") && onVerDetalle;
  const showPreviousValues =
    previousSubtotal !== undefined && previousTotal !== undefined;

  return (
    <div
      className={cn("flex items-center gap-2 flex-wrap justify-end", className)}
    >
      {/* ── Badge REVISIÓN #N ────────────────────────────────────────── */}
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wider shadow-sm",
          config.classes,
        )}
      >
        <Icon className="h-3.5 w-3.5" />
        {config.label}
        {revisionNumber != null && (
          <span className="ml-0.5 text-xs font-black opacity-90">
            #{revisionNumber}
          </span>
        )}
      </span>

      {/* ── Ver detalle button ─────────────────────────────────────── */}
      {showVerDetalle && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onVerDetalle}
          disabled={verDetalleDisabled}
          className="h-8 gap-1.5 text-xs bg-primary/50 rounded-full px-4 border-border/60 hover:border-primary/40 hover:bg-primary/5 font-semibold"
        >
          <Eye className="h-3.5 w-3.5" />
          Ver detalle de la liquidación previa
        </Button>
      )}

      {/* ── Valores previos (inline horizontal) ────────────────────── */}
      {showPreviousValues && (
        <div className="inline-flex items-center gap-3 rounded-full border border-border/50 bg-card px-3 py-1 text-xs shadow-sm">
          <span className="font-bold uppercase tracking-wider text-[10px] text-muted-foreground">
            Previa
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="text-muted-foreground text-[10px] uppercase tracking-wider">
              Sub
            </span>
            <span className="font-semibold">
              {formatSolesCompact(previousSubtotal)}
            </span>
          </span>
          <span className="h-3 w-px bg-border" />
          <span className="inline-flex items-center gap-1">
            <span className="text-muted-foreground text-[10px] uppercase tracking-wider">
              Total
            </span>
            <span className="font-bold text-primary">
              {formatSolesCompact(previousTotal)}
            </span>
          </span>
        </div>
      )}
    </div>
  );
}
