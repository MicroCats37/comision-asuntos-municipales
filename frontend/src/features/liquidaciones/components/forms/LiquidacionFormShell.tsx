"use client";

import type { ReactNode } from "react";
import { useCallback, useMemo } from "react";

import type { FieldValues, UseFormReturn } from "react-hook-form";
import type { ZodType } from "zod";
import type { GenericModalSize } from "@/components/genericModal/GenericModal";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import {
  LiquidacionFormHeader,
  type LiquidacionFormMode,
} from "./LiquidacionFormHeader";

/**
 * Item shape mínimo que el shell necesita. Los tipos reales (Edif, Taludes, IV, HU, MS)
 * extienden este shape con sus campos específicos vía structural typing.
 */
export interface LiquidacionSourceItem {
  liquidacion_general: {
    id: string;
    sub_total: number;
    total: number;
    numero_revision: number | string;
    contacto?: unknown;
    [key: string]: unknown;
  };
  liquidacion_tipo?: unknown;
  liquidacion_especifica?: unknown;
  [key: string]: unknown;
}

interface SuccessMessages {
  create?: string;
  edit?: string;
  nuevaRevision?: string;
  relacionada?: string;
}

export interface LiquidacionFormShellProps<
  T extends FieldValues,
  TItem extends LiquidacionSourceItem,
> {
  // ── App-level ───────────────────────────────────────────────────────
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  size?: GenericModalSize;

  // ── Mode + data ────────────────────────────────────────────────────
  mode: LiquidacionFormMode;
  /** Item siendo editado (mode='edit') o previa (mode='nueva-revision'/'relacionada'). null en create. */
  sourceItem: TItem | null;

  // ── Schema ─────────────────────────────────────────────────────────
  schema: ZodType<T>;
  initialData: Partial<T>;

  // ── Visual ─────────────────────────────────────────────────────────
  eyebrow: string;
  icon: ReactNode;
  /** Texto del título — ej: "Nueva Liquidación", "Editar Liquidación", "Nueva Revisión" */
  titlePrefix: string;
  description?: string;

  // ── Primary action ─────────────────────────────────────────────────
  primaryLabel: string;
  primaryLoadingLabel: string;
  primaryLoading: boolean;

  // ── Body rendering ─────────────────────────────────────────────────
  renderBody: (ctx: {
    methods: UseFormReturn<T>;
    isEdit: boolean;
    isRevisionLike: boolean;
    sourceItem: TItem | null;
    canEditProyecto: boolean;
  }) => ReactNode;

  // ── Submission ────────────────────────────────────────────────────
  /** Submit para mode='create'. Recibe form data (incluye `contacto` desde el schema si aplica). */
  onSubmitCreate?: (data: T) => Promise<unknown>;
  /** Submit para mode='edit'. Recibe form data + canEditProyecto. */
  onSubmitEdit?: (data: T, canEditProyecto: boolean) => Promise<unknown>;
  /** Submit para mode='nueva-revision'. Recibe form data + liquidacionPreviaId. */
  onSubmitNuevaRevision?: (
    data: T,
    liquidacionPreviaId: string,
  ) => Promise<unknown>;
  /** Submit para mode='relacionada'. Recibe form data + liquidacionPreviaId. */
  onSubmitRelacionada?: (
    data: T,
    liquidacionPreviaId: string,
  ) => Promise<unknown>;

  /** Mensajes de éxito por mode. Default: "Liquidación creada/editada correctamente", etc. */
  successMessages?: SuccessMessages;

  /** Hook post-submit. En create se ejecuta después de solicitar el cierre. */
  onAfterSubmit?: (mode: LiquidacionFormMode, result: unknown) => void;

  // ── Policies (caller overrides defaults) ──────────────────────────
  /** Default: create/nueva-revision=true, edit=basado en revision>1, relacionada=false. */
  computeCanEditProyecto?: (
    mode: LiquidacionFormMode,
    sourceItem: TItem | null,
  ) => boolean;
  /** Default: usa sourceItem.liquidacion_general.sub_total y total. */
  getPreviousValues?: (
    sourceItem: TItem | null,
  ) => { subTotal: number; total: number } | undefined;
  /** Default: edit → numero_revision; nueva-revision → previa.revision + 2; relacionada → 1 (vinculada, no incrementa). */
  getRevisionNumber?: (
    mode: LiquidacionFormMode,
    sourceItem: TItem | null,
  ) => number | undefined;

  // ── Ver detalle (solo nueva-revision / relacionada) ───────────────
  onVerDetalle?: () => void;
}

