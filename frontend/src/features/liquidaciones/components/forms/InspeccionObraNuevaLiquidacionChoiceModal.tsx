"use client";

import { ArrowRight, Building2, ClipboardCheck, Plus } from "lucide-react";
/**
 * InspeccionObraNuevaLiquidacionChoiceModal — Modal de elección inicial.
 *
 * Punto único de entrada para crear una liquidación de Inspección de Obra.
 * Pregunta si la liquidación tiene una previa (Edificación o Habilitación
 * Urbana) y, según la respuesta, abre el modal unificado en el mode correspondiente:
 *
 *  - "Sin previa" → LiquidacionInspeccionObraFormModal mode='create'
 *  - "Con previa" → SeleccionarPreviaModal → LiquidacionInspeccionObraFormModal
 *                                mode='relacionada'
 *
 * Mantiene el patrón consistente con el resto de la app: 1 botón "Nueva
 * Liquidación" en la vista → este modal → flujo interno.
 */
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ChoiceKind = "con-previa" | "sin-previa";

interface InspeccionObraNuevaLiquidacionChoiceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChoose: (kind: ChoiceKind) => void;
}

interface ChoiceCardProps {
  icon: typeof Building2;
  title: string;
  description: string;
  badge?: string;
  onClick: () => void;
}

function ChoiceCard({
  icon: Icon,
  title,
  description,
  badge,
  onClick,
}: ChoiceCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex w-full items-start gap-4 rounded-xl border border-border bg-card p-5 text-left",
        "transition-all duration-200 hover:border-primary/60 hover:bg-primary/[0.02] hover:shadow-sm",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
      )}
    >
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-foreground">{title}</h3>
          {badge && (
            <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-bold text-primary">
              {badge}
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      </div>
      <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0 mt-3" />
    </button>
  );
}

export function InspeccionObraNuevaLiquidacionChoiceModal({
  open,
  onOpenChange,
  onChoose,
}: InspeccionObraNuevaLiquidacionChoiceModalProps) {
  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content className="flex flex-col max-h-[90vh]">
        <GenericModal.Header className="relative px-6 py-4 border-b border-border/60 bg-gradient-to-r from-muted/30 via-muted/10 to-transparent shrink-0">
          <div className="absolute right-4 top-4 z-10">
            <GenericModal.CloseX />
          </div>
          <div className="flex items-start gap-3 pr-12">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
              <ClipboardCheck className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-black text-foreground tracking-tight">
                Nueva Liquidación — Inspección de Obra
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Elige cómo quieres crear la liquidación
              </p>
            </div>
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="flex-1 overflow-y-auto p-6">
          <div className="space-y-3">
            <ChoiceCard
              icon={Plus}
              title="Sin previa"
              description="Crea la primera liquidación de Inspección de Obra: completa los datos del proyecto, municipalidad y entidad manualmente."
              badge="RECOMENDADO"
              onClick={() => onChoose("sin-previa")}
            />
            <ChoiceCard
              icon={Building2}
              title="Con previa"
              description="Busca una liquidación previa (Edificación o Habilitación Urbana) y crea una liquidación relacionada heredando su proyecto."
              badge="HEREDA PROYECTO"
              onClick={() => onChoose("con-previa")}
            />
          </div>
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border shrink-0">
          <div className="flex justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
          </div>
        </GenericModal.Footer>
      </GenericModal.Content>
    </GenericModal>
  );
}
