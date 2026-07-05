"use client";

import { X } from "lucide-react";
import React, {
  createContext,
  useCallback,
  useContext,
  useImperativeHandle,
  useMemo,
  useState,
} from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type {
  GenericModalBodyProps,
  GenericModalCloseProps,
  GenericModalCloseXProps,
  GenericModalContentProps,
  GenericModalContextType,
  GenericModalFooterProps,
  GenericModalHeaderProps,
  GenericModalProps,
  GenericModalRef,
  GenericModalTriggerProps,
} from "./GenericModal.types";

/**
 * Internal Modal Context for Deep Component Communication
 */
const GenericModalContext = createContext<GenericModalContextType | undefined>(
  undefined,
);

/**
 * Hook to share modal state and actions with any child component
 */
export const useGenericModal = () => {
  const context = useContext(GenericModalContext);
  if (!context) {
    throw new Error(
      "useGenericModal must be used within a <GenericModal /> Provider",
    );
  }
  return context;
};

/**
 * GenericModalRoot (React 19 Pattern)
 * Simple modal implementation with unconditional backdrop rendering.
 */
const GenericModalRoot = ({
  open: controlledOpen,
  onOpenChange,
  children,
  ref,
  preventClose = false,
  onBeforeClose,
}: GenericModalProps) => {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);
  const [hasHeader, setHasHeader] = useState(false);

  const isOpen =
    controlledOpen !== undefined ? controlledOpen : uncontrolledOpen;

  const handleOpenChange = useCallback(
    async (nextOpen: boolean) => {
      // Interceptor logic
      if (isOpen && !nextOpen && onBeforeClose) {
        const canClose = await onBeforeClose();
        if (!canClose) return;
      }

      if (onOpenChange) onOpenChange(nextOpen);
      else setUncontrolledOpen(nextOpen);
    },
    [isOpen, onOpenChange, onBeforeClose],
  );

  const registerHeader = useCallback((exists: boolean) => {
    setHasHeader(exists);
  }, []);

  const actions: GenericModalRef = useMemo(
    () => ({
      open: () => handleOpenChange(true),
      close: () => handleOpenChange(false),
      forceClose: () => {
        if (onOpenChange) onOpenChange(false);
        else setUncontrolledOpen(false);
      },
      isOpen,
      preventClose,
      hasHeader,
      registerHeader,
    }),
    [
      handleOpenChange,
      onOpenChange,
      isOpen,
      preventClose,
      hasHeader,
      registerHeader,
    ],
  );

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useImperativeHandle(ref, () => actions, [actions]);

  return (
    <GenericModalContext.Provider value={actions}>
      <Dialog open={isOpen} onOpenChange={handleOpenChange}>
        {children}
      </Dialog>
    </GenericModalContext.Provider>
  );
};

// --- Compound Atom Sections ---

/** Simple wrapper for trigger */
const ModalTrigger = ({ children, asChild }: GenericModalTriggerProps) => (
  <DialogTrigger asChild={asChild}>{children}</DialogTrigger>
);

/** Size presets for GenericModal */
export type GenericModalSize = "sm" | "md" | "lg" | "xl" | "full";

/** Pure layout container: Does not render the close button automatically. */
const ModalContent = ({
  children,
  className,
  size = "md",
}: GenericModalContentProps & { size?: GenericModalSize }) => {
  const { preventClose, hasHeader } = useGenericModal();

  return (
    <DialogContent
      overlayClassName="bg-black/50 backdrop-brightness-50"
      className={cn(
  // 1. Estructura interna básica
  "grid grid-rows-[auto_1fr_auto] p-0 overflow-hidden border border-border shadow-lg gap-0",
  
  // 2. Comportamiento en Móvil (Reseteado y forzado a pantalla completa)
  "fixed left-4 right-4 top-4 bottom-4 w-auto h-auto translate-x-0 translate-y-0",
  
  // 3. Comportamiento Desktop (A partir de SM) - Centrado perfecto
  "sm:left-1/2 sm:top-1/2 sm:right-auto sm:bottom-auto",
  "sm:-translate-x-1/2 sm:-translate-y-1/2",
  
  // 4. El tamaño dinámico adaptativo (Solo en Desktop)
  "sm:w-max sm:h-auto",
  "sm:max-w-[calc(100vw-32px)]", 
  "sm:max-h-[calc(100vh-32px)]", 
  
  className,
)}
      showCloseButton={false}
      onPointerDownOutside={(e) => {
        if (preventClose) e.preventDefault();
      }}
      onEscapeKeyDown={(e) => {
        if (preventClose) e.preventDefault();
      }}
    >
      {!hasHeader && (
        <DialogTitle className="sr-only">Modal Content</DialogTitle>
      )}
      {children}
    </DialogContent>
  );
};

