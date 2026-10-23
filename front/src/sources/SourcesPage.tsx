import { useMemo, useState } from "react";
import {
  ApiError,
  useApi,
  useApiMutation,
  useApiQuery,
  useQueryClient,
  type Channel,
  type SourcesState,
} from "../api";
import searchIcon from "../assets/icons/search.svg";
import { channelCountLabel } from "../lib/plural";
import "./sources.css";

const tones = ["dark", "red", "light"] as const;

function initials(name: string): string {
  return (
    name
      .split(/[\s.:-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase() ?? "")
      .join("") || "•"
  );
}

function toneFor(channel: Channel): (typeof tones)[number] {
  let hash = 0;
  for (const char of channel.id) hash = (hash * 31 + char.charCodeAt(0)) % 997;
  return tones[hash % tones.length]!;
}

export default function SourcesPage() {
  const api = useApi();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"channels" | "catalog">("channels");
  const [query, setQuery] = useState("");

  const sources = useApiQuery({
    queryKey: ["sources"],
    queryFn: (signal) => api.sources.state({ signal }),
  });

  const profile = useApiQuery({
    queryKey: ["profile"],
    queryFn: (signal) => api.profile.get({ signal }),
  });

  const catalog = useApiQuery({
    queryKey: ["sources", "catalog", query],
    queryFn: (signal) => api.sources.catalog({ q: query.trim() || undefined }, { signal }),
    enabled: tab === "catalog",
  });

  const applyState = (state: SourcesState) => {
    queryClient.setQueryData(["sources"], state);
    void queryClient.invalidateQueries({ queryKey: ["sources", "catalog"] });
  };

  const subscribe = useApiMutation<SourcesState, string>({
    mutationFn: (channelId) => api.sources.subscribe(channelId),
    onSuccess: applyState,
  });

  const unsubscribe = useApiMutation<SourcesState, string>({
    mutationFn: (channelId) => api.sources.unsubscribe(channelId),
    onSuccess: applyState,
  });

  const unsubscribeAll = useApiMutation<SourcesState, void>({
    mutationFn: () => api.sources.unsubscribeAll(),
    onSuccess: applyState,
  });

  const restore = useApiMutation<SourcesState, void>({
    mutationFn: () => api.sources.restore(),
    onSuccess: applyState,
  });

  const data = sources.data;
  const channels = useMemo(() => data?.channels ?? [], [data?.channels]);
  const recommended = useMemo(
    () =>
      (profile.data?.categories ?? [])
        .slice()
        .sort((a, b) => b.weight - a.weight)
        .slice(0, 2)
        .map((category) => category.short_name),
    [profile.data?.categories],
  );
  const remaining = Math.max(0, (data?.catalog_total ?? 0) - channels.length);
  const pending = subscribe.isPending || unsubscribe.isPending;

  const toggleChannel = (channel: Channel) => {
    if (channel.subscribed) unsubscribe.mutate(channel.id);
    else subscribe.mutate(channel.id);
  };

  if (sources.isPending) {
    return (
      <div className="sources-page sources-state">
        <p>Загружаем источники…</p>
      </div>
    );
  }

  if (sources.isError || !data) {
    return (
      <div className="sources-page sources-state">
        <p>{sources.error instanceof ApiError ? sources.error.detail : "Не удалось загрузить источники"}</p>
        <button type="button" className="sources-retry" onClick={() => sources.refetch()}>
          Повторить
        </button>
      </div>
    );
  }

  return (
    <div className="sources-page">
      <header className="sources-head">
        <h1>Источники</h1>
        <button
          type="button"
          className="sources-search-button"
          aria-label="Найти канал"
          onClick={() => setTab("catalog")}
        >
          <img src={searchIcon} alt="" width={18} height={18} />
        </button>
      </header>

      <div className="sources-tabs" role="tablist" aria-label="Источники">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "channels"}
          className={tab === "channels" ? "sources-tab is-active" : "sources-tab"}
          onClick={() => setTab("channels")}
        >
          Каналы <span>{channels.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "catalog"}
          className={tab === "catalog" ? "sources-tab is-active" : "sources-tab"}
          onClick={() => setTab("catalog")}
        >
          Каталог <span>{data.catalog_total}</span>
        </button>
      </div>

      {tab === "channels" ? (
        <>
          <section className="sources-hint">
            <span className="sources-hint__avatar" aria-hidden="true">
              Пр
            </span>
            <div>
              <p className="sources-hint__label">Подобрали каналы под профиль</p>
              <p className="sources-hint__value">{recommended.join(" · ") || "Ваш бизнес"}</p>
            </div>
          </section>

          {channels.length === 0 ? (
            <div className="sources-empty">
              <p>Все каналы отключены.</p>
              <button
                type="button"
                className="sources-restore"
                onClick={() => restore.mutate()}
                disabled={restore.isPending}
              >
                Вернуть рекомендованные
              </button>
            </div>
          ) : (
            <ul className="sources-grid">
              {channels.map((channel) => (
                <li key={channel.id} className="source-cell">
                  <div className="source-tile" data-tone={toneFor(channel)}>
                    <span className="source-avatar" aria-hidden="true">
                      {initials(channel.name)}
                    </span>
                    <span className="source-check" aria-label="Подписан">
                      ✓
                    </span>
                  </div>
                  <p className="source-name">{channel.name}</p>
                  <p className="source-type">{channel.recommended ? "Профиль" : "Свой"}</p>
                </li>
              ))}

              {remaining > 0 ? (
                <li className="source-cell">
                  <button type="button" className="source-more" onClick={() => setTab("catalog")}>
                    <span aria-hidden="true">↘</span>
                    <span>
                      Посмотреть ещё
                      <br />
                      {channelCountLabel(remaining)}
                    </span>
                  </button>
                </li>
              ) : null}
            </ul>
          )}

          {channels.length > 0 ? (
            <button
              type="button"
              className="sources-unsubscribe"
              onClick={() => unsubscribeAll.mutate()}
              disabled={unsubscribeAll.isPending}
            >
              {unsubscribeAll.isPending ? "Отписываемся…" : "Отписаться от всех"}
            </button>
          ) : null}
        </>
      ) : (
        <div className="sources-catalog">
          <label className="field sources-search">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Поиск канала или @handle"
              autoFocus
            />
          </label>

          {catalog.isPending ? <p className="sources-note">Ищем каналы…</p> : null}
          {catalog.isError ? <p className="form-error">Не удалось загрузить каталог</p> : null}

          <ul className="catalog-list">
            {(catalog.data?.items ?? []).map((channel) => (
              <li key={channel.id}>
                <button
                  type="button"
                  className="catalog-row"
                  aria-pressed={channel.subscribed}
                  disabled={pending}
                  onClick={() => toggleChannel(channel)}
                >
                  <span className="catalog-avatar" data-tone={toneFor(channel)} aria-hidden="true">
                    {initials(channel.name)}
                  </span>
                  <span className="catalog-body">
                    <span className="catalog-name">{channel.name}</span>
                    <span className="catalog-topics">{channel.handle ?? channel.topics}</span>
                  </span>
                  <span className={channel.subscribed ? "catalog-action is-subscribed" : "catalog-action"}>
                    {channel.subscribed ? "✓" : "+"}
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {catalog.data && catalog.data.items.length === 0 ? (
            <p className="sources-note">Ничего не нашлось. Попробуйте другой запрос.</p>
          ) : null}
        </div>
      )}
    </div>
  );
}
