import { lazy, type ComponentType } from "react";

export const routes: Record<string, ComponentType> = {
  "/": lazy(() => import("../pages/Home")),
  "/about": lazy(() => import("../pages/About")),
  "/profile": lazy(() => import("../pages/Profile")),
  "/profile/reports/:form": lazy(() => import("../profile/ReportSummaryScreen")),
  "/sources": lazy(() => import("../sources/SourcesPage")),
  "/tracked": lazy(() => import("../tracked/TrackedScreen")),
  "/tracked/archive": lazy(() => import("../tracked/ArchiveScreen")),
  "/hidden": lazy(() => import("../hidden/HiddenScreen")),
  "/search": lazy(() => import("../search/SearchScreen")),
  "/event/:id": lazy(() => import("../event/EventScreen")),
};

export function resolveRoute(path: string): ComponentType | undefined {
  if (routes[path]) return routes[path];
  if (path.startsWith("/event/")) return routes["/event/:id"];
  if (path.startsWith("/profile/reports/")) return routes["/profile/reports/:form"];
  return undefined;
}
