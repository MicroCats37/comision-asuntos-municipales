import { vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { MeResponse } from "@/features/auth/schemas/auth.types";
import { ProtectedSidebar } from "./ProtectedSidebar";
import * as nextNavigation from "next/navigation";

// ── Mock next/navigation ──────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
  })),
}));

// ── Mock useAuthStore ─────────────────────────────────────────────────────────

const mockLogout = vi.fn();

vi.mock("@/features/auth/store/auth.store", () => ({
  useAuthStore: vi.fn(() => ({
    logout: mockLogout,
  })),
}));

// ── Mock useIsMobile ──────────────────────────────────────────────────────────

vi.mock("@/hooks/use-mobile", () => ({
  useIsMobile: vi.fn(() => false),
}));

// ── Mock UI components ────────────────────────────────────────────────────────

vi.mock("@/components/ui/avatar", () => ({
  Avatar: vi.fn(({ children }) => (
    <div data-testid="avatar">{children}</div>
  )),
  AvatarFallback: vi.fn(({ children }) => (
    <div data-testid="avatar-fallback">{children}</div>
  )),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const mockUser: MeResponse = {
  id: 1,
  email: "test@example.com",
  nombres: "Test",
  apellidos: "User",
  rol: "admin" as const,
};

const setupPathname = (path: string) => {
  (nextNavigation.usePathname as ReturnType<typeof vi.fn>).mockReturnValue(path);
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("ProtectedSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupPathname("/");
  });

  describe("Desktop rendering", () => {
    it("renders sidebar on desktop", () => {
      const { container } = render(<ProtectedSidebar user={mockUser} />);
      expect(container.querySelector("aside")).toBeInTheDocument();
    });

    it("displays user name in footer", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Test User")).toBeInTheDocument();
    });

    it("displays CAM Liquidaciones branding", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("CAM Liquidaciones")).toBeInTheDocument();
    });

    it("renders Dashboard link as active when on root path", () => {
      setupPathname("/");
      render(<ProtectedSidebar user={mockUser} />);
      const dashboardLink = screen.getByText("Dashboard");
      expect(dashboardLink.closest("a")).toHaveClass(
        "bg-sidebar-accent",
      );
    });
  });

  describe("Navigation items", () => {
    it("renders Liquidaciones accordion group", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Liquidaciones")).toBeInTheDocument();
    });

    it("renders all 6 Liquidaciones sub-items", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Edificaciones")).toBeInTheDocument();
      expect(screen.getByText("Habilitación Urbana")).toBeInTheDocument();
      expect(screen.getByText("Mecánica de Suelos")).toBeInTheDocument();
      expect(screen.getByText("Impacto Vial")).toBeInTheDocument();
      expect(screen.getByText("Taludes")).toBeInTheDocument();
      expect(screen.getByText("Inspección de Obra")).toBeInTheDocument();
    });

    it("renders Operativa accordion group", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Operativa")).toBeInTheDocument();
    });

    it("renders Delegados and Inspectores under Operativa", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Delegados")).toBeInTheDocument();
      expect(screen.getByText("Inspectores")).toBeInTheDocument();
    });

    it("renders Finanzas accordion group", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Finanzas")).toBeInTheDocument();
    });

    it("renders Finanzas and Matriz Histórica under Finanzas", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Finanzas")).toBeInTheDocument();
      expect(screen.getByText("Matriz Histórica")).toBeInTheDocument();
    });
  });

  describe("Active route highlighting", () => {
    it("highlights Edificaciones when on that path", () => {
      setupPathname("/liquidaciones/edificaciones");
      render(<ProtectedSidebar user={mockUser} />);
      const edificacionesLink = screen.getByText("Edificaciones");
      expect(edificacionesLink.closest("a")).toHaveClass("bg-sidebar-accent");
    });

    it("highlights Delegados when on that path", () => {
      setupPathname("/delegados");
      render(<ProtectedSidebar user={mockUser} />);
      const delegadosLink = screen.getByText("Delegados");
      expect(delegadosLink.closest("a")).toHaveClass("bg-sidebar-accent");
    });

    it("highlights Finanzas when on /finanzas path", () => {
      setupPathname("/finanzas");
      render(<ProtectedSidebar user={mockUser} />);
      const finanzasLink = screen.getByText("Finanzas").closest("button");
      expect(finanzasLink).toHaveClass("bg-sidebar-accent");
    });

    it("highlights Matriz Histórica when on /tarifario path", () => {
      setupPathname("/tarifario");
      render(<ProtectedSidebar user={mockUser} />);
      const matrizLink = screen.getByText("Matriz Histórica");
      expect(matrizLink.closest("a")).toHaveClass("bg-sidebar-accent");
    });
  });

  describe("Logout functionality", () => {
    it("renders logout button", () => {
      render(<ProtectedSidebar user={mockUser} />);
      expect(screen.getByText("Cerrar sesión")).toBeInTheDocument();
    });

    it("logout button calls logout and redirects to /login", async () => {
      const mockRouterPush = vi.fn();
      (nextNavigation.useRouter as ReturnType<typeof vi.fn>).mockReturnValue({
        push: mockRouterPush,
        replace: vi.fn(),
      });

      render(<ProtectedSidebar user={mockUser} />);

      const logoutButton = screen.getByText("Cerrar sesión");
      logoutButton.click();

      // Wait for async logout handler
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(mockLogout).toHaveBeenCalled();
      expect(mockRouterPush).toHaveBeenCalledWith("/login");
    });
  });

  describe("Responsive behavior", () => {
    it("renders desktop sidebar without hamburger menu button", () => {
      const { container } = render(<ProtectedSidebar user={mockUser} />);
      // Desktop sidebar should NOT have the floating menu button
      expect(
        container.querySelector('[aria-label="Abrir menú"]'),
      ).not.toBeInTheDocument();
    });

    it("renders mobile sidebar with hamburger menu button", () => {
      // Override the useIsMobile mock for this test
      const { useIsMobile } = vi.importMock("@/hooks/use-mobile")();
      (useIsMobile as ReturnType<typeof vi.fn>).mockReturnValue(true);

      const { container } = render(<ProtectedSidebar user={mockUser} />);

      // Mobile should show hamburger button
      expect(container.querySelector('[aria-label="Abrir menú"]')).toBeInTheDocument();
    });
  });

  describe("Routing structure", () => {
    it("all Liquidaciones sub-items have correct href attributes", () => {
      render(<ProtectedSidebar user={mockUser} />);

      const liquidacionesItems = [
        { text: "Edificaciones", href: "/liquidaciones/edificaciones" },
        {
          text: "Habilitación Urbana",
          href: "/liquidaciones/habilitacion-urbana",
        },
        { text: "Mecánica de Suelos", href: "/liquidaciones/mecanica-suelos" },
        { text: "Impacto Vial", href: "/liquidaciones/impacto-vial" },
        { text: "Taludes", href: "/liquidaciones/taludes" },
        {
          text: "Inspección de Obra",
          href: "/liquidaciones/inspeccion-obra",
        },
      ];

      liquidacionesItems.forEach(({ text, href }) => {
        const link = screen.getByText(text).closest("a");
        expect(link).toHaveAttribute("href", href);
      });
    });

    it("Operativa items have correct href attributes", () => {
      render(<ProtectedSidebar user={mockUser} />);

      expect(screen.getByText("Delegados").closest("a")).toHaveAttribute(
        "href",
        "/delegados",
      );
      expect(screen.getByText("Inspectores").closest("a")).toHaveAttribute(
        "href",
        "/inspectores",
      );
    });

    it("Finanzas items have correct href attributes", () => {
      render(<ProtectedSidebar user={mockUser} />);

      expect(screen.getByText("Finanzas").closest("a")).toHaveAttribute(
        "href",
        "/finanzas",
      );
      expect(screen.getByText("Matriz Histórica").closest("a")).toHaveAttribute(
        "href",
        "/tarifario",
      );
    });
  });
});
