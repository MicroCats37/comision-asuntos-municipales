/**
 * LiquidacionHabilitacionUrbanaStepperModal — Componente concreto para Habilitación Urbana.
 *
 * ── Flujo de pasos ───────────────────────────────────────────────────────────
 *   1. Liquidación    → municipalidad + area_solicitada + cotización
 *   2. Proyecto       → buscar existente (XOR) o crear inline
 *   3. Personas       → proyectistas + contactos
 *   4. Confirmación   → revisión final + submit
 *
 * ── Arquitectura ─────────────────────────────────────────────────────────────
 *   AppStepperFormModal (genérico) + stepper-ui-store-factory.ts (Zustand)
 *   React Hook Form + Zod (validación por paso)
 *   Hooks HU-específicos: useCrearHabilitacionUrbanaPrimeraRevision,
 *                          useCotizarHabilitacionUrbanaPrimeraRevision
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, CheckCircle, FileText, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useForm } from "react-hook-form";
import { AppStepperFormModal } from "@/components-app/forms/AppStepperFormModal";
import { notify } from "@/errors";
import { useCrearHabilitacionUrbanaPrimeraRevision } from "../../hooks/useHabilitacionUrbana";
import { useCotizarHabilitacionUrbanaPrimeraRevision } from "../../hooks/useHabilitacionUrbana";
import { useMunicipalidades } from "../../hooks/useMunicipalidades";
import { useEspecialidadesVigentesLiquidacion } from "../../hooks/useEspecialidadesVigentesLiquidacion";
import { stepHabilitacionUrbanaSchema } from "../../schemas/liquidacion-habilitacion-urbana.schema";
import { useHabilitacionUrbanaStepperStore, type CotizacionState } from "../../store";
import type { ContactoInline } from "../../types/contacto";
import type { ProyectistaInline } from "../../types/proyectista";
import type { CotizacionHabilitacionUrbanaResponse } from "../../types/liquidacion-habilitacion-urbana.types";
import type { CrearHabilitacionUrbanaPrimeraRevisionIn } from "../../types/liquidacion-habilitacion-urbana.types";
import { ContactoFormModal } from "../ContactoFormModal";
import { ProyectistaFormModal } from "../ProyectistaFormModal";
import { Step1Proyecto } from "../steps/Step1Proyecto";
import { Step3Personas } from "../steps/Step3Personas";
import { StepHabilitacionUrbanaLiquidacion } from "../steps/StepHabilitacionUrbanaLiquidacion";
import { StepHabilitacionUrbanaConfirmacion } from "../steps/StepHabilitacionUrbanaConfirmacion";

type FormData = {
  municipalidad_id: string;
  area_solicitada: number;
  expediente?: string;
  observacion?: string;
};

const STEP_IDS = ["liquidacion", "proyecto", "personas", "confirmacion"] as const;

const KIND_LABEL = "Habilitación Urbana";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionHabilitacionUrbanaStepperModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LiquidacionHabilitacionUrbanaStepperModal({
  open,
  onOpenChange,
  onSuccess,
}: LiquidacionHabilitacionUrbanaStepperModalProps) {
  const crearMutation = useCrearHabilitacionUrbanaPrimeraRevision();
  const cotizarMutation = useCotizarHabilitacionUrbanaPrimeraRevision();
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  // ── Especialidades vigentes para el tipo de liquidación ───────────────────
  const { data: especialidadesData } = useEspecialidadesVigentesLiquidacion("habilitacion-urbana");
  const especialidadOptions: Array<{ label: string; value: string }> =
    especialidadesData?.items
      ? [
          ...new Map(
            especialidadesData.items.map((esp) => ({
              label: esp.nombre,
              value: esp.id,
            })).map((opt) => [opt.value, opt]),
          ).values(),
        ]
      : [];
  const especialidadLabels: Record<string, string> = {};
  if (especialidadesData?.items) {
    for (const esp of especialidadesData.items) {
      especialidadLabels[esp.id] = esp.nombre;
    }
  }

  const formMethods = useForm<FormData>({
    resolver: zodResolver(stepHabilitacionUrbanaSchema),
    defaultValues: {
      municipalidad_id: "" as never,
      area_solicitada: 0 as never,
      expediente: "",
      observacion: "",
    },
    mode: "onBlur",
  });

  const store = useHabilitacionUrbanaStepperStore();

  // ── Reset on close ─────────────────────────────────────────────────────────
  // Seleccionar reset como función estable para evitar loop infinito:
  // useEffect depende de store completo → identity cambia en cada render → reset → loop.
  const resetStepper = useHabilitacionUrbanaStepperStore((state) => state.reset);
  const { reset: resetForm } = formMethods;

  useEffect(() => {
    if (!open) {
      resetStepper();
      resetForm();
    }
  }, [open, resetStepper, resetForm]);

  // ── Modales hijos ────────────────────────────────────────────────────────────
  const [showProyectistaModal, setShowProyectistaModal] = useState(false);
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<number | null>(null);

  const handleProyectistaSaved = useCallback(
    (proyectista: ProyectistaInline) => {
      store.addProyectista(proyectista);
      setShowProyectistaModal(false);
    },
    [store.addProyectista],
  );

  const handleContactoSaved = useCallback(
    (contacto: ContactoInline) => {
      if (editingContactoIndex !== null) {
        store.updateContacto(editingContactoIndex, contacto);
      } else {
        store.addContacto(contacto);
      }
      setShowContactoModal(false);
      setEditingContactoIndex(null);
    },
    [editingContactoIndex, store.addContacto, store.updateContacto],
  );

  // ── Cotización desde store ───────────────────────────────────────────────────
  const cotizacionQuote: CotizacionHabilitacionUrbanaResponse | null =
    (store.cotizacion.quote as CotizacionHabilitacionUrbanaResponse | null) ?? null;

  // ── Items normalizados para confirmación ────────────────────────────────────
  const getLiquidacionItems = (data: FormData) => {
    type Item = { label: string; value: string | number; highlight?: boolean };
    const items: Item[] = [
      {
        label: "Área Solicitada",
        value: data.area_solicitada,
        highlight: true,
      },
    ];
    if (data.expediente) {
      items.push({ label: "Expediente", value: data.expediente });
    }
    if (data.observacion) {
      items.push({ label: "Observación", value: data.observacion });
    }
    return items;
  };

  // ── Step configuration ───────────────────────────────────────────────────────
  const steps: import("@/components-app/forms/AppStepperFormModal").StepConfig[] = [
    // Step 1: Liquidación
    {
      id: STEP_IDS[0],
      title: "Liquidación",
      icon: FileText,
      description: "Datos de la liquidación y cotización",
      validate: async ({ methods }: { methods: UseFormReturn<FieldValues> }) => {
        const valid = await methods.trigger(["municipalidad_id", "area_solicitada"]);
        return valid;
      },
      render: ({
        methods,
        isActive,
      }: {
        methods: UseFormReturn<FieldValues>;
        currentStep: number;
        isActive: boolean;
      }) => (
        <StepHabilitacionUrbanaLiquidacion
          methods={methods}
          isActive={isActive}
          municipalidades={municipalidades || []}
          isLoadingMunicipalidades={isLoadingMunicipalidades}
          cotizarMutation={cotizarMutation}
          quote={cotizacionQuote}
          setCotizacionQuote={(q) => store.setCotizacionQuote(q as CotizacionState["quote"])}
          setCotizacionError={store.setCotizacionError}
          setCotizacionCalculating={store.setCotizacionCalculating}
        />
      ),
    },

    // Step 2: Proyecto
    {
      id: STEP_IDS[1],
      title: "Proyecto",
      icon: Building2,
      description: "Selecciona o crea el proyecto para esta liquidación",
      validate: ({ methods: _methods }: { methods: UseFormReturn<FieldValues> }) => {
        const hasProyectoExistente = !!store.selectedProyecto;
        const hasProyectoInline = !!store.proyectoInline;
        if (!hasProyectoExistente && !hasProyectoInline) {
          notify.error("Selecciona o crea un proyecto antes de continuar");
          return false;
        }
        if (hasProyectoExistente && hasProyectoInline) {
          notify.error("No puede seleccionar y crear un proyecto al mismo tiempo");
          return false;
        }
        return true;
      },
      render: ({
        methods,
        isActive,
      }: {
        methods: UseFormReturn<FieldValues>;
        currentStep: number;
        isActive: boolean;
      }) => <Step1Proyecto methods={methods} isActive={isActive} store={store} />,
    },

    // Step 3: Personas
    {
      id: STEP_IDS[2],
      title: "Personas",
      icon: Users,
      description: "Agrega proyectistas y contactos de referencia",
      render: ({
        methods,
        isActive,
      }: {
        methods: UseFormReturn<FieldValues>;
        currentStep: number;
        isActive: boolean;
      }) => (
          <Step3Personas
          methods={methods}
          isActive={isActive}
          store={store}
          especialidadOptions={especialidadOptions}
          especialidadLabels={especialidadLabels}
          onOpenProyectistaModal={() => setShowProyectistaModal(true)}
          onRemoveProyectista={(cip) => store.removeProyectista(cip)}
          onOpenContactoModal={() => {
            setEditingContactoIndex(null);
            setShowContactoModal(true);
          }}
          onEditContacto={(index) => {
            setEditingContactoIndex(index);
            setShowContactoModal(true);
          }}
          onRemoveContacto={(index) => store.removeContacto(index)}
        />
      ),
    },

    // Step 4: Confirmación
    {
      id: STEP_IDS[3],
      title: "Confirmación",
      icon: CheckCircle,
      description: "Revisa toda la información antes de crear la liquidación",
      render: ({
        methods,
        isActive,
      }: {
        methods: UseFormReturn<FieldValues>;
        currentStep: number;
        isActive: boolean;
      }) => {
        const data = methods.getValues();
        return (
          <StepHabilitacionUrbanaConfirmacion
            methods={methods}
            isActive={isActive}
            tipoLabel={KIND_LABEL}
            liquidacionItems={getLiquidacionItems(data as FormData)}
            municipalidades={municipalidades?.map((m) => ({ id: m.id, nombre: m.nombre }))}
            quote={cotizacionQuote}
          />
        );
      },
    },
  ];

  // ── Submit ──────────────────────────────────────────────────────────────────
  const handleSubmit = useCallback(
    async (data: FormData) => {
      const { selectedProyecto, proyectoInline, selectedProyectistas: _sp, selectedContactos } = store;

      const hasProyectoExistente = !!selectedProyecto;
      const hasProyectoInline = !!proyectoInline;

      if (!hasProyectoExistente && !hasProyectoInline) {
        notify.error("Debe seleccionar o crear un proyecto");
        return;
      }

      if (hasProyectoExistente && hasProyectoInline) {
        notify.error("No puede seleccionar y crear un proyecto al mismo tiempo");
        return;
      }

      const contactosPayload = (selectedContactos as ContactoInline[]).map(({ localId: _lid, ...contacto }) => contacto);

      const submitData: CrearHabilitacionUrbanaPrimeraRevisionIn = {
        ...(hasProyectoInline
          ? {
              proyecto_inline: {
                denominacion: proyectoInline!.denominacion,
                direccion: proyectoInline!.direccion || undefined,
                distrito_id: proyectoInline!.distrito_id,
                nombre_propietario: proyectoInline!.nombre_propietario,
                entidad: proyectoInline!.entidad,
              },
            }
          : { proyecto_public_id: selectedProyecto!.public_id }),
        municipalidad_id: data.municipalidad_id,
        area_solicitada: Number(data.area_solicitada),
        expediente: data.expediente,
        observacion: data.observacion,
        tarifas_ids: store.selectedTarifasIds,
        contactos: contactosPayload,
      };

      try {
        await crearMutation.mutateAsync(submitData);
        notify.success("Liquidación creada correctamente");
        store.reset();
        formMethods.reset();
        onSuccess?.();
        onOpenChange(false);
      } catch {
        // Error ya manejado por la mutación
      }
    },
    [store, crearMutation, onSuccess, onOpenChange, formMethods],
  );

  return (
    <>
      <AppStepperFormModal
        open={open}
        onOpenChange={onOpenChange}
        title={`Nueva Liquidación ${KIND_LABEL}`}
        eyebrow="Habilitación Urbana"
        icon={<FileText className="h-5 w-5 text-primary" />}
        description={`Registra una nueva liquidación de ${KIND_LABEL.toLowerCase()}`}
        steps={steps}
        schema={stepHabilitacionUrbanaSchema}
        formMethods={formMethods}
        onSubmit={handleSubmit as (data: FieldValues) => unknown}
        isLoading={crearMutation.isPending}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        cancelLabel="Cancelar"
        backLabel="Anterior"
        nextLabel="Siguiente"
        preventClose={crearMutation.isPending}
      />

      <ProyectistaFormModal
        open={showProyectistaModal}
        onOpenChange={setShowProyectistaModal}
        onSaved={handleProyectistaSaved}
        especialidadOptions={especialidadOptions}
      />

      <ContactoFormModal
        open={showContactoModal}
        onOpenChange={setShowContactoModal}
        onSaved={handleContactoSaved}
        initialData={
          editingContactoIndex !== null
            ? store.selectedContactos[editingContactoIndex]
            : undefined
        }
      />
    </>
  );
}
