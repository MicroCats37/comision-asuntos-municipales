import { describe, expect, it } from "vitest";
import { buildCrearEdificacionesPayload } from "../hooks/useCrearEdificaciones";
import { buildCrearHabilitacionUrbanaPayload } from "../hooks/useCrearHabilitacionUrbana";
import { buildCrearImpactoVialPayload } from "../hooks/useCrearImpactoVial";
import { buildCrearInspeccionObraPayload } from "../hooks/useCrearInspeccionObra";
import { buildCrearMecanicaSuelosPayload } from "../hooks/useCrearMecanicaSuelos";
import { buildCrearNuevaRevisionEdificacionesPayload } from "../hooks/useCrearNuevaRevisionEdificaciones";
import { buildCrearNuevaRevisionHabilitacionUrbanaPayload } from "../hooks/useCrearNuevaRevisionHabilitacionUrbana";
import { buildCrearNuevaRevisionImpactoVialPayload } from "../hooks/useCrearNuevaRevisionImpactoVial";
import { buildCrearNuevaRevisionMecanicaSuelosPayload } from "../hooks/useCrearNuevaRevisionMecanicaSuelos";
import { buildCrearNuevaRevisionTaludesPayload } from "../hooks/useCrearNuevaRevisionTaludes";
import { buildCrearRelacionadaEdificacionesPayload } from "../hooks/useCrearRelacionadaEdificaciones";
import { buildCrearRelacionadaHabilitacionUrbanaPayload } from "../hooks/useCrearRelacionadaHabilitacionUrbana";
import { buildCrearRelacionadaImpactoVialPayload } from "../hooks/useCrearRelacionadaImpactoVial";
import { buildCrearRelacionadaInspeccionObraPayload } from "../hooks/useCrearRelacionadaInspeccionObra";
import { buildCrearRelacionadaMecanicaSuelosPayload } from "../hooks/useCrearRelacionadaMecanicaSuelos";
import { buildCrearRelacionadaTaludesPayload } from "../hooks/useCrearRelacionadaTaludes";
import { buildCrearTaludesPayload } from "../hooks/useCrearTaludes";
import type { EdificacionesFormData } from "./liquidacion-edificaciones-form.schema";
import type { HabilitacionUrbanaFormData } from "./liquidacion-habilitacion-urbana-form.schema";
import type { ImpactoVialFormData } from "./liquidacion-impacto-vial-form.schema";
import { buildM2EditPayload } from "./liquidacion-m2-edit.schema";
import type { MecanicaSuelosFormData } from "./liquidacion-mecanica-suelos-form.schema";
import { buildPOEditPayload } from "./liquidacion-po-edit.schema";
import type { TaludesFormData } from "./liquidacion-taludes-form.schema";
import { buildVisitasEditPayload } from "./liquidacion-visitas-edit.schema";
import type { VisitasFormData } from "./liquidacion-visitas-form.schema";

const PROYECTO = {
  municipalidad_id: "municipalidad-1",
  expediente: "EXP-001",
  observacion: "Observación",
  denominacion: "PROYECTO",
  nombre_propietario: "PROPIETARIO",
  direccion: "DIRECCIÓN",
  distrito_id: "distrito-1",
  entidad_tipo_documento: "RUC" as const,
  entidad_numero_documento: "20123456789",
  entidad_razon_social: "EMPRESA SAC",
};

const edificacionesData = {
  ...PROYECTO,
  valor_declarado: 1000,
  tipo_tramite: "OBRA_NUEVA" as const,
  tarifa_unica_id: "tarifa-1",
  especialidades_seleccionadas: ["especialidad-1"],
  numero_revision: 3,
} as EdificacionesFormData;

const taludesData = {
  ...PROYECTO,
  valor_declarado: 1000,
  tarifa_unica_id: "tarifa-1",
  especialidades_seleccionadas: ["especialidad-1"],
  numero_revision: 5,
} as TaludesFormData;

const impactoVialData = {
  ...PROYECTO,
  valor_declarado: 1000,
  tarifa_unica_id: "tarifa-1",
  especialidades_seleccionadas: ["especialidad-1"],
  numero_revision: 1,
} as ImpactoVialFormData;

const habilitacionUrbanaData = {
  ...PROYECTO,
  urbanizacion: "URBANIZACIÓN",
  area_solicitada: 250,
  tarifa_m2_id: "tarifa-m2-1",
  numero_revision: 3,
} as HabilitacionUrbanaFormData;

const mecanicaSuelosData = {
  ...PROYECTO,
  urbanizacion: "URBANIZACIÓN",
  area_solicitada: 250,
  tarifa_m2_id: "tarifa-m2-1",
  numero_revision: 5,
} as MecanicaSuelosFormData;

const visitasData = {
  ...PROYECTO,
  cantidad_visitas: 3,
  categoria: "4" as const,
  tarifa_visitas_id: "tarifa-visitas-1",
  inspector_operacion_id: "operacion-1",
} as VisitasFormData;

