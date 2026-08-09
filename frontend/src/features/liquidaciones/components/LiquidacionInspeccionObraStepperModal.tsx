/**
 * LiquidacionInspeccionObraStepperModal — Formulario para Inspección de Obra (primera revisión).
 *
 * ── Flujo de pasos ───────────────────────────────────────────────────────────
 *   1. Liquidación    → municipalidad + cantidad_visitas + categoria + cotización
 *   2. Proyecto       → buscar existente (XOR) o crear inline
 *   3. Personas       → proyectistas + contactos
 *   4. Confirmación   → revisión final + submit
 *
 * ── Arquitectura ─────────────────────────────────────────────────────────────
 *   AppStepperFormModal (genérico) + stepper-ui-store-factory.ts (Zustand)
 *   React Hook Form + Zod (validación por paso)
 *   Hooks IO-específicos: useCrearInspeccionObraPrimeraRevision,
 *                          useCotizarInspeccionObraPrimeraRevision
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, CheckCircle, FileText, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useForm } from "react-hook-form";
import { AppStepperFormModal } from "@/components-app/forms/AppStepperFormModal";
import { notify } from "@/errors";
import { useCrearInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useCotizarInspeccionObraPrimeraRevision } from "../hooks/useInspeccionObra";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { useEspecialidadesVigentesLiquidacion } from "../hooks/useEspecialidadesVigentesLiquidacion";
import { stepInspeccionObraSchema } from "../schemas/liquidacion-inspeccion-obra.schema";
import { useInspeccionObraStepperStore, type CotizacionState } from "../store";
import type { ContactoInline } from "../types/contacto";
import type { CotizacionIOResponse } from "../types/liquidacion-inspeccion-obra.types";
import type { CrearInspeccionObraPrimeraRevisionIn } from "../types/liquidacion-inspeccion-obra.types";
import type { ProyectistaInline } from "../types/proyectista";
import { ContactoFormModal } from "./ContactoFormModal";
import { ProyectistaFormModal } from "./ProyectistaFormModal";
import { Step1Proyecto } from "./steps/Step1Proyecto";
import { Step3Personas } from "./steps/Step3Personas";
import { StepInspeccionObraLiquidacion } from "./steps/StepInspeccionObraLiquidacion";
import {
  StepInspeccionObraConfirmacion,
  type LiquidacionDisplayItem,
} from "./steps/StepInspeccionObraConfirmacion";

/** Labels para categorías IO */
const CATEGORIA_LABELS: Record<string, string> = {
  C1: "Categoría C1",
  C2: "Categoría C2",
  C3: "Categoría C3",
  C4: "Categoría C4",
};

type FormData = {
  municipalidad_id: string;
  cantidad_visitas: number;
  categoria: "C1" | "C2" | "C3" | "C4";
  expediente?: string;
  observacion?: string;
};

const STEP_IDS = ["liquidacion", "proyecto", "personas", "confirmacion"] as const;

const TIPO_LABEL = "Inspección de Obra";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionInspeccionObraStepperModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LiquidacionInspeccionObraStepperModal({
  open,
  onOpenChange,
  onSuccess,
}: LiquidacionInspeccionObraStepperModalProps) {
  const crearMutation = useCrearInspeccionObraPrimeraRevision();
  const cotizarMutation = useCotizarInspeccionObraPrimeraRevision();
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  // ── Especialidades vigentes para el tipo de liquidación ───────────────────
  const { data: especialidadesData } = useEspecialidadesVigentesLiquidacion("inspeccion-obra");
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
    resolver: zodResolver(stepInspeccionObraSchema),
    defaultValues: {
      municipalidad_id: "" as never,
      cantidad_visitas: 1 as never,
      categoria: undefined as never,
      expediente: "",
      observacion: "",
    },
    mode: "onBlur",
  });

  const store = useInspeccionObraStepperStore();

  // ── Reset on close ─────────────────────────────────────────────────────────
  // Seleccionar reset como función estable para evitar loop infinito:
  // useEffect depende de store completo → identity cambia en cada render → reset → loop.
  const resetStepper = useInspeccionObraStepperStore((state) => state.reset);
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
  const cotizacionQuote: CotizacionIOResponse | null =
    (store.cotizacion.quote as CotizacionIOResponse | null) ?? null;

  // ── Items normalizados para confirmación ────────────────────────────────────
  const getLiquidacionItems = (data: FormData): LiquidacionDisplayItem[] => {
    const items: LiquidacionDisplayItem[] = [
      { label: "Cant. Visitas", value: data.cantidad_visitas },
      {
        label: "Categoría",
        value: CATEGORIA_LABELS[data.categoria] ?? data.categoria,
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
        const valid = await methods.trigger(["municipalidad_id", "cantidad_visitas", "categoria"]);
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
        <StepInspeccionObraLiquidacion
          methods={methods}
          isActive={isActive}
          municipalidades={municipalidades || []}
          isLoadingMunicipalidades={isLoadingMunicipalidades}
          cotizarMutation={cotizarMutation}
          quote={cotizacionQuote}
          setCotizacionQuote={(q) =>
            store.setCotizacionQuote(
              q as CotizacionState["quote"],
            )
          }
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
          <StepInspeccionObraConfirmacion
            methods={methods}
            isActive={isActive}
            tipoLabel={TIPO_LABEL}
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
      const { selectedProyecto, proyectoInline, selectedProyectistas: _sp, selectedContactos } =
        store;

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

      const contactosPayload = (selectedContactos as ContactoInline[]).map(
        ({ localId: _lid, ...contacto }) => contacto,
      );

      const submitData: CrearInspeccionObraPrimeraRevisionIn = {
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
        cantidad_visitas: Number(data.cantidad_visitas),
        categoria: data.categoria,
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
        title={`Nueva Liquidación ${TIPO_LABEL}`}
        eyebrow="Inspección de Obra"
        icon={<FileText className="h-5 w-5 text-primary" />}
        description={`Registra una nueva liquidación de ${TIPO_LABEL.toLowerCase()}`}
        steps={steps}
        schema={stepInspeccionObraSchema}
        formMethods={formMethods}
        onSubmit={handleSubmit as (data: FieldValues) => unknown}
        isLoading={crearMutation.isPending}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        cancelLabel="Cancelar"
        backLabel="Anterior"
        nextLabel="Siguiente"
        preventClose={true}
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
