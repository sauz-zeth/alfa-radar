import { BottomNav } from "../components/BottomNav";
import { PageOutlet } from "../components/PageOutlet";
import { DesktopShell } from "../desktop/DesktopShell";
import { useMediaQuery } from "../lib/useMediaQuery";
import { Redirect, useRouter } from "../router";
import { Splash } from "../auth/Splash";
import { OnboardingPage } from "./OnboardingPage";
import { useOnboarding } from "./useOnboarding";

export function OnboardingGate() {
  const { path } = useRouter();
  const { data, isPending, isError, refetch } = useOnboarding();
  const isDesktop = useMediaQuery("(min-width: 1200px)");

  if (isPending) return <Splash />;

  if (isError || !data) {
    return (
      <div className="app-splash">
        <p>Не удалось загрузить данные профиля.</p>
        <button type="button" className="button button--ghost" onClick={() => refetch()}>
          Повторить
        </button>
      </div>
    );
  }

  const onOnboarding = path === "/onboarding";

  if (!data.completed && !onOnboarding) return <Redirect to="/onboarding" />;
  if (data.completed && onOnboarding) return <Redirect to="/" />;
  if (onOnboarding) return <OnboardingPage state={data} />;

  if (isDesktop) {
    return (
      <DesktopShell>
        <PageOutlet />
      </DesktopShell>
    );
  }

  return (
    <div className="app-shell">
      <PageOutlet />
      <BottomNav />
    </div>
  );
}
