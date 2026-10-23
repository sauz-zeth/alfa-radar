import { useEffect, useState } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery } from "../../api";
import { directionLabels } from "../dictionary";
import { formatMoney, formatShare } from "../format";
import { OnboardingLayout } from "../OnboardingLayout";
import { useOnboarding } from "../useOnboarding";
import type { SimpleStepProps } from "./types";

export function CounterpartiesStep({ onDone }: SimpleStepProps) {
  const api = useApi();
  const { data: state } = useOnboarding();
  const [names, setNames] = useState<Record<string, string>>({});

  const counterparties = useApiQuery({
    queryKey: ["onboarding", "counterparties"],
    queryFn: (signal) => api.onboarding.counterparties({ signal }),
    staleTime: Infinity,
  });

  useEffect(() => {
    if (!counterparties.data) return;
    setNames(
      Object.fromEntries(counterparties.data.map((item) => [item.id, item.display_name])),
    );
  }, [counterparties.data]);

  const save = useApiMutation<unknown, void>({
    mutationFn: () =>
      api.onboarding.renameCounterparties({
        items: (counterparties.data ?? []).map((item) => ({
          id: item.id,
          name: names[item.id] ?? item.display_name,
        })),
      }),
    onSuccess: onDone,
  });

  const items = counterparties.data ?? [];
  const directions = ["supplier", "buyer"] as const;

  if (!state) return null;

  return (
    <OnboardingLayout
      state={state}
      title="Контрагенты"
      description="Агент нашёл поставщиков и покупателей по платежам и оценил важность. Имена по умолчанию можно изменить — агент будет использовать их в разборе."
      footer={
        <>
          {save.error ? (
            <p className="form-error">{save.error instanceof ApiError ? save.error.detail : "Не удалось сохранить"}</p>
          ) : null}
          <button
            type="button"
            className="button button--primary button--block"
            disabled={save.isPending || counterparties.isPending}
            onClick={() => save.mutate()}
          >
            {save.isPending ? "Сохраняем…" : "Продолжить"}
          </button>
        </>
      }
    >
      {counterparties.isPending ? <p className="onboarding-note">Считаем контрагентов…</p> : null}
      {counterparties.isError ? <p className="form-error">Не удалось получить контрагентов</p> : null}
      {!counterparties.isPending && items.length === 0 ? (
        <p className="onboarding-note">
          По этому бизнесу пока нет платежей — контрагенты появятся позже. Можно продолжить.
        </p>
      ) : null}

      {directions.map((direction) => {
        const group = items.filter((item) => item.direction === direction);
        if (group.length === 0) return null;
        return (
          <section key={direction} className="onboarding-section">
            <h2 className="onboarding-section__title">
              {directionLabels[direction]} · {group.length}
            </h2>
            <div className="counterparty-list">
              {group.map((item) => (
                <div key={item.id} className="counterparty-card">
                  <div className="counterparty-card__head">
                    <input
                      className="counterparty-card__input"
                      value={names[item.id] ?? item.display_name}
                      onChange={(event) =>
                        setNames((current) => ({ ...current, [item.id]: event.target.value }))
                      }
                      aria-label={`Название контрагента ${item.display_name}`}
                    />
                    <span className="badge">{item.importance}</span>
                  </div>
                  <p className="counterparty-card__meta">
                    {formatMoney(item.total_amount)} · {formatShare(item.share)} оборота ·{" "}
                    {item.payments_count} платежей
                  </p>
                  {item.note ? <p className="counterparty-card__note">{item.note}</p> : null}
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </OnboardingLayout>
  );
}