const DEFAULT_SUCCESS: Required<SuccessMessages> = {
  create: "Liquidación creada correctamente",
  edit: "Liquidación editada correctamente",
  nuevaRevision: "Nueva revisión creada correctamente",
  relacionada: "Liquidación relacionada creada correctamente",
};

const defaultGetPreviousValues = <TItem extends LiquidacionSourceItem>(
  sourceItem: TItem | null,
): { subTotal: number; total: number } | undefined => {
  if (!sourceItem) return undefined;
  const lg = sourceItem.liquidacion_general;
  return {
    subTotal: Number(lg.sub_total ?? 0),
    total: Number(lg.total ?? 0),
  };
};

const defaultComputeCanEditProyecto = <TItem extends LiquidacionSourceItem>(
  mode: LiquidacionFormMode,
  sourceItem: TItem | null,
): boolean => {
  if (mode === "create" || mode === "nueva-revision") return true;
  if (mode === "edit" && sourceItem) {
    const n = Number(sourceItem.liquidacion_general.numero_revision);
    return n <= 1;
  }
  return false;
};

const defaultGetRevisionNumber = <TItem extends LiquidacionSourceItem>(
  mode: LiquidacionFormMode,
  sourceItem: TItem | null,
): number | undefined => {
  if (!sourceItem) return undefined;
  if (mode === "edit") {
    return Number(sourceItem.liquidacion_general.numero_revision);
  }
  if (mode === "nueva-revision") {
    // Siguiente revisión (skip pares): previa=N → nueva=N+2
    const n = Number(sourceItem.liquidacion_general.numero_revision);
    return Number.isFinite(n) ? n + 2 : undefined;
  }
  if (mode === "relacionada") {
    // Vinculada a una previa: siempre arranca en revisión 1 (no incrementa)
    return 1;
  }
  return undefined;
};

/**
 * LiquidacionFormShell — Wrapper genérico para los 4 modes de liquidación.
 *
 * Encapsula toda la lógica repetida entre tipos:
 *  - State: contacto, contactoModalOpen
 *  - Pre-fill de contacto desde sourceItem
 *  - Header con badge + valores previos + botón "Ver detalle"
 *  - AppFormModal wrapper
 *  - Submission con 4 ramas (create/edit/nueva-revision/relacionada)
 *  - ContactoFormModal sibling
 *
 * El caller (modal por tipo) provee:
 *  - sourceItem: el item editado o la previa
 *  - schema + initialData
 *  - renderBody: la composición del body con sus smart fields específicos
 *  - 4 onSubmit: handlers de mutación (uno por mode)
 *  - Datos visuales: title, icon, eyebrow, etc.
 */
export function LiquidacionFormShell<
  T extends FieldValues,
  TItem extends LiquidacionSourceItem,
