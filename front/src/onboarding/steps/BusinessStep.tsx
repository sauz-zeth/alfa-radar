import { useState } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery, type BusinessListItem, type OnboardingState } from "../../api";
import { productLabels } from "../dictionary";
import { formatMoney } from "../format";
import { OnboardingLayout } from "../OnboardingLayout";
import type { StepProps } from "./types";

function products(item: BusinessListItem): string[] {
  return Object.entries(productLabels)
    .filter(([key]) => Boolean(item[key as keyof BusinessListItem]))
    .map(([, label]) => label);
}

export function BusinessStep({ state, onDone }: StepProps) {
  const api = useApi();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(state.profile?.company_uid ?? null);

  const businesses = useApiQuery({
    queryKey: ["businesses", search],
    queryFn: (signal) =>
      api.businesses.list({ search: search.trim() || undefined, limit: 50 }, { signal }),
  });

  const choose = useApiMutation<OnboardingState, string>({
    mutationFn: (uid) => api.onboarding.business({ uid }),
    onSuccess: onDone,
  });

  const items = businesses.data?.items ?? [];

  return (
    <OnboardingLayout
      state={state}
      title="Выберите бизнес"
      description="Войдите от лица компании из обезличенных данных Альфа-Банка. От этого зависят новости, контрагенты и оценка влияния."
      footer={
        <>
          {choose.error ? (
            <p className="form-error">{choose.error instanceof ApiError ? choose.error.detail : "Не удалось выбрать бизнес"}</p>
          ) : null}
          <button
            type="button"
            className="button button--primary button--block"
            disabled={!selected || choose.isPending}
            onClick={() => selected && choose.mutate(selected)}
          >
            {choose.isPending ? "Подключаем бизнес…" : "Продолжить"}
          </button>
        </>
      }
    >
      <label className="field onboarding-search">
        <span>Поиск по UID, городу или ОКВЭД</span>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Например, Москва"
          autoFocus
        />
      </label>

      <div className="business-list" role="radiogroup" aria-label="Бизнесы">
        {businesses.isPending ? <p className="onboarding-note">Загружаем бизнесы…</p> : null}
        {businesses.isError ? <p className="form-error">Не удалось загрузить список бизнесов</p> : null}
        {!businesses.isPending && items.length === 0 ? (
          <p className="onboarding-note">Ничего не нашлось. Попробуйте другой запрос.</p>
        ) : null}
        {items.map((item) => {
          const isSelected = selected === item.uid;
          return (
            <button
              key={item.uid}
              type="button"
              role="radio"
              aria-checked={isSelected}
              className={isSelected ? "business-card is-selected" : "business-card"}
              onClick={() => setSelected(item.uid)}
            >
              <span className="business-card__top">
                <span className="business-card__uid">{item.uid}</span>
                {item.revenue_segment ? <span className="badge">{item.revenue_segment}</span> : null}
              </span>
              <span className="business-card__title">{item.main_okved_name ?? "Бизнес без отраслевого кода"}</span>
              <span className="business-card__meta">
                {[item.city ?? item.region, formatMoney(item.revenue), item.amount_workers_fns_gradation]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
              {item.tags.length > 0 ? (
                <span className="business-card__tags">
                  {item.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="badge">
                      {tag}
                    </span>
                  ))}
                </span>
              ) : null}
              {products(item).length > 0 ? (
                <span className="business-card__products">{products(item).join(" · ")}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </OnboardingLayout>
  );
}
