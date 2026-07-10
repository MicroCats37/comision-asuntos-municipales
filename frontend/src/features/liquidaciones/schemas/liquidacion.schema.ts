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

// Proyecto Inline para creación en línea (dentro de primera revisión)
export const proyectoInlineSchema = z.object({
  denominacion: z.string().min(1, "Denominación es requerida"),
  direccion: z.string().optional(),
  distrito_id: z.string().uuid("Distrito es requerido").optional(),
  entidad_id: z.string().uuid("Entidad es requerida").optional().nullable(),
});

// XOR: proyecto_public_id O proyecto_inline, nunca ambos ni ninguno
export const proyectoXorSchema = z
  .object({
    proyecto_public_id: z.string().optional(),
    proyecto_inline: proyectoInlineSchema.optional(),
  })
  .refine(
    (data) =>
      (data.proyecto_public_id && !data.proyecto_inline) ||
      (!data.proyecto_public_id && data.proyecto_inline),
    {
      message:
        "Debe proporcionar proyecto_public_id O proyecto_inline, nunca ambos",
    },
  );

export const primeraRevisionSchema = z.object({
  // XOR: uno de los dos es requerido
  proyecto_public_id: z.string().min(1, "Proyecto es requerido").optional(),
  proyecto_inline: proyectoInlineSchema.optional(),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z.number().positive("Valor debe ser positivo"),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()).default([]),
  proyectistas_ids: z.array(z.string()).default([]),
  // Tarifas: array de 1 UUID para esta fase
  tarifas_ids: z.array(z.string().uuid()).default([]),
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
export const paginatedLiquidacionesResponseSchema = apiResponseSchema(
  paginatedLiquidacionesPayloadSchema,
);

// ── Flat LiquidacionEdificacionOut Schemas (Phase 4+) ───────────────────────────

/** Especialidad anidada en revisión */
const especialidadOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

/** Tarifa anidada en revisión */
const tarifaOutSchema = z.object({
  id: z.string(),
  derecho_minimo: z.number().nullable(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number().nullable(),
  porcentaje_liquidacion: z.number(),
});

/** Revisión anidada en edificaciones */
const revisionOutSchema = z.object({
  id: z.string(),
  especialidades: z.array(especialidadOutSchema),
  tarifa: tarifaOutSchema,
});

/** Entidad anidada en proyecto */
const entidadOutSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});

/** Proyecto anidado en liquidación */
const proyectoOutSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  nombre: z.string(),
  direccion: z.string().nullable(),
  valor_proyecto: z.union([z.number(), z.string()]),
  entidad: entidadOutSchema.nullable(),
});

/** Provincia básica anidada */
const provinciaBasicOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

/** Distrito básico anidado */
const distritoBasicOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  provincia: provinciaBasicOutSchema.nullable(),
});

/** Municipalidad anidada */
const municipalidadOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: provinciaBasicOutSchema.nullable(),
  distrito: distritoBasicOutSchema.nullable(),
});

/** Valores financieros anidados */
const valoresOutSchema = z.object({
  subtotal: z.union([z.number(), z.string()]),
  igv: z.union([z.number(), z.string()]),
  total: z.union([z.number(), z.string()]),
  total_a_pagar: z.union([z.number(), z.string()]),
});

/** Proyectista anidado en edificaciones */
const proyectistaOutSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  descripcion: z.string().nullable(),
});

/** Delegado anidado en edificaciones */
const delegadoOutSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  tipo: z.string().nullable(),
});

/** Contacto anidado en edificaciones */
const contactoOutSchema = z.object({
  id: z.string(),
  nombres: z.string().nullable(),
  apellidos: z.string().nullable(),
  dni: z.string().nullable(),
  cargo: z.string().nullable(),
  telefono: z.string().nullable(),
  celular: z.string().nullable(),
  email: z.string().nullable(),
  direccion: z.string().nullable(),
  principal: z.boolean(),
  descripcion: z.string().nullable(),
});

/**
 * Payload schema para respuesta de creación/detalle de LiquidacionEdificacionOut.
 * Estructura PLANA con objetos anidados (proyecto, municipalidad, valores, etc.)
 * que coincide con el backend LiquidacionEdificacionOut.
 */
export const liquidacionEdificacionOutPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  fecha_registro: z.string(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  numero_revision: z.number(),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  tramite_accion: tramiteAccionSchema,
  proyecto: proyectoOutSchema,
  entidad: entidadOutSchema.nullable(),
  municipalidad: municipalidadOutSchema,
  valores: valoresOutSchema,
  proyectistas: z.array(proyectistaOutSchema),
  delegados: z.array(delegadoOutSchema),
  contactos: z.array(contactoOutSchema),
  revisiones: z.array(revisionOutSchema),
  // Campos financieros directos (duplicados de valores para conveniencia)
  subtotal: z.union([z.number(), z.string()]),
  igv: z.union([z.number(), z.string()]),
  total: z.union([z.number(), z.string()]),
  total_a_pagar: z.union([z.number(), z.string()]),
});