>(props: LiquidacionFormShellProps<T, TItem>) {
  const {
    open,
    onOpenChange,
    onSuccess,
    size,
    mode,
    sourceItem,
    schema,
    initialData,
    eyebrow,
    icon,
    titlePrefix,
    description,
    primaryLabel,
    primaryLoadingLabel,
    primaryLoading,
    renderBody,
    onSubmitCreate,
    onSubmitEdit,
    onSubmitNuevaRevision,
    onSubmitRelacionada,
    successMessages,
    onAfterSubmit,
    computeCanEditProyecto = defaultComputeCanEditProyecto as never,
    getPreviousValues = defaultGetPreviousValues as never,
    getRevisionNumber = defaultGetRevisionNumber as never,
    onVerDetalle,
  } = props;

  const success = { ...DEFAULT_SUCCESS, ...successMessages };

  // ── Cómputos derivados (valores pasados por header y body) ──────────
  const previousValues = useMemo(
    () =>
      (
        getPreviousValues as (
          s: TItem | null,
        ) => { subTotal: number; total: number } | undefined
      )(sourceItem),
    [sourceItem, getPreviousValues],
  );

  const revisionNumber = useMemo(
    () =>
      (
        getRevisionNumber as (
          m: LiquidacionFormMode,
          s: TItem | null,
        ) => number | undefined
      )(mode, sourceItem),
    [mode, sourceItem, getRevisionNumber],
  );

  const canEditProyecto = useMemo(
    () =>
      (
        computeCanEditProyecto as (
          m: LiquidacionFormMode,
          s: TItem | null,
        ) => boolean
      )(mode, sourceItem),
    [mode, sourceItem, computeCanEditProyecto],
  );

  const isEdit = mode === "edit";
  const isRevisionLike = mode === "nueva-revision" || mode === "relacionada";

  // ── Header con badge + Ver detalle ──────────────────────────────────
  const headerActions = (
    <LiquidacionFormHeader
      mode={mode}
      revisionNumber={revisionNumber}
      onVerDetalle={onVerDetalle}
      previousSubtotal={previousValues?.subTotal}
      previousTotal={previousValues?.total}
    />
  );

  // ── Submission con 4 ramas ─────────────────────────────────────────
  const handleSubmit = useCallback(
    async (data: T) => {
      // Sin try/catch local: los errores se propagan a AppFormModal.handleFormSubmit
      // (modal NO cierra en error) → GenericForm (muestra submissionMessage inline).
      // Los mutation hooks ya muestran notify.error() (toast rojo) en error.
      if (mode === "create" && onSubmitCreate) {
        const result = await onSubmitCreate(data);
        onSuccess?.();
        onOpenChange(false);
        // El Dialog cierra con una animación de salida (~100ms, `duration-100` en
        // dialog.tsx). window.print() es síncrono y congelaría esa animación si se
        // llamara antes de que termine, dejando el modal atascado a medio cerrar.
        // Diferir la impresión justo por encima de la animación garantiza que el
        // modal ya esté cerrado cuando se abre el diálogo de impresión.
        setTimeout(() => onAfterSubmit?.(mode, result), 150);
        return;
      }
      if (mode === "edit" && onSubmitEdit) {
        await onSubmitEdit(data, canEditProyecto);
        notify.success(success.edit);
        onAfterSubmit?.(mode, null);
        onSuccess?.();
        return;
      }
      if (mode === "nueva-revision" && onSubmitNuevaRevision) {
        const prevId = sourceItem?.liquidacion_general.id;
        if (!prevId) return;
        const result = await onSubmitNuevaRevision(data, prevId);
        notify.success(success.nuevaRevision);
        onAfterSubmit?.(mode, result);
        onSuccess?.();
        return;
      }
      if (mode === "relacionada" && onSubmitRelacionada) {
        const prevId = sourceItem?.liquidacion_general.id;
        if (!prevId) return;
        const result = await onSubmitRelacionada(data, prevId);
        notify.success(success.relacionada);
        onAfterSubmit?.(mode, result);
        onSuccess?.();
        return;
      }
    },
    [
      mode,
      sourceItem,
      canEditProyecto,
      onSubmitCreate,
      onSubmitEdit,
      onSubmitNuevaRevision,
      onSubmitRelacionada,
      success.edit,
      success.nuevaRevision,
      success.relacionada,
      onAfterSubmit,
      onSuccess,
      onOpenChange,
    ],
  );

  return (
    <>
      {/* biome-ignore lint/suspicious/noExplicitAny: shell usa genéricos sobre T extends FieldValues */}
      <AppFormModal<any>
        open={open}
        onOpenChange={onOpenChange}
        title={`${titlePrefix} — ${eyebrow}`}
        description={description}
        eyebrow={eyebrow}
        icon={icon}
        primaryLabel={primaryLabel}
        primaryLoadingLabel={primaryLoadingLabel}
        primaryLoading={primaryLoading}
        onPrimary={() => undefined}
        schema={schema as never}
        initialData={initialData as never}
        onSubmit={handleSubmit as never}
        headerActions={headerActions}
        size={size}
      >
        {({ methods }) =>
          renderBody({
            methods: methods as UseFormReturn<T>,
            isEdit,
            isRevisionLike,
            sourceItem,
            canEditProyecto,
          })
        }
      </AppFormModal>
    </>
  );
}
