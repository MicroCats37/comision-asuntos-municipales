import {
  type MutationFunction,
  type QueryKey,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

interface UseGenericOptimisticUpdateOptions<TItem, TVars> {
  queryKey: QueryKey;
  mutationFn: MutationFunction<TItem, TVars>;
  updaterFn: (oldData: TItem[] | undefined, variables: TVars) => TItem[];
}

export function useGenericOptimisticUpdate<TItem, TVars>({
  queryKey,
  mutationFn,
  updaterFn,
}: UseGenericOptimisticUpdateOptions<TItem, TVars>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey });
      // Snapshot previous value
      const previousData = queryClient.getQueryData<TItem[]>(queryKey);
      // Optimistically update cache
      queryClient.setQueryData<TItem[]>(queryKey, (old) =>
        updaterFn(old, variables),
      );
      return { previousData };
    },
    onError: (_err, _vars, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
    },
    onSettled: () => {
      // Optional: uncomment to refetch after mutation settles
      // queryClient.invalidateQueries({ queryKey });
    },
  });
}
