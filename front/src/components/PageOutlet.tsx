import { Suspense } from "react";
import NotFound from "../pages/NotFound";
import { useRouter } from "../router";
import { resolveRoute } from "../routes";

export function PageOutlet() {
  const { path } = useRouter();
  const Page = resolveRoute(path) ?? NotFound;

  return (
    <Suspense fallback={<p className="loading">Loading…</p>}>
      <Page />
    </Suspense>
  );
}
