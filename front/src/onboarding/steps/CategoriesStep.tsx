import { useEffect, useRef, useState } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery } from "../../api";
import { OnboardingLayout } from "../OnboardingLayout";
import { useOnboarding } from "../useOnboarding";
import type { SimpleStepProps } from "./types";

const levels = [
  { key: "direct", label: "Прямое", weight: 1 },
  { key: "indirect", label: "Косвенное", weight: 0.6 },
  { key: "none", label: "Не влияет", weight: 0 },
] as const;

type LevelKey = (typeof levels)[number]["key"];

function levelOf(weight: number): LevelKey {
  if (weight >= 0.8) return "direct";
  if (weight >= 0.3) return "indirect";
  return "none";
}

export function CategoriesStep({ onDone }: SimpleStepProps) {
  const api = useApi();
  const { data: state } = useOnboarding();
  const [weights, setWeights] = useState<Record<number, number>>({});
  const suggested = useRef(false);

  const categories = useApiQuery({
    queryKey: ["onboarding", "categories"],
    queryFn: (signal) => api.onboarding.categories({ signal }),
  });

  const suggest = useApiMutation({
    mutationFn: () => api.onboarding.suggestCategories(),
    onSuccess: () => {
      void categories.refetch();
    },
  });

  useEffect(() => {
    if (!categories.data || categories.data.length > 0 || suggested.current) return;
    suggested.current = true;
    suggest.mutate();
  }, [categories.data, suggest]);

  useEffect(() => {
    if (!categories.data) return;
    setWeights(
      Object.fromEntries(categories.data.map((item) => [item.category_id, item.weight])),
    );
  }, [categories.data]);

  const save = useApiMutation<unknown, void>({
    mutationFn: async () => {
      for (const category of categories.data ?? []) {
        const next = weights[category.category_id] ?? category.weight;
        if (Math.abs(next - category.weight) > 0.001) {
          await api.onboarding.patchCategory(category.category_id, { weight: next });
        }
      }
    },
    onSuccess: onDone,
  });

  const items = (categories.data ?? []).map((item) => ({
    ...item,
    weight: weights[item.category_id] ?? item.weight,
  }));
  const loading = categories.isPending || suggest.isPending;

  if (!state) return null;

  return (
    <OnboardingLayout
      state={state}
      title="Категории влияния"
      description="Мы рассчитали, какие темы влияют на бизнес. Укажите характер влияния — лента будет поднимать более важные новости."
      footer={
        <>
          {save.error ? (
            <p className="form-error">{save.error instanceof ApiError ? save.error.detail : "Не удалось сохранить"}</p>
          ) : null}
          <button
            type="button"
            className="button button--primary button--block"
            disabled={save.isPending || loading || items.length === 0}
            onClick={() => save.mutate()}
          >
            {save.isPending ? "Сохраняем…" : "Продолжить"}
          </button>
        </>
      }
    >
      {loading ? <p className="onboarding-note">Считаем важность категорий…</p> : null}
      {!loading && items.length === 0 ? (
        <p className="onboarding-note">Не удалось подобрать категории для этого бизнеса.</p>
      ) : null}

      {items.length > 0 ? (
        <section className="onboarding-section">
          <div className="category-list">
            {items.map((category) => {
              const current = levelOf(category.weight);
              return (
                <div key={category.category_id} className="category-row">
                  <div>
                    <p className="category-row__name">{category.name}</p>
                    <p className="category-row__rationale">{category.rationale || category.description}</p>
                  </div>
                  <div
                    className="category-segment"
                    role="group"
                    aria-label={`Влияние категории ${category.name}`}
                  >
                    {levels.map((level) => (
                      <button
                        key={level.key}
                        type="button"
                        aria-pressed={current === level.key}
                        className={
                          current === level.key
                            ? "category-segment__button is-active"
                            : "category-segment__button"
                        }
                        onClick={() =>
                          setWeights((values) => ({
                            ...values,
                            [category.category_id]: level.weight,
                          }))
                        }
                      >
                        {level.label}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}
    </OnboardingLayout>
  );
}
