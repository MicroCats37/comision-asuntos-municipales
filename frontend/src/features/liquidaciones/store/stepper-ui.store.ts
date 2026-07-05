"use client";

import { create } from "zustand";
import type { EntidadResult } from "@/features/entidades/types/entidad";
import type { ContactoInline } from "../types/contacto";
import type { CotizacionQuote } from "../types/liquidacion-edificaciones";
import type { ProyectistaInline } from "../types/proyectista";

// ── Entidad Simple (matches normalizeProyectoResponse return type) ─────────────

export interface EntidadSimple {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
}

// ── Entidad Inline for proyecto_inline ─────────────────────────────────────

export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Step UI State ────────────────────────────────────────────────────────────

interface StepUIState {
  currentStep: number;
  direction: "forward" | "backward";
  isTransitioning: boolean;
}

// ── Cached Display State ─────────────────────────────────────────────────────
// These are UI selections that survive across steps.
// RHF field values (municipalidad_id, tipo_tramite, etc.) live in the form,
// NOT in this store.

export interface CachedProyecto {
  id: string;
  public_id: string;
  denominacion: string;
  direccion: string;
  distrito?: string | null;
  entidad?: EntidadSimple | null;
}

export interface CotizacionState {
  quote: CotizacionQuote | null;
  isCalculating: boolean;
  lastError: string | null;
}

interface LiquidacionStepperUIState extends StepUIState {
  // Cached selections (survive step navigation)
  selectedProyecto: CachedProyecto | null;
  // Modo inline: datos para crear proyecto al vuelo
  proyectoInline: {
    denominacion: string;
    direccion: string;
    distrito_id?: string;
    nombre_propietario: string;
    entidad: EntidadInline;
  } | null;
  selectedProyectistas: ProyectistaInline[];
  selectedContactos: ContactoInline[];
  // Cotización (Step 4)
  cotizacion: CotizacionState;
  // Revisiones (locked + selected)
  lockedRevisionIds: string[];
  selectedRevisionIds: string[];
  // Entidad for inline proyecto creation (full EntidadResult from child modals)
  entidad: import("@/features/entidades/types/entidad").EntidadResult | null;
  // Tarifas seleccionadas: array de 1 UUID para esta fase
  selectedTarifasIds: string[];
}

// ── Actions ──────────────────────────────────────────────────────────────────

interface LiquidacionStepperUIActions {
  // Step navigation
  setStep: (step: number) => void;
  nextStep: () => void;
  previousStep: () => void;
  goToStep: (step: number) => void;
  setTransitioning: (val: boolean) => void;
  reset: () => void;

  // Proyecto
  setSelectedProyecto: (proyecto: CachedProyecto | null) => void;

  // Proyecto Inline
  setProyectoInline: (data: {
    denominacion: string;
    direccion: string;
    distrito_id?: string;
    nombre_propietario: string;
    entidad: EntidadInline;
  } | null) => void;

  // Proyectistas
  setSelectedProyectistas: (proyectistas: ProyectistaInline[]) => void;
  addProyectista: (proyectista: ProyectistaInline) => void;
  removeProyectista: (cip: string) => void;

  // Contactos
  setSelectedContactos: (contactos: ContactoInline[]) => void;
  addContacto: (contacto: ContactoInline) => void;
  updateContacto: (index: number, contacto: ContactoInline) => void;
  removeContacto: (index: number) => void;

  // Delegados — kept for compatibility with Step2LiquidacionDelegados/Step5Confirmacion but not populated in creation flow
  selectedDelegados: string[];
  toggleDelegado: (id: string) => void;

  // Revisiones
  setSelectedRevisionIds: (ids: string[]) => void;
  setLockedRevisionIds: (ids: string[]) => void;
  toggleRevision: (id: string) => void;

  // Tarifas — array para no-edificación (múltiples tariffs)
  setSelectedTarifasId: (tarifaId: string) => void;
  setSelectedTarifasIds: (tarifaIds: string[]) => void;
  addSelectedTarifaId: (tarifaId: string) => void;
  removeSelectedTarifaId: (tarifaId: string) => void;

  // Entidad
  setEntidad: (entidad: import("@/features/entidades/types/entidad").EntidadResult | null) => void;

  // Cotización
  setCotizacionQuote: (quote: CotizacionQuote | null) => void;
  setCotizacionCalculating: (val: boolean) => void;
  setCotizacionError: (error: string | null) => void;
}

// ── Initial State ────────────────────────────────────────────────────────────

const initialCotizacionState: CotizacionState = {
  quote: null,
  isCalculating: false,
  lastError: null,
};

const initialUIState: StepUIState = {
  currentStep: 0,
  direction: "forward",
  isTransitioning: false,
};

// ── Store ─────────────────────────────────────────────────────────────────────

export const useLiquidacionStepperUIStore = create<
  LiquidacionStepperUIState & LiquidacionStepperUIActions