describe("numero_revision — payloads de creación (top level)", () => {
  it("envía numero_revision en el top level del body de Edificaciones", () => {
    const payload = buildCrearEdificacionesPayload(edificacionesData);

    expect(payload.numero_revision).toBe(3);
    expect(payload).not.toHaveProperty("liquidacion_general.numero_revision");
  });

  it("envía numero_revision en el top level del body de Habilitación Urbana", () => {
    const payload = buildCrearHabilitacionUrbanaPayload(habilitacionUrbanaData);

    expect(payload.numero_revision).toBe(3);
    expect(payload).not.toHaveProperty("liquidacion_general.numero_revision");
  });

  it("envía numero_revision en el top level del body de Mecánica de Suelos", () => {
    const payload = buildCrearMecanicaSuelosPayload(mecanicaSuelosData);

    expect(payload.numero_revision).toBe(5);
    expect(payload).not.toHaveProperty("liquidacion_general.numero_revision");
  });

  it("envía numero_revision en el top level del body de Taludes", () => {
    const payload = buildCrearTaludesPayload(taludesData);

    expect(payload.numero_revision).toBe(5);
    expect(payload).not.toHaveProperty("liquidacion_general.numero_revision");
  });

  it("envía numero_revision en el top level del body de Impacto Vial", () => {
    const payload = buildCrearImpactoVialPayload(impactoVialData);

    expect(payload.numero_revision).toBe(1);
    expect(payload).not.toHaveProperty("liquidacion_general.numero_revision");
  });
});

describe("numero_revision — payloads de nueva revisión (top level)", () => {
  it("envía numero_revision junto al liquidacion_previa_id", () => {
    const payloads = [
      buildCrearNuevaRevisionEdificacionesPayload(
        edificacionesData,
        "previa-1",
      ),
      buildCrearNuevaRevisionHabilitacionUrbanaPayload(
        habilitacionUrbanaData,
        "previa-1",
      ),
      buildCrearNuevaRevisionMecanicaSuelosPayload(
        mecanicaSuelosData,
        "previa-1",
      ),
      buildCrearNuevaRevisionTaludesPayload(taludesData, "previa-1"),
      buildCrearNuevaRevisionImpactoVialPayload(impactoVialData, "previa-1"),
    ];

    for (const payload of payloads) {
      expect(payload.liquidacion_previa_id).toBe("previa-1");
      expect(payload.numero_revision).toBeDefined();
      expect(payload).not.toHaveProperty("liquidacion_general.numero_revision");
    }
  });
});

describe("numero_revision — payloads de relacionada (top level)", () => {
  it("envía numero_revision junto al liquidacion_previa_id", () => {
    const payloads = [
      buildCrearRelacionadaEdificacionesPayload(edificacionesData, "previa-1"),
      buildCrearRelacionadaHabilitacionUrbanaPayload(
        habilitacionUrbanaData,
        "previa-1",
      ),
      buildCrearRelacionadaMecanicaSuelosPayload(
        mecanicaSuelosData,
        "previa-1",
      ),
      buildCrearRelacionadaTaludesPayload(taludesData, "previa-1"),
      buildCrearRelacionadaImpactoVialPayload(impactoVialData, "previa-1"),
    ];

    for (const payload of payloads) {
      expect(payload.liquidacion_previa_id).toBe("previa-1");
      expect(payload.numero_revision).toBeDefined();
      expect(payload).not.toHaveProperty("liquidacion_general.numero_revision");
    }
  });
});

describe("numero_revision — payloads de edición (bloque liquidacion_general)", () => {
  it("envía numero_revision dentro del bloque liquidacion_general en tipos PO", () => {
    const payload = buildPOEditPayload(edificacionesData);

    expect(payload.liquidacion_general?.numero_revision).toBe(3);
  });

  it("envía numero_revision dentro del bloque liquidacion_general en tipos M2", () => {
    const payload = buildM2EditPayload(habilitacionUrbanaData);

    expect(payload.liquidacion_general?.numero_revision).toBe(3);
  });
});

describe("Inspección de Obra — revision-less", () => {
  it("no envía numero_revision en ningún payload", () => {
    const create = buildCrearInspeccionObraPayload(visitasData);
    const relacionada = buildCrearRelacionadaInspeccionObraPayload({
      liquidacion_previa_id: "previa-1",
      cantidad_visitas: 3,
      tarifa_visitas_id: "tarifa-visitas-1",
      inspector_operacion_id: "operacion-1",
    });
    const edit = buildVisitasEditPayload(visitasData);

    expect(create).not.toHaveProperty("numero_revision");
    expect(create).not.toHaveProperty("liquidacion_general.numero_revision");
    expect(relacionada).not.toHaveProperty("numero_revision");
    expect(relacionada).not.toHaveProperty(
      "liquidacion_general.numero_revision",
    );
    expect(edit.liquidacion_general).not.toHaveProperty("numero_revision");
  });
});
