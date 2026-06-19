"use client";

import {
  type DehydratedState,
  HydrationBoundary,
  QueryClientProvider,
} from "@tanstack/react-query";
import { type PropsWithChildren, useState } from "react";
import { toast } from "sonner";
import { configureToast } from "@/errors";
import { createQueryClient } from "@/lib/query-client";

interface ProvidersProps extends PropsWithChildren {
  dehydratedState?: DehydratedState;
}

export default function Providers({
  children,
  dehydratedState,
}: ProvidersProps) {
  const [queryClient] = useState(() => {
    // Configure global toast adapter for API hooks
    configureToast(toast.error, toast.success);
    return createQueryClient();
  });

  return (
    <QueryClientProvider client={queryClient}>
      <HydrationBoundary state={dehydratedState}>{children}</HydrationBoundary>
    </QueryClientProvider>
  );
}
