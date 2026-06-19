"use client";

import { useState } from "react";
import { FileText, LogOutIcon, Menu, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import {
  Avatar,
  AvatarFallback,
} from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import type { MeResponse } from "@/features/auth/schemas/auth.types";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { useIsMobile } from "@/hooks/use-mobile";

/**
 * Navigation items for protected routes.
 * isActive is determined dynamically via usePathname in the component.
 */
const navItems = [
  {
    title: "Liquidaciones",
    icon: FileText,
    href: "/liquidaciones",
  },
];

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
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                onClick={handleNavClick}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
                )}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <span className="min-w-0 truncate">{item.title}</span>
              </a>
            );
          })}
        </div>
      </nav>

      {/* Footer - User info and logout */}
      <div className="border-t border-sidebar-border p-2">
        {/* User info */}
        <div className="flex items-center gap-3 px-3 py-3">
          <Avatar size="sm" className="shrink-0">
            <AvatarFallback>
              {user.nombre?.charAt(0) ?? ""}{user.apellido?.charAt(0) ?? ""}
            </AvatarFallback>
          </Avatar>
          <div className="flex min-w-0 flex-col">
            <p className="truncate text-sm font-medium">
              {user.nombre} {user.apellido}
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
