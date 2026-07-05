"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, CheckCircle, FileText, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useForm, useWatch } from "react-hook-form";
import { AppStepperFormModal } from "@/components-app/forms/AppStepperFormModal";
import { notify } from "@/errors";
import { useCrearPrimeraRevision } from "../hooks/useCrearLiquidacion";
import { useMunicipalidades } from "../hooks/useMunicipalidades";
import { useRevisionesVigentes } from "../hooks/useRevisionesVigentes";
import { useVariablesFinancieras } from "../hooks/useVariablesFinancieras";
import { liquidacionEdificacionFormSchema } from "../schemas/liquidacion-edificaciones-form.schema";
import { useLiquidacionStepperUIStore } from "../store";
import type { ContactoInline } from "../types/contacto";
import type { LiquidacionEdificacionSubmitData } from "../types/liquidacion-edificaciones-form.types";
import type { LiquidacionStepperModalProps } from "../types/liquidacion-stepper.types";
import type { ProyectistaInline } from "../types/proyectista";
import { ContactoFormModal } from "./ContactoFormModal";
import { ProyectistaFormModal } from "./ProyectistaFormModal";
import {
  Step1Proyecto,
  Step2Liquidacion,
  Step3Personas,
  Step5Confirmacion,
} from "./steps";

// ── Tipos ──────────────────────────────────────────────────────────────────────
// FormData se infiere directamente del schema de Zod para mantener una única fuente de verdad.
// LiquidacionEdificacionFormSchema define la estructura completa del formulario (tipos, validaciones).
type FormData =
  import("../schemas/liquidacion-edificaciones-form.schema").LiquidacionEdificacionFormSchema;

const formSchema = liquidacionEdificacionFormSchema;

// Identificadores estables de cada paso del stepper.
// Se usan como key de React y como referencia en el store para navegación.
const STEP_IDS = [
  "liquidacion",
  "proyecto",
  "personas",
  "confirmacion",
] as const;

/**
 * LiquidacionStepperModal — Formulario multipaso para crear una liquidación de edificación.
 *
 * ── Flujo de pasos ─────────────────────────────────────────────────────────────
 *
 *   1. Liquidación    → municipalidad, tipo trámite, valor, revisiones, cotización
 *   2. Proyecto       → buscar existente (XOR) o crear inline
 *   3. Personas       → proyectistas + contactos
 *   4. Confirmación   → revisión final + submit
 *
 * ── Arquitectura ────────────────────────────────────────────────────────────────
 *
 * Este componente es una capa delgada de orquestación que:
 * 1. Obtiene datos maestros vía hooks de TanStack Query (municipalidades, revisiones, etc.)
 * 2. Configura las definiciones de cada paso (step configs) con su ícono, título y validación
 * 3. Delega la UI (modal, stepper, navegación) al componente genérico `AppStepperFormModal`
 *
 * Flujo de datos:
 *   TanStack Query (datos maestros) → AppStepperFormModal (UI genérica)
 *   Zustand Store (UI state: proyecto, proyectistas, contactos, tarifas)
 *   React Hook Form (valores del formulario, validación Zod)
 *
 * ── Separación de estado ────────────────────────────────────────────────────────
 *
 *   RHF (formMethods)          → campos del formulario: municipalidad_id, tipo_tramite, etc.
 *   Zustand (stepperUIStore)   → selecciones UI que sobreviven entre pasos: proyecto,
 *                                proyectistas, contactos, tarifas, cotización
 *
 *   ¿Por qué Zustand para selecciones UI?
 *   Porque RHF pierde el estado cuando un campo no está montado (al cambiar de paso).
 *   Zustand mantiene las selecciones vivas durante toda la navegación del stepper.
 *
 * ── Patrón XOR proyecto ─────────────────────────────────────────────────────────
 *
 *   El usuario elige UNA de dos opciones mutuamente excluyentes:
 *   A) Seleccionar un proyecto existente (por public_id)
 *   B) Crear un proyecto inline (denominación + dirección + entidad + propietario)
 *   Ambas se validan como XOR tanto en `validate` del Step 2 como en `handleSubmit`.
 */
