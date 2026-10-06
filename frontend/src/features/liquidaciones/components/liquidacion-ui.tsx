"use client";

import {
  Building2,
  Eye,
  FileText,
  HardHat,
  Map,
  MoreHorizontal,
  Mountain,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

/**
 * Item descriptor for CardActionsMenu.
 * icon and onAction are rendered inside a DropdownMenuItem.
 */
export interface CardActionItem {
  icon?: React.ReactNode;
  label: string;
  onAction: () => void;
}

/**
 * Grouped actions dropdown using shadcn DropdownMenu.
 * Renders a trigger button "Opciones" (with MoreHorizontal icon) that opens
 * a menu listing each item. The standalone primary action (e.g. "Ver detalle")
 * is passed separately via primaryAction and rendered outside the dropdown.
 */
export function CardActionsMenu({
  items,
  primaryAction,
}: {
  items: CardActionItem[];
  primaryAction?: React.ReactNode;
}) {
  const activeItems = items;
  if (activeItems.length === 0 && !primaryAction) return null;

  return (
    <div className="flex items-center gap-1.5">
      {activeItems.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="default"
              className="gap-1.5 h-8 px-3"
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
              <span>Opciones</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {activeItems.map((item, idx) => (
              <DropdownMenuItem
                key={idx}
                onSelect={(e) => {
                  e.preventDefault();
                  item.onAction();
                }}
              >
                {item.icon && (
                  <span className="mr-1.5 flex items-center">{item.icon}</span>
                )}
                <span>{item.label}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
      {primaryAction}
    </div>
  );
}

export const formatCurrency = (value: number | null | undefined): string =>
  value == null
    ? "—"
    : `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const formatDate = (isoString: string): string => {
  if (!isoString) return "—";
  try {
    return new Date(isoString).toLocaleDateString("es-PE", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
};

export const getEstadoBadgeClass = (estado: string): string => {
  switch (estado) {
    case "PAGADO":
      return "bg-success/10 text-success border-success/20";
    case "PENDIENTE":
      return "bg-warning/10 text-warning border-warning/20";
    case "ANULADO":
      return "bg-destructive/10 text-destructive border-destructive/20";
    default:
      return "bg-muted text-muted-foreground border-border";
  }
};

export const formatEnumLabel = (value: string | null | undefined): string => {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

export function SectionCard({
  icon,
  title,
  children,
  className,
}: {
  icon: React.ReactNode;
  title: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-card shadow-sm overflow-hidden",
        className,
      )}
    >
      <div className="flex items-center gap-2 px-4 py-2.5 border-b bg-muted/30">
        <span className="text-muted-foreground/70">{icon}</span>
        <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
          {title}
        </h4>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

export function LabelValue({
  label,
  value,
  className,
  valueClassName,
}: {
  label: string;
  value: React.ReactNode;
  className?: string;
  valueClassName?: string;
}) {
  return (
    <div className={cn("flex flex-col", className)}>
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
        {label}
      </span>
      <span
        className={cn("text-sm font-medium text-foreground", valueClassName)}
      >
        {value}
      </span>
    </div>
  );
}

/**
 * Quiet corroboration card showing already-calculated Subtotal and Total.
 * Rendered in edit modals via LiquidacionFormBodyBase.valoresActualesSection
 * so the user sees the current calculated amounts while editing.
 */
export function ValoresActualesCard({
  subTotal,
  total,
  title,
}: {
  subTotal: number;
  total: number;
  /** Optional title shown above the values. Default no title. */
  title?: string;
}) {
  return (
    <div className="rounded-lg border border-border/50 bg-card p-3 space-y-1">
      {title && (
        <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
          {title}
        </p>
      )}
      <LabelValue
        label="Subtotal"
        value={formatCurrency(subTotal)}
        valueClassName="text-xs"
      />
      <LabelValue
        label="Total"
        value={formatCurrency(total)}
        valueClassName="text-sm font-bold text-primary"
      />
    </div>
  );
}

/**
 * Action button shared by liquidacion list cards.
 * Renders a span[role=button] with keyboard support (Enter/Space).
 * variant "primary" highlights the button (used for "Ver detalle").
 */
export function LiquidacionCardAction({
  icon,
  label,
  onAction,
  variant = "default",
  className,
}: {
  icon?: React.ReactNode;
  label: React.ReactNode;
  onAction: () => void;
  variant?: "default" | "primary";
  className?: string;
}) {
  return (
    <span
      role="button"
      tabIndex={0}
      onClick={(e) => {
        e.stopPropagation();
        onAction();
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.stopPropagation();
          onAction();
        }
      }}
      className={cn(
        "inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold cursor-pointer select-none transition-colors",
        variant === "primary"
          ? "border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50"
          : "border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary",
        className,
      )}
    >
      {icon}
      {label}
    </span>
  );
}

/** Maps tipo_liquidacion.codigo to a human-readable badge label */
export function getKindBadgeFromCodigo(
  codigo: string | null | undefined,
): string {
  switch (codigo) {
    case "EDIFICACION":
      return "Edificación";
    case "HABILITACION_URBANA":
      return "Habilitación Urbana";
    case "MECANICA_SUELOS":
      return "Mecánica de Suelos";
    case "IMPACTO_VIAL":
      return "Impacto Vial";
    case "TALUDES":
      return "Taludes";
    case "INSPECCION_OBRA":
      return "Inspección de Obra";
    default:
      return codigo ?? "—";
  }
}

/** Maps tipo_liquidacion.codigo to a Lucide icon */
export function getKindIconFromCodigo(
  codigo: string | null | undefined,
): LucideIcon {
  switch (codigo) {
    case "EDIFICACION":
      return Building2;
    case "HABILITACION_URBANA":
      return Map;
    case "MECANICA_SUELOS":
      return Mountain;
    case "IMPACTO_VIAL":
      return Eye;
    case "TALUDES":
      return Mountain;
    case "INSPECCION_OBRA":
      return HardHat;
    default:
      return FileText;
  }
}
