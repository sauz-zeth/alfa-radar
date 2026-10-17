import { Suspense } from "react";
import NotFound from "../pages/NotFound";
import { useRouter } from "../router";
import { routes } from "../routes";

export function PageOutlet() {
  const { path } = useRouter();
  const Page = routes[path] ?? NotFound;

  return (
    <Suspense fallback={<p className="loading">Loading…</p>}>
      <Page />
    </Suspense>
  );
}
