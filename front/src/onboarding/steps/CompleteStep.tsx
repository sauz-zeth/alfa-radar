import { ApiError, useApi, useApiMutation, type OnboardingState } from "../../api";
import { formatMoney } from "../format";
import { OnboardingLayout } from "../OnboardingLayout";
import type { StepProps } from "./types";

export function CompleteStep({ state, onDone }: StepProps) {
  const api = useApi();
  const profile = state.profile;
  const company = profile?.company;
  const complete = useApiMutation<OnboardingState, void>({
    mutationFn: () => api.onboarding.complete(),
    onSuccess: onDone,
  });

  return (
    <OnboardingLayout
      state={state}
      title="Всё готово"
      description="Профиль собран. Дальше — персональная лента новостей с оценкой влияния и разбором в «Отслеживаемом»."
      footer={
        <>
          {complete.error ? (
            <p className="form-error">
              {complete.error instanceof ApiError ? complete.error.detail : "Не удалось завершить настройку"}
            </p>
          ) : null}
          <button
            type="button"
            className="button button--primary button--block"
            onClick={() => complete.mutate()}
            disabled={complete.isPending}
          >
            {complete.isPending ? "Открываем ленту…" : "Перейти в ленту"}
          </button>
        </>
      }
    >
      <section className="onboarding-summary">
        <p className="onboarding-summary__label">Бизнес</p>
        <p className="onboarding-summary__value">{profile?.business_name ?? "—"}</p>
        <p className="onboarding-summary__meta">
          {[company?.uid, company?.city, formatMoney(company?.revenue)].filter(Boolean).join(" · ")}
        </p>
        <p className="onboarding-summary__label">Роль</p>
        <p className="onboarding-summary__value">{profile?.role_label ?? "—"}</p>
      </section>
    </OnboardingLayout>
  );
}
