import { useCallback } from "react";
import { useApi, useApiQuery, useQueryClient } from "../api";

export function useOnboarding() {
  const api = useApi();
  const queryClient = useQueryClient();
  const query = useApiQuery({
    queryKey: ["onboarding"],
    queryFn: (signal) => api.onboarding.state({ signal }),
  });

  const refresh = useCallback(
    () => queryClient.invalidateQueries({ queryKey: ["onboarding"] }),
    [queryClient],
  );

  return { ...query, refresh };
}
