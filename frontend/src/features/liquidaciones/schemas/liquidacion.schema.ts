/**
 * Zod schemas para formulario de liquidaciones.
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const tipoTramiteEdificacionesSchema = z.enum([
  "OBRA_NUEVA",
  "DEMOLICION",
  "AMPLIACION",
  "REMODELACION",
  "MODIFICACION_LICENCIA",
  "REINTEGRO",
  "PROYECTO_CON_PLANTAS_TIPICAS",
]);

export const tramiteAccionSchema = z.enum(["PRIMERA_REVISION", "REVISION"]);

// ── Inner Schemas (data fields only) ────────────────────────────────────────

export const primeraRevisionSchema = z.object({
  proyecto_public_id: z.string().min(1, "Proyecto es requerido"),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z.number().positive("Valor debe ser positivo"),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()).default([]),
  proyectistas_ids: z.array(z.string()).default([]),
});

export type PrimeraRevisionSchema = z.infer<typeof primeraRevisionSchema>;

// ── API Response Wrapper Schemas (match backend ApiResponse[T]) ──────────────

/** Data payload for paginated liquidaciones list response */
const paginatedLiquidacionesPayloadSchema = z.object({
  items: z.array(
    z.object({
      id: z.string(),
      public_id: z.string().optional(),
      numero_revision: z.number(),
      estado: z.string(),
      municipalidad_id: z.string().nullable().optional(),
      municipalidad_nombre: z.string().nullable().optional(),
      tipo_tramite: tipoTramiteEdificacionesSchema.optional(),
      tramite_accion: tramiteAccionSchema.optional(),
      valor_proyecto: z.number(),
      proyecto_public_id: z.string(),
      proyecto_denominacion: z.string(),
      fecha_registro: z.string(),
      total: z.number(),
    }),
  ),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper schema for paginated liquidaciones list response */
export const paginatedLiquidacionesResponseSchema = apiResponseSchema(paginatedLiquidacionesPayloadSchema);

/** Data payload for liquidacion snapshot response */
const liquidacionSnapshotPayloadSchema = z.object({
  liquidacion: z.object({
    id: z.string(),
    public_id: z.string(),
    estado: z.string(),
    fecha_creacion: z.string(),
    proyecto: z.object({
      id: z.string(),
      public_id: z.string(),
      nombre: z.string(),
      direccion: z.string(),
      valor_proyecto: z.union([z.number(), z.string()]),
      entidad: z
        .object({
          id: z.string().nullable(),
          tipo: z.string().nullable(),
          nombre: z.string().nullable(),
          ruc: z.string().nullable(),
        })
        .nullable(),
      // NOTE: distrito not present in backend ProyectoOut for crearNuevaRevision
    }),
    municipalidad: z.object({
      id: z.string(),
      nombre: z.string(),
      codigo: z.string().nullable(),
      // NOTE: backend presenter sets provincia=None and distrito=None explicitly
      provincia: z
        .object({
          id: z.string(),
          nombre: z.string(),
        })
        .nullable(),
      distrito: z
        .object({
          id: z.string(),
          nombre: z.string(),
          provincia: z
            .object({
              id: z.string(),
              nombre: z.string(),
            })
            .nullable(),
        })
        .nullable(),
    }),
    observacion: z.string(),
  }),
  edificaciones: z.object({
    public_id: z.string(),
    numero_revision: z.number(),
    tipo_tramite: tipoTramiteEdificacionesSchema,
    tramite_accion: tramiteAccionSchema,
    proyectistas: z.array(
      z.object({
        id: z.string(),
        cip: z.string().nullable(),
dni: z.string().nullable(),
        cap: z.string().nullable(),
        nombres: z.string(),
        apellidos: z.string(),
      }),
    ),
    revisiones: z.array(
      z.object({
        id: z.string(),
        // numero_revision fue removido de cada revisión — solo existe en nivel edificaciones
        especialidad: z.string(),
        tarifa: z.object({
          id: z.string(),
          derecho_minimo: z.union([z.string(), z.number()]),
          derecho_maximo: z.union([z.string(), z.number(), z.null()]),
          porcentaje_minimo_uit: z.union([z.string(), z.number()]),
        }),
        monto_base: z.union([z.number(), z.string()]),
        cobra: z.boolean(),
        // NOTE: derecho not present in backend RevisionOut for crearNuevaRevision
      }),
    ),
  }),
  totales: z.object({
    subtotal: z.union([z.number(), z.string()]),
    igv: z.union([z.number(), z.string()]),
    total: z.union([z.number(), z.string()]),
    liquidacion_total: z.union([z.number(), z.string()]),
    total_a_pagar: z.union([z.number(), z.string()]),
  }),
  // NOTE: _metadata not present in backend LiquidacionSnapshotOut for crearNuevaRevision
});

/** Wrapper schema for liquidacion snapshot response */
export const liquidacionSnapshotResponseSchema = apiResponseSchema(liquidacionSnapshotPayloadSchema);

/** Wrapper schema for crear primera revision request payload */
export const crearPrimeraRevisionPayloadSchema = z.object({
  liquidacion: primeraRevisionSchema,
});

// ── Snapshot List Schemas ──────────────────────────────────────────────────────

/** Schema for paginated snapshot list response */
const liquidacionSnapshotListPayloadSchema = z.object({
  items: z.array(
    z.object({
      liquidacion_id: z.string(),
      public_id: z.string(),
      numero_liquidacion: z.string(),
      estado: z.string(),
      fecha_registro: z.string(),
      municipalidad: z.object({
        id: z.string(),
        nombre: z.string(),
        codigo: z.string().nullable(),
        provincia: z
          .object({
            id: z.string(),
            nombre: z.string(),
          })
          .nullable(),
        distrito: z
          .object({
            id: z.string(),
            nombre: z.string(),
            provincia: z
              .object({
                id: z.string(),
                nombre: z.string(),
              })
              .nullable(),
          })
          .nullable(),
      }),
      observacion: z.string().nullable(),
      proyecto: z.object({
        id: z.string(),
        public_id: z.string(),
        nombre: z.string(),
        direccion: z.string().nullable(),
        valor_proyecto: z.number(),
        entidad: z
          .object({
            id: z.string(),
            tipo: z.string().nullable(),
            nombre: z.string().nullable(),
            ruc: z.string().nullable(),
          })
          .nullable(),
        distrito: z
          .object({
            id: z.string(),
            nombre: z.string(),
            provincia: z
              .object({
                id: z.string(),
                nombre: z.string(),
              })
              .nullable(),
          })
          .nullable()
          .nullish(),
      }),
      edificaciones: z.object({
        public_id: z.string(),
        numero_revision: z.number(),
        tipo_tramite: tipoTramiteEdificacionesSchema,
        tramite_accion: tramiteAccionSchema,
        proyectistas: z.array(
          z.object({
            id: z.string(),
            cip: z.string().nullable(),
            dni: z.string().nullable(),
            cap: z.string().nullable(),
            nombres: z.string(),
            apellidos: z.string(),
          }),
        ),
        revisiones: z.array(
          z.object({
            id: z.string(),
            // numero_revision fue removido de cada revisión — solo existe en nivel edificaciones
            especialidad: z.string(),
            tarifa: z.object({
              id: z.string(),
              derecho_minimo: z.number(),
              derecho_maximo: z.number().nullable(),
              porcentaje_minimo_uit: z.number(),
            }),
            monto_base: z.number(),
            cobra: z.boolean(),
            derecho: z.number().nullish(),
          }),
        ),
      }),
      totales: z.object({
        subtotal: z.number(),
        igv: z.number(),
        total: z.number(),
        liquidacion_total: z.number(),
        total_a_pagar: z.number(),
      }),
    }),
  ),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper schema for snapshot list response */
export const liquidacionSnapshotListResponseSchema = apiResponseSchema(liquidacionSnapshotListPayloadSchema);

// ── Cotización / Quote Schemas ──────────────────────────────────────────────────

/** Schema for cotizacion quote response payload */
const cotizacionQuotePayloadSchema = z.object({
  numero_revision: z.number(),
  revisiones: z.array(
    z.object({
      id: z.string(),
      especialidad: z.string(),
      tarifa: z.object({
        id: z.string(),
        derecho_minimo: z.number(),
        derecho_maximo: z.number().nullable(),
        porcentaje_minimo_uit: z.number(),
      }),
      monto_base: z.number(),
      cobra: z.boolean(),
    }),
  ),
  totales: z.object({
    subtotal: z.number(),
    igv: z.number(),
    total: z.number(),
    liquidacion_total: z.number(),
    total_a_pagar: z.number(),
  }),
  _metadata: z.object({
    igv_valor: z.number(),
    uit_valor: z.number(),
    cobra: z.boolean(),
  }),
});

/** Wrapper schema for cotizacion quote response */
export const cotizacionQuoteResponseSchema = apiResponseSchema(cotizacionQuotePayloadSchema);

/** Schema for cotizar primera revision request payload */
export const cotizacionPrimeraRevisionPayloadSchema = z.object({
  proyecto_public_id: z.string().min(1, "Proyecto es requerido"),
  valor_proyecto: z.number().positive("Valor debe ser positivo"),
  valor_base_calculo: z.number().positive("Valor base de cálculo debe ser positivo"),
});

/** Wrapper schema for cotizar primera revision request */
export const cotizacionPrimeraRevisionRequestSchema = z.object({
  liquidacion: cotizacionPrimeraRevisionPayloadSchema,
});

/** Schema for cotizar nueva revision request payload */
export const cotizacionNuevaRevisionPayloadSchema = z.object({
  liquidacion_previa_id: z.string().uuid("Liquidación previa es requerida"),
  revisiones_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una revisión"),
});

/** Wrapper schema for cotizar nueva revision request */
export const cotizacionNuevaRevisionRequestSchema = cotizacionNuevaRevisionPayloadSchema;

// ── Nueva Revisión Schemas ─────────────────────────────────────────────────────

/** Schema for revision vigente item embedded in formulario response */
const revisionVigenteFormularioSchema = z.object({
  id: z.string(),
  especialidades: z.array(z.object({
    id: z.string(),
    nombre: z.string(),
  })),
  tarifa_id: z.string(),
  porcentaje_liquidacion: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number(),
  habilitada: z.boolean(),
});

/** Schema for proyectista actual item in formulario response */
const proyectistaActualSchema = z.object({
  id: z.string(),
  cip: z.string().nullable(),
  dni: z.string(),
  cap: z.string().nullable(),
  nombres: z.string(),
  apellidos: z.string(),
});

/** Payload schema for GET /nueva-revision/formulario response */
const nuevaRevisionFormularioPayloadSchema = z.object({
  liquidacion_previa_id: z.string().uuid(),
  numero_revision: z.number(),
  cobra: z.boolean(),
  proyecto_id: z.string().uuid(),
  proyecto_public_id: z.string(),
  proyecto_nombre: z.string(),
  valor_proyecto: z.number(),
  valor_base_calculo: z.number(),
  revisiones_vigentes: z.array(revisionVigenteFormularioSchema),
  proyectistas_actuales: z.array(proyectistaActualSchema),
});

/** Wrapper schema for nueva revision formulario response */
export const nuevaRevisionFormularioResponseSchema = apiResponseSchema(nuevaRevisionFormularioPayloadSchema);

/** Schema for crear nueva revision request payload */
export const crearNuevaRevisionPayloadSchema = z.object({
  liquidacion_previa_id: z.string().uuid("Liquidación previa es requerida"),
  revisiones_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una revisión"),
  proyectistas_ids: z.array(z.string().uuid()).default([]),
  observacion: z.string().optional(),
});

/** Wrapper schema for crear nueva revision request */
export const crearNuevaRevisionRequestSchema = z.object({
  liquidacion: crearNuevaRevisionPayloadSchema,
});
