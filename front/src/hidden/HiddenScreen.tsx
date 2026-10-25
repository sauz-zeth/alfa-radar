import { useMemo, useState } from "react";
import {
  ApiError,
  useApi,
  useApiMutation,
  useApiQuery,
  useQueryClient,
  type HiddenItem,
  type HiddenTabKey,
} from "../api";
import { pluralRu } from "../lib/plural";
import { Link } from "../router";
import "./hidden.css";

const HIDDEN_TTL_DAYS = 7;

const dayLabel = (count: number) => pluralRu(count, ["день", "дня", "дней"]);

function metaLabel(item: HiddenItem): string {
  // shortcut: the API exposes no hidden-since field; derive it from the 7-day TTL until it does.
  const hiddenDays = Math.max(0, HIDDEN_TTL_DAYS - item.expires_in_days);
  return [
    `Было в ленте ${item.age_days} ${dayLabel(item.age_days)}`,
    `В скрытом ${hiddenDays} ${dayLabel(hiddenDays)}`,
    `удалим через ${item.expires_in_days} ${dayLabel(item.expires_in_days)}`,
  ].join(" · ");
}

export default function HiddenScreen() {
  const api = useApi();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<HiddenTabKey>("stale");

  const hidden = useApiQuery({
    queryKey: ["feed", "hidden", activeTab],
    queryFn: (signal) => api.feed.hidden({ tab: activeTab }, { signal }),
    placeholderData: (previous) => previous,
    staleTime: 0,
    refetchOnMount: "always",
  });

  const restore = useApiMutation<unknown, string>({
    mutationFn: (id) => api.feed.restore(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["feed"] });
    },
  });

  const data = hidden.data;
  const total = useMemo(
    () => data?.tabs.reduce((sum, tab) => sum + tab.count, 0) ?? 0,
    [data],
  );
  const tabs = useMemo(
    () => (data?.tabs ?? []).filter((tab) => tab.count > 0 || tab.key === activeTab),
    [activeTab, data],
  );

  if (hidden.isError && !data) {
    return (
      <div className="hidden-page hidden-state">
        <p>
          {hidden.error instanceof ApiError
            ? hidden.error.detail
            : "Не удалось загрузить скрытые новости"}
        </p>
        <button type="button" className="hidden-state__retry" onClick={() => hidden.refetch()}>
          Повторить
        </button>
      </div>
    );
  }

  if (hidden.isPending && !data) {
    return (
      <div className="hidden-page hidden-state">
        <p>Загружаем скрытые…</p>
      </div>
    );
  }

  return (
    <div className="hidden-page">
      <section className="hidden-summary" aria-labelledby="hidden-title">
        <h1 className="hidden-summary__title" id="hidden-title">
          Скрытые · {total}
        </h1>
        <p className="hidden-summary__text">{data?.description}</p>
        <p className="hidden-summary__note">
          Новости старше {HIDDEN_TTL_DAYS} дней удаляются автоматически
        </p>
        <Link to="/" className="hidden-summary__link">
          Вернуться в ленту
        </Link>
      </section>

      <div className="hidden-content">
        <div className="hidden-tabs" role="tablist" aria-label="Почему новости скрыты">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={tab.key === activeTab}
              className={tab.key === activeTab ? "hidden-tab is-active" : "hidden-tab"}
              onClick={() => setActiveTab(tab.key as HiddenTabKey)}
            >
              {tab.label} · {tab.count}
            </button>
          ))}
        </div>

        <div className="hidden-list" aria-busy={hidden.isFetching}>
          {data?.items.length ? (
            <ul className="hidden-list__items">
              {data.items.map((item) => (
                <li className="hidden-row" key={item.id}>
                  <span className="hidden-row__score" aria-label={`Важность ${item.importance}`}>
                    {item.importance}
                  </span>
                  <div className="hidden-row__body">
                    <h2 className="hidden-row__title">{item.title}</h2>
                    <p className="hidden-row__meta">{metaLabel(item)}</p>
                  </div>
                  <button
                    type="button"
                    className="hidden-row__restore"
                    aria-label={`Вернуть «${item.title}»`}
                    disabled={restore.isPending}
                    onClick={() => restore.mutate(item.id)}
                  >
                    Вернуть
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="hidden-empty">Здесь пока пусто.</p>
          )}
        </div>
      </div>
    </div>
  );
}
