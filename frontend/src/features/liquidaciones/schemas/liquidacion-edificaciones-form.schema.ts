/**
 * Zod schema for Edificaciones creation/edit form.
 * General fields (proyecto, trámite, contacto) vienen del base compartido.
 *
 * El motor PorcentajeObra de Edificaciones tiene TRES estrategias de
 * cotización (union discriminada). El dato del motor depende de la estrategia
 * activa:
 *   - NORMAL_SELECCIONADAS / TARIFA_HABILITADAS_PARTICIPANTES → valor
 *     declarado del proyecto.
 *   - TOTAL_EXPLICITO → valor informativo de la obra y total final autoritativo.
 *
 * La validación por estrategia vive en `superRefine` porque `total_explicito`
 * sólo es obligatorio en TOTAL_EXPLICITO.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  numeroRevisionFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";
import {
  ESTRATEGIA_NORMAL,
  ESTRATEGIAS_COTIZACION_PO,
  MENSAJE_TOTAL_EXPLICITO_NUMERO,
  MENSAJE_VALOR_DECLARADO_NUMERO,
  validarDatosDeEstrategia,
} from "./liquidacion-po-estrategia.schema";
import { TipoTramiteEdificacionesSchema } from "./tramite.schema";

export const edificacionesFormSchema = z
  .object({
    ...proyectoFormSchema.shape,
    ...generalFormSchema.shape,
    // Número de revisión — etiqueta editable (1, 3 o 5)
    ...numeroRevisionFormSchema.shape,
    // ── Estrategia de cotización (union discriminada SOLO de Edificaciones) ──
    estrategia_cotizacion: z
      .enum(ESTRATEGIAS_COTIZACION_PO, {
        error: "Selecciona una estrategia de cotización",
      })
      .default(ESTRATEGIA_NORMAL),
    // Especifica fields (motor PorcentajeObra)
    /** Valor declarado del proyecto — exigido por las tres estrategias. */
    valor_declarado: z
      .number({
        error: (issue) =>
          issue.input === undefined || issue.input === null || issue.input === ""
            ? "El valor declarado es requerido"
            : MENSAJE_VALOR_DECLARADO_NUMERO,
      })
      .finite(MENSAJE_VALOR_DECLARADO_NUMERO)
      .optional(),
    /** Total final con IGV — exigido por TOTAL_EXPLICITO. */
    total_explicito: z
      .number({
        error: (issue) =>
          issue.input === undefined || issue.input === null || issue.input === ""
            ? "El total final es requerido"
            : MENSAJE_TOTAL_EXPLICITO_NUMERO,
      })
      .finite(MENSAJE_TOTAL_EXPLICITO_NUMERO)
      .optional(),
    /** Tipo de trámite de edificaciones — requerido. El smart field de tarifas
     *  muestra un mensaje informativo hasta que se setee. */
    tipo_tramite: TipoTramiteEdificacionesSchema,
    // Smart Field outputs — set by Smart Fields via setValue
    /** ID de la única tarifa vigente de porcentaje de obra */
    tarifa_unica_id: z.string().min(1, "No se pudo cargar la tarifa vigente"),
    /** IDs de especialidades seleccionadas por el usuario — al menos una */
    especialidades_seleccionadas: z
      .array(z.string())
      .min(1, "Selecciona al menos una especialidad")
      .optional(),
    // Contacto principal (singular, managed via ContactoFormModal)
    contacto: contactoInlineSchema.optional(),
  })
  .superRefine((data, ctx) => {
    const estrategia = data.estrategia_cotizacion ?? ESTRATEGIA_NORMAL;
    for (const issue of validarDatosDeEstrategia(estrategia, data)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: issue.message,
        path: [issue.path],
      });
    }
  });

export type EdificacionesFormData = z.infer<typeof edificacionesFormSchema>;
