"use client";

import { ChevronDown, LogOutIcon, Menu, X } from "lucide-react";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { MeResponse } from "@/features/auth/schemas/auth.types";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { useIsMobile } from "@/hooks/use-mobile";
import { clearAuthSessionAndRedirect } from "@/lib/auth/session-client";
import { cn } from "@/lib/utils";
import {
  isEntryActive,
  isItemActive,
  NAV_ENTRIES,
  type NavEntry,
  type NavGroup,
  type NavItem,
} from "./nav-config";

/**
 * ProtectedSidebar - institutional wine/gold sidebar for authenticated routes.
 *
 * Visual language shared with the Mesa de Partes app: deep wine gradient
 * surface, gold accents, icon tiles and a user dropdown in the footer.
 * CAM keeps its own route tree (Liquidación, Operativa, Finanzas, Recibos).
 *
 * Desktop supports collapse/expand (persisted in localStorage); mobile uses a
 * floating toggle with a slide-in overlay.
 */

const COLLAPSED_STORAGE_KEY = "cam-sidebar-collapsed";

/** Wine gradient surface shared by the desktop rail and the mobile overlay. */
const SIDEBAR_SURFACE =
  "bg-[radial-gradient(circle_at_top_left,oklch(0.55_0.15_25),transparent_18rem),linear-gradient(180deg,oklch(0.38_0.16_22),oklch(0.25_0.12_24))]";

/** Top level row (direct link or accordion header). */
const NAV_ROW_BASE =
  "group/item relative flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-sm font-bold transition-all duration-200 ease-out";

/** Icon tile used by every row — the active state turns it solid white. */
const ICON_TILE_BASE =
  "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-all duration-200";
const ICON_TILE_ACTIVE = "bg-white text-primary shadow-sm";
const ICON_TILE_IDLE =
  "bg-white/10 text-white/80 group-hover/item:bg-white/15 group-hover/item:text-white";

/** Nested row (children of a group). */
const NAV_CHILD_BASE =
  "relative flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200";

/** Gold marker for the active route. */
const ACTIVE_MARKER =
  "absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-accent shadow-sm";

interface SidebarChildrenProps {
  items: NavItem[];
  pathname: string;
  depth: number;
  onNavigate: () => void;
}

/**
 * Renders one level of the navigation tree (recursively).
 */
function SidebarChildren({
  items,
  pathname,
  depth,
  onNavigate,
}: SidebarChildrenProps) {
  return (
    <div
      className={cn(
        "mt-1 space-y-0.5 border-l border-white/15",
        depth === 1 ? "ml-4 pl-3" : "ml-3 pl-3",
      )}
    >
      {items.map((item) => {
        const grandchildren = item.children ?? [];

        if (grandchildren.length === 0) {
          const active = isItemActive(pathname, item);
          return (
            <a
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                NAV_CHILD_BASE,
                active
                  ? "bg-white/15 font-bold text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white",
              )}
            >
              {active && <span className={ACTIVE_MARKER} aria-hidden="true" />}
              <span className="min-w-0 truncate">{item.title}</span>
            </a>
          );
        }

        return (
          <div key={item.href} className="space-y-0.5">
            <p className="px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-white/45">
              {item.title}
            </p>
            <SidebarChildren
              items={grandchildren}
              pathname={pathname}
              depth={depth + 1}
              onNavigate={onNavigate}
            />
          </div>
        );
      })}
    </div>
  );
}

interface SidebarEntryProps {
  entry: NavEntry;
  pathname: string;
  expanded: boolean;
  isGroupOpen: boolean;
  onToggleGroup: () => void;
  onNavigate: () => void;
}

/**
 * Renders a top level entry — either a direct link or an accordion group.
 */
