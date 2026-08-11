"use client";

import {
  Award,
  CheckCircle2,
  Loader2,
  Search,
  User,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useIngenieroHabilitado } from "../hooks/useIngenieroHabilitado";
import type { ProyectistaFormModalProps } from "../types/liquidacion-edificaciones-form.types";
import type { ProyectistaInline } from "../types/proyectista";

const proyectistaSchema = z.object({
  cip: z.string().regex(/^\d{3,6}$/, "El CIP debe tener entre 3 y 6 dígitos"),
  especialidad_id: z.string().uuid("Debe seleccionar una especialidad"),
  descripcion: z.string().optional(),
});

type ProyectistaFormData = z.infer<typeof proyectistaSchema>;

export function ProyectistaFormModal({
  open,
  onOpenChange,
  onSaved,
  especialidadOptions = [],
}: ProyectistaFormModalProps) {
  // ── CIP search state (separate from form's hidden cip field) ─────────────
  // cipSearchValue: raw input as user types (can be >= 6 digits during input)
  const [cipSearchValue, setCipSearchValue] = useState("");
  // cipToQuery: CIP passed to the hook — only set when user clicks "Buscar"
  const [cipToQuery, setCipToQuery] = useState<string | null>(null);

  // Ref to hold RHF methods — populated in children render, used in useEffect
  const methodsRef = useRef<UseFormReturn<ProyectistaFormData> | null>(null);

  // Minimum 3 digits, maximum 6 digits required before enabling the Buscar button
  const digits = cipSearchValue.replace(/\D/g, "");
  const canSearch = digits.length >= 3 && digits.length <= 6;

  // Query ingeniero habilitado when cipToQuery is set (triggered by Buscar)
  const {
    data: ingeniero,
    isFetching,
    isFetched,
    error,
  } = useIngenieroHabilitado(cipToQuery);

  // After query completes, determine the validation outcome
  const queryDone = isFetched && !isFetching;
  const ingenieroFound = queryDone && !error && ingeniero != null;
  const ingenieroNotFound = queryDone && (!ingeniero || error);
  const isHabilitado = ingenieroFound && ingeniero.habilitado;

  // ── Sync found CIP to RHF form so Zod validation passes on submit ──
  useEffect(() => {
    if (!methodsRef.current) return;
    if (ingenieroFound && ingeniero?.cip) {
      methodsRef.current.setValue("cip", ingeniero.cip, {
        shouldValidate: true,
      });
    }
  }, [ingenieroFound, ingeniero?.cip]);

  const handleBuscar = useCallback(() => {
    if (!canSearch || isFetching) return;
    const digitsOnly = cipSearchValue.replace(/\D/g, "");
    setCipToQuery(digitsOnly);
  }, [canSearch, isFetching, cipSearchValue]);

  const handleReset = () => {
    setCipSearchValue("");
    setCipToQuery(null);
  };

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      handleReset();
    }
    onOpenChange(nextOpen);
  };

  const handleSubmit = async (data: ProyectistaFormData) => {
    if (!isFetched || isFetching) {
      notify.error("Primero debe buscar y validar el CIP");
      throw new Error("CIP search is still pending");
    }

    if (!ingenieroFound) {
      notify.error("No se encontró ingeniero con este CIP");
      throw new Error("CIP not found");
    }

    if (!isHabilitado) {
      notify.error("El ingeniero no está habilitado");
      throw new Error("Engineer is not habilitado");
    }

    const proyectistaInline: ProyectistaInline = {
      cip: ingeniero.cip,
      especialidad_id: data.especialidad_id,
      descripcion: data.descripcion || undefined,
      // Display fields
      nombres: ingeniero.nombres,
      apellidos: ingeniero.apellidos,
      habilitado: ingeniero.habilitado,
      capitulo: ingeniero.capitulo,
    };

    notify.success("Proyectista agregado correctamente");
    handleReset();
    onSaved(proyectistaInline);
  };

  return (
    <AppFormModal<ProyectistaFormData>
      open={open}
      onOpenChange={handleClose}
      title="Agregar Proyectista"
      description="Busca un ingeniero habilitado por su CIP"
      eyebrow="Proyecto"
      icon={<User className="h-5 w-5 text-primary" />}
      primaryLabel="Agregar"
      primaryLoadingLabel="Agregando..."
      primaryLoading={false}
      primaryDisabled={!isHabilitado}
      onPrimary={() => undefined}
      schema={proyectistaSchema}
      initialData={{ cip: "", especialidad_id: "", descripcion: "" }}
      onSubmit={handleSubmit}
      onFieldChange={() => {}}
      size="md"
    >
      {({ methods }) => {
        // Keep ref in sync with the form methods
        methodsRef.current = methods;
        return (
          <div className="space-y-4">
            {/* CIP Validation Section */}
            <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
              <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                <Award className="h-4 w-4" />
                <h3 className="text-sm font-semibold uppercase tracking-wide">
                  Validación CIP
                </h3>
              </div>

              {/* CIP Search Input + Buscar Button (like Proyecto search) */}
              <div className="flex gap-2">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Ej: 163222"
                    className="flex h-11 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    value={cipSearchValue}
                    onChange={(e) => setCipSearchValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleBuscar();
                      }
                    }}
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    type="button"
                    variant="default"
                    size="default"
                    className="h-11 rounded-xl gap-2"
                    onClick={handleBuscar}
                    disabled={!canSearch || isFetching}
                  >
                    {isFetching ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    Buscar
                  </Button>
                </div>
              </div>

              {/* Idle state — before any search */}
              {!cipToQuery && !isFetching && (
                <p className="text-sm text-muted-foreground">
                  Ingrese el CIP y presione Buscar para validar
                </p>
              )}

              {/* Loading State */}
              {isFetching && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Buscando CIP...
                </div>
              )}

              {/* Error / Not Found State */}
              {ingenieroNotFound && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                  <XCircle className="h-4 w-4 text-destructive" />
                  <span className="text-sm text-destructive">
                    No se encontró ingeniero con este CIP
                  </span>
                </div>
              )}

              {/* Success State - Engineer Info */}
              {ingenieroFound && (
                <div className="space-y-3">
                  {isHabilitado ? (
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <span className="text-sm font-medium text-green-700">
                        Ingeniero habilitado
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                      <XCircle className="h-4 w-4 text-destructive" />
                      <span className="text-sm text-destructive">
                        Ingeniero NO habilitado
                      </span>
                    </div>
                  )}

                  {/* Engineer Details */}
                  <div className="grid grid-cols-2 gap-4 p-3 rounded-lg bg-muted/50">
                    <div>
                      <p className="text-xs text-muted-foreground">Nombres</p>
                      <p className="text-sm font-medium">{ingeniero.nombres}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Apellidos</p>
                      <p className="text-sm font-medium">
                        {ingeniero.apellidos}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">CIP</p>
                      <p className="text-sm font-medium">{ingeniero.cip}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Capítulo</p>
                      <p className="text-sm font-medium">
                        {ingeniero.capitulo || "N/A"}
                      </p>
                    </div>
                  </div>

                  {/* Disabled if not habilitado */}
                  {!isHabilitado && (
                    <p className="text-sm text-destructive">
                      No se puede agregar un ingeniero que no esté habilitado.
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Especialidad Selection — only shown when ingeniero is found and habilitado */}
            {ingenieroFound && isHabilitado && (
              <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
                <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
                  <Award className="h-4 w-4" />
                  <h3 className="text-sm font-semibold uppercase tracking-wide">
                    Especialidad
                  </h3>
                </div>

                <GenericInput
                  field={{
                    name: "especialidad_id",
                    label: "Especialidad",
                    type: "searchable-select",
                    required: true,
                    placeholder: "Seleccione especialidad",
                    options: especialidadOptions,
                    icon: Award,
                    labelClassName: "text-primary font-semibold",
                  }}
                  register={methods.register as any}
                  control={methods.control as any}
                  errors={methods.formState.errors as any}
                />

                <GenericInput
                  field={{
                    name: "descripcion",
                    label: "Descripción (opcional)",
                    type: "textarea",
                    placeholder: "Descripción o nota adicional...",
                    icon: Award,
                    labelClassName: "text-primary font-semibold",
                  }}
                  register={methods.register as any}
                  control={methods.control as any}
                  errors={methods.formState.errors as any}
                />
              </div>
            )}
          </div>
        );
      }}
    </AppFormModal>
  );
}
