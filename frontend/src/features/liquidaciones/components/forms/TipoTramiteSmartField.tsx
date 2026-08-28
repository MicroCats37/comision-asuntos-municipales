"use client";

import { Check, ChevronDown, FileText } from "lucide-react";
import { type UseFormReturn, useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import type { TipoTramiteEdificaciones } from "../../schemas/tramite.schema";

/** Labels for the 8 tipo_tramite options (Title Case matching backend display) */
const TIPO_TRAMITE_LABELS: Record<TipoTramiteEdificaciones, string> = {
  OBRA_NUEVA: "Obra Nueva",
  DEMOLICION: "Demolición",
  AMPLIACION: "Ampliación",
  REMODELACION: "Remodelación",
  MODIFICACION_LICENCIA: "Modificación de Licencia",
  REINTEGRO: "Reintegro",
  VARIACION_PROYECTO_APROBADO: "Variación de Proyecto Aprobado",
  PROYECTO_CON_PLANTAS_TIPICAS: "Proyecto con Plantas Típicas",
};

/** Grupo A — TODAS las especialidades se aplican (rígido). */
const GRUPO_TODAS: TipoTramiteEdificaciones[] = [
  "OBRA_NUEVA",
  "DEMOLICION",
  "REINTEGRO",
  "AMPLIACION",
  "REMODELACION",
  "PROYECTO_CON_PLANTAS_TIPICAS",
];

/** Grupo B — especialidades particulares (checkbox de 1 a 3). */
const GRUPO_PARTICULARES: TipoTramiteEdificaciones[] = [
  "MODIFICACION_LICENCIA",
  "VARIACION_PROYECTO_APROBADO",
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TipoTramiteSmartFieldProps {
  methods: UseFormReturn<any>;
}

/**
 * TipoTramiteSmartField — Smart Field del tipo de trámite de Edificaciones.
 *
 * Desplegable con DropdownMenu que separa en dos grupos:
 * - "Todas las Especialidades" (obra nueva, demolición, reintegro, etc.)
 * - "Especialidades Particulares" (modificación de licencia, variación de proyecto)
 *
 * Reactivo vía `useWatch`: cualquier cambio se refleja al instante en
 * EspecialidadesPorTipoTramiteSmartField (que también hace watch del mismo campo).
 */
export function TipoTramiteSmartField({ methods }: TipoTramiteSmartFieldProps) {
  const tipoTramite = useWatch({
    control: methods.control,
    name: "tipo_tramite",
  }) as TipoTramiteEdificaciones | undefined;

  const handleSelect = (value: TipoTramiteEdificaciones) => {
    methods.setValue("tipo_tramite", value, { shouldValidate: true });
  };

  const renderItem = (value: TipoTramiteEdificaciones) => {
    const isSelected = tipoTramite === value;
    return (
      <DropdownMenuItem
        key={value}
        onSelect={() => handleSelect(value)}
        className={isSelected ? "bg-accent/50 font-semibold" : undefined}
      >
        {TIPO_TRAMITE_LABELS[value]}
        {isSelected && <Check className="ml-auto size-4 text-primary" />}
      </DropdownMenuItem>
    );
  };

  return (
    <div className="space-y-2">
      <Label htmlFor="tipo_tramite">
        Tipo de Trámite <span className="text-destructive">*</span>
      </Label>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            id="tipo_tramite"
            type="button"
            variant="outline"
            className="w-full justify-between gap-2 font-normal"
          >
            <span className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              {tipoTramite
                ? TIPO_TRAMITE_LABELS[tipoTramite]
                : "Seleccione tipo de trámite"}
            </span>
            <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-[var(--radix-dropdown-menu-trigger-width)]">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Todas las Especialidades</DropdownMenuLabel>
            {GRUPO_TODAS.map(renderItem)}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuLabel>Especialidades Particulares</DropdownMenuLabel>
            {GRUPO_PARTICULARES.map(renderItem)}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
