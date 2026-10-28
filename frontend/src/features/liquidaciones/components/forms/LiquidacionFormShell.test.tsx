import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { LiquidacionFormShell } from "./LiquidacionFormShell";

vi.mock("@/components-app/forms/AppFormModal", () => ({
  AppFormModal: ({
    onSubmit,
  }: {
    onSubmit: (data: { amount: number }) => Promise<void>;
  }) => (
    <button type="button" onClick={() => void onSubmit({ amount: 10 })}>
      Submit
    </button>
  ),
}));

vi.mock("./LiquidacionFormHeader", () => ({
  LiquidacionFormHeader: () => null,
}));

vi.mock("@/errors", () => ({
  notify: { success: vi.fn() },
}));

describe("LiquidacionFormShell", () => {
  it("closes an edited liquidation before running its post-submit action", async () => {
    const onOpenChange = vi.fn();
    const onSuccess = vi.fn();
    const onAfterSubmit = vi.fn();
    const onSubmitEdit = vi.fn().mockResolvedValue({ id: "result-id" });

    render(
      <LiquidacionFormShell
        open
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        mode="edit"
        sourceItem={{
          liquidacion_general: {
            id: "liquidacion-id",
            sub_total: 10,
            total: 10,
            numero_revision: 1,
          },
        }}
        schema={z.object({ amount: z.number() })}
        initialData={{ amount: 10 }}
        eyebrow="Test"
        icon={<span />}
        titlePrefix="Edit"
        primaryLabel="Save"
        primaryLoadingLabel="Saving"
        primaryLoading={false}
        renderBody={() => null}
        onSubmitEdit={onSubmitEdit}
        onAfterSubmit={onAfterSubmit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(onSuccess).toHaveBeenCalledOnce();
    expect(onAfterSubmit).not.toHaveBeenCalled();

    await waitFor(() => expect(onAfterSubmit).toHaveBeenCalledOnce(), {
      timeout: 1_000,
    });
    expect(onAfterSubmit).toHaveBeenCalledWith("edit", { id: "result-id" });
    expect(onOpenChange.mock.invocationCallOrder[0]).toBeLessThan(
      onAfterSubmit.mock.invocationCallOrder[0],
    );
  });
});
