import type { OnboardingState } from "../api";
import { BusinessStep } from "./steps/BusinessStep";
import { CategoriesStep } from "./steps/CategoriesStep";
import { CompleteStep } from "./steps/CompleteStep";
import { CounterpartiesStep } from "./steps/CounterpartiesStep";
import { ProfileStep } from "./steps/ProfileStep";
import { ReportingStep } from "./steps/ReportingStep";
import { RoleStep } from "./steps/RoleStep";
import { useOnboarding } from "./useOnboarding";
import "./onboarding.css";

export function OnboardingPage({ state }: { state: OnboardingState }) {
  const { refresh } = useOnboarding();
  const done = () => {
    void refresh();
  };

  switch (state.next_step) {
    case "business_selected":
      return <BusinessStep state={state} onDone={done} />;
    case "profile_filled":
      return <ProfileStep state={state} onDone={done} />;
    case "role_selected":
      return <RoleStep state={state} onDone={done} />;
    case "counterparties_configured":
      return <CounterpartiesStep onDone={done} />;
    case "categories_configured":
      return <CategoriesStep onDone={done} />;
    case "reporting_uploaded":
      return <ReportingStep onDone={done} />;
    default:
      return <CompleteStep state={state} onDone={done} />;
  }
}
