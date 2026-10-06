"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class GenericErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log via notify if available
    if (typeof window !== "undefined") {
      import("@/errors").then(({ notify }) => {
        notify.error(error.message || "An error occurred");
      });
    }
    this.props.onError?.(error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      const { fallback } = this.props;
      if (fallback) {
        return fallback(this.state.error, this.handleReset);
      }
      return (
        <div className="p-4 text-center">
          <p className="text-destructive">Something went wrong</p>
          <button
            type="button"
            onClick={this.handleReset}
            className="mt-2 underline"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