export function LiquidacionStepperModal({
  open,
  onOpenChange,
  onSuccess,
}: LiquidacionStepperModalProps) {
  const crearMutation = useCrearPrimeraRevision();

  // ── Datos maestros ───────────────────────────────────────────────────────────
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();
  const { data: variablesFinancieras, isLoading: isLoadingVariables } =
    useVariablesFinancieras();

  // ── Instancia de React Hook Form ────────────────────────────────────────────
  // Debe ir antes de useRevisionesVigentes para poder watch el tipo_tramite.
  const formMethods = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      municipalidad_id: "" as never,
      tipo_tramite: "OBRA_NUEVA" as never,
      valor_proyecto: 0 as never,
      expediente: "",
      valor_base_calculo: 0 as never,
      observacion: "",
      revisiones_ids: [] as never,
      proyectistas: [] as never,
      contactos: [] as never,
      proyecto_public_id: "",
    },
    mode: "onBlur",
  });

  // ── Mantener revisiones_ids siempre como array (aunque ya no se use) ────
  useEffect(() => {
    if (!formMethods.getValues("revisiones_ids")) {
      formMethods.setValue("revisiones_ids", [] as never, {
        shouldValidate: false,
      });
    }
  }, [formMethods]);

  // ── Filtrar revisiones vigentes por tipo_tramite actual ──────────────────
  const watchedTipoTramite =
    (useWatch({
      control: formMethods.control,
      name: "tipo_tramite",
    }) as string) ?? "OBRA_NUEVA";
  const { data: revisionesVigentes, isLoading: isLoadingRevisiones } =
    useRevisionesVigentes({
      tipo_tramite: watchedTipoTramite,
      tramite_accion: "PRIMERA_REVISION",
    });

  // ── Metadatos de especialidades ─────────────────────────────────────────────
  const especialidadOptions: Array<{ label: string; value: string }> =
    revisionesVigentes
      ? [
          ...new Map(
            revisionesVigentes
              .flatMap((rev) =>
                rev.especialidades.map((esp) => ({
                  label: esp.nombre,
                  value: esp.id,
                })),
              )
              .map((opt) => [opt.value, opt]),
          ).values(),
        ]
      : [];

  const especialidadLabels: Record<string, string> = {};
  if (revisionesVigentes) {
    for (const rev of revisionesVigentes) {
      for (const esp of rev.especialidades) {
        especialidadLabels[esp.id] = esp.nombre;
      }
    }
  }

  // ── Store Zustand (estado UI del stepper) ──────────────────────────────────
  const store = useLiquidacionStepperUIStore();

  // ── Modales hijos ────────────────────────────────────────────────────────────
  // Estos modales se renderizan FUERA de AppStepperFormModal para evitar
  // conflictos de z-index y problemas de nesting de formularios.
  // Estado: show/hide + índice de contacto en edición (null = nuevo, number = editar).
  const [showProyectistaModal, setShowProyectistaModal] = useState(false);
  const [showContactoModal, setShowContactoModal] = useState(false);
  const [editingContactoIndex, setEditingContactoIndex] = useState<
    number | null
  >(null);

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

  // ── Configuración de pasos del stepper ──────────────────────────────────────
  // Cada step define: id, título, ícono, descripción, validación opcional y render.
  // El componente AppStepperFormModal maneja la navegación, animaciones y footer.
  // La validación de cada paso se ejecuta ANTES de permitir avanzar al siguiente.

  const steps: import("@/components-app/forms/AppStepperFormModal").StepConfig[] =
    [
      // ── Step 1: Liquidación ───────────────────────────────────────────────────
      // Datos del trámite + cotización integrada con botón "Cotizar".
      // Desktop: 2 columnas (datos+revisiones | cotización). Mobile: apilado.
      {
        id: STEP_IDS[0],
        title: "Liquidación",
        icon: FileText,
        description: "Datos de la liquidación, revisión/tarifa y cotización",
        validate: async ({
          methods,
        }: {
          methods: UseFormReturn<FieldValues>;
          currentStep: number;
        }) => {
          const valid = await methods.trigger([
            "municipalidad_id",
            "tipo_tramite",
            "valor_proyecto",
          ]);
          if (!valid) return false;

          if (store.selectedTarifasIds.length === 0) {
            notify.error("Selecciona una revisión/tarifa antes de continuar");
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
        }) => (
          <Step2Liquidacion
            methods={methods}
            isActive={isActive}
            municipalidades={municipalidades || []}
            isLoadingMunicipalidades={isLoadingMunicipalidades}
            revisionesVigentes={revisionesVigentes}
            isLoadingRevisiones={isLoadingRevisiones}
            variablesFinancieras={variablesFinancieras}
            isLoadingVariables={isLoadingVariables}
          />
        ),
      },

      // ── Step 2: Proyecto ──────────────────────────────────────────────────────
      // El usuario elige entre buscar un proyecto existente o crear uno inline.
      // Validación XOR: exactamente uno de los dos modos debe estar activo.
      {
        id: STEP_IDS[1],
        title: "Proyecto",
        icon: Building2,
        description: "Selecciona o crea el proyecto para esta liquidación",
        validate: ({
          methods: _methods,
        }: {
          methods: UseFormReturn<FieldValues>;
          currentStep: number;
        }) => {
          const hasProyectoExistente = !!store.selectedProyecto;
          const hasProyectoInline = !!store.proyectoInline;

          if (!hasProyectoExistente && !hasProyectoInline) {
            notify.error("Selecciona o crea un proyecto antes de continuar");
            return false;
          }

          if (hasProyectoExistente && hasProyectoInline) {
            notify.error(
              "No puede seleccionar y crear un proyecto al mismo tiempo",
            );
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

      // ── Step 3: Personas ──────────────────────────────────────────────────────
      // Gestión de proyectistas (por CIP y especialidad) y contactos de referencia.
      // Cada sub-entidad se agrega/edita/elimina mediante modales hijos.
      // El estado vive en Zustand para persistir entre pasos del stepper.
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

      // ── Step 4: Confirmación ─────────────────────────────────────────────────
      // Resumen final de todos los datos antes de enviar.
      // Es el último paso: el botón "Siguiente" se reemplaza por "Crear Liquidación".
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
        }) => (
          <Step5Confirmacion
            methods={methods}
            isActive={isActive}
            municipalidades={municipalidades?.map((m) => ({
              id: m.id,
              nombre: m.nombre,
            }))}
            especialidadLabels={especialidadLabels}
            variablesFinancieras={variablesFinancieras}
            isLoadingVariables={isLoadingVariables}
          />
        ),
      },
    ];

  // ── Submit: construir payload y enviar a la API ────────────────────────────
  // Flujo:
  //   1. Validar XOR proyecto (existente vs inline)
  //   2. Validar que haya exactamente una tarifa seleccionada
  //   3. Determinar valor_base_calculo según tipo de trámite
  //   4. Construir payload con proyecto_inline O proyecto_public_id
  //   5. Ejecutar mutación → notificar éxito → resetear store + form → cerrar modal
  const handleSubmit = useCallback(
    async (data: FormData) => {
      const {
        selectedProyecto,
        proyectoInline,
        selectedProyectistas,
        selectedContactos,
        selectedTarifasIds,
      } = store;

      // ── Validación XOR proyecto ────────────────────────────────────────────
      const hasProyectoExistente = !!selectedProyecto;
      const hasProyectoInline = !!proyectoInline;

      if (!hasProyectoExistente && !hasProyectoInline) {
        notify.error("Debe seleccionar o crear un proyecto");
        return;
      }

      if (hasProyectoExistente && hasProyectoInline) {
        notify.error(
          "No puede seleccionar y crear un proyecto al mismo tiempo",
        );
        return;
      }

      // ── Validación tarifa única ────────────────────────────────────────────
      if (!selectedTarifasIds || selectedTarifasIds.length === 0) {
        notify.error("Debe seleccionar exactamente una tarifa");
        return;
      }

      // ── Cálculo de valor base ──────────────────────────────────────────────
      // Si es "PROYECTO_CON_PLANTAS_TIPICAS" y hay valor_base_calculo > 0,
      // se usa ese valor. En cualquier otro caso, se usa valor_proyecto.
      const isPlantasTipicas =
        data.tipo_tramite === "PROYECTO_CON_PLANTAS_TIPICAS";
      const valorBaseCalculo =
        isPlantasTipicas &&
        data.valor_base_calculo &&
        data.valor_base_calculo > 0
          ? data.valor_base_calculo
          : data.valor_proyecto;

      // ── Limpiar localId de contactos antes de enviar ──────────────────────
      // localId es un identificador temporal para el frontend, no se envía a la API.
      const contactosPayload = selectedContactos.map(
        ({ localId: _localId, ...contacto }) => contacto,
      );

      // ── Construir payload final ────────────────────────────────────────────
      // XOR: si es proyecto inline → proyecto_inline, si no → proyecto_public_id
      const submitData: LiquidacionEdificacionSubmitData = {
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
          : {
              proyecto_public_id: selectedProyecto!.public_id,
            }),
        municipalidad_id: data.municipalidad_id,
        tipo_tramite: data.tipo_tramite,
        valor_proyecto: data.valor_proyecto,
        expediente: data.expediente,
        valor_base_calculo: valorBaseCalculo,
        observacion: data.observacion,
        revisiones_ids: [],
        proyectistas: selectedProyectistas.map((p) => ({
          cip: p.cip,
          especialidad_id: p.especialidad_id,
          descripcion: p.descripcion,
        })),
        contactos: contactosPayload,
        tarifas_ids: selectedTarifasIds,
      };

      try {
        await crearMutation.mutateAsync(
          submitData as import("../types/liquidacion-edificaciones").PrimeraRevisionFormData,
        );
        notify.success("Liquidación creada correctamente");
        store.reset();
        formMethods.reset();
        onSuccess?.();
        onOpenChange(false);
      } catch {
        // El error ya fue manejado por la mutación (TanStack Query onError / notificaciones)
      }
    },
    [store, crearMutation, onSuccess, onOpenChange, formMethods],
  );

  return (
    <>
      {/* ── Modal Stepper principal ────────────────────────────────────────────
          AppStepperFormModal es el componente genérico reutilizable que maneja:
          - Navegación entre pasos (anterior/siguiente + animaciones)
          - Validación por paso (step.validate)
          - Renderizado condicional del paso activo
          - Footer con botones de acción (cancelar, atrás, siguiente, submit)
          - Estado de carga durante el envío (isLoading) */}
      <AppStepperFormModal
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación Edificación"
        eyebrow="Edificaciones"
        icon={<FileText className="h-5 w-5 text-primary" />}
        description="Registra una nueva liquidación de edificación"
        steps={steps}
        schema={formSchema}
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

      {/* ── Modales hijos ─────────────────────────────────────────────────────
          Renderizados fuera del GenericForm para evitar:
          - Conflictos de z-index (stacking contexts anidados)
          - Doble nesting de formularios (form dentro de form es HTML inválido)
          - Problemas de focus trap entre modales anidados */}
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
