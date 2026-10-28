import { useRef } from "react";

export interface LatestRequestGuard {
  begin: () => number;
  invalidate: () => void;
  isLatest: (requestId: number) => boolean;
}

export function createLatestRequestGuard(): LatestRequestGuard {
  let latestRequestId = 0;

  return {
    begin: () => ++latestRequestId,
    invalidate: () => {
      latestRequestId += 1;
    },
    isLatest: (requestId) => requestId === latestRequestId,
  };
}

export function useLatestRequestGuard(): LatestRequestGuard {
  const guardRef = useRef<LatestRequestGuard | null>(null);
  if (guardRef.current === null) {
    guardRef.current = createLatestRequestGuard();
  }
  return guardRef.current;
}
