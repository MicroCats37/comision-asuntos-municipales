// ── Stepper Stores (multi-step form logic) ───────────────────────────────────
export type {
  CachedProyecto,
  CotizacionState,
  EntidadSimple,
  EntidadInline,
  LiquidacionStepperUIState,
  LiquidacionStepperUIActions,
  LiquidacionStepperStore,
} from "./stepper-ui-store-factory";
export {
  createLiquidacionStepperStore,
  useEdificacionStepperStore,
  useHabilitacionUrbanaStepperStore,
  useMecanicaSuelosStepperStore,
  useImpactoVialStepperStore,
  useTaludesStepperStore,
  useInspeccionObraStepperStore,
} from "./stepper-ui-store-factory";

// ── List UI Stores (flat, list-level state) ──────────────────────────────────
export type {
  EdificacionesUIStore,
} from "./edificaciones-ui-list.store";
export { useEdificacionesUIStore } from "./edificaciones-ui-list.store";

export type {
  HabilitacionUrbanaUIStore,
} from "./habilitacion-urbana-ui-list.store";
export { useHabilitacionUrbanaUIStore } from "./habilitacion-urbana-ui-list.store";

export type {
  MecanicaSuelosUIStore,
} from "./mecanica-suelos-ui-list.store";
export { useMecanicaSuelosUIStore } from "./mecanica-suelos-ui-list.store";

export type {
  ImpactoVialUIStore,
} from "./impacto-vial-ui-list.store";
export { useImpactoVialUIStore } from "./impacto-vial-ui-list.store";

export type {
  TaludesUIStore,
} from "./taludes-ui-list.store";
export { useTaludesUIStore } from "./taludes-ui-list.store";

export type {
  InspeccionObraUIStore,
} from "./inspeccion-obra-ui-list.store";
export { useInspeccionObraUIStore } from "./inspeccion-obra-ui-list.store";
