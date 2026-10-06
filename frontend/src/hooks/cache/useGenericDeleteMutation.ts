import {
  type MutationFunction,
  type QueryKey,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

interface UseGenericDeleteMutationOptions<TId = string | number> {
  queryKey: QueryKey;
  mutationFn: MutationFunction<void, TId>;
}

export function useGenericDeleteMutation<
  TItem extends { id: string | number },
>({ queryKey, mutationFn }: UseGenericDeleteMutationOptions<TItem["id"]>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: (_data, deletedId) => {
      // Remove item from list cache
      queryClient.setQueryData<TItem[]>(
        queryKey,
        (old) => old?.filter((item) => item.id !== deletedId) ?? [],
      );
      // Remove detail cache
      queryClient.removeQueries({ queryKey: [...queryKey, deletedId] });
    },
  });
}
