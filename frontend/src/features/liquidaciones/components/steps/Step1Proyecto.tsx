"use client";

import { Building2, FileText, Loader2, MapPin, Search } from "lucide-react";
import { useEffect } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import { notify } from "@/errors";
import { useProyectoBuscar } from "../../hooks/useProyecto";
import { normalizeProyectoResponse } from "../../services/proyecto.service";
import type { CachedProyecto, LiquidacionStepperStore } from "../../store";
import { EntidadLookupField } from "../EntidadLookupField";

interface Step1ProyectoProps {
  methods: UseFormReturn<FieldValues>;
  isActive: boolean;
  store: LiquidacionStepperStore;
}

export function Step1Proyecto({
  methods,
  isActive,
  store,
}: Step1ProyectoProps) {
  const {
    selectedProyecto,
    setSelectedProyecto,
    proyectoInline,
    setProyectoInline,
  } = store;

  const buscarMutation = useProyectoBuscar();

  // Smart watch: usar el valor real de RHF en vez de estado local duplicado
  const watchedProyectoPublicId = useWatch({
    control: methods.control,
    name: "proyecto_public_id",
  });

  const watchedEntidadTipoDocumento = useWatch({
    control: methods.control,
    name: "entidad_tipo_documento",
  });
  const watchedEntidadNumeroDocumento = useWatch({
    control: methods.control,
    name: "entidad_numero_documento",
  });
  const watchedEntidadRazonSocial = useWatch({
    control: methods.control,
    name: "entidad_razon_social",
  });

  // Sync watched entidad fields to store
  useEffect(() => {
    if (!isActive) return;
    if (store.selectedProyecto) return;

    if (
      watchedEntidadTipoDocumento ||
      watchedEntidadNumeroDocumento ||
      watchedEntidadRazonSocial
    ) {
      const existing = store.proyectoInline;
      const denominacion =
        methods.getValues("denominacion") || existing?.denominacion || "";
      const direccion =
        methods.getValues("direccion") || existing?.direccion || "";
      const nombrePropietario =
        methods.getValues("nombre_propietario") ||
        existing?.nombre_propietario ||
        "";

      setProyectoInline({
        denominacion,
        direccion,
        nombre_propietario: nombrePropietario,
        entidad: {
          tipo_documento:
            (watchedEntidadTipoDocumento as string) ||
            existing?.entidad?.tipo_documento ||
            "RUC",
          numero_documento:
            (watchedEntidadNumeroDocumento as string) ||
            existing?.entidad?.numero_documento ||
            "",
          razon_social:
            (watchedEntidadRazonSocial as string) ||
            existing?.entidad?.razon_social ||
            "",
        },
      });
    }
  }, [
    watchedEntidadTipoDocumento,
    watchedEntidadNumeroDocumento,
    watchedEntidadRazonSocial,
    isActive,
    methods,
    setProyectoInline,
  ]);

  // Sync proyecto_public_id into RHF when selecting an existing proyecto
  useEffect(() => {
    if (selectedProyecto?.public_id) {
      methods.setValue("proyecto_public_id", selectedProyecto.public_id, {
        shouldValidate: true,
        shouldDirty: true,
      });
    }
  }, [selectedProyecto?.public_id, methods]);

  // Sync proyectoInline from store back to RHF when re-entering the step
  useEffect(() => {
    if (!isActive || selectedProyecto || !proyectoInline) return;

    methods.setValue("denominacion", proyectoInline.denominacion || "", {
      shouldValidate: false,
      shouldDirty: true,
    });
    methods.setValue("direccion", proyectoInline.direccion || "", {
      shouldValidate: false,
      shouldDirty: true,
    });
    methods.setValue(
      "nombre_propietario",
      proyectoInline.nombre_propietario || "",
      {
        shouldValidate: false,
        shouldDirty: true,
      },
    );
    methods.setValue(
      "entidad_tipo_documento",
      proyectoInline.entidad?.tipo_documento || "RUC",
      {
        shouldValidate: false,
        shouldDirty: true,
      },
    );
    methods.setValue(
      "entidad_numero_documento",
      proyectoInline.entidad?.numero_documento || "",
      {
        shouldValidate: false,
        shouldDirty: true,
      },
    );
    methods.setValue(
      "entidad_razon_social",
      proyectoInline.entidad?.razon_social || "",
      {
        shouldValidate: false,
        shouldDirty: true,
      },
    );
    methods.setValue("proyecto_public_id", "", { shouldValidate: false });
  }, [isActive, selectedProyecto, proyectoInline, methods]);

  // Project search
  const handleSearch = async () => {
    const query = (watchedProyectoPublicId as string)?.trim();
    if (!query) {
      notify.error("Ingresa un ID de proyecto para buscar");
      return;
    }
    try {
      const result = await buscarMutation.mutateAsync(query);
      const data = normalizeProyectoResponse(result);
      if (data?.public_id) {
        const proyecto: CachedProyecto = {
          id: data.id,
          public_id: data.public_id,
          denominacion: data.denominacion,
          direccion: data.direccion || "",
          distrito: data.distrito,
          entidad: data.entidad,
        };
        setProyectoInline(null);
        setSelectedProyecto(proyecto);
        notify.success(`Proyecto "${data.denominacion}" seleccionado`);
      } else {
        notify.error("No se encontró un proyecto con ese ID");
      }
    } catch {
      notify.error("Error al buscar el proyecto");
    }
  };

  // Clear project selection
  const handleClearProyecto = () => {
    setSelectedProyecto(null);
    setProyectoInline(null);
    methods.setValue("proyecto_public_id", "", { shouldValidate: false });
  };

  // Handle field changes → sync to store + RHF
  const handleFieldChange = (field: string, value: string) => {
    methods.setValue(field as keyof FieldValues, value, {
      shouldValidate: false,
      shouldDirty: true,
    });

    const current = store.proyectoInline ?? {
      denominacion: "",
      direccion: "",
      nombre_propietario: "",
      entidad: {
        tipo_documento: "RUC",
        numero_documento: "",
        razon_social: "",
      },
    };

    if (field === "denominacion") {
      setProyectoInline({ ...current, denominacion: value });
      setSelectedProyecto(null);
    } else if (field === "direccion") {
      setProyectoInline({ ...current, direccion: value });
    } else if (field === "nombre_propietario") {
      setProyectoInline({ ...current, nombre_propietario: value });
    } else if (field === "entidad_tipo_documento") {
      setProyectoInline({
        ...current,
        entidad: { ...current.entidad, tipo_documento: value },
      });
    } else if (field === "entidad_numero_documento") {
      setProyectoInline({
        ...current,
        entidad: { ...current.entidad, numero_documento: value },
      });
    } else if (field === "entidad_razon_social") {
      setProyectoInline({
        ...current,
        entidad: { ...current.entidad, razon_social: value },
      });
    }
  };

  if (!isActive) return null;

  // Show selected project card
  if (selectedProyecto) {
    return (
      <div className="space-y-4 min-w-0 max-w-full">
        <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-3 min-w-0 overflow-hidden">
          <FormSectionHeader
            title="Proyecto Seleccionado"
            icon={Building2}
            variant="soft"
          />

          <div className="space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-semibold text-foreground truncate">
                  {selectedProyecto.denominacion}
                </p>
                <p className="text-sm text-muted-foreground">
                  {selectedProyecto.public_id}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleClearProyecto}
                className="rounded-lg gap-1.5 shrink-0"
              >
                Cambiar
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              {selectedProyecto.direccion || "Sin dirección"}
              {selectedProyecto.distrito && ` - ${selectedProyecto.distrito}`}
            </p>
            {selectedProyecto.entidad && (
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-sm">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  <span>{selectedProyecto.entidad.nombre}</span>
                  {selectedProyecto.entidad.tipo && (
                    <span className="text-xs text-muted-foreground">
                      ({selectedProyecto.entidad.tipo})
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Main form: search + inline proyecto
  return (
    <div className="space-y-4 min-w-0 max-w-full">
      {/* Buscar Proyecto Existente */}
      <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden">
        <FormSectionHeader
          title="Buscar Proyecto Existente"
          icon={Search}
          variant="soft"
        />

        <GenericInput
          field={{
            name: "proyecto_public_id",
            label: "ID del Proyecto",
            type: "text",
            placeholder: "Ej: PROY-2026-00001",
            icon: FileText,
            labelClassName: "text-primary font-semibold",
          }}
          register={methods.register as never}
          control={methods.control as never}
          errors={methods.formState.errors}
        />

        <Button
          type="button"
          size="default"
          onClick={handleSearch}
          disabled={
            buscarMutation.isPending ||
            !(watchedProyectoPublicId as string)?.trim()
          }
          className="w-full h-10 rounded-xl gap-2"
        >
          {buscarMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          Buscar Proyecto
        </Button>
      </div>

      {/* Nuevo Proyecto */}
      <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden">
        <FormSectionHeader
          title="Datos del Proyecto"
          icon={Building2}
          variant="soft"
        />

        <GenericInput
          field={{
            name: "denominacion",
            label: "Denominación",
            type: "text",
            required: true,
            placeholder: "Nombre del proyecto",
            icon: Building2,
            labelClassName: "text-primary font-semibold",
          }}
          register={methods.register as never}
          control={methods.control as never}
          errors={methods.formState.errors}
        />

        <GenericInput
          field={{
            name: "direccion",
            label: "Dirección",
            type: "text",
            placeholder: "Dirección del proyecto",
            icon: MapPin,
            labelClassName: "text-primary font-semibold",
          }}
          register={methods.register as never}
          control={methods.control as never}
          errors={methods.formState.errors}
        />

        <EntidadLookupField
          control={methods.control as never}
          errors={methods.formState.errors as never}
          onFieldChange={handleFieldChange}
        />

        <GenericInput
          field={{
            name: "nombre_propietario",
            label: "Nombre del Propietario",
            type: "text",
            required: true,
            placeholder: "Nombre del propietario o representante legal",
            icon: Building2,
            labelClassName: "text-primary font-semibold",
          }}
          register={methods.register as never}
          control={methods.control as never}
          errors={methods.formState.errors}
        />
      </div>
    </div>
  );
}
