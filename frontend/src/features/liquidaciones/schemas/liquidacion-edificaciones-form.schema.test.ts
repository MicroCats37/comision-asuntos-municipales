/**
 * Schema del formulario de Edificaciones con estrategias de cotización.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecución de
 * la suite queda reservada para el Módulo 8 de la verificación final.
 */
import { describe, expect, it } from "vitest";
import { edificacionesFormSchema } from "./liquidacion-edificaciones-form.schema";
import {
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
} from "./liquidacion-po-estrategia.schema";

const BASE = {
  nombre_propietario: "Propietario",
  direccion: "Av. Siempre Viva 742",
  entidad_tipo_documento: "RUC",
  entidad_numero_documento: "20509876543",
  entidad_razon_social: "EMPRESA SAC",
  municipalidad_id: "mun-1",
  numero_revision: 1,
  tipo_tramite: "OBRA_NUEVA",
  tarifa_unica_id: "tarifa-1",
  especialidades_seleccionadas: ["esp-1"],
  estrategia_cotizacion: ESTRATEGIA_NORMAL,
  valor_declarado: 1000000,
};

const mensajesDe = (
  resultado: ReturnType<typeof edificacionesFormSchema.safeParse>,
) =>
  resultado.error?.issues.map((issue) => ({
    message: issue.message,
    path: issue.path.join("."),
  })) ?? [];

describe("formulario de Edificaciones — estrategia por defecto", () => {
  it("materializa NORMAL_SELECCIONADAS cuando no viene la estrategia", () => {
    const { estrategia_cotizacion: _omit, ...sinEstrategia } = BASE;
    const resultado = edificacionesFormSchema.safeParse(sinEstrategia);

    expect(resultado.success).toBe(true);
    if (resultado.success) {
      expect(resultado.data.estrategia_cotizacion).toBe(ESTRATEGIA_NORMAL);
    }
  });

  it("mantiene el contrato de número de revisión (shape accesible)", () => {
    expect(edificacionesFormSchema.shape).toHaveProperty("numero_revision");
  });
});

describe("formulario de Edificaciones — dato exigido por la estrategia", () => {
  it("NORMAL_SELECCIONADAS exige el valor declarado", () => {
    const { valor_declarado: _omit, ...sinValor } = BASE;
    const resultado = edificacionesFormSchema.safeParse(sinValor);

    expect(resultado.success).toBe(false);
    expect(mensajesDe(resultado)).toContainEqual({
      message: "El valor declarado es requerido",
      path: "valor_declarado",
    });
  });

  it("NORMAL_SELECCIONADAS rechaza el valor declarado no positivo", () => {
    const resultado = edificacionesFormSchema.safeParse({
      ...BASE,
      valor_declarado: 0,
    });

    expect(resultado.success).toBe(false);
    expect(mensajesDe(resultado)).toContainEqual({
      message: "El valor declarado debe ser positivo",
      path: "valor_declarado",
    });
  });

  it("TOTAL_EXPLICITO exige el total final", () => {
    const resultado = edificacionesFormSchema.safeParse({
      ...BASE,
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      valor_declarado: 1000000,
      total_explicito: undefined,
    });

    expect(resultado.success).toBe(false);
    expect(mensajesDe(resultado)).toContainEqual({
      message: "El total final es requerido",
      path: "total_explicito",
    });
  });

  it("TOTAL_EXPLICITO rechaza el total final no positivo", () => {
    const resultado = edificacionesFormSchema.safeParse({
      ...BASE,
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      valor_declarado: 1000000,
      total_explicito: 0,
    });

    expect(resultado.success).toBe(false);
    expect(mensajesDe(resultado)).toContainEqual({
      message: "El total final debe ser positivo",
      path: "total_explicito",
    });
  });

  it("TOTAL_EXPLICITO rechaza un valor declarado no positivo", () => {
    const resultado = edificacionesFormSchema.safeParse({
      ...BASE,
      estrategia_cotizacion: ESTRATEGIA_TOTAL,
      valor_declarado: 0,
      total_explicito: 177,
    });

    expect(resultado.success).toBe(false);
    expect(mensajesDe(resultado)).toContainEqual({
      message: "El valor declarado debe ser positivo",
      path: "valor_declarado",
    });
  });

  it("NORMAL_SELECCIONADAS ignora un total explícito residual", () => {
    const resultado = edificacionesFormSchema.safeParse({
      ...BASE,
      valor_declarado: 1000000,
      total_explicito: 0,
    });

    expect(resultado.success).toBe(true);
  });
});