/** Standalone Close Button (X icon) */
const ModalCloseX = ({ className }: GenericModalCloseXProps) => {
  const { close, preventClose } = useGenericModal();

  if (preventClose) return null; // Standard: don't show X if close is blocked

  return (
    <button
      type="button"
      onClick={() => close()}
      className={cn(
        "absolute right-4 top-4 p-1 rounded-full opacity-70 ring-offset-background bg-primary/30 transition-all duration-200 border-2 border-transparent hover:border-primary/50",
        "hover:opacity-100 hover:bg-accent",
        "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        "disabled:pointer-events-none",
        "data-[state=open]:bg-accent data-[state=open]:text-muted-foreground z-50",
        className,
      )}
    >
      <X className="h-4 w-4 text-muted-foreground" />
      <span className="sr-only">Close</span>
    </button>
  );
};

/** Modular Header: Sticky candidate */
const ModalHeader = ({
  title,
  description,
  className,
  children,
}: GenericModalHeaderProps) => {
  const { registerHeader } = useGenericModal();

  React.useEffect(() => {
    registerHeader(true);
    return () => registerHeader(false);
  }, [registerHeader]);

  return (
    <DialogHeader className={cn("shrink-0 p-6 pb-0", className)}>
      {title && (
        <DialogTitle className="text-2xl font-bold text-foreground">
          {title}
        </DialogTitle>
      )}
      {description && (
        <DialogDescription className="text-muted-foreground mt-2">
          {description}
        </DialogDescription>
      )}
      {children}
    </DialogHeader>
  );
};

/** Modular Body: The Scrollable Workspace — uses Radix ScrollArea */
const ModalBody = ({
  children,
  className,
  scrollable = true,
}: GenericModalBodyProps) => (
  <ScrollArea className={cn("overflow-hidden", className)}>
    <div className={cn("p-4", !scrollable && "overflow-auto")}>{children}</div>
  </ScrollArea>
);

/** Modular Footer: Sticky Bottom by default */
const ModalFooter = ({
  children,
  className,
  sticky = true,
}: GenericModalFooterProps) => (
  <div
    className={cn(
      "shrink-0 p-6 pt-2 flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 border-t border-border",
      sticky && "",
      className,
    )}
  >
    {children}
  </div>
);

/** Headless Closer wrapper */
const ModalClose = ({ children, asChild }: GenericModalCloseProps) => {
  const { close } = useGenericModal();

  if (asChild && React.isValidElement(children)) {
    const child = children as React.ReactElement<{
      onClick?: React.MouseEventHandler;
    }>;

    return React.cloneElement(child, {
      onClick: (e: React.MouseEvent) => {
        child.props.onClick?.(e);
        close();
      },
    });
  }

  return (
    <button
      type="button"
      onClick={() => close()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") close();
      }}
      className="contents"
    >
      {children}
    </button>
  );
};

// --- Modular Composition Export ---

/**
 * Final GenericModal Export with Compound Components
 */
export const GenericModal = Object.assign(GenericModalRoot, {
  Trigger: ModalTrigger,
  Content: ModalContent,
  Header: ModalHeader,
  Body: ModalBody,
  Footer: ModalFooter,
  Close: ModalClose,
  CloseX: ModalCloseX,
} as unknown as typeof GenericModalRoot & {
  Trigger: typeof ModalTrigger;
  Content: typeof ModalContent;
  Header: typeof ModalHeader;
  Body: typeof ModalBody;
  Footer: typeof ModalFooter;
  Close: typeof ModalClose;
  CloseX: typeof ModalCloseX;
});
