/**
 * Modo de cotización del motor IO (Inspección de Obra) — discriminador y
 * rehidratación.
 *
 * La ejecución de la suite queda reservada para la fase de verificación.
 *
 * Contrato cubierto (io-continuidad-visitas-ui):
 *  · El modo es un discriminador TIPADO con DOS valores: "NORMAL" y
 *    "CONTINUAR" (patrón PO/Edificaciones).
 *  · Una IO con continuidad PERSISTIDA se rehidrata en modo "CONTINUAR": su
 *    `sub_total` es la diferencia, no el valor completo.
 *  · El modo es de VISTA: no viaja al backend (el schema del form lo acepta y
 *    los builders de payload lo ignoran).
 */
import { describe, expect, it } from "vitest";
import {
  hidratarModoCotizacionDesdeItem,
  MODO_COTIZACION_IO_POR_DEFECTO,
  resolverModoCotizacionPersistido,
} from "../utils/modoCotizacionIo";
import {
  esModoCotizacionValido,
  MODO_COTIZACION_IO_CONTINUAR,
  MODO_COTIZACION_IO_DESCRIPCIONES,
  MODO_COTIZACION_IO_LABELS,
  MODO_COTIZACION_IO_NORMAL,
  MODOS_COTIZACION_IO,
  modoCotizacionIOSchema,
} from "./liquidacion-io-modo-cotizacion.schema";
import { visitasFormSchema } from "./liquidacion-visitas-form.schema";

const baseFormData = {
  cantidad_visitas: 3,
  categoria: "4",
  tarifa_visitas_id: "tarifa-2",
  inspector_operacion_id: "operacion-1",
  municipalidad_id: "municipalidad-1",
  expediente: "EXP-1",
  denominacion: "Proyecto",
  nombre_propietario: "Propietario",
  direccion: "Direccion",
  entidad_tipo_documento: "RUC",
  entidad_numero_documento: "20123456789",
  entidad_razon_social: "Entidad",
};

describe("modo de cotización de IO — discriminador", () => {
  it("expone exactamente dos modos canónicos", () => {
    expect(MODOS_COTIZACION_IO).toEqual([
      MODO_COTIZACION_IO_NORMAL,
      MODO_COTIZACION_IO_CONTINUAR,
    ]);
  });

  it("acepta los dos modos y rechaza cualquier otro valor", () => {
    expect(modoCotizacionIOSchema.safeParse("NORMAL").success).toBe(true);
    expect(modoCotizacionIOSchema.safeParse("CONTINUAR").success).toBe(true);
    expect(modoCotizacionIOSchema.safeParse("CONTINUIDAD").success).toBe(false);
    expect(modoCotizacionIOSchema.safeParse(undefined).success).toBe(false);
  });

  it("valida el modo con el guard de tipos", () => {
    expect(esModoCotizacionValido("NORMAL")).toBe(true);
    expect(esModoCotizacionValido("CONTINUAR")).toBe(true);
    expect(esModoCotizacionValido("apagar")).toBe(false);
    expect(esModoCotizacionValido(null)).toBe(false);
  });

  it("etiqueta y describe los dos modos", () => {
    expect(MODO_COTIZACION_IO_LABELS[MODO_COTIZACION_IO_NORMAL]).toBe("Normal");
    expect(MODO_COTIZACION_IO_LABELS[MODO_COTIZACION_IO_CONTINUAR]).toBe(
      "Continuar",
    );
    expect(
      MODO_COTIZACION_IO_DESCRIPCIONES[MODO_COTIZACION_IO_CONTINUAR],
    ).toContain("diferencia");
  });
});

describe("modo de cotización de IO — rehidratación", () => {
  it("una IO con continuidad persistida se rehidrata en modo Continuar", () => {
    expect(resolverModoCotizacionPersistido({ id: "cont-1" })).toBe(
      MODO_COTIZACION_IO_CONTINUAR,
    );
  });

  it("una IO sin continuidad se rehidrata en modo Normal", () => {
    expect(resolverModoCotizacionPersistido(null)).toBe(
      MODO_COTIZACION_IO_NORMAL,
    );
    expect(resolverModoCotizacionPersistido(undefined)).toBe(
      MODO_COTIZACION_IO_POR_DEFECTO,
    );
  });

  it("hidrata el modo desde el item persistido", () => {
    expect(
      hidratarModoCotizacionDesdeItem({
        liquidacion_tipo: { continuidad: { id: "cont-1" } },
      }),
    ).toEqual({ modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR });

    expect(
      hidratarModoCotizacionDesdeItem({
        liquidacion_tipo: { continuidad: null },
      }),
    ).toEqual({ modo_cotizacion: MODO_COTIZACION_IO_NORMAL });

    expect(hidratarModoCotizacionDesdeItem({})).toEqual({
      modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
    });
  });
});

describe("modo de cotización de IO — schema del formulario", () => {
  it("el form acepta el modo declarado", () => {
    const result = visitasFormSchema.safeParse({
      ...baseFormData,
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
    });

    expect(result.success).toBe(true);
  });

  it("el form sigue siendo válido sin modo (lo que hereda todo lo legacy)", () => {
    const result = visitasFormSchema.safeParse(baseFormData);

    expect(result.success).toBe(true);
  });

  it("el form rechaza un modo desconocido", () => {
    const result = visitasFormSchema.safeParse({
      ...baseFormData,
      modo_cotizacion: "CONTINUIDAD",
    });

    expect(result.success).toBe(false);
  });
});
