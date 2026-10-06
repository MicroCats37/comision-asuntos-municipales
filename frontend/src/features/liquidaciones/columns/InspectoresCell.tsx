"use client";

import { ChevronDown, UserCog } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface InspectorLike {
  perfil_ingeniero?: {
    id?: string;
    cip?: string;
    dni?: string | null;
    nombres?: string;
    apellido_paterno?: string;
    apellido_materno?: string;
    nombre_completo?: string;
  };
  categoria?: string | null;
  numero_registro?: string | null;
  dictamen_revision?: string | null;
}

interface Props {
  inspectores?: InspectorLike[] | null;
}

/**
 * Inspectores section cell — each inspector renders as a clickable
 * card showing: nombre + TITULAR/ALTERNO badge + dictamen inline.
 * Hover reveals full inspector info (CIP / DNI / registro).
 */
export function InspectoresCell({ inspectores }: Props) {
  const list = inspectores ?? [];
  if (list.length === 0) return null;

  return (
    <div
      className="flex flex-col justify-center 
    gap-1 px-3 py-3.5 min-w-0 text-center"
    >
      <div className="flex flex-col gap-1 min-w-0">
        {list.map((ins, i) => {
          const nombre = ins.perfil_ingeniero?.nombre_completo ?? "Sin nombre";
          const categoria = ins.categoria;
          const cip = ins.perfil_ingeniero?.cip;
          const dni = ins.perfil_ingeniero?.dni;
          const registro = ins.numero_registro;
          const dictamen = ins.dictamen_revision;

          return (
            <Tooltip key={nombre + i}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="flex flex-col items-center gap-0.5 rounded-md bg-secondary/40 border border-secondary/50 px-2 py-1 min-w-0 w-full hover:bg-secondary/60 transition-colors text-left"
                >
                  <div className="flex items-center gap-1 min-w-0 w-full justify-center">
                    <UserCog className="h-3 w-3 shrink-0 text-muted-foreground/60" />
                    <span className="text-xs font-semibold text-foreground truncate max-w-full">
                      {nombre}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-1.5 min-w-0 w-full justify-center">
                    {categoria ? (
                      <span
                        className={
                          "inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider " +
                          (categoria === "TITULAR"
                            ? "bg-primary/10 text-primary"
                            : "bg-secondary text-secondary-foreground/80")
                        }
                      >
                        {categoria}
                      </span>
                    ) : null}
                    {dictamen ? (
                      <span className="text-[10px] text-muted-foreground/70 italic truncate">
                        Dict. {dictamen}
                      </span>
                    ) : null}
                  </div>
                </button>
              </TooltipTrigger>
              <TooltipContent
                side="right"
                sideOffset={6}
                className="max-w-xs p-0 overflow-hidden"
              >
                <div className="bg-popover text-popover-foreground rounded-md border shadow-md">
                  <div className="px-3 py-2 border-b bg-muted/40 text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between gap-2">
                    <span>{nombre}</span>
                    {categoria ? (
                      <span
                        className={
                          "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] " +
                          (categoria === "TITULAR"
                            ? "bg-primary/10 text-primary"
                            : "bg-secondary text-secondary-foreground/80")
                        }
                      >
                        {categoria}
                      </span>
                    ) : null}
                  </div>
                  <div className="divide-y divide-border/40 text-[11px]">
                    {cip ? (
                      <div className="grid grid-cols-[auto_1fr] gap-x-3 px-3 py-1.5">
                        <span className="text-muted-foreground/70 uppercase tracking-wider text-[10px] font-semibold">
                          CIP
                        </span>
                        <span className="font-mono">{cip}</span>
                      </div>
                    ) : null}
                    {dni ? (
                      <div className="grid grid-cols-[auto_1fr] gap-x-3 px-3 py-1.5">
                        <span className="text-muted-foreground/70 uppercase tracking-wider text-[10px] font-semibold">
                          DNI
                        </span>
                        <span className="font-mono">{dni}</span>
                      </div>
                    ) : null}
                    {registro ? (
                      <div className="grid grid-cols-[auto_1fr] gap-x-3 px-3 py-1.5">
                        <span className="text-muted-foreground/70 uppercase tracking-wider text-[10px] font-semibold">
                          Reg
                        </span>
                        <span className="font-mono">{registro}</span>
                      </div>
                    ) : null}
                    {dictamen ? (
                      <div className="grid grid-cols-[auto_1fr] gap-x-3 px-3 py-1.5">
                        <span className="text-muted-foreground/70 uppercase tracking-wider text-[10px] font-semibold">
                          Dictamen
                        </span>
                        <span className="font-mono">{dictamen}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}
