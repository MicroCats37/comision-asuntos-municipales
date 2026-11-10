/**
 * RH MENSUAL — borrado con confirmacion escrita del CIP (delegado + inspector).
 *
 * Estos tests se ESCRIBEN pero NO se ejecutan en esta fase: la ejecucion
 * consolidada es la fase final de verificacion.
 *
 * Se renderizan las VISTAS y las CARDS reales: solo se mockean la capa de
 * datos (listado + mutacion) y los modales pesados, que no participan del
 * flujo de borrado.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecibosDelegadosView } from "./RecibosDelegadosView";
import { RecibosInspectoresView } from "./RecibosInspectoresView";

const mocks = vi.hoisted(() => {
  const recibo = (id: string, key: string, cip: string) => ({
    id,
    totales: {},
    detalles: [],
    [key]: { id: `${key}-1`, cip, nombre_completo: `${key} Uno` },
  });
  const lista = (items: unknown[]) => ({
    items,
    total: items.length,
    totalPages: 1,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
  return {
    lista,
    eliminarDelegado: vi.fn(),
    eliminarInspector: vi.fn(),
    rhD1: recibo("rh-d1", "delegado", "100001"),
    rhD0: recibo("rh-d0", "delegado", ""),
    rhI1: recibo("rh-i1", "inspector", "200002"),
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/liquidaciones/recibos",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/features/finanzas/hooks/useRecibosDelegados", () => ({
  useRecibosDelegados: () => mocks.lista([mocks.rhD1, mocks.rhD0]),
}));

vi.mock("@/features/finanzas/hooks/useRecibosInspectores", () => ({
  useRecibosInspectores: () => mocks.lista([mocks.rhI1]),
}));

vi.mock("@/features/finanzas/hooks/useEliminarReciboDelegado", () => ({
  useEliminarReciboDelegado: () => ({ eliminar: mocks.eliminarDelegado }),
}));

vi.mock("@/features/finanzas/hooks/useEliminarReciboInspector", () => ({
  useEliminarReciboInspector: () => ({ eliminar: mocks.eliminarInspector }),
}));

vi.mock("@/features/liquidaciones/hooks/useMunicipalidades", () => ({
  useMunicipalidades: () => ({ data: [] }),
}));

vi.mock("@/features/finanzas/components/filtros", () => ({
  RecibosDelegadosFiltroModal: () => null,
  RecibosInspectoresFiltroModal: () => null,
}));

vi.mock("@/features/finanzas/components/modals/RHMensualExcelModal", () => ({
  RHMensualExcelModal: () => null,
}));

vi.mock("@/features/finanzas/components/modals/RhDelegadoMensualModal", () => ({
  RhDelegadoMensualModal: () => null,
}));

vi.mock(
  "@/features/finanzas/components/modals/RhInspectorMensualModal",
  () => ({ RhInspectorMensualModal: () => null }),
);

const CASOS = [
  { nombre: "delegado", Vista: RecibosDelegadosView, cip: "100001" },
  { nombre: "inspector", Vista: RecibosInspectoresView, cip: "200002" },
];

/** Mutacion de borrado e id del recibo, segun el flujo. */
const flujo = (nombre: string) =>
  nombre === "delegado"
    ? { eliminar: mocks.eliminarDelegado, id: "rh-d1" }
    : { eliminar: mocks.eliminarInspector, id: "rh-i1" };

/** Boton "Eliminar" de la card (por indice, segun el orden de la lista). */
const botonCard = (indice: number) =>
  screen.getAllByRole("button", { name: "Eliminar recibo" })[indice];

const botonConfirmar = () => screen.getByRole("button", { name: "Eliminar" });

beforeEach(() => {
  mocks.eliminarDelegado.mockClear();
  mocks.eliminarInspector.mockClear();
});

describe.each(CASOS)("RH mensual de $nombre", ({ Vista, cip, nombre }) => {
  it("exige el CIP de esa persona y solo borra con el CIP correcto", async () => {
    const { eliminar, id } = flujo(nombre);
    render(<Vista />);

    fireEvent.click(botonCard(0));

    expect(
      await screen.findByText(`Para confirmar, escribe el CIP ${cip}`),
    ).toBeInTheDocument();
    expect(botonConfirmar()).toBeDisabled();

    // Un valor equivocado no habilita el borrado.
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "999" } });
    expect(botonConfirmar()).toBeDisabled();

    // Con el CIP correcto se emite UN solo borrado.
    fireEvent.change(screen.getByRole("textbox"), { target: { value: cip } });
    fireEvent.click(botonConfirmar());

    await waitFor(() => expect(eliminar).toHaveBeenCalledWith(id));
    expect(eliminar).toHaveBeenCalledTimes(1);
  });
});

describe("RH mensual de delegado — casos de borde", () => {
  it("cancelar la confirmacion no borra", async () => {
    render(<RecibosDelegadosView />);

    fireEvent.click(botonCard(0));
    await screen.findByRole("textbox");

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(mocks.eliminarDelegado).not.toHaveBeenCalled();
  });

  it("un recibo sin CIP conserva la confirmacion ordinaria", async () => {
    render(<RecibosDelegadosView />);

    fireEvent.click(botonCard(1));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(botonConfirmar()).toBeEnabled();

    fireEvent.click(botonConfirmar());
    await waitFor(() =>
      expect(mocks.eliminarDelegado).toHaveBeenCalledWith("rh-d0"),
    );
  });
});