function SidebarEntry({
  entry,
  pathname,
  expanded,
  isGroupOpen,
  onToggleGroup,
  onNavigate,
}: SidebarEntryProps) {
  const active = isEntryActive(pathname, entry);

  if (entry.type === "link") {
    if (!expanded) {
      return (
        <a
          href={entry.href}
          onClick={onNavigate}
          title={entry.title}
          aria-label={entry.title}
          aria-current={active ? "page" : undefined}
          className="flex w-full items-center justify-center"
        >
          <span
            className={cn(
              ICON_TILE_BASE,
              active ? ICON_TILE_ACTIVE : ICON_TILE_IDLE,
            )}
          >
            <entry.icon className="h-3.5 w-3.5" />
          </span>
        </a>
      );
    }

    return (
      <a
        href={entry.href}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className={cn(
          NAV_ROW_BASE,
          active
            ? "bg-white/15 text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
            : "text-white/78 hover:bg-white/10 hover:text-white",
        )}
      >
        {active && (
          <span
            className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-accent shadow-sm"
            aria-hidden="true"
          />
        )}
        <span
          className={cn(
            ICON_TILE_BASE,
            active ? ICON_TILE_ACTIVE : ICON_TILE_IDLE,
          )}
        >
          <entry.icon className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1 truncate">{entry.title}</span>
      </a>
    );
  }

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={onToggleGroup}
        title={entry.title}
        aria-label={entry.title}
        className="flex w-full cursor-pointer items-center justify-center"
      >
        <span
          className={cn(
            ICON_TILE_BASE,
            active ? ICON_TILE_ACTIVE : ICON_TILE_IDLE,
          )}
        >
          <entry.icon className="h-3.5 w-3.5" />
        </span>
      </button>
    );
  }

  return (
    <div className="space-y-0.5">
      <button
        type="button"
        onClick={onToggleGroup}
        aria-expanded={isGroupOpen}
        className={cn(
          NAV_ROW_BASE,
          active
            ? "bg-white/15 text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
            : "text-white/78 hover:bg-white/10 hover:text-white",
        )}
      >
        <span
          className={cn(
            ICON_TILE_BASE,
            active ? ICON_TILE_ACTIVE : ICON_TILE_IDLE,
          )}
        >
          <entry.icon className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1 truncate text-left">{entry.title}</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 transition-transform duration-200",
            isGroupOpen && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>

      <div
        className={cn(
          "overflow-hidden transition-all duration-200 ease-in-out",
          isGroupOpen ? "max-h-[32rem] opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <SidebarChildren
          items={entry.children}
          pathname={pathname}
          depth={1}
          onNavigate={onNavigate}
        />
      </div>
    </div>
  );
}

export function ProtectedSidebar({ user }: { user: MeResponse }) {
  const pathname = usePathname();
  const logout = useAuthStore((state) => state.logout);
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Explicit user overrides only. Groups without an override fall back to
  // "open when the current route belongs to them" (see isGroupOpen below).
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});

  // Restore the persisted collapse preference after hydration.
  useEffect(() => {
    try {
      if (window.localStorage.getItem(COLLAPSED_STORAGE_KEY) === "true") {
        setCollapsed(true);
      }
    } catch {
      // localStorage unavailable — keep the default expanded state.
    }
  }, []);

  const showLabels = isMobile || !collapsed;

  /**
   * A group is open when the user explicitly toggled it, otherwise it follows
   * the current route: only the group owning the active page starts open.
   */
  const isGroupOpen = (entry: NavGroup): boolean =>
    openGroups[entry.title] ?? isEntryActive(pathname, entry);

  const handleToggleCollapse = () => {
    setCollapsed((previous) => {
      const next = !previous;
      try {
        window.localStorage.setItem(COLLAPSED_STORAGE_KEY, String(next));
      } catch {
        // Persistence is best-effort.
      }
      return next;
    });
  };

  const handleToggleGroup = (entry: NavEntry) => {
    if (entry.type !== "group") return;

    if (collapsed && !isMobile) {
      // Collapsed rail: expand first, then reveal the requested group.
      setCollapsed(false);
      setOpenGroups((previous) => ({ ...previous, [entry.title]: true }));
      return;
    }
    setOpenGroups((previous) => ({
      ...previous,
      [entry.title]: !(previous[entry.title] ?? isEntryActive(pathname, entry)),
    }));
  };

  const handleLogout = async () => {
    logout();
    await clearAuthSessionAndRedirect();
  };

  const handleNavigate = () => {
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const brand = (
    <>
      <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white shadow-lg shadow-black/20 ring-2 ring-white/30">
        <Image
          src="/images/logo.png"
          alt="Logo del Colegio de Ingenieros del Perú"
          width={42}
          height={42}
          className="h-10 w-10 object-contain"
          priority
        />
      </div>
      {showLabels && (
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="text-pretty text-[13px] font-black leading-[1.25] tracking-tight text-white">
            Comisión de Asuntos Municipales
          </span>
          <span className="text-pretty text-[9px] font-semibold uppercase leading-[1.45] tracking-[0.14em] text-white/70">
            Colegio de Ingenieros del Perú
          </span>
        </div>
      )}
    </>
  );

  const sidebarContent = (
    <>
      {/* Brand panel — doubles as the collapse toggle on desktop */}
      {isMobile ? (
        <div className="flex items-center gap-3 border-b border-white/10 bg-white/[0.04] px-5 py-5 pr-14">
          {brand}
        </div>
      ) : (
        <button
          type="button"
          onClick={handleToggleCollapse}
          title={collapsed ? "Expandir menú lateral" : "Colapsar menú lateral"}
          aria-label={
            collapsed ? "Expandir menú lateral" : "Colapsar menú lateral"
          }
          aria-expanded={!collapsed}
          className={cn(
            "relative flex w-full cursor-pointer border-b border-white/10 bg-white/[0.04] transition-colors hover:bg-white/[0.07] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 focus-visible:ring-inset",
            collapsed
              ? "h-16 items-center justify-center"
              : "items-center gap-3 px-5 py-5",
          )}
        >
          {brand}
        </button>
      )}

      {/* Navigation */}
      <nav className="sidebar-scroll flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        {showLabels && (
          <p className="mb-3 px-2 text-[10px] font-black uppercase tracking-[0.22em] text-white/45">
            Navegación
          </p>
        )}

        <div className="space-y-1">
          {NAV_ENTRIES.map((entry) => (
            <SidebarEntry
              key={entry.type === "link" ? entry.href : entry.title}
              entry={entry}
              pathname={pathname}
              expanded={showLabels}
              isGroupOpen={entry.type === "group" ? isGroupOpen(entry) : false}
              onToggleGroup={() => handleToggleGroup(entry)}
              onNavigate={handleNavigate}
            />
          ))}
        </div>
      </nav>

      {/* Gold separator above the footer */}
      <div
        className="mx-4 mb-1 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent"
        aria-hidden="true"
      />

      {/* Footer — user dropdown with the logout action */}
      <div className="border-t border-white/10 px-3 py-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className={cn(
                "flex w-full cursor-pointer items-center gap-3 rounded-2xl bg-white/8 px-3 py-3 backdrop-blur-sm transition-colors duration-200 hover:bg-white/12",
                !showLabels && "justify-center px-0",
              )}
              title={
                showLabels ? undefined : `${user.nombres} ${user.apellidos}`
              }
            >
              <Avatar className="shrink-0 ring-2 ring-white/25 after:border-white/30 after:mix-blend-normal">
                <AvatarFallback className="bg-white text-xs font-bold text-primary">
                  {user.nombres?.charAt(0) ?? ""}
                  {user.apellidos?.charAt(0) ?? ""}
                </AvatarFallback>
              </Avatar>
              {showLabels && (
                <div className="flex min-w-0 flex-col text-left">
                  <p className="truncate text-sm font-bold text-white">
                    {user.nombres} {user.apellidos}
                  </p>
                  <p className="truncate text-[10px] text-white/55">
                    Colegio de Ingenieros
                  </p>
                </div>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" sideOffset={8} className="w-52">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col gap-0.5">
                <p className="text-sm font-semibold">
                  {user.nombres} {user.apellidos}
                </p>
                <p className="text-xs text-muted-foreground">
                  Colegio de Ingenieros
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              className="gap-2"
              onClick={handleLogout}
            >
              <LogOutIcon className="h-4 w-4" />
              <span>Cerrar sesión</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </>
  );

  // Mobile: floating toggle + overlay sidebar with backdrop
  if (isMobile) {
    return (
      <>
        {!mobileOpen && (
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
            className={cn(
              "fixed top-4 left-4 z-40 flex h-10 w-10 cursor-pointer items-center justify-center rounded-xl",
              "bg-primary text-primary-foreground shadow-lg",
              "transition-all duration-200 ease-out hover:scale-105 hover:bg-primary/90 active:scale-95",
            )}
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        {mobileOpen && (
          <button
            type="button"
            aria-label="Cerrar menú"
            onClick={() => setMobileOpen(false)}
            className="fixed inset-0 z-40 cursor-default bg-black/30 backdrop-blur-sm"
          />
        )}

        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 flex w-72 flex-col text-white shadow-2xl",
            SIDEBAR_SURFACE,
            "transform transition-transform duration-300 ease-out",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
            className={cn(
              "absolute top-4 right-4 flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg",
              "text-white/70 transition-all duration-200",
              "hover:bg-white/10 hover:text-white active:scale-95",
            )}
          >
            <X className="h-5 w-5" />
          </button>

          {sidebarContent}
        </aside>
      </>
    );
  }

  // Desktop: collapsible wine rail
  return (
    <aside
      className={cn(
        "flex h-svh flex-col border-r border-primary/20 text-white shadow-xl shadow-primary/10 transition-[width] duration-300 ease-out",
        SIDEBAR_SURFACE,
        collapsed ? "w-[4.75rem]" : "w-64",
      )}
    >
      {sidebarContent}
    </aside>
  );
}
