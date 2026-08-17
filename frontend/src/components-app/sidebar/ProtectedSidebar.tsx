"use client";

import {
  ChevronDown,
  DollarSign,
  FileText,
  LogOutIcon,
  Menu,
  Receipt,
  Users,
  X,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { MeResponse } from "@/features/auth/schemas/auth.types";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

/**
 * Accordion group for Liquidaciones with General and Edificaciones sub-items.
 */
const liquidacionesGroup = {
  title: "Liquidación",
  icon: FileText,
  children: [
    {
      title: "Edificaciones",
      href: "/liquidaciones/edificaciones",
    },
    {
      title: "Habilitación Urbana",
      href: "/liquidaciones/habilitacion-urbana",
    },
    {
      title: "Mecánica de Suelos",
      href: "/liquidaciones/mecanica-suelos",
    },
    {
      title: "Impacto Vial",
      href: "/liquidaciones/impacto-vial",
    },
    {
      title: "Taludes",
      href: "/liquidaciones/taludes",
    },
    {
      title: "Inspección de Obra",
      href: "/liquidaciones/inspeccion-obra",
    },
  ],
};

/**
 * Accordion group for Operativa with Delegados and Inspectores sub-items.
 */
const operativaGroup = {
  title: "Operativa",
  icon: Users,
  children: [
    {
      title: "Delegados",
      href: "/liquidaciones/delegados",
    },
    {
      title: "Inspectores",
      href: "/liquidaciones/inspectores",
    },
  ],
};

/**
 * Accordion group for Finanzas with Tarifas sub-item.
 */
const finanzasGroup = {
  title: "Finanzas",
  icon: DollarSign,
  children: [
    {
      title: "Tarifas",
      href: "/liquidaciones/finanzas",
    },
  ],
};

/**
 * Accordion group for Recibos por Honorario.
 */
const recibosGroup = {
  title: "Recibos por Honorario",
  icon: Receipt,
  children: [
    {
      title: "Recibos Delegados",
      href: "/liquidaciones/recibos-delegados",
    },
    {
      title: "Recibos Inspectores",
      href: "/liquidaciones/recibos-inspectores",
    },
  ],
};

/**
 * ProtectedSidebar - provides sidebar navigation for authenticated routes.
 * Fully responsive: desktop shows a bordered sidebar; mobile shows a floating
 * toggle button and a slide-in overlay with backdrop blur.
 */
export function ProtectedSidebar({ user }: { user: MeResponse }) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const isMobile = useIsMobile();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [liquidacionesOpen, setLiquidacionesOpen] = useState(true);
  const [operativaOpen, setOperativaOpen] = useState(true);
  const [finanzasOpen, setFinanzasOpen] = useState(true);
  const [recibosOpen, setRecibosOpen] = useState(true);

  const handleLogout = async () => {
    try {
      const { clearAuthCookies } = await import("@/lib/auth");
      await clearAuthCookies();
      logout();
      router.push("/login");
    } catch {
      // If clearAuthCookies fails, still logout locally
      logout();
      router.push("/login");
    }
  };

  const handleNavClick = () => {
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const isChildActive = liquidacionesGroup.children.some(
    (child) => pathname === child.href,
  );

  const isOperativaChildActive = operativaGroup.children.some(
    (child) => pathname === child.href,
  );

  const isFinanzasChildActive = finanzasGroup.children.some(
    (child) => pathname === child.href,
  );

  const isRecibosChildActive = recibosGroup.children.some(
    (child) => pathname === child.href,
  );

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-sidebar-border px-4 py-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
          <FileText className="h-5 w-5" />
        </div>
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm font-bold">CAM Liquidaciones</span>
          <span className="truncate text-xs text-muted-foreground">CAM</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-auto p-2">
        <div className="space-y-1">
          {/* Liquidación Accordion Group */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setLiquidacionesOpen((prev) => !prev)}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isChildActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
              )}
            >
              <liquidacionesGroup.icon className="h-4 w-4 shrink-0" />
              <span className="min-w-0 truncate flex-1 text-left">
                {liquidacionesGroup.title}
              </span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform duration-200",
                  liquidacionesOpen && "rotate-180",
                )}
              />
            </button>

            {/* Sub-items */}
            <div
              className={cn(
                "overflow-hidden transition-all duration-200 ease-in-out",
                liquidacionesOpen
                  ? "max-h-96 opacity-100"
                  : "max-h-0 opacity-0",
              )}
            >
              <div className="ml-4 mt-1 space-y-0.5 border-l border-sidebar-border pl-3">
                {liquidacionesGroup.children.map((child) => {
                  const isActive = pathname === child.href;
                  return (
                    <a
                      key={child.href}
                      href={child.href}
                      onClick={handleNavClick}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
                      )}
                    >
                      <span className="min-w-0 truncate">{child.title}</span>
                    </a>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Operativa Accordion Group */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setOperativaOpen((prev) => !prev)}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isOperativaChildActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
              )}
            >
              <operativaGroup.icon className="h-4 w-4 shrink-0" />
              <span className="min-w-0 truncate flex-1 text-left">
                {operativaGroup.title}
              </span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform duration-200",
                  operativaOpen && "rotate-180",
                )}
              />
            </button>

            {/* Sub-items */}
            <div
              className={cn(
                "overflow-hidden transition-all duration-200 ease-in-out",
                operativaOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0",
              )}
            >
              <div className="ml-4 mt-1 space-y-0.5 border-l border-sidebar-border pl-3">
                {operativaGroup.children.map((child) => {
                  const isActive = pathname === child.href;
                  return (
                    <a
                      key={child.href}
                      href={child.href}
                      onClick={handleNavClick}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
                      )}
                    >
                      <span className="min-w-0 truncate">{child.title}</span>
                    </a>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Finanzas Accordion Group */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setFinanzasOpen((prev) => !prev)}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isFinanzasChildActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
              )}
            >
              <finanzasGroup.icon className="h-4 w-4 shrink-0" />
              <span className="min-w-0 truncate flex-1 text-left">
                {finanzasGroup.title}
              </span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform duration-200",
                  finanzasOpen && "rotate-180",
                )}
              />
            </button>

            {/* Sub-items */}
            <div
              className={cn(
                "overflow-hidden transition-all duration-200 ease-in-out",
                finanzasOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0",
              )}
            >
              <div className="ml-4 mt-1 space-y-0.5 border-l border-sidebar-border pl-3">
                {finanzasGroup.children.map((child) => {
                  const isActive = pathname === child.href;
                  return (
                    <a
                      key={child.href}
                      href={child.href}
                      onClick={handleNavClick}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
                      )}
                    >
                      <span className="min-w-0 truncate">{child.title}</span>
                    </a>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Recibos por Honorario Accordion Group */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setRecibosOpen((prev) => !prev)}
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isRecibosChildActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
              )}
            >
              <recibosGroup.icon className="h-4 w-4 shrink-0" />
              <span className="min-w-0 truncate flex-1 text-left">
                {recibosGroup.title}
              </span>
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 shrink-0 transition-transform duration-200",
                  recibosOpen && "rotate-180",
                )}
              />
            </button>

            {/* Sub-items */}
            <div
              className={cn(
                "overflow-hidden transition-all duration-200 ease-in-out",
                recibosOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0",
              )}
            >
              <div className="ml-4 mt-1 space-y-0.5 border-l border-sidebar-border pl-3">
                {recibosGroup.children.map((child) => {
                  const isActive = pathname === child.href;
                  return (
                    <a
                      key={child.href}
                      href={child.href}
                      onClick={handleNavClick}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
                        isActive
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
                      )}
                    >
                      <span className="min-w-0 truncate">{child.title}</span>
                    </a>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Footer - User info and logout */}
      <div className="border-t border-sidebar-border p-2">
        {/* User info */}
        <div className="flex items-center gap-3 px-3 py-3">
          <Avatar size="sm" className="shrink-0">
            <AvatarFallback>
              {user.nombres?.charAt(0) ?? ""}
              {user.apellidos?.charAt(0) ?? ""}
            </AvatarFallback>
          </Avatar>
          <div className="flex min-w-0 flex-col">
            <p className="truncate text-sm font-medium">
              {user.nombres} {user.apellidos}
            </p>
          </div>
        </div>

        {/* Logout button */}
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10 hover:text-destructive"
        >
          <LogOutIcon className="h-4 w-4 shrink-0" />
          <span className="min-w-0 truncate">Cerrar sesión</span>
        </button>
      </div>
    </>
  );

  // Mobile: floating toggle + overlay sidebar with backdrop
  if (isMobile) {
    return (
      <>
        {/* Floating menu button */}
        {!mobileOpen && (
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
            className="fixed top-4 left-4 z-40 flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background text-foreground shadow-lg transition-colors hover:bg-accent"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        {/* Backdrop */}
        {mobileOpen && (
          <div
            className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
        )}

        {/* Overlay sidebar */}
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 w-72 flex flex-col bg-sidebar text-sidebar-foreground shadow-2xl transform transition-transform duration-200 ease-in-out",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          {/* Mobile close trigger */}
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
            className="absolute top-4 right-4 flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          >
            <X className="h-5 w-5" />
          </button>

          {sidebarContent}
        </aside>
      </>
    );
  }

  // Desktop: standard sidebar with subtle shadow and right border
  return (
    <aside className="flex h-svh w-64 flex-col bg-sidebar text-sidebar-foreground border-r border-border shadow-sm">
      {sidebarContent}
    </aside>
  );
}
