/**
 * Selector de previas — Fase 5 (números de revisión repetidos).
 *
 * El selector lista el paginado del tipo correspondiente y devuelve TODAS las
 * revisiones. Como el número de revisión es una ETIQUETA editable, dos
 * liquidaciones hermanas pueden mostrar la misma ("Rev. 3"): el selector NO
 * puede deduplicarlas ni elegir una hermana canónica — cada una se muestra y
 * se puede seleccionar por su propia identidad.
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { SeleccionarPreviaModal } from "./SeleccionarPreviaModal";

// El modal genérico se sustituye por un passthrough: el test focuses en la
// LÓGICA del selector (qué liquidaciones lista y cuáles selecciona), no en el
// comportamiento del diálogo (Radix/ScrollArea).
vi.mock("@/components/genericModal/GenericModal", () => {
  const Passthrough = ({ children }: { children?: ReactNode }) => (
    <div>{children}</div>
  );
  return {
    GenericModal: Object.assign(Passthrough, {
      Content: Passthrough,
      Header: Passthrough,
      Body: Passthrough,
      Footer: Passthrough,
      CloseX: () => null,
    }),
  };
});

// El detalle se dispara solo al pulsar "Ver detalle"; no participa de este test.
vi.mock("../../components/detail", () => ({
  composeDetalleSections: () => null,
  LiquidacionDetalleModal: () => null,
}));

const HERMANO_A = {
  liquidacion_general: {
    id: "hermano-a",
    numero_revision: 3,
    expediente: "EXP-A",
    denominacion_de_proyecto: "PROYECTO HERMANO A",
    tipo_liquidacion: { codigo: "EDIFICACION" },
    proyecto: {
      nombre_propietario: "PROPIETARIO A",
      direccion: "AV. A 111",
      entidad: {
        tipo_documento: "RUC",
        numero_documento: "20123456789",
      },
    },
  },
  liquidacion_especifica: { id: "esp-a", numero: 10 },
  liquidacion_tipo: { id: "tipo-1", tipo_tramite: "OBRA_NUEVA" },
};

const HERMANO_B = {
  liquidacion_general: {
    id: "hermano-b",
    numero_revision: 3,
    expediente: "EXP-B",
    denominacion_de_proyecto: "PROYECTO HERMANO B",
    tipo_liquidacion: { codigo: "EDIFICACION" },
    proyecto: {
      nombre_propietario: "PROPIETARIO B",
      direccion: "AV. B 222",
      entidad: {
        tipo_documento: "RUC",
        numero_documento: "20999999999",
      },
    },
  },
  liquidacion_especifica: { id: "esp-b", numero: 11 },
  liquidacion_tipo: { id: "tipo-1", tipo_tramite: "OBRA_NUEVA" },
};

vi.mock("../../hooks/useLiquidacionesPrevias", () => ({
  useLiquidacionesPrevias: () => ({
    items: [HERMANO_A, HERMANO_B],
    total: 2,
    page: 1,
    pageSize: 10,
    totalPages: 1,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

function buscarEnElSelector() {
  fireEvent.change(screen.getByLabelText("N° Documento (RUC/DNI)"), {
    target: { value: "20123456789" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
}

describe("SeleccionarPreviaModal — hermanos con el mismo número de revisión", () => {
  it("lista AMBAS liquidaciones hermanas (no deduplica por revisión)", () => {
    render(
      <SeleccionarPreviaModal
        open
        onOpenChange={vi.fn()}
        tipoPermitido="EDIFICACION"
        onSelect={vi.fn()}
      />,
    );

    buscarEnElSelector();

    expect(screen.getByText("PROYECTO HERMANO A")).toBeInTheDocument();
    expect(screen.getByText("PROYECTO HERMANO B")).toBeInTheDocument();
  });

  it("muestra la etiqueta de revisión de cada hermana (dos veces «Rev. 3»)", () => {
    render(
      <SeleccionarPreviaModal
        open
        onOpenChange={vi.fn()}
        tipoPermitido="EDIFICACION"
        onSelect={vi.fn()}
      />,
    );

    buscarEnElSelector();

    expect(screen.getAllByText("Rev. 3")).toHaveLength(2);
  });

  it("permite seleccionar CUALQUIER hermana (no impone una canónica)", () => {
    const onSelect = vi.fn();
    render(
      <SeleccionarPreviaModal
        open
        onOpenChange={vi.fn()}
        tipoPermitido="EDIFICACION"
        onSelect={onSelect}
      />,
    );

    buscarEnElSelector();
    fireEvent.click(screen.getByText("PROYECTO HERMANO B"));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0].liquidacion_general.id).toBe("hermano-b");
  });
});
