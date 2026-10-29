/**
 * Payload de Edificaciones con estrategias de cotización: create, edit,
 * nueva revisión y relacionada.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para el Módulo 8 de la verificación final.
 */
import { describe, expect, it } from "vitest";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import {
  ESTRATEGIA_HABILITADAS,
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
} from "../schemas/liquidacion-po-estrategia.schema";
import { buildPOTipoPayload } from "../schemas/liquidacion-po-edit.schema";
import { buildCrearEdificacionesPayload } from "./useCrearEdificaciones";
import { buildCrearNuevaRevisionEdificacionesPayload } from "./useCrearNuevaRevisionEdificaciones";
import { buildCrearRelacionadaEdificacionesPayload } from "./useCrearRelacionadaEdificaciones";

const BASE_FORM = {
  denominacion: "OBRA NUEVA",
  nombre_propietario: "Propietario",
  direccion: "Av. Siempre Viva 742",
  distrito_id: "distrito-1",
  entidad_tipo_documento: "RUC",
  entidad_numero_documento: "20509876543",
  entidad_razon_social: "EMPRESA SAC",
  municipalidad_id: "mun-1",
  expediente: "EXP-1",
  observacion: "",
  numero_revision: 1,
  estrategia_cotizacion: ESTRATEGIA_NORMAL,
  valor_declarado: 1000000,
  total_explicito: undefined,
  tipo_tramite: "OBRA_NUEVA",
  tarifa_unica_id: "tarifa-1",
  especialidades_seleccionadas: ["esp-1"],
};

const formData = (
  overrides: Partial<EdificacionesFormData> = {},
): EdificacionesFormData =>
  ({ ...BASE_FORM, ...overrides }) as unknown as EdificacionesFormData;

const TARIFAS_ESPERADAS = [
  { tarifa_porcentaje_obra_id: "tarifa-1", especialidad_id: "esp-1" },
];

describe("create — union discriminada de estrategias", () => {
  it("NORMAL_SELECCIONADAS envía el valor declarado y el discriminador", () => {
    const payload = buildCrearEdificacionesPayload(formData());

    expect(payload.liquidacion_especifica.estrategia_cotizacion).toBe(
      ESTRATEGIA_NORMAL,
    );
    expect(payload.liquidacion_especifica.datos).toEqual({
      valor_declarado: 1000000,
    });
    expect(payload.liquidacion_especifica.tipo_tramite).toBe("OBRA_NUEVA");
    expect(payload.liquidacion_especifica.tarifas).toEqual(TARIFAS_ESPERADAS);
  });

  it("TARIFA_HABILITADAS_PARTICIPANTES envía el valor declarado", () => {
    const payload = buildCrearEdificacionesPayload(
      formData({ estrategia_cotizacion: ESTRATEGIA_HABILITADAS }),
    );

    expect(payload.liquidacion_especifica.estrategia_cotizacion).toBe(
      ESTRATEGIA_HABILITADAS,
    );
    expect(payload.liquidacion_especifica.datos).toEqual({
      valor_declarado: 1000000,
    });
  });

  it("TOTAL_EXPLICITO envía el valor informativo y el total final", () => {
    const payload = buildCrearEdificacionesPayload(
      formData({
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
        valor_declarado: 1000000,
        total_explicito: 177,
      }),
    );

    expect(payload.liquidacion_especifica.estrategia_cotizacion).toBe(
      ESTRATEGIA_TOTAL,
    );
    expect(payload.liquidacion_especifica.datos).toEqual({
      valor_declarado: 1000000,
      total_explicito: 177,
    });
  });

  it("no filtra los datos de estrategia en liquidacion_general", () => {
    const payload = buildCrearEdificacionesPayload(
      formData({
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
        valor_declarado: 1000000,
        total_explicito: 177,
      }),
    );

    expect(payload.liquidacion_general).not.toHaveProperty(
      "estrategia_cotizacion",
    );
    expect(payload.liquidacion_general).not.toHaveProperty("valor_declarado");
    expect(payload.liquidacion_general).not.toHaveProperty("total_explicito");
  });
});

