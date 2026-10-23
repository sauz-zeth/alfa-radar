import { useState } from "react";
import { ApiError, useApi, useApiMutation, type OnboardingState } from "../../api";
import { OnboardingLayout } from "../OnboardingLayout";
import type { StepProps } from "./types";

export function ProfileStep({ state, onDone }: StepProps) {
  const api = useApi();
  const [entrepreneurName, setEntrepreneurName] = useState(
    state.profile?.entrepreneur_name ?? "Иван Иванов",
  );
  const [businessName, setBusinessName] = useState(state.profile?.business_name ?? "Моя компания");

  const save = useApiMutation<OnboardingState, void>({
    mutationFn: () =>
      api.onboarding.profile({
        entrepreneur_name: entrepreneurName,
        business_name: businessName,
      }),
    onSuccess: onDone,
  });

  const skip = useApiMutation<OnboardingState, void>({
    mutationFn: () => api.onboarding.skip({ step: "profile_filled" }),
    onSuccess: onDone,
  });

  const error = save.error ?? skip.error;

  return (
    <OnboardingLayout
      state={state}
      title="Как вас представить"
      description="Имя и название бизнеса увидит агент, когда будет готовить разбор новости. Если пропустить, останутся значения по умолчанию."
      footer={
        <>
          {error ? (
            <p className="form-error">{error instanceof ApiError ? error.detail : "Не удалось сохранить"}</p>
          ) : null}
          <div className="onboarding-actions">
            <button
              type="button"
              className="button button--ghost button--block"
              onClick={() => skip.mutate()}
              disabled={skip.isPending || save.isPending}
            >
              Пропустить
            </button>
            <button
              type="button"
              className="button button--primary button--block"
              onClick={() => save.mutate()}
              disabled={save.isPending || skip.isPending}
            >
              {save.isPending ? "Сохраняем…" : "Продолжить"}
            </button>
          </div>
        </>
      }
    >
      <div className="onboarding-fields">
        <label className="field">
          <span>Имя предпринимателя</span>
          <input
            value={entrepreneurName}
            onChange={(event) => setEntrepreneurName(event.target.value)}
            placeholder="Иван Иванов"
            autoFocus
          />
        </label>
        <label className="field">
          <span>Название бизнеса</span>
          <input
            value={businessName}
            onChange={(event) => setBusinessName(event.target.value)}
            placeholder="Моя компания"
          />
        </label>
      </div>
    </OnboardingLayout>
  );
}
