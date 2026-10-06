"use client";

import { Phone, UserCog } from "lucide-react";
import type { LiquidacionGeneralOutput } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { cn } from "@/lib/utils";
import { DetalleSection } from "./DetalleSection";

interface Props {
  lg: LiquidacionGeneralOutput;
}

const formatContacto = (c: LiquidacionGeneralOutput["contacto"]) => {
  if (!c) return null;
  const name = [c.nombres, c.apellidos].filter(Boolean).join(" ");
  return name || null;
};

const formatUsuario = (u: LiquidacionGeneralOutput["usuario_creador"]) => {
  if (!u) return null;
  const name = [u.nombres, u.apellidos].filter(Boolean).join(" ");
  return name || u.username || null;
};

export function DetalleContactoSection({ lg }: Props) {
  const contacto = lg.contacto;
  const usuario = lg.usuario_creador;
  const hasAny = contacto != null || usuario != null;
  if (!hasAny) return null;

  return (
    <DetalleSection
      title="Contacto y registro"
      icon={UserCog}
      className="lg:col-span-6"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
        {contacto ? (
          <div className="space-y-2 min-w-0">
            <div className="flex items-center gap-1.5">
              <Phone className="h-3.5 w-3.5 text-muted-foreground/60" />
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                Contacto
              </span>
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                {formatContacto(contacto) ?? "-"}
              </p>
              {contacto.cargo ? (
                <p className="text-xs text-muted-foreground">
                  {contacto.cargo}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                {contacto.dni ? (
                  <span>
                    <span className="text-muted-foreground/60">DNI</span>{" "}
                    <span className="font-mono">{contacto.dni}</span>
                  </span>
                ) : null}
                {(contacto.celular ?? contacto.telefono) ? (
                  <span className="font-mono">
                    {contacto.celular ?? contacto.telefono}
                  </span>
                ) : null}
                {contacto.email ? (
                  <a
                    href={`mailto:${contacto.email}`}
                    className={cn(
                      "hover:text-primary transition-colors break-all",
                    )}
                  >
                    {contacto.email}
                  </a>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}

        {usuario ? (
          <div className="space-y-2 min-w-0">
            <div className="flex items-center gap-1.5">
              <UserCog className="h-3.5 w-3.5 text-muted-foreground/60" />
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                Creado por
              </span>
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                {formatUsuario(usuario) ?? "-"}
              </p>
              {usuario.username ? (
                <p className="text-xs text-muted-foreground">
                  @{usuario.username}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                {usuario.dni ? (
                  <span>
                    <span className="text-muted-foreground/60">DNI</span>{" "}
                    <span className="font-mono">{usuario.dni}</span>
                  </span>
                ) : null}
                {usuario.email ? (
                  <a
                    href={`mailto:${usuario.email}`}
                    className="hover:text-primary transition-colors"
                  >
                    {usuario.email}
                  </a>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </DetalleSection>
  );
}
