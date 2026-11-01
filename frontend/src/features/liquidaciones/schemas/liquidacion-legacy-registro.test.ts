import { describe, expect, it } from "vitest";
import { buildCrearEdificacionesPayload } from "../hooks/useCrearEdificaciones";
import { buildCrearHabilitacionUrbanaPayload } from "../hooks/useCrearHabilitacionUrbana";
import { buildCrearImpactoVialPayload } from "../hooks/useCrearImpactoVial";
import { buildCrearInspeccionObraPayload } from "../hooks/useCrearInspeccionObra";
import { buildCrearMecanicaSuelosPayload } from "../hooks/useCrearMecanicaSuelos";
import { buildCrearTaludesPayload } from "../hooks/useCrearTaludes";
import type { EdificacionesFormData } from "./liquidacion-edificaciones-form.schema";
import type { HabilitacionUrbanaFormData } from "./liquidacion-habilitacion-urbana-form.schema";
import type { ImpactoVialFormData } from "./liquidacion-impacto-vial-form.schema";
import { legacyRegistroFieldsSchema } from "./liquidacion-legacy-registro-form.schema";
import type { MecanicaSuelosFormData } from "./liquidacion-mecanica-suelos-form.schema";
import type { TaludesFormData } from "./liquidacion-taludes-form.schema";
import type { VisitasFormData } from "./liquidacion-visitas-form.schema";

const GENERAL = {
  municipalidad_id: "municipalidad-1",
  expediente: "EXP-001",
  observacion: "Registro histórico",
  denominacion: "PROYECTO HISTÓRICO",
  nombre_propietario: "PROPIETARIO",
  direccion: "DIRECCIÓN",
  distrito_id: "distrito-1",
  entidad_tipo_documento: "RUC" as const,
  entidad_numero_documento: "20123456789",
  entidad_razon_social: "EMPRESA SAC",
  numero: 1250,
  fecha_registro: "2023-06-15",
};

describe("registro legacy", () => {
  it("requiere número positivo y fecha ISO", () => {
    expect(
      legacyRegistroFieldsSchema.safeParse({
        numero: 1250,
        fecha_registro: "2023-06-15",
      }).success,
    ).toBe(true);
    expect(legacyRegistroFieldsSchema.safeParse({}).success).toBe(false);
    expect(
      legacyRegistroFieldsSchema.safeParse({
        numero: 0,
        fecha_registro: "15/06/2023",
      }).success,
    ).toBe(false);
  });

  it("agrega la identidad histórica al top level de los seis payloads", () => {
    const payloads = [
      buildCrearEdificacionesPayload(
        {
          ...GENERAL,
          numero_revision: 1,
          estrategia_cotizacion: "NORMAL_SELECCIONADAS",
          valor_declarado: 1000,
          tipo_tramite: "OBRA_NUEVA",
          tarifa_unica_id: "tarifa-po",
          especialidades_seleccionadas: ["especialidad-1"],
        } as EdificacionesFormData,
        true,
      ),
      buildCrearTaludesPayload(
        {
          ...GENERAL,
          numero_revision: 1,
          valor_declarado: 1000,
          tarifa_unica_id: "tarifa-po",
          especialidades_seleccionadas: ["especialidad-1"],
        } as TaludesFormData,
        true,
      ),
      buildCrearImpactoVialPayload(
        {
          ...GENERAL,
          numero_revision: 1,
          valor_declarado: 1000,
          tarifa_unica_id: "tarifa-po",
          especialidades_seleccionadas: ["especialidad-1"],
        } as ImpactoVialFormData,
        true,
      ),
      buildCrearHabilitacionUrbanaPayload(
        {
          ...GENERAL,
          numero_revision: 1,
          area_solicitada: 100,
          tarifa_m2_id: "tarifa-m2",
        } as HabilitacionUrbanaFormData,
        true,
      ),
      buildCrearMecanicaSuelosPayload(
        {
          ...GENERAL,
          numero_revision: 1,
          area_solicitada: 100,
          tarifa_m2_id: "tarifa-m2",
        } as MecanicaSuelosFormData,
        true,
      ),
      buildCrearInspeccionObraPayload(
        {
          ...GENERAL,
          cantidad_visitas: 2,
          categoria: "1",
          tarifa_visitas_id: "tarifa-visitas",
          inspector_operacion_id: "operacion-actual",
        } as VisitasFormData,
        true,
      ),
    ];

    for (const payload of payloads) {
      expect(payload).toMatchObject({
        numero: 1250,
        fecha_registro: "2023-06-15",
      });
      expect(payload).not.toHaveProperty("legacy");
    }
  });

  it("omite la operación del inspector en Inspección de Obra legacy", () => {
    const payload = buildCrearInspeccionObraPayload(
      {
        ...GENERAL,
        cantidad_visitas: 2,
        categoria: "1",
        tarifa_visitas_id: "tarifa-visitas",
        inspector_operacion_id: "operacion-actual",
      } as VisitasFormData,
      true,
    );

    expect(payload.liquidacion_especifica).not.toHaveProperty(
      "inspector_operacion_id",
    );
  });
});
