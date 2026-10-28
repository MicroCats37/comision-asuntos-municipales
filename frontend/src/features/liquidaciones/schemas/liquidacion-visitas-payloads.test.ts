import { describe, expect, it } from "vitest";
import { buildCotizacionNuevaRevisionVisitasPayload } from "../components/forms/TarifasVisitasNuevaRevisionSmartField";
import { buildCotizacionVisitasPayload } from "../components/forms/TarifasVisitasSinPreviaSmartField";
import { buildCrearInspeccionObraPayload } from "../hooks/useCrearInspeccionObra";
import { buildCrearRelacionadaInspeccionObraPayload } from "../hooks/useCrearRelacionadaInspeccionObra";
import { buildVisitasEditPayload } from "./liquidacion-visitas-edit.schema";
import type { VisitasFormData } from "./liquidacion-visitas-form.schema";

const visitasFormData = {
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
} as VisitasFormData;

describe("IO normal payloads", () => {
  it("omits categoria from normal and edit quote payloads", () => {
    const normal = buildCotizacionVisitasPayload(3, "tarifa-2");
    const create = buildCotizacionNuevaRevisionVisitasPayload(
      3,
      "tarifa-2",
      "create",
    );
    const edit = buildCotizacionNuevaRevisionVisitasPayload(
      3,
      "tarifa-2",
      "edit",
    );

    expect(normal.liquidacion_especifica.datos).toEqual({
      cantidad_visitas: 3,
    });
    expect(create).not.toHaveProperty("liquidacion_especifica.datos.categoria");
    expect(edit).not.toHaveProperty("liquidacion_tipo.datos.categoria");
  });

  it("omits categoria from create, related, and PATCH payloads", () => {
    const create = buildCrearInspeccionObraPayload(visitasFormData);
    const related = buildCrearRelacionadaInspeccionObraPayload({
      liquidacion_previa_id: "previa-1",
      cantidad_visitas: 3,
      tarifa_visitas_id: "tarifa-2",
      inspector_operacion_id: "operacion-1",
    });
    const edit = buildVisitasEditPayload(visitasFormData);

    expect(create).not.toHaveProperty("liquidacion_especifica.datos.categoria");
    expect(related).not.toHaveProperty(
      "liquidacion_especifica.datos.categoria",
    );
    expect(edit).not.toHaveProperty("liquidacion_tipo.datos.categoria");
  });
});
