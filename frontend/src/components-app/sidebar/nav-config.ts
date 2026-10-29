import type { LucideIcon } from "lucide-react";
import { DollarSign, FileText, Receipt, Users } from "lucide-react";

/**
 * Navigation tree for the CAM protected shell.
 *
 * Kept separate from the sidebar component so the route tree stays declarative
 * and the active-route resolution stays unit-testable.
 */

/** Leaf entry — always a real route. */
export interface NavItem {
  title: string;
  href: string;
  /** Third level (e.g. Recibos Delegados → Mensual). */
  children?: NavItem[];
}

/** Direct link entry (no children, no accordion). */
export interface NavLink {
  type: "link";
  title: string;
  href: string;
  icon: LucideIcon;
}

/** Accordion entry with one level of children. */
export interface NavGroup {
  type: "group";
  title: string;
  icon: LucideIcon;
  children: NavItem[];
}

export type NavEntry = NavLink | NavGroup;

export const NAV_ENTRIES: NavEntry[] = [
  {
    type: "group",
    title: "Liquidación",
    icon: FileText,
    children: [
      { title: "Edificaciones", href: "/liquidaciones/edificaciones" },
      {
        title: "Habilitación Urbana",
        href: "/liquidaciones/habilitacion-urbana",
      },
      {
        title: "Mecánica de Suelos",
        href: "/liquidaciones/mecanica-suelos",
      },
      { title: "Impacto Vial", href: "/liquidaciones/impacto-vial" },
      { title: "Taludes", href: "/liquidaciones/taludes" },
      { title: "Inspección de Obra", href: "/liquidaciones/inspeccion-obra" },
    ],
  },
  {
    type: "group",
    title: "Operativa",
    icon: Users,
    children: [
      { title: "Delegados", href: "/liquidaciones/delegados" },
      { title: "Inspectores", href: "/liquidaciones/inspectores" },
    ],
  },
  {
    type: "group",
    title: "Finanzas",
    icon: DollarSign,
    children: [{ title: "Tarifas", href: "/liquidaciones/finanzas" }],
  },
  {
    type: "group",
    title: "Recibos por Honorario",
    icon: Receipt,
    children: [
      {
        title: "Recibos Delegados",
        href: "/liquidaciones/recibos-delegados/mensual",
        children: [
          {
            title: "Mensual",
            href: "/liquidaciones/recibos-delegados/mensual",
          },
          {
            title: "Detalle",
            href: "/liquidaciones/recibos-delegados/detalle",
          },
          {
            title: "Trimestral",
            href: "/liquidaciones/reparticiones-estacionales",
          },
        ],
      },
      {
        title: "Recibos Inspectores",
        href: "/liquidaciones/recibos-inspectores/mensual",
        children: [
          {
            title: "Mensual",
            href: "/liquidaciones/recibos-inspectores/mensual",
          },
          {
            title: "Detalle",
            href: "/liquidaciones/recibos-inspectores/detalle",
          },
        ],
      },
    ],
  },
];

/**
 * True when `pathname` is the target route or a nested route below it.
 * Detail pages (`/liquidaciones/edificaciones/12`) keep their parent active.
 */
export function isPathActive(pathname: string, href: string): boolean {
  if (!pathname || !href) return false;
  if (pathname === href) return true;
  return pathname.startsWith(`${href}/`);
}

/** True when the item or any of its descendants matches the current path. */
export function isItemActive(pathname: string, item: NavItem): boolean {
  if (isPathActive(pathname, item.href)) return true;
  return (item.children ?? []).some((child) => isItemActive(pathname, child));
}

/** True when the entry (link or group) contains the current path. */
export function isEntryActive(pathname: string, entry: NavEntry): boolean {
  if (entry.type === "link") {
    return isPathActive(pathname, entry.href);
  }
  return entry.children.some((child) => isItemActive(pathname, child));
}
