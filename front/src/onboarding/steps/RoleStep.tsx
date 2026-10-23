import { useState } from "react";
import { ApiError, useApi, useApiMutation, type OnboardingState, type Role } from "../../api";
import { roles } from "../dictionary";
import { OnboardingLayout } from "../OnboardingLayout";
import type { StepProps } from "./types";

export function RoleStep({ state, onDone }: StepProps) {
  const api = useApi();
  const [role, setRole] = useState<Role | null>((state.profile?.role as Role | null | undefined) ?? null);

  const save = useApiMutation<OnboardingState, Role>({
    mutationFn: (value) => api.onboarding.role({ role: value }),
    onSuccess: onDone,
  });

  return (
    <OnboardingLayout
      state={state}
      title="Ваша роль в компании"
      description="Роль попадёт в профиль бизнеса. Агент учтёт её, когда будет формировать отчёт по новости и действия в «Отслеживаемом»."
      footer={
        <>
          {save.error ? (
            <p className="form-error">{save.error instanceof ApiError ? save.error.detail : "Не удалось сохранить роль"}</p>
          ) : null}
          <button
            type="button"
            className="button button--primary button--block"
            disabled={!role || save.isPending}
            onClick={() => role && save.mutate(role)}
          >
            {save.isPending ? "Сохраняем…" : "Продолжить"}
          </button>
        </>
      }
    >
      <div className="option-list" role="radiogroup" aria-label="Роль в компании">
        {roles.map((item) => (
          <button
            key={item.value}
            type="button"
            role="radio"
            aria-checked={role === item.value}
            className={role === item.value ? "option-card is-selected" : "option-card"}
            onClick={() => setRole(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </OnboardingLayout>
  );
}
