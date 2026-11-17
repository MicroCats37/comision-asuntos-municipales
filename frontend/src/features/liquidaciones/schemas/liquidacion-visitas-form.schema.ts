/**
 * Zod schema for Visitas creation forms (Inspeccion Obra).
 * Keeps categoria as derived visual state; backend payloads use tarifa_visitas_id.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";
import { modoCotizacionIOSchema } from "./liquidacion-io-modo-cotizacion.schema";
import { withLegacyRegistroFields } from "./liquidacion-legacy-registro-form.schema";

/**
 * Discriminador de modo de la OPERACIÓN de continuidad (edición de IO).
 *
 * Viaja en `liquidacion_tipo.continuidad.modo` del PATCH de IO:
 *  · `activar`    → crea el registro de continuidad (la IO no tenía ninguna).
 *  · `mantener`   → actualiza el registro de continuidad vigente.
 *  · `desactivar` → elimina el registro y restaura el valor completo de B.
 *
 * AUSENTE = no hay operación de continuidad: el PATCH solo reprecia B con el
 * crédito congelado (comportamiento vigente). Por eso el bloque de formulario
 * rehidratado en edición NO lleva `modo`: solo lo recibe si el usuario
 * interactúa con la sección de continuidad.
 */
export const modoContinuidadVisitasSchema = z.enum([
  "activar",
  "mantener",
  "desactivar",
]);

export type ModoContinuidadVisitas = z.infer<
  typeof modoContinuidadVisitasSchema
>;

/**
 * Bloque OPCIONAL de continuidad de visitas (Inspección de Obra).
 *
 * Se activa desde `Liquidaciones > Inspección de Obra > Continuar` y permite
 * registrar que la liquidación nueva (B) continúa un trabajo de inspección
 * previo (A), acreditando el crédito de las visitas no realizadas.
 *
 * `monto_acumulado` / `total_acumulado` NO se envían: los calcula el servidor
 * a la tarifa de B.
 *
 * El dato que el usuario DECLARA es `total_pagado_previa`: el monto BRUTO
 * pagado en la IO previa (IGV incluido). El servidor lo valida y deriva el par
 * (crédito NETO, crédito BRUTO) con el IGV efectivo de la ruta; el cliente no
 * hace aritmética monetaria (DD-7).
 *
 * `subtotal_credito` (crédito NETO) se conserva SOLO como camino LEGACY /
 * manual: si no hay bruto declarado, el servidor lo usa como crédito neto.
 * Si hay bruto declarado, el BRUTO MANDA y el neto se ignora.
 *
 * NO hay límite de crédito en el cliente: el invariante IV-5 del servidor
 * ("el crédito no puede superar el valor completo del trabajo") responde 400.
 */
