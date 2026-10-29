import { Building2 } from "lucide-react";
import { describe, expect, it } from "vitest";
import {
  isEntryActive,
  isItemActive,
  isPathActive,
  NAV_ENTRIES,
  type NavEntry,
  type NavGroup,
} from "./nav-config";

function findEntry(title: string): NavEntry {
  const entry = NAV_ENTRIES.find((candidate) => candidate.title === title);
  if (!entry) {
    throw new Error(`Nav entry "${title}" not found`);
  }
  return entry;
}

describe("isPathActive", () => {
  it("matches the exact route", () => {
    expect(
      isPathActive(
        "/liquidaciones/edificaciones",
        "/liquidaciones/edificaciones",
      ),
    ).toBe(true);
  });

  it("matches nested detail routes", () => {
    expect(
      isPathActive(
        "/liquidaciones/edificaciones/42",
        "/liquidaciones/edificaciones",
      ),
    ).toBe(true);
    expect(
      isPathActive(
        "/liquidaciones/reparticiones-estacionales/7",
        "/liquidaciones/reparticiones-estacionales",
      ),
    ).toBe(true);
  });

  it("does not match sibling routes with a shared prefix", () => {
    expect(
      isPathActive(
        "/liquidaciones/edificaciones-legacy",
        "/liquidaciones/edificaciones",
      ),
    ).toBe(false);
    expect(isPathActive("/liquidaciones", "/liquidaciones/edificaciones")).toBe(
      false,
    );
  });

  it("ignores empty input", () => {
    expect(isPathActive("", "/liquidaciones/edificaciones")).toBe(false);
    expect(isPathActive("/liquidaciones/edificaciones", "")).toBe(false);
  });
});

describe("isItemActive", () => {
  it("activates a nested leaf from its grandparent", () => {
    const recibos = findEntry("Recibos por Honorario") as NavGroup;
    const delegados = recibos.children[0];

    expect(
      isItemActive("/liquidaciones/recibos-delegados/detalle", delegados),
    ).toBe(true);
    expect(
      isItemActive("/liquidaciones/recibos-inspectores/mensual", delegados),
    ).toBe(false);
  });
});

describe("isEntryActive", () => {
  it("activates the group that owns the current route", () => {
    const liquidacion = findEntry("Liquidación");

    expect(isEntryActive("/liquidaciones/taludes/9", liquidacion)).toBe(true);
    expect(isEntryActive("/liquidaciones/delegados", liquidacion)).toBe(false);
  });

  it("activates a direct link on its own route only", () => {
    const link: NavEntry = {
      type: "link",
      title: "Proyectos",
      href: "/proyectos",
      icon: Building2,
    };

    expect(isEntryActive("/proyectos", link)).toBe(true);
    expect(isEntryActive("/liquidaciones", link)).toBe(false);
  });

  it("exposes only groups — no direct links in the CAM route tree", () => {
    expect(NAV_ENTRIES.every((entry) => entry.type === "group")).toBe(true);
  });
});
