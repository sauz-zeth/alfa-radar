import { useEffect } from "react";
import { Splash } from "../auth/Splash";
import { useRouter } from "./useRouter";

export function Redirect({ to, replace = true }: { to: string; replace?: boolean }) {
  const { navigate } = useRouter();
  useEffect(() => {
    navigate(to, { replace });
  }, [navigate, replace, to]);
  return <Splash />;
}
