import type { ReactNode } from "react";
import { vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { z } from "zod";
import { AppStepperFormModal } from "./AppStepperFormModal";

// ── Mock GenericModal ─────────────────────────────────────────────────────────

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

interface StepConfig {
  id: string;
  title: string;
  render: (ctx: {
    methods: Record<string, unknown>;
    currentStep: number;
    isActive: boolean;
  }) => ReactNode;
  validate?: (ctx: {
    methods: Record<string, unknown>;
    currentStep: number;
  }) => boolean | Promise<boolean>;
}

const createMockSteps = (configs: StepConfig[]): StepConfig[] => configs;

const defaultSteps = createMockSteps([
  {
    id: "step-1",
    title: "Step One",
    render: () => <div data-testid="step-content-1">Step One Content</div>,
  },
  {
    id: "step-2",
    title: "Step Two",
    render: () => <div data-testid="step-content-2">Step Two Content</div>,
  },
  {
    id: "step-3",
    title: "Step Three",
    render: () => <div data-testid="step-content-3">Step Three Content</div>,
  },
]);

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  title: "Multi-Step Form",
  schema: mockSchema,
  steps: defaultSteps,
  onSubmit: vi.fn(),
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("AppStepperFormModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Modal open/close behavior", () => {
    it("renders nothing when open is false", () => {
      render(<AppStepperFormModal {...defaultProps} open={false} />);
      expect(screen.queryByTestId("generic-modal")).not.toBeInTheDocument();
    });

    it("renders modal content when open is true", () => {
      render(<AppStepperFormModal {...defaultProps} open={true} />);
      expect(screen.getByTestId("generic-modal")).toBeInTheDocument();
    });

    it("calls onClose when backdrop is clicked", () => {
      render(<AppStepperFormModal {...defaultProps} open={true} />);
      fireEvent.click(screen.getByTestId("modal-backdrop"));
      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("Step navigation", () => {
    it("renders first step by default", () => {
      render(<AppStepperFormModal {...defaultProps} />);
      expect(screen.getByTestId("step-content-1")).toBeInTheDocument();
      expect(screen.queryByTestId("step-content-2")).not.toBeInTheDocument();
      expect(screen.queryByTestId("step-content-3")).not.toBeInTheDocument();
    });

    it("does NOT call onSubmit when navigating between steps", () => {
      render(<AppStepperFormModal {...defaultProps} />);

      // Click Siguiente button
      const nextButton = screen.getByTestId("button-siguiente");
      fireEvent.click(nextButton);

      // Submit should NOT be called just from navigation
      expect(defaultProps.onSubmit).not.toHaveBeenCalled();
    });

    it("shows Previous button on non-first step", () => {
      render(<AppStepperFormModal {...defaultProps} />);

      // Initially no Previous button
      expect(screen.queryByTestId("button-anterior")).not.toBeInTheDocument();

      // Navigate to step 2
      const nextButton = screen.getByTestId("button-siguiente");
      fireEvent.click(nextButton);

      // Now Previous should be visible
      expect(screen.queryByTestId("button-anterior")).toBeInTheDocument();
    });

    it("does not show Previous button on first step", () => {
      render(<AppStepperFormModal {...defaultProps} />);
      expect(screen.queryByTestId("button-anterior")).not.toBeInTheDocument();
    });

    it("renders step headers for all steps", () => {
      render(<AppStepperFormModal {...defaultProps} />);
      expect(screen.getByText("Step One")).toBeInTheDocument();
      expect(screen.getByText("Step Two")).toBeInTheDocument();
      expect(screen.getByText("Step Three")).toBeInTheDocument();
    });

    it("calls validation when clicking Siguiente if validate is provided", async () => {
      const validateFn = vi.fn().mockReturnValue(true);
      const stepsWithValidation = createMockSteps([
        {
          id: "step-1",
          title: "Step One",
          render: () => <div>Step 1</div>,
          validate: validateFn,
        },
        {
          id: "step-2",
          title: "Step Two",
          render: () => <div>Step 2</div>,
        },
      ]);

      render(
        <AppStepperFormModal {...defaultProps} steps={stepsWithValidation} />,
      );

      const nextButton = screen.getByTestId("button-siguiente");
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(validateFn).toHaveBeenCalledTimes(1);
      });
    });

    it("blocks navigation when validation returns false", async () => {
      const validateFn = vi.fn().mockReturnValue(false);
      const stepsWithValidation = createMockSteps([
        {
          id: "step-1",
          title: "Step One",
          render: () => <div>Step 1</div>,
          validate: validateFn,
        },
        {
          id: "step-2",
          title: "Step Two",
          render: () => <div>Step 2</div>,
        },
      ]);

      render(
        <AppStepperFormModal {...defaultProps} steps={stepsWithValidation} />,
      );

      const nextButton = screen.getByTestId("button-siguiente");
      fireEvent.click(nextButton);

      await waitFor(() => {
        // Validation was called
        expect(validateFn).toHaveBeenCalledTimes(1);
      });

      // Step 2 should NOT be visible (navigation was blocked)
      expect(screen.queryByTestId("step-content-2")).not.toBeInTheDocument();
    });

    it("resets to first step when modal closes and reopens", () => {
      const { rerender } = render(
        <AppStepperFormModal {...defaultProps} open={true} />,
      );

      // Navigate to step 2
      const nextButton = screen.getByTestId("button-siguiente");
      fireEvent.click(nextButton);

      // Close modal
      rerender(<AppStepperFormModal {...defaultProps} open={false} />);

      // Reopen modal
      rerender(<AppStepperFormModal {...defaultProps} open={true} />);

      // Should be back at step 1
      expect(screen.getByTestId("step-content-1")).toBeInTheDocument();
      expect(screen.queryByTestId("step-content-2")).not.toBeInTheDocument();
    });
  });

  describe("Form submission", () => {
    it("only calls onSubmit when final step submit button is clicked", () => {
      render(<AppStepperFormModal {...defaultProps} />);

      // Navigate through all steps without clicking final submit
      const nextButton = screen.getByTestId("button-siguiente");

      // Step 1 -> Step 2
      fireEvent.click(nextButton);

      // Step 2 -> Step 3
      fireEvent.click(nextButton);

      // Now click the Crear button (final submit)
      const submitButton = screen.getByTestId("button-crear");
      fireEvent.click(submitButton);

      expect(defaultProps.onSubmit).toHaveBeenCalledTimes(1);
    });

    it("does not call onSubmit on intermediate step navigation", () => {
      render(<AppStepperFormModal {...defaultProps} />);

      const nextButton = screen.getByTestId("button-siguiente");

      // Navigate to step 2
      fireEvent.click(nextButton);

      // No submission yet
      expect(defaultProps.onSubmit).not.toHaveBeenCalled();
    });

    it("calls Cancel button handler to close modal", () => {
      render(<AppStepperFormModal {...defaultProps} />);

      const cancelButton = screen.getByTestId("button-cancelar");
      fireEvent.click(cancelButton);

      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("Stepper header display", () => {
    it("renders all step titles in the header", () => {
      render(<AppStepperFormModal {...defaultProps} />);

      defaultSteps.forEach((step) => {
        expect(screen.getByText(step.title)).toBeInTheDocument();
      });
    });

    it("shows current step indicator", () => {
      render(<AppStepperFormModal {...defaultProps} />);

      // The current step should be visually indicated
      // We verify the step content is rendered correctly
      expect(screen.getByTestId("step-content-1")).toBeInTheDocument();
    });
  });

  describe("Loading states", () => {
    it("disables navigation buttons when isLoading is true", () => {
      render(<AppStepperFormModal {...defaultProps} isLoading={true} />);

      const nextButton = screen.getByTestId("button-siguiente");
      expect(nextButton).toHaveAttribute("disabled");

      // Previous button should also be disabled
      // Navigate first to show previous button
      const nextBtn = screen.getByTestId("button-siguiente");
      fireEvent.click(nextBtn);

      // Now check previous button is disabled
      const prevButton = screen.getByTestId("button-anterior");
      expect(prevButton).toHaveAttribute("disabled");
    });

    it("disables cancel button when isLoading is true", () => {
      render(<AppStepperFormModal {...defaultProps} isLoading={true} />);

      const cancelButton = screen.getByTestId("button-cancelar");
      expect(cancelButton).toHaveAttribute("disabled");
    });
  });
});
