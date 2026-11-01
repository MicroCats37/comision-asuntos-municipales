import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { RHReparticionEstacional } from "@/features/finanzas/schemas/rh-reparticion-estacional.schema";
import { ReparticionCard } from "./RHReparticionesEstacionalesView";

const item: RHReparticionEstacional = {
  identidad: {
    id: "reparticion-1",
    created_at: "2026-10-30T10:00:00",
  },
  general: {
    especialidad_revision: {
      id: "especialidad-1",
      nombre: "Ingeniería Civil",
    },
    periodo: 2026,
    mes_desde: 1,
    mes_hasta: 3,
  },
  distribucion: {
    total_fondo_comun: 1500,
    numero_capitulos: 1,
    numero_delegados: 1,
    monto_por_participacion: 750,
    residual: 0,
    detalles_delegados: [
      {
        delegado: {
          id: "delegado-1",
          cip: "123456",
          dni: "12345678",
          nombre_completo: "Delegado Uno",
        },
        monto: 750,
      },
    ],
    detalles_capitulos: [
      {
        capitulo: {
          id: "capitulo-1",
          nombre: "Capítulo Civil",
        },
        monto: 750,
      },
    ],
  },
};

describe("ReparticionCard", () => {
  it("usa la jerarquía RH y muestra la distribución dentro de la card", () => {
    render(<ReparticionCard item={item} />);

    expect(
      screen.getByRole("heading", { name: "Recibo de Honorario Trimestral" }),
    ).toBeInTheDocument();
    expect(screen.getByText("2026 · T1 (Ene–Mar)")).toBeInTheDocument();
    expect(screen.getByText("Ingeniería Civil")).toBeInTheDocument();
    expect(screen.getByText("Delegado Uno")).toBeInTheDocument();
    expect(screen.getByText("Capítulo Civil")).toBeInTheDocument();
  });

  it("mantiene las acciones estandarizadas de editar y eliminar", () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    render(<ReparticionCard item={item} onEdit={onEdit} onDelete={onDelete} />);

    fireEvent.click(
      screen.getByRole("button", { name: "Editar RH trimestral" }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Eliminar RH trimestral" }),
    );

    expect(onEdit).toHaveBeenCalledWith(item);
    expect(onDelete).toHaveBeenCalledWith(item.identidad.id);
  });
});
