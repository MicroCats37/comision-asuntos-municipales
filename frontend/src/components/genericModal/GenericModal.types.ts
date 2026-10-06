import type { ReactNode, Ref } from "react";

/**
 * Context type for deep modal state sharing.
 * Allows any child component to call modal actions.
 */
export interface GenericModalContextType {
  open: () => void;
  close: () => void;
  forceClose: () => void;
  isOpen: boolean;
  preventClose?: boolean;
  /** Internal tracking for A11y auto-detection */
  hasHeader: boolean;
  registerHeader: (exists: boolean) => void;
}

/**
 * Exposes methods to a parent component via React.Ref
 */
export type GenericModalRef = GenericModalContextType;

// --- Component Props ---

export interface GenericModalProps {
  /**
   * React 19: ref is a standard prop.
   * Forwarding is no longer handled via forwardRef wrapper.
   */
  ref?: Ref<GenericModalRef>;
  /** Controlled open state */
  open?: boolean;
  /** Callback fired when the open state changes. Required for controlled mode. */
  onOpenChange?: (open: boolean) => void;
  /** If true, blocks clicking outside or ESC to close. */
  preventClose?: boolean;
  /** Async or sync interceptor before closing. Return false to cancel close. */
  onBeforeClose?: () => boolean | Promise<boolean>;
  children: ReactNode;
}

/** Root wrapper for trigger */
export interface GenericModalTriggerProps {
  children: ReactNode;
  asChild?: boolean;
}

export interface GenericModalContentProps {
  children: ReactNode;
  /**
   * Optional override for width/styles.
   * By default, it uses 'w-full md:w-fit' (hug content) up to md.
   */
  className?: string;
  /** Force show/hide the top-right X button. Defaults to !preventClose */
  showCloseButton?: boolean;
}

export interface GenericModalHeaderProps {
  title?: ReactNode;
  description?: ReactNode;
  className?: string;
  children?: ReactNode; // For deep customization
}

export interface GenericModalBodyProps {
  children: ReactNode;
  className?: string;
  /** Enables y-scroll when content exceeds modal height. Default true. */
  scrollable?: boolean;
}

export interface GenericModalFooterProps {
  children: ReactNode;
  className?: string;
  /** If true, stays at the bottom (sticky) even if body scrolls. Default true. */
  sticky?: boolean;
}

/** Headless closer: wraps any UI element and calls close() on click */
export interface GenericModalCloseProps {
  children: ReactNode;
  asChild?: boolean;
}

/** Predefined Close Button (X icon) as a standalone piece */
export interface GenericModalCloseXProps {
  className?: string;
}
