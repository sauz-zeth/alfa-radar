import { lazy, type ComponentType } from "react";

export const routes: Record<string, ComponentType> = {
  "/": lazy(() => import("../pages/Home")),
  "/about": lazy(() => import("../pages/About")),
  "/profile": lazy(() => import("../pages/Profile")),
};
