/**
 * NuevaRHReparticionEstacionalModal — modo EDICIÓN (RH Trimestral).
 *
 * Cubre la precarga desde el item compuesto del listado, el envío del PATCH
 * con el bloque general de entrada y el cierre sin efectos.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RHReparticionEstacional } from "@/features/finanzas/schemas/rh-reparticion-estacional.schema";

const mocks = vi.hoisted(() => ({
  actualizar: vi.fn(),
  cotizar: vi.fn(),
  crear: vi.fn(),
}));

vi.mock("@/features/finanzas/hooks/useCotizarRHReparticionEstacional", () => ({
  useCotizarRHReparticionEstacional: () => ({
    cotizar: mocks.cotizar,
    isPending: false,
  }),
}));

vi.mock("@/features/finanzas/hooks/useCrearRHReparticionEstacional", () => ({
  useCrearRHReparticionEstacional: () => ({
    crear: mocks.crear,
    isPending: false,
  }),
}));

vi.mock(
  "@/features/finanzas/hooks/useActualizarRHReparticionEstacional",
  () => ({
    useActualizarRHReparticionEstacional: () => ({
      actualizar: mocks.actualizar,
      isPending: false,
    }),
  }),
);

vi.mock("@/features/liquidaciones/hooks", () => ({
  useEspecialidadesRevision: () => ({
    data: [{ id: "esp-1", nombre: "Ingeniería Civil" }],
    isLoading: false,
  }),
  useDelegadosVigentesPorEspecialidad: () => ({
    data: [
      {
        id: "delegado-1",
        nombre_completo: "Carlos Ramirez Lopez",
        cip: "100001",
        tipo: "TITULAR",
        especialidad: { id: "esp-1", nombre: "Ingeniería Civil" },
      },
      {
        id: "delegado-2",
        nombre_completo: "Ana Torres Meza",
        cip: "100002",
        tipo: "TITULAR",
        especialidad: { id: "esp-1", nombre: "Ingeniería Civil" },
      },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/errors", () => ({
  notify: { error: vi.fn(), success: vi.fn() },
}));

import { NuevaRHReparticionEstacionalModal } from "./NuevaRHReparticionEstacionalModal";

const item = {
  identidad: {
    id: "reparticion-1",
    created_at: "2026-10-30T10:00:00Z",
  },
  general: {
    especialidad_revision: { id: "esp-1", nombre: "Ingeniería Civil" },
    periodo: 2026,
    mes_desde: 1,
    mes_hasta: 3,
  },
  distribucion: {
    total_fondo_comun: 100,
    numero_capitulos: 1,
    numero_delegados: 1,
    monto_por_participacion: 50,
    residual: 0,
    detalles_delegados: [
      {
        delegado: {
          id: "delegado-1",
          cip: "100001",
          dni: "11111111",
          nombre_completo: "Carlos Ramirez Lopez",
        },
        monto: 50,
      },
    ],
    detalles_capitulos: [
      {
        capitulo: { id: "capitulo-1", nombre: "Ingeniería Civil" },
        monto: 50,
      },
    ],
  },
} as unknown as RHReparticionEstacional;

const cotizarResult = {
  especialidad_revision_id: "esp-1",
  especialidad_revision_nombre: "Ingeniería Civil",
  periodo: 2026,
  mes_desde: 1,
  mes_hasta: 3,
  total_fondo_comun: 100,
  numero_capitulos: 1,
  numero_delegados: 1,
  divisor_total: 2,
  monto_por_participacion: 50,
  residual: 0,
  detalles_delegados: [
    {
      delegado: {
        id: "delegado-1",
        cip: "100001",
        dni: "11111111",
        nombre_completo: "Carlos Ramirez Lopez",
      },
      monto: 50,
    },
  ],
  detalles_capitulos: [
    { capitulo: { id: "capitulo-1", nombre: "Ingeniería Civil" }, monto: 50 },
  ],
};

describe("NuevaRHReparticionEstacionalModal — modo edición", () => {
  beforeEach(() => {
    mocks.actualizar.mockReset();
    mocks.cotizar.mockReset();
    mocks.crear.mockReset();
    mocks.cotizar.mockResolvedValue({ data: cotizarResult });
    mocks.actualizar.mockResolvedValue({ data: item });
  });

  it("muestra el título de edición y precarga el delegado persistido", () => {
    render(
      <NuevaRHReparticionEstacionalModal
        open
        onOpenChange={vi.fn()}
        editContext={item}
      />,
    );

    expect(screen.getByText("Editar Trimestral")).toBeInTheDocument();
    // En modo edición el botón final NO es el de creación.
    expect(
      screen.queryByRole("button", { name: "Crear Repartición" }),
    ).toBeNull();

    // La lista de candidatos muestra el delegado persistido y lo cuenta.
    fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(screen.getByText("Carlos Ramirez Lopez")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Cotizar \(1\)/ }),
    ).toBeInTheDocument();
  });

  it("envía el PATCH con el bloque general precargado", async () => {
    render(
      <NuevaRHReparticionEstacionalModal
        open
        onOpenChange={vi.fn()}
        editContext={item}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    fireEvent.click(screen.getByRole("button", { name: /Cotizar \(1\)/ }));
    await waitFor(() => expect(mocks.cotizar).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(mocks.actualizar).toHaveBeenCalledTimes(1));

    const payload = mocks.actualizar.mock.calls[0][0];
    expect(payload).toEqual({
      especialidad_revision_id: "esp-1",
      periodo: 2026,
      mes_desde: 1,
      mes_hasta: 3,
      delegado_ids: ["delegado-1"],
    });
    // La edición NO crea una repartición nueva.
    expect(mocks.crear).not.toHaveBeenCalled();
  });

  it("cerrar sin confirmar no dispara el PATCH", () => {
    const onOpenChange = vi.fn();

    render(
      <NuevaRHReparticionEstacionalModal
        open
        onOpenChange={onOpenChange}
        editContext={item}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(mocks.actualizar).not.toHaveBeenCalled();
    expect(mocks.cotizar).not.toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
