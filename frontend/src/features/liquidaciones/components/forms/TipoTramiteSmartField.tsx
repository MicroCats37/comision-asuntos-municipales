"use client";

import { Check, ChevronDown, FileText } from "lucide-react";
import { useEffect } from "react";
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

interface TipoTramiteSmartFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: UseFormReturn pattern matches existing smart fields
  methods: UseFormReturn<any>;
  denominationFieldName?: string;
  /**
   * Número de revisión esperado. Cuando es > 1, el auto-fill agrega el sufijo
   * "{tipo_tramite}-{nro}{ra|da|ta|...} revisión". Cuando es 1 o undefined,
   * solo se setea el enum.
   */
  revisionNumber?: number;
}

const getRevisionOrdinal = (revisionNumber: number) => {
  const suffixByLastDigit: Record<number, string> = {
    1: "ra",
    2: "da",
    3: "ra",
    4: "ta",
    5: "ta",
    6: "ta",
    7: "ma",
    8: "va",
    9: "na",
    0: "ma",
  };

  return `${revisionNumber}${suffixByLastDigit[revisionNumber % 10]}`;
};

/**
 * Compone el denominacion de proyecto según tipo_tramite + revisionNumber.
 * - Sin revision o revision===1 → label en upper case (e.g., "OBRA NUEVA")
 * - revision>1 → label + ordinal en upper case (e.g., "OBRA NUEVA 3RA REVISIÓN")
 *
 * NO usa el enum code del tipo_tramite ni guiones — solo el label humano
 * en mayúsculas, separado por espacio.
 */
function buildDenominacion(
  tipoTramite: TipoTramiteEdificaciones,
  revisionNumber: number | undefined,
): string {
  const label = TIPO_TRAMITE_LABELS[tipoTramite].toUpperCase();
  if (revisionNumber && revisionNumber > 1) {
    return `${label} ${getRevisionOrdinal(revisionNumber).toUpperCase()} REVISIÓN`;
  }
  return label;
}

/**
 * TipoTramiteSmartField — Smart Field del tipo de trámite de Edificaciones.
 *
 * Desplegable con DropdownMenu que separa en dos grupos:
 * - "Todas las Especialidades" (obra nueva, demolición, reintegro, etc.)
 * - "Especialidades Particulares" (modificación de licencia, variación de proyecto)
 *
 * Auto-fill de denominacion: vía `useEffect` que observa `tipo_tramite` y
 * actualiza el campo denominacion con `{tipo_tramite}-{nro}{ordinal} revisión`
 * cuando hay revisionNumber > 1.
 *
 * Reactivo vía `useWatch`: cualquier cambio se refleja al instante en
 * TarifasYEspecialidadesSmartField (que también hace watch del mismo campo).
 */
export function TipoTramiteSmartField({
  methods,
  denominationFieldName = "denominacion",
  revisionNumber,
}: TipoTramiteSmartFieldProps) {
  const tipoTramite = useWatch({
    control: methods.control,
    name: "tipo_tramite",
  }) as TipoTramiteEdificaciones | undefined;

  // Auto-fill denominacion cuando cambia tipo_tramite (también en mount para
  // refrescar el valor pre-cargado de initialData).
  useEffect(() => {
    if (!tipoTramite) return;
    const denominacion = buildDenominacion(tipoTramite, revisionNumber);
    methods.setValue(denominationFieldName, denominacion, {
      shouldDirty: false,
      shouldValidate: false,
    });
  }, [tipoTramite, revisionNumber, denominationFieldName, methods]);

  const handleSelect = (value: TipoTramiteEdificaciones) => {
    // El useEffect se encarga del auto-fill; solo seteamos el tipo_tramite aquí.
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
          <div className="relative w-full">
            <FileText className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Button
              id="tipo_tramite"
              type="button"
              variant="outline"
              className="h-8 w-fit justify-between pl-10 pr-3 font-normal gap-2"
            >
              <span>
                {tipoTramite
                  ? TIPO_TRAMITE_LABELS[tipoTramite]
                  : "Seleccione tipo de trámite"}
              </span>
              <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </div>
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
