import { describe, expect, it } from "vitest";
import {
  RHReparticionEstacionalActualizarInSchema,
  RHReparticionEstacionalCotizarInSchema,
  RHReparticionEstacionalCrearInSchema,
  RHReparticionEstacionalDeleteSchema,
  RHReparticionEstacionalGeneralInSchema,
  RHReparticionEstacionalResponseSchema,
  RHReparticionEstacionalSchema,
} from "./rh-reparticion-estacional.schema";

const item = {
  identidad: {
    id: "6ee80f48-1219-4f7d-a14a-c126c963a329",
    created_at: "2026-10-30T10:00:00Z",
  },
  general: {
    especialidad_revision: {
      id: "0eec6392-5880-45f1-a6ef-d184ad31ce4e",
      nombre: "Ingeniería Civil",
    },
    periodo: 2026,
    mes_desde: 1,
    mes_hasta: 3,
  },
  distribucion: {
    total_fondo_comun: "1000.00",
    numero_capitulos: 1,
    numero_delegados: 1,
    monto_por_participacion: "500.00",
    residual: "0.00",
    detalles_delegados: [
      {
        delegado: {
          id: "61c2f970-a89e-4bd9-9ba7-2ae249fc96c2",
          cip: "123456",
          dni: "12345678",
          nombre_completo: "Delegado Ejemplo",
        },
        monto: "500.00",
      },
    ],
    detalles_capitulos: [
      {
        capitulo: {
          id: "c4789adf-510a-4a6f-9f8f-82f5a2ef236f",
          nombre: "Ingeniería Civil",
        },
        monto: "500.00",
      },
    ],
  },
};

describe("RHReparticionEstacionalSchema", () => {
  it("parses the composed list item with embedded distribution details", () => {
    const parsed = RHReparticionEstacionalSchema.parse(item);

    expect(parsed.distribucion.total_fondo_comun).toBe(1000);
    expect(parsed.distribucion.detalles_delegados[0]?.monto).toBe(500);
  });

  it("rejects the removed flat list shape", () => {
    expect(
      RHReparticionEstacionalSchema.safeParse({
        id: item.identidad.id,
        periodo: item.general.periodo,
        total_fondo_comun: 1000,
      }).success,
    ).toBe(false);
  });
});

const payload = {
  especialidad_revision_id: "0eec6392-5880-45f1-a6ef-d184ad31ce4e",
  periodo: 2026,
  mes_desde: 1,
  mes_hasta: 3,
  delegado_ids: ["61c2f970-a89e-4bd9-9ba7-2ae249fc96c2"],
};

describe("RH Reparticion Estacional — input schemas", () => {
  it("cotizar, crear y actualizar comparten el mismo bloque general", () => {
    expect(RHReparticionEstacionalCotizarInSchema).toBe(
      RHReparticionEstacionalGeneralInSchema,
    );
    expect(RHReparticionEstacionalCrearInSchema).toBe(
      RHReparticionEstacionalGeneralInSchema,
    );
    expect(RHReparticionEstacionalActualizarInSchema).toBe(
      RHReparticionEstacionalGeneralInSchema,
    );
  });

  it("acepta el payload de edición con el mismo bloque general", () => {
    const parsed = RHReparticionEstacionalActualizarInSchema.parse(payload);

    expect(parsed.especialidad_revision_id).toBe(
      "0eec6392-5880-45f1-a6ef-d184ad31ce4e",
    );
    expect(parsed.periodo).toBe(2026);
    expect(parsed.mes_desde).toBe(1);
    expect(parsed.mes_hasta).toBe(3);
    expect(parsed.delegado_ids).toHaveLength(1);
  });

  it("rechaza una edición sin delegados seleccionados", () => {
    expect(
      RHReparticionEstacionalActualizarInSchema.safeParse({
        ...payload,
        delegado_ids: [],
      }).success,
    ).toBe(false);
  });

  it("rechaza un rango de meses fuera de 1-12", () => {
    expect(
      RHReparticionEstacionalActualizarInSchema.safeParse({
        ...payload,
        mes_hasta: 13,
      }).success,
    ).toBe(false);
  });
});

describe("RH Reparticion Estacional — responses", () => {
  it("valida el envelope de un item compuesto (PATCH y listado)", () => {
    const parsed = RHReparticionEstacionalResponseSchema.parse({
      success: true,
      data: item,
      error: null,
      message: "Repartición estacional actualizada correctamente.",
    });

    expect(parsed.success).toBe(true);
    expect(parsed.data?.identidad.id).toBe(item.identidad.id);
  });

  it("el payload de borrado sólo lleva el id (el mensaje va en el envelope)", () => {
    const parsed = RHReparticionEstacionalDeleteSchema.parse({
      id: item.identidad.id,
    });

    expect(parsed.id).toBe(item.identidad.id);

    // El mensaje NO se duplica dentro del payload.
    const parsedWithExtra = RHReparticionEstacionalDeleteSchema.parse({
      id: item.identidad.id,
      message: "duplicado",
    });
    expect(Object.keys(parsedWithExtra)).toEqual(["id"]);
  });
});
