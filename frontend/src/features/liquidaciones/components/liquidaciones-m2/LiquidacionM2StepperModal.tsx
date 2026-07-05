/**
 * LiquidacionM2StepperModal — Base genérico para liquidaciones M2 (primera revisión).
 *
 * Tipos soportados: Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes.
 *
 * ── Flujo de pasos ───────────────────────────────────────────────────────────
 *   1. Liquidación    → municipalidad + area_solicitada + cotización
 *   2. Proyecto       → buscar existente (XOR) o crear inline
 *   3. Personas       → proyectistas + contactos
 *   4. Confirmación   → revisión final + submit
 *
 * ── Arquitectura ─────────────────────────────────────────────────────────────
 *   AppStepperFormModal (genérico) + stepper-ui.store.ts (Zustand)
 *   React Hook Form + Zod (validación por paso)
 *   Phase 2 hooks: useCotizarNoEdificacionM2, useCrearNoEdificacionM2
 *
 * Este componente es una capa delgada de orquestación — NO tiene branching M2 vs IO.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, CheckCircle, FileText, Users } from "lucide-react";
import { useCallback, useState } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useForm } from "react-hook-form";
import { AppStepperFormModal } from "@/components-app/forms/AppStepperFormModal";
import { notify } from "@/errors";
import { useCrearNoEdificacionM2 } from "../../hooks/useNoEdificacion";
import { useCotizarNoEdificacionM2 } from "../../hooks/useNoEdificacion";
import { useMunicipalidades } from "../../hooks/useMunicipalidades";
import { stepM2Schema } from "../../schemas/liquidacion-no-edificacion.schema";
import { useLiquidacionStepperUIStore, type CotizacionState } from "../../store";
import type { ContactoInline } from "../../types/contacto";
import type {
  LiquidacionM2Kind,
  LiquidacionM2BaseIn,
  CotizacionM2Response,
} from "../../types/liquidacion-no-edificacion.types";
import type { ProyectistaInline } from "../../types/proyectista";
import { ContactoFormModal } from "../ContactoFormModal";
import { ProyectistaFormModal } from "../ProyectistaFormModal";
import { Step1Proyecto } from "../steps/Step1Proyecto";
import { Step3Personas } from "../steps/Step3Personas";
import { StepM2Liquidacion } from "../steps/StepM2Liquidacion";
import {
  NoEdificacionConfirmacionStep,
  type LiquidacionDisplayItem,
} from "../steps/NoEdificacionConfirmacionStep";

type FormData = {
  municipalidad_id: string;
  area_solicitada: number;
  expediente?: string;
  observacion?: string;
};

const STEP_IDS = ["liquidacion", "proyecto", "personas", "confirmacion"] as const;

// ── Labels por kind ───────────────────────────────────────────────────────────

export const M2_KIND_LABELS: Record<LiquidacionM2Kind, string> = {
  "habilitacion-urbana": "Habilitación Urbana",
  "mecanica-suelos": "Mecánica de Suelos",
  "impacto-vial": "Impacto Vial",
  "taludes": "Taludes",
};

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LiquidacionM2StepperModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  kind: LiquidacionM2Kind;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LiquidacionM2StepperModal({
  open,
  onOpenChange,
  onSuccess,
  kind,
}: LiquidacionM2StepperModalProps) {
  const crearMutation = useCrearNoEdificacionM2(kind);
  const cotizarMutation = useCotizarNoEdificacionM2(kind);
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  const formMethods = useForm<FormData>({
    resolver: zodResolver(stepM2Schema),
    defaultValues: {
      municipalidad_id: "" as never,
      area_solicitada: 0 as never,
      expediente: "",
      observacion: "",
    },
    mode: "onBlur",
  });

  const store = useLiquidacionStepperUIStore();

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
  const cotizacionQuote: CotizacionM2Response | null =
    (store.cotizacion.quote as CotizacionM2Response | null) ?? null;

  // ── Items normalizados para confirmación ────────────────────────────────────
  const getLiquidacionItems = (data: FormData): LiquidacionDisplayItem[] => {
    const items: LiquidacionDisplayItem[] = [
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
        <StepM2Liquidacion
          methods={methods}
          isActive={isActive}
          municipalidades={municipalidades || []}
          isLoadingMunicipalidades={isLoadingMunicipalidades}
          kind={kind}
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
      }) => <Step1Proyecto methods={methods} isActive={isActive} />,
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
          especialidadOptions={[]}
          especialidadLabels={{}}
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
          <NoEdificacionConfirmacionStep
            methods={methods}
            isActive={isActive}
            tipoLabel={M2_KIND_LABELS[kind]}
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

      const submitData: LiquidacionM2BaseIn = {
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
        title={`Nueva Liquidación ${M2_KIND_LABELS[kind]}`}
        eyebrow="No Edificación"
        icon={<FileText className="h-5 w-5 text-primary" />}
        description={`Registra una nueva liquidación de ${M2_KIND_LABELS[kind].toLowerCase()}`}
        steps={steps}
        schema={stepM2Schema}
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
        especialidadOptions={[]}
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
