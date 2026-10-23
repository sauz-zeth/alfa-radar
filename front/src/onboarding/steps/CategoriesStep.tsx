import { useEffect, useRef, useState } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery } from "../../api";
import { groupCategories } from "../dictionary";
import { formatWeight } from "../format";
import { OnboardingLayout } from "../OnboardingLayout";
import { useOnboarding } from "../useOnboarding";
import type { SimpleStepProps } from "./types";

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
  const groups = groupCategories(items);
  const loading = categories.isPending || suggest.isPending;

  if (!state) return null;

  return (
    <OnboardingLayout
      state={state}
      title="Категории влияния"
      description="Мы рассчитали, какие темы сильнее всего влияют на бизнес. Вес можно поправить — лента будет поднимать более важные новости."
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

      {groups.map((group) => (
        <section key={group.key} className="onboarding-section">
          <h2 className="onboarding-section__title">{group.label}</h2>
          <div className="category-list">
            {group.items.map((category) => (
              <div key={category.category_id} className="category-row">
                <div className="category-row__head">
                  <div>
                    <p className="category-row__name">{category.name}</p>
                    <p className="category-row__rationale">{category.rationale || category.description}</p>
                  </div>
                  <span className="category-row__weight">{formatWeight(category.weight)}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={Math.round(category.weight * 100)}
                  onChange={(event) =>
                    setWeights((current) => ({
                      ...current,
                      [category.category_id]: Number(event.target.value) / 100,
                    }))
                  }
                  aria-label={`Вес категории ${category.name}`}
                />
              </div>
            ))}
          </div>
        </section>
      ))}
    </OnboardingLayout>
  );
}