>()((set, get) => ({
  // ── Initial UI state ──────────────────────────────────────────────────────
  ...initialUIState,

  // ── Cached selections ───────────────────────────────────────────────────────
  selectedProyecto: null,
  proyectoInline: null,
  selectedProyectistas: [],
  selectedContactos: [],
  selectedDelegados: [],
  lockedRevisionIds: [],
  selectedRevisionIds: [],
  entidad: null,
  cotizacion: { ...initialCotizacionState },
  selectedTarifasIds: [],

  // ── Step navigation ─────────────────────────────────────────────────────────
  setStep: (step) =>
    set({
      currentStep: step,
      direction: step > get().currentStep ? "forward" : "backward",
    }),

  nextStep: () =>
    set((s) => ({
      currentStep: s.currentStep + 1,
      direction: "forward",
      isTransitioning: true,
    })),

  previousStep: () =>
    set((s) => ({
      currentStep: Math.max(0, s.currentStep - 1),
      direction: "backward",
      isTransitioning: true,
    })),

  goToStep: (step) =>
    set((s) => ({
      currentStep: step,
      direction: step > s.currentStep ? "forward" : "backward",
      isTransitioning: true,
    })),

  setTransitioning: (val) => set({ isTransitioning: val }),

  reset: () =>
    set({
      ...initialUIState,
      selectedProyecto: null,
      proyectoInline: null,
      selectedProyectistas: [],
      selectedContactos: [],
      selectedDelegados: [],
      lockedRevisionIds: [],
      selectedRevisionIds: [],
      entidad: null,
      cotizacion: { ...initialCotizacionState },
      selectedTarifasIds: [],
    }),

  // ── Proyecto ────────────────────────────────────────────────────────────────
  setSelectedProyecto: (proyecto) => set({ selectedProyecto: proyecto }),

  // ── Proyecto Inline ────────────────────────────────────────────────────────
  setProyectoInline: (data) => set({ proyectoInline: data }),

  // ── Proyectistas ────────────────────────────────────────────────────────────
  setSelectedProyectistas: (proyectistas) =>
    set({ selectedProyectistas: proyectistas }),
  addProyectista: (proyectista) =>
    set((s) => ({
      selectedProyectistas: s.selectedProyectistas.some(
        (p) => p.cip === proyectista.cip,
      )
        ? s.selectedProyectistas
        : [...s.selectedProyectistas, proyectista],
    })),
  removeProyectista: (cip) =>
    set((s) => ({
      selectedProyectistas: s.selectedProyectistas.filter((p) => p.cip !== cip),
    })),

  // ── Contactos ───────────────────────────────────────────────────────────────
  setSelectedContactos: (contactos) => set({ selectedContactos: contactos }),
  addContacto: (contacto) =>
    set((s) => ({
      selectedContactos: [
        ...s.selectedContactos,
        {
          ...contacto,
          localId:
            contacto.localId ??
            `local-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        },
      ],
    })),
  updateContacto: (index, contacto) =>
    set((s) => {
      const updated = [...s.selectedContactos];
      updated[index] = contacto;
      return { selectedContactos: updated };
    }),
  removeContacto: (index) =>
    set((s) => ({
      selectedContactos: s.selectedContactos.filter((_, i) => i !== index),
    })),

  // ── Delegados ───────────────────────────────────────────────────────────────
  // Note: selectedDelegados is kept for compatibility but not populated in creation flow
  toggleDelegado: (id) =>
    set((s) => ({
      selectedDelegados: s.selectedDelegados.includes(id)
        ? s.selectedDelegados.filter((d) => d !== id)
        : [...s.selectedDelegados, id],
    })),

  // ── Revisiones ──────────────────────────────────────────────────────────────
  setSelectedRevisionIds: (ids) => set({ selectedRevisionIds: ids }),
  setLockedRevisionIds: (ids) => set({ lockedRevisionIds: ids }),
  toggleRevision: (id) =>
    set((s) => ({
      selectedRevisionIds: s.selectedRevisionIds.includes(id)
        ? s.selectedRevisionIds.filter((r) => r !== id)
        : [...s.selectedRevisionIds, id],
    })),

  // ── Tarifas ─────────────────────────────────────────────────────────────────
  setSelectedTarifasId: (tarifaId) => set({ selectedTarifasIds: [tarifaId] }),
  setSelectedTarifasIds: (tarifaIds) => set({ selectedTarifasIds: tarifaIds }),
  addSelectedTarifaId: (tarifaId) =>
    set((s) => ({
      selectedTarifasIds: s.selectedTarifasIds.includes(tarifaId)
        ? s.selectedTarifasIds
        : [...s.selectedTarifasIds, tarifaId],
    })),
  removeSelectedTarifaId: (tarifaId) =>
    set((s) => ({
      selectedTarifasIds: s.selectedTarifasIds.filter((id) => id !== tarifaId),
    })),

  // ── Entidad ─────────────────────────────────────────────────────────────────
  setEntidad: (entidad) => set({ entidad }),

  // ── Cotización ──────────────────────────────────────────────────────────────
  setCotizacionQuote: (quote) =>
    set((s) => ({ cotizacion: { ...s.cotizacion, quote } })),
  setCotizacionCalculating: (val) =>
    set((s) => ({ cotizacion: { ...s.cotizacion, isCalculating: val } })),
  setCotizacionError: (error) =>
    set((s) => ({ cotizacion: { ...s.cotizacion, lastError: error } })),
}));
