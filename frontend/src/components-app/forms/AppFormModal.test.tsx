import type { ReactNode } from "react";
import { vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { z } from "zod";
import { AppFormModal } from "./AppFormModal";

// ── Mock GenericModal ─────────────────────────────────────────────────────────

vi.mock("@/components/genericModal/GenericModal", () => ({
  GenericModal: vi.fn(({ children, open, onOpenChange, preventClose }) => {
    if (!open) return null;
    return (
      <div data-testid="generic-modal" data-open={open}>
        <button
          data-testid="modal-backdrop"
          onClick={() => onOpenChange?.(false)}
        />
        <button
          data-testid="modal-close-x"
          onClick={() => onOpenChange?.(false)}
        />
        <div data-prevent-close={preventClose}>{children}</div>
      </div>
    );
  }),
}));

vi.mock("@/components/genericModal/GenericModal", () => ({
  GenericModal: Object.assign(
    vi.fn(({ children, open, onOpenChange, preventClose }) => {
      if (!open) return null;
      return (
        <div data-testid="generic-modal" data-open={open}>
          <button
            data-testid="modal-backdrop"
            onClick={() => onOpenChange?.(false)}
          />
          <button
            data-testid="modal-close-x"
            onClick={() => onOpenChange?.(false)}
          />
          <div data-prevent-close={preventClose}>{children}</div>
        </div>
      );
    }),
    {
      Content: vi.fn(({ children }) => (
        <div data-testid="modal-content">{children}</div>
      )),
      Header: vi.fn(({ children }) => (
        <div data-testid="modal-header">{children}</div>
      )),
      Body: vi.fn(({ children }) => (
        <div data-testid="modal-body">{children}</div>
      )),
      Footer: vi.fn(({ children }) => (
        <div data-testid="modal-footer">{children}</div>
      )),
      CloseX: vi.fn(() => <button data-testid="close-x">X</button>),
    },
  ),
}));

// ── Mock GenericForm ───────────────────────────────────────────────────────────

const mockGenericFormSubmit = vi.fn();
const mockGenericFormChildren = vi.fn();

vi.mock("@/components/genericForm/GenericForm", () => ({
  GenericForm: vi.fn(({ children, onSubmit, isLoading, skipFooter }) => {
    mockGenericFormChildren.mockImplementation(children);
    return (
      <div
        data-testid="generic-form"
        data-loading={isLoading}
        data-skip-footer={skipFooter}
      >
        {typeof children === "function"
          ? children({
              methods: {},
              isSubmitting: false,
              onSubmit: mockGenericFormSubmit,
              submissionMessage: null,
            })
          : children}
      </div>
    );
  }),
}));

// ── Mock Button ───────────────────────────────────────────────────────────────

vi.mock("@/components/ui/button", () => ({
  Button: vi.fn(({ children, onClick, type, disabled }) => (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      data-testid={`button-${children?.toString().toLowerCase() ?? "unnamed"}`}
    >
      {children}
    </button>
  )),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const mockSchema = z.object({
  name: z.string().min(1, "Name is required"),
});

const mockUser = {
  id: 1,
  email: "test@example.com",
  nombres: "Test",
  apellidos: "User",
  rol: "admin" as const,
};

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  title: "Test Modal",
  schema: mockSchema,
  onSubmit: vi.fn(),
  children: ({ onSubmit }: { onSubmit: () => void }) => (
    <button onClick={onSubmit}>Submit</button>
  ),
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("AppFormModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Modal open/close behavior", () => {
    it("renders nothing when isOpen is false", () => {
      render(<AppFormModal {...defaultProps} isOpen={false} />);
      expect(screen.queryByTestId("generic-modal")).not.toBeInTheDocument();
    });

    it("renders modal content when isOpen is true", () => {
      render(<AppFormModal {...defaultProps} isOpen={true} />);
      expect(screen.getByTestId("generic-modal")).toBeInTheDocument();
      expect(screen.getByTestId("modal-content")).toBeInTheDocument();
    });

    it("calls onClose when modal backdrop is clicked", () => {
      render(<AppFormModal {...defaultProps} isOpen={true} />);
      fireEvent.click(screen.getByTestId("modal-backdrop"));
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });

    it("does not call onClose when backdrop is clicked if preventClose is true", () => {
      render(<AppFormModal {...defaultProps} isOpen={true} preventClose={true} />);
      fireEvent.click(screen.getByTestId("modal-backdrop"));
      expect(defaultProps.onClose).not.toHaveBeenCalled();
    });

    it("renders modal title", () => {
      render(<AppFormModal {...defaultProps} title="My Custom Title" />);
      expect(screen.getByText("My Custom Title")).toBeInTheDocument();
    });

    it("renders modal description when provided", () => {
      render(
        <AppFormModal
          {...defaultProps}
          description="This is a description"
        />,
      );
      expect(screen.getByText("This is a description")).toBeInTheDocument();
    });
  });

  describe("onClose prop passing", () => {
    it("passes correct onClose handler to GenericModal", () => {
      const customOnClose = vi.fn();
      render(<AppFormModal {...defaultProps} onClose={customOnClose} />);

      fireEvent.click(screen.getByTestId("modal-backdrop"));
      expect(customOnClose).toHaveBeenCalledTimes(1);
    });

    it("closes modal when GenericModal's onOpenChange is called with false", () => {
      render(<AppFormModal {...defaultProps} />);
      expect(screen.getByTestId("generic-modal")).toBeInTheDocument();

      fireEvent.click(screen.getByTestId("modal-close-x"));
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("GenericForm prop passing", () => {
    it("passes schema to GenericForm", () => {
      render(<AppFormModal {...defaultProps} />);
      const form = screen.getByTestId("generic-form");
      expect(form).toBeInTheDocument();
    });

    it("passes isLoading state to GenericForm", () => {
      render(<AppFormModal {...defaultProps} isLoading={true} />);
      expect(screen.getByTestId("generic-form")).toHaveAttribute(
        "data-loading",
        "true",
      );
    });

    it("passes skipFooter=true to GenericForm", () => {
      render(<AppFormModal {...defaultProps} />);
      expect(screen.getByTestId("generic-form")).toHaveAttribute(
        "data-skip-footer",
        "true",
      );
    });

    it("renders GenericForm body content", () => {
      const childrenRender = vi.fn();
      render(
        <AppFormModal
          {...defaultProps}
          children={childrenRender}
        />,
      );
      expect(childrenRender).toHaveBeenCalled();
    });
  });

  describe("Footer buttons", () => {
    it("renders Cancel button that calls onClose by default", () => {
      render(<AppFormModal {...defaultProps} />);
      const cancelButton = screen.getByTestId("button-cancelar");
      expect(cancelButton).toBeInTheDocument();
    });

    it("renders custom secondary label", () => {
      render(<AppFormModal {...defaultProps} secondaryLabel="Cerrar" />);
      expect(screen.getByTestId("button-cerrar")).toBeInTheDocument();
    });

    it("renders primary submit button", () => {
      render(<AppFormModal {...defaultProps} primaryLabel="Crear" />);
      const submitButton = screen.getByTestId("button-crear");
      expect(submitButton).toBeInTheDocument();
    });

    it("disables Cancel button when primaryLoading is true", () => {
      render(
        <AppFormModal {...defaultProps} primaryLoading={true} />,
      );
      const cancelButton = screen.getByTestId("button-cancelar");
      expect(cancelButton).toHaveAttribute("disabled");
    });
  });

  describe("Form submission", () => {
    it("closes modal after successful submit", async () => {
      const onSubmit = vi.fn().mockResolvedValue(undefined);
      render(
        <AppFormModal
          {...defaultProps}
          onSubmit={onSubmit}
        />,
      );

      // Simulate form submission via the wrapped onSubmit
      const onChildSubmit = mockGenericFormChildren.mock.calls[0][0].onSubmit;
      await onChildSubmit({ name: "Test" });

      expect(onSubmit).toHaveBeenCalledWith({ name: "Test" });
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });
  });
});