describe("edit — PATCH con estrategia y dato propio", () => {
  it("NORMAL_SELECCIONADAS transiciona con el valor declarado", () => {
    const tipo = buildPOTipoPayload(formData());

    expect(tipo.estrategia_cotizacion).toBe(ESTRATEGIA_NORMAL);
    expect(tipo.datos).toEqual({ valor_declarado: 1000000 });
    expect(tipo.tipo_tramite).toBe("OBRA_NUEVA");
    expect(tipo.tarifas).toEqual(TARIFAS_ESPERADAS);
  });

  it("TOTAL_EXPLICITO transiciona con el valor informativo y total final", () => {
    const tipo = buildPOTipoPayload(
      formData({
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
        valor_declarado: 1000000,
        total_explicito: 177,
      }),
    );

    expect(tipo.estrategia_cotizacion).toBe(ESTRATEGIA_TOTAL);
    expect(tipo.datos).toEqual({
      valor_declarado: 1000000,
      total_explicito: 177,
    });
  });

  it("los motores sin estrategia (Taludes / Impacto Vial) no envían estrategia", () => {
    const tipo = buildPOTipoPayload({
      valor_declarado: 1000000,
      tarifa_unica_id: "tarifa-1",
      especialidades_seleccionadas: ["esp-1"],
    } as unknown as Parameters<typeof buildPOTipoPayload>[0]);

    expect(tipo.estrategia_cotizacion).toBeUndefined();
    expect(tipo.datos).toEqual({ valor_declarado: 1000000 });
    expect(tipo.datos).not.toHaveProperty("total_explicito");
  });
});

describe("paridad create / edit — los datos coinciden", () => {
  it("NORMAL_SELECCIONADAS: el `datos` es idéntico en create y edit", () => {
    const create = buildCrearEdificacionesPayload(formData());
    const edit = buildPOTipoPayload(formData());

    expect(create.liquidacion_especifica.datos).toEqual(edit.datos);
    expect(create.liquidacion_especifica.estrategia_cotizacion).toBe(
      edit.estrategia_cotizacion,
    );
  });

  it("TOTAL_EXPLICITO: el `datos` es idéntico en create y edit", () => {
    const data = formData({
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      valor_declarado: 1000000,
      total_explicito: 177,
    });
    const create = buildCrearEdificacionesPayload(data);
    const edit = buildPOTipoPayload(data);

    expect(create.liquidacion_especifica.datos).toEqual(edit.datos);
  });
});

describe("nueva revisión y relacionada — heredan la estrategia", () => {
  it("la nueva revisión envía la estrategia y su dato propio", () => {
    const payload = buildCrearNuevaRevisionEdificacionesPayload(
      formData(),
      "previa-1",
    );

    expect(payload.liquidacion_previa_id).toBe("previa-1");
    expect(payload.liquidacion_especifica.estrategia_cotizacion).toBe(
      ESTRATEGIA_NORMAL,
    );
    expect(payload.liquidacion_especifica.datos).toEqual({
      valor_declarado: 1000000,
    });
  });

  it("la nueva revisión TOTAL_EXPLICITO envía ambos valores", () => {
    const payload = buildCrearNuevaRevisionEdificacionesPayload(
      formData({
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
        valor_declarado: 1000000,
        total_explicito: 177,
      }),
      "previa-1",
    );

    expect(payload.liquidacion_especifica.estrategia_cotizacion).toBe(
      ESTRATEGIA_TOTAL,
    );
    expect(payload.liquidacion_especifica.datos).toEqual({
      valor_declarado: 1000000,
      total_explicito: 177,
    });
  });

  it("la relacionada envía la union discriminada", () => {
    const payload = buildCrearRelacionadaEdificacionesPayload(
      formData({
        estrategia_cotizacion: ESTRATEGIA_TOTAL,
        valor_declarado: 1000000,
        total_explicito: 177,
      }),
      "previa-1",
    );

    expect(payload.liquidacion_especifica.estrategia_cotizacion).toBe(
      ESTRATEGIA_TOTAL,
    );
    expect(payload.liquidacion_especifica.datos).toEqual({
      valor_declarado: 1000000,
      total_explicito: 177,
    });
    expect(payload.liquidacion_especifica.tarifas).toEqual(TARIFAS_ESPERADAS);
  });
});