/** Wrapper schema para respuesta de creación/detalle (ApiResponse[LiquidacionEdificacionOut]) */
export const liquidacionEdificacionOutResponseSchema = apiResponseSchema(
  liquidacionEdificacionOutPayloadSchema,
);

/**
 * @deprecated Usar liquidacionEdificacionOutPayloadSchema y liquidacionEdificacionOutResponseSchema.
 * Este schema espera la estructura antigua { data: { liquidacion, edificaciones, totales } }.
 */
const liquidacionSnapshotPayloadSchema = z.object({
  liquidacion: z.object({
    id: z.string(),
    public_id: z.string(),
    estado: z.string(),
    fecha_creacion: z.string(),
    expediente: z.string().nullable(),
    observacion: z.string().nullable(),
    proyecto: z.object({
      id: z.string(),
      public_id: z.string(),
      nombre: z.string(),
      direccion: z.string().nullable(),
      valor_proyecto: z.union([z.number(), z.string()]),
      entidad: z
        .object({
          id: z.string().nullable(),
          tipo: z.string().nullable(),
          nombre: z.string().nullable(),
          ruc: z.string().nullable(),
        })
        .nullable(),
    }),
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
  }),
  edificaciones: z.object({
    public_id: z.string(),
    numero_revision: z.number(),
    tipo_tramite: tipoTramiteEdificacionesSchema,
    tramite_accion: tramiteAccionSchema,
    proyectistas: z.array(
      z.object({
        id: z.string(),
        perfil_ingeniero_id: z.string(),
        perfil_ingeniero_nombres: z.string(),
        perfil_ingeniero_apellidos: z.string(),
        perfil_ingeniero_cip: z.string(),
        especialidad_id: z.string(),
        especialidad_nombre: z.string(),
        descripcion: z.string().nullable(),
      }),
    ),
    delegados: z.array(
      z.object({
        id: z.string(),
        perfil_ingeniero_id: z.string(),
        perfil_ingeniero_nombres: z.string(),
        perfil_ingeniero_apellidos: z.string(),
        perfil_ingeniero_cip: z.string(),
        especialidad_id: z.string(),
        especialidad_nombre: z.string(),
        tipo: z.string().nullable(),
      }),
    ),
    revisiones: z.array(
      z.object({
        id: z.string(),
        // NOTE: Updated to especialidades (plural list) instead of especialidad singular
        especialidades: z.array(
          z.object({
            id: z.string(),
            nombre: z.string(),
          }),
        ),
        tarifa: z.object({
          id: z.string(),
        }),
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
});

/**
 * @deprecated Usar liquidacionEdificacionOutResponseSchema.
 */
export const liquidacionSnapshotResponseSchema = apiResponseSchema(
  liquidacionSnapshotPayloadSchema,
);

/** Wrapper schema for crear primera revision request payload */
export const crearPrimeraRevisionPayloadSchema = z.object({
  liquidacion: primeraRevisionSchema,
});

// ── Flat List Schemas (Phase 4+) ───────────────────────────────────────────────────

/**
 * Schema para lista paginada de edificaciones.
 * El backend retorna el objeto completo LiquidacionEdificacionOut en cada item
 * (no un LiquidacionEdificacionesListItemOut aplanado).
 * Estructura: ApiResponse { success, data: { items: LiquidacionEdificacionOut[], total, page, page_size, total_pages }, error }
 */
export const liquidacionesEdificacionPaginatedResponseSchema = apiResponseSchema(
  z.object({
    items: z.array(liquidacionEdificacionOutPayloadSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
  }),
);

/**
 * @deprecated Usar liquidacionEdificacionesListResponseSchema.
 * Este schema espera la estructura antigua con objetos anidados en cada item.
 */
const liquidacionSnapshotListPayloadSchema = z.object({
  items: z.array(
    z.object({
      liquidacion_id: z.string(),
      public_id: z.string(),
      numero_liquidacion: z.string(),
      estado: z.string(),
      fecha_registro: z.string(),
      municipalidad: z.object({
        id: z.string().nullable(),
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
        valor_proyecto: z.union([z.number(), z.string()]),
        entidad: z
          .object({
            id: z.string().nullable(),
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
        tipo_tramite: tipoTramiteEdificacionesSchema.optional(),
        tramite_accion: tramiteAccionSchema.optional(),
        proyectistas: z.array(
          z.object({
            id: z.string(),
            perfil_ingeniero_id: z.string().nullable(),
            perfil_ingeniero_nombres: z.string().nullable(),
            perfil_ingeniero_apellidos: z.string().nullable(),
            perfil_ingeniero_cip: z.string().nullable(),
            especialidad_id: z.string().nullable(),
            especialidad_nombre: z.string().nullable(),
            descripcion: z.string().nullable(),
          }),
        ),
        delegados: z.array(z.unknown()).default([]),
        revisiones: z.array(
          z.object({
            id: z.string(),
            especialidades: z.array(
              z.object({
                id: z.string(),
                nombre: z.string(),
              }),
            ),
            tarifa: z.object({
              id: z.string(),
            }),
          }),
        ),
      }),
      totales: z.object({
        subtotal: z.union([z.number(), z.string()]),
        sub_total: z.union([z.number(), z.string()]).optional(),
        igv: z.union([z.number(), z.string()]),
        total: z.union([z.number(), z.string()]),
        liquidacion_total: z.union([z.number(), z.string()]),
        total_a_pagar: z.union([z.number(), z.string()]),
      }),
    }),
  ),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/**
 * @deprecated Usar liquidacionEdificacionesListResponseSchema.
 */
export const liquidacionSnapshotListResponseSchema = apiResponseSchema(
  liquidacionSnapshotListPayloadSchema,
);

// ── Cotización / Quote Schemas ──────────────────────────────────────────────────

/** Schema for cotizacion quote response payload */
const cotizacionQuotePayloadSchema = z.object({
  numero_revision: z.number(),
  revisiones: z.array(
    z.object({
      id: z.string(),
      especialidades: z.array(
        z.object({
          id: z.string(),
          nombre: z.string(),
        }),
      ),
      tarifa: z.object({
        id: z.string(),
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
    valor_base_calculo: z.number(),
  }),
});

/** Wrapper schema for cotizacion quote response */
export const cotizacionQuoteResponseSchema = apiResponseSchema(
  cotizacionQuotePayloadSchema,
);

/** Schema for cotizar primera revision request payload */
export const cotizacionPrimeraRevisionPayloadSchema = z.object({
  tipo_tramite: z.string().optional(),
  valor_proyecto: z.number().positive("Valor debe ser positivo"),
  valor_base_calculo: z
    .number()
    .positive("Valor base de cálculo debe ser positivo"),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar exactamente una tarifa"),
});

/** Wrapper schema for cotizar primera revision request */
export const cotizacionPrimeraRevisionRequestSchema = z.object({
  liquidacion: cotizacionPrimeraRevisionPayloadSchema,
});

/** Schema for cotizar nueva revision request payload */
export const cotizacionNuevaRevisionPayloadSchema = z.object({
  liquidacion_previa_id: z.string().uuid("Liquidación previa es requerida"),
  revisiones_ids: z
    .array(z.string().uuid())
    .min(1, "Debe seleccionar al menos una revisión"),
});

/** Wrapper schema for cotizar nueva revision request */
export const cotizacionNuevaRevisionRequestSchema =
  cotizacionNuevaRevisionPayloadSchema;

// ── Nueva Revisión Schemas ─────────────────────────────────────────────────────

/** Schema for revision vigente item embedded in formulario response */
const revisionVigenteFormularioSchema = z.object({
  id: z.string(),
  especialidades: z.array(
    z.object({
      id: z.string(),
      nombre: z.string(),
    }),
  ),
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
  perfil_ingeniero_id: z.string().nullable().optional(),
  perfil_ingeniero_nombres: z.string().nullable().optional(),
  perfil_ingeniero_apellidos: z.string().nullable().optional(),
  perfil_ingeniero_cip: z.string().nullable().optional(),
  especialidad_id: z.string().nullable().optional(),
  especialidad_nombre: z.string().nullable().optional(),
  descripcion: z.string().nullable().optional(),
  // legacy fallback fields
  cip: z.string().nullable().optional(),
  dni: z.string().optional(),
  cap: z.string().nullable().optional(),
  nombres: z.string().optional(),
  apellidos: z.string().optional(),
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
  tipo_tramite: z.string(),
});

/** Wrapper schema for nueva revision formulario response */
export const nuevaRevisionFormularioResponseSchema = apiResponseSchema(
  nuevaRevisionFormularioPayloadSchema,
);

/** Schema for crear nueva revision request payload */
export const crearNuevaRevisionPayloadSchema = z.object({
  liquidacion_previa_id: z.string().uuid("Liquidación previa es requerida"),
  revisiones_ids: z
    .array(z.string().uuid())
    .min(1, "Debe seleccionar al menos una revisión"),
  proyectistas_ids: z.array(z.string().uuid()).default([]),
  observacion: z.string().optional(),
});

/** Wrapper schema for crear nueva revision request */
export const crearNuevaRevisionRequestSchema = z.object({
  liquidacion: crearNuevaRevisionPayloadSchema,
});