export const continuidadVisitasFormSchema = z.object({
  /**
   * Modo de la operación de continuidad (SOLO edición de IO).
   *
   * Es la ÚNICA señal de que el usuario interactuó con la sección de
   * continuidad: si está ausente, el PATCH NO lleva el bloque
   * `liquidacion_tipo.continuidad` y el servidor conserva el crédito
   * congelado. En la creación no se usa (el endpoint de alta no tiene
   * discriminador de modo).
   */
  modo: modoContinuidadVisitasSchema.optional(),
  /** ID de la liquidación de IO previa (A) dentro de CAM. Opcional. */
  liquidacion_previa_id: z.string().optional(),
  /** Campo histórico: la UI ya no lo solicita ni lo envía. */
  visitas_previas_pendientes: z.coerce
    .number()
    .int("Las visitas pendientes deben ser un número entero")
    .min(0, "Las visitas pendientes no pueden ser negativas")
    .max(9999, "Las visitas pendientes exceden el máximo permitido")
    .optional(),
  /** Visitas totales de la previa (informativo cuando la previa no está en CAM). */
  visitas_previas_totales: z.coerce
    .number()
    .int("Las visitas totales deben ser un número entero")
    .min(0, "Las visitas totales no pueden ser negativas")
    .max(9999, "Las visitas totales exceden el máximo permitido")
    .optional(),
  /** Categoría de la previa (informativo). */
  categoria_previa: z.string().optional(),
  /**
   * BRUTO declarado pagado en la liquidación de IO previa (IGV incluido).
   *
   * Es la ENTRADA autoritativa del crédito: el servidor lo valida y deriva el
   * par (crédito neto, crédito bruto) con el IGV efectivo de la ruta.
   *
   * El rango del formulario es `>= 0` (no negativo): un campo vacío equivale
   * a 0 y significa "sin bruto declarado" (el payload omite la clave). El
   * `gt=0` del backend solo aplica a lo que VIAJA.
   */
  total_pagado_previa: z.coerce
    .number()
    .nonnegative(
      "El total pagado en la liquidación previa no puede ser negativo",
    )
    .max(
      9999999999.99,
      "El total pagado en la liquidación previa excede el máximo permitido",
    )
    .nullish(),
  /**
   * Crédito NETO (camino LEGACY / manual).
   *
   * Solo se usa cuando NO hay `total_pagado_previa`: si el bruto está
   * declarado, el servidor ignora este campo. Ausente equivale a 0 (el
   * servidor aplica ese default).
   */
  subtotal_credito: z.coerce
    .number()
    .min(0, "El crédito no puede ser negativo")
    .optional(),
  /** Observación sobre la continuidad. */
  observacion: z.string().optional(),
});

export type ContinuidadVisitasFormData = z.infer<
  typeof continuidadVisitasFormSchema
>;

export const visitasFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Tipo de liquidación (seleccionable via selectSearchable). NO se envía
  // al backend — se usa solo en frontend para filtrar el modal de inspectores.
  tipo_liquidacion_id: z.string().optional(),
  // Especifica fields
  cantidad_visitas: z
    .number({
      error: (issue) =>
        issue.input === undefined || issue.input === null || issue.input === ""
          ? "La cantidad de visitas es requerida"
          : "La cantidad de visitas debe ser un número válido",
    })
    .int("La cantidad de visitas debe ser un número entero")
    .positive("La cantidad de visitas debe ser positiva")
    .max(9999, "La cantidad de visitas excede el máximo permitido"),
  categoria: z.enum(["1", "2", "3", "4"], {
    message: "Categoría es requerida",
  }),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_visitas_id: z.string().min(1, "No se pudo cargar la tarifa vigente"),
  // Contacto (used in edit modal — not in creation form)
  contacto: contactoInlineSchema.optional(),
  // InspectorOperacion seleccionado para crear IO. El backend deriva el inspector desde esta operación.
  inspector_operacion_id: z.string().min(1, "Falta asignar al inspector"),
  // Inspector seleccionado, usado solo como estado visual del selector.
  inspector_id: z.string().optional(),
  /**
   * MODO DE COTIZACIÓN del motor IO ("NORMAL" | "CONTINUAR").
   *
   * Discriminador TIPADO (patrón PO/Edificaciones): lo consume el SmartField
   * de tarifas para decidir qué panel es el activo Y viaja al backend como
   * discriminador de la union de la cotización (`modo_cotizacion`). En
   * CONTINUAR viaja además el bloque `continuidad` con el bruto declarado.
   */
  modo_cotizacion: modoCotizacionIOSchema.optional(),
  // Continuidad OPCIONAL con la liquidación previa (bloque de "Continuar").
  continuidad: continuidadVisitasFormSchema.optional(),
});

export type VisitasFormData = z.infer<typeof visitasFormSchema>;

export const visitasLegacyFormSchema = withLegacyRegistroFields(
  visitasFormSchema.extend({
    inspector_id: z.string().min(1, "Falta asignar al inspector"),
    inspector_operacion_id: z.string().min(1, "Falta asignar al inspector"),
  }) as unknown as z.ZodType<VisitasFormData>,
);
