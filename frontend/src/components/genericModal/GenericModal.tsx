"use client";

import { X } from "lucide-react";
import React, {
  createContext,
  useCallback,
  useContext,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
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
  hideOverlay = false,
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
  hideOverlay = false,
}: GenericModalContentProps & { size?: GenericModalSize }) => {
  const { preventClose, hasHeader } = useGenericModal();

  return (
    <DialogPortal>
      {!hideOverlay && (
        <DialogOverlay className="bg-black/50 backdrop-blur-sm" />
      )}
      <DialogContent
        className={cn(
          "grid grid-rows-[auto_1fr_auto] p-0 overflow-hidden",
          "border border-border shadow-lg gap-0",
          "left-4 right-4 top-4 bottom-4 translate-x-0 translate-y-0 w-auto max-w-none max-h-none",
          "lg:left-1/2 lg:right-auto lg:top-1/2 lg:bottom-auto lg:-translate-x-1/2 lg:-translate-y-1/2",
          "sm:left-1/8 sm:right-1/8 sm:top-1/2 sm:bottom-auto sm:translate-x-0 sm:-translate-y-1/2",
          "sm:max-w-[95vw] sm:max-h-[90vh]",
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
    </DialogPortal>
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
