import { useEffect, useState } from "react";
import {
  ApiError,
  useApi,
  useApiMutation,
  useApiQuery,
  useQueryClient,
  type SearchNews,
} from "../api";
import { pluralRu } from "../lib/plural";
import { Link, useRouter } from "../router";
import "./search.css";

const MIN_QUERY = 2;
const RESULT_LIMIT = 10;

const impactTones: Record<string, string> = {
  risk: "risk",
  opportunity: "opportunity",
  mixed: "mixed",
  neutral: "neutral",
};

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

function NewsRow({
  item,
  tracked,
  pending,
  onToggleTracked,
}: {
  item: SearchNews;
  tracked: boolean;
  pending: boolean;
  onToggleTracked: (id: string, tracked: boolean) => void;
}) {
  const tone = impactTones[item.impact] ?? "neutral";

  return (
    <li className="search-news-row">
      <Link to={`/event/${item.id}`} className="search-news">
        <span className="search-news__meta">
          <span>{item.source_name}</span>
          <span>{shortDate(item.published_at)}</span>
          <span>{pluralRu(item.source_count, ["источник", "источника", "источников"])}</span>
          <span className="search-news__importance" aria-label={`Важность ${item.importance}`}>
            {item.importance}
          </span>
          <span className={`search-news__impact search-news__impact--${tone}`}>
            {item.impact_label}
          </span>
        </span>
        <span className="search-news__title">{item.title}</span>
      </Link>
      <button
        type="button"
        className={tracked ? "search-news__track is-on" : "search-news__track"}
        aria-pressed={tracked}
        disabled={pending}
        onClick={() => onToggleTracked(item.id, tracked)}
      >
        {tracked ? "Отслеживается" : "Отслеживать"}
      </button>
    </li>
  );
}

export default function SearchScreen() {
  const api = useApi();
  const queryClient = useQueryClient();
  const { search, navigate } = useRouter();
  const urlQuery = new URLSearchParams(search).get("q") ?? "";
  const [query, setQuery] = useState(urlQuery);
  const [trackedOverrides, setTrackedOverrides] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setQuery(urlQuery);
  }, [urlQuery]);

  const trackMutation = useApiMutation<unknown, { id: string; tracked: boolean }>({
    mutationFn: ({ id, tracked }) =>
      tracked ? api.feed.untrack(id) : api.feed.track(id),
    onSuccess: (_data, variables) => {
      setTrackedOverrides((current) => ({ ...current, [variables.id]: !variables.tracked }));
      void queryClient.invalidateQueries({ queryKey: ["search"] });
      void queryClient.invalidateQueries({ queryKey: ["tracked"] });
      void queryClient.invalidateQueries({ queryKey: ["feed"] });
    },
  });

  const trimmed = query.trim();
  const active = trimmed.length >= MIN_QUERY;

  const results = useApiQuery({
    queryKey: ["search", trimmed],
    queryFn: (signal) => api.search.search({ q: trimmed }, { signal }),
    enabled: active,
    staleTime: 0,
    refetchOnMount: "always",
  });

  const history = useApiQuery({
    queryKey: ["search-history"],
    queryFn: (signal) => api.search.history({ signal }),
    staleTime: 0,
    refetchOnMount: "always",
  });

  useEffect(() => {
    if (results.data) void queryClient.invalidateQueries({ queryKey: ["search-history"] });
  }, [results.data, queryClient]);

  const recent = history.data?.items ?? [];

  const data = results.data;
  const news = data?.news.slice(0, RESULT_LIMIT) ?? [];
  const empty = Boolean(data && data.total_news === 0);

  return (
    <div className="search-page">
      <header className="search-head">
        <h1 className="search-head__title">Поиск</h1>
        <p className="search-head__subtitle">Новости в ленте за последние дни</p>
        <label className="search-field">
          <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
            <circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <path
              d="M12.5 12.5 16 16"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск по новостям"
            aria-label="Поиск по новостям"
            autoFocus
            enterKeyHint="search"
          />
        </label>
      </header>

      {!active ? (
        <div className="search-start">
          <p className="search-hint">
            Введите хотя бы {MIN_QUERY} символа, чтобы найти новости по заголовку и тексту.
          </p>
          {recent.length > 0 ? (
            <div className="search-recent">
              <p className="search-recent__label">Недавно искали</p>
              <div className="search-recent__chips">
                {recent.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className="search-recent__chip"
                    onClick={() => navigate(`/search?q=${encodeURIComponent(item.query)}`)}
                  >
                    {item.query}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : results.isPending ? (
        <div className="search-state">
          <p>Ищем по базе…</p>
        </div>
      ) : results.isError ? (
        <div className="search-state">
          <p>
            {results.error instanceof ApiError
              ? results.error.detail
              : "Не удалось выполнить поиск."}
          </p>
          <button type="button" className="search-retry" onClick={() => results.refetch()}>
            Повторить
          </button>
        </div>
      ) : data ? (
        empty ? (
          <div className="search-state">
            <p>По запросу «{trimmed}» ничего не нашлось.</p>
            <p className="search-state__note">Попробуйте другое название или более короткий запрос.</p>
          </div>
        ) : (
          <div className="search-results" aria-busy={results.isFetching}>
            {news.length > 0 ? (
              <section className="search-section" aria-labelledby="search-news">
                <div className="search-section__head">
                  <h2 className="search-section__title" id="search-news">
                    Новости
                  </h2>
                  <span className="search-section__count">{data.total_news}</span>
                </div>
                <ul className="search-list">
                  {news.map((item) => (
                    <NewsRow
                      key={item.id}
                      item={item}
                      tracked={trackedOverrides[item.id] ?? item.is_tracked}
                      pending={trackMutation.isPending && trackMutation.variables?.id === item.id}
                      onToggleTracked={(id, tracked) => trackMutation.mutate({ id, tracked })}
                    />
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        )
      ) : null}
    </div>
  );
}
