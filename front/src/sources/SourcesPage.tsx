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
import { channelCountLabel, pluralRu } from "../lib/plural";
import { useMediaQuery } from "../lib/useMediaQuery";
import { ChannelCard } from "./ChannelCard";
import { channelInitials, channelTone, formatSubscribers } from "./channelVisuals";
import { SourceIcon } from "./SourceIcon";
import { MoreCard } from "./MoreCard";
import { officialSources } from "./officialSources";
import { SourcesHeader, type SourcesTab } from "./SourcesHeader";
import "./sources.css";

export default function SourcesPage() {
  const api = useApi();
  const queryClient = useQueryClient();
  const isDesktop = useMediaQuery("(min-width: 1200px)");
  const [tab, setTab] = useState<SourcesTab>("channels");
  const [query, setQuery] = useState("");
  const [addQuery, setAddQuery] = useState("");

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

  const addChannel = useApiMutation<SourcesState, string>({
    mutationFn: (query) => api.sources.addChannel({ query }),
    onSuccess: (state) => {
      applyState(state);
      setAddQuery("");
      setTab("channels");
    },
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
  const covers = useMemo(() => {
    const picks = channels.filter((channel) => channel.recommended).slice(0, 2);
    const list = picks.length > 0 ? picks : channels.slice(0, 2);
    return [0, 1].map((index) => (list[index] ? channelInitials(list[index].name) : "•"));
  }, [channels]);
  const pending = subscribe.isPending || unsubscribe.isPending;
  const canAddSource = /^(@|https?:\/\/)/i.test(addQuery.trim());

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

  const catalogView = (
    <div className="sources-catalog">
      <label className="field sources-search">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Поиск канала или @handle"
          autoFocus
        />
      </label>

      <form
        className="sources-add"
        onSubmit={(event) => {
          event.preventDefault();
          if (canAddSource && !addChannel.isPending) {
            addChannel.mutate(addQuery.trim());
          }
        }}
      >
        <div className="sources-add__field">
          <input
            value={addQuery}
            onChange={(event) => setAddQuery(event.target.value)}
            placeholder="@handle, t.me/... или URL RSS-ленты"
            aria-label="Новый источник"
          />
          <button
            type="submit"
            className="sources-add__button"
            disabled={!canAddSource || addChannel.isPending}
          >
            {addChannel.isPending ? "Добавляем…" : "Добавить"}
          </button>
        </div>
        {addChannel.isError ? (
          <p className="form-error">
            {addChannel.error instanceof ApiError
              ? addChannel.error.detail
              : "Не удалось добавить источник"}
          </p>
        ) : null}
      </form>

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
              <span className="catalog-avatar" data-tone={channelTone(channel)} aria-hidden="true">
                {channel.avatar_url ? (
                  <img src={channel.avatar_url} alt="" loading="lazy" />
                ) : (
                  channelInitials(channel.name)
                )}
              </span>
              <span className="catalog-body">
                <span className="catalog-name">
                  <SourceIcon type={channel.source_type} />
                  {channel.name}
                </span>
                <span className="catalog-topics">
                  {channel.handle ?? channel.topics}
                  {channel.tg_subscribers
                    ? ` · ${formatSubscribers(channel.tg_subscribers)}`
                    : ""}
                </span>
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
  );

  const emptyView = (
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
  );

  if (isDesktop) {
    const officialLabel = pluralRu(officialSources.length, [
      "официальный источник",
      "официальных источника",
      "официальных источников",
    ]);

    return (
      <div className="sources-page sources-page--desktop">
        <SourcesHeader
          variant="desktop"
          tab={tab}
          channelCount={channels.length}
          catalogCount={data.catalog_total}
          onTabChange={setTab}
          subtitle={`${channelCountLabel(channels.length)} · ${officialLabel}`}
          query={query}
          onQueryChange={setQuery}
        />

        <div className="sources-desktop-body">
          <aside className="sources-desktop-aside">
            <section className="sources-summary">
              <strong className="sources-summary__count">{channels.length}</strong>
              <div className="sources-summary__copy">
                <p className="sources-summary__title">
                  Подписали вас на {channelCountLabel(channels.length)}
                </p>
                <p className="sources-summary__text">
                  {recommended.length > 0
                    ? `Подобрали из каталога под профиль «${recommended.join(", ")}». `
                    : ""}
                  Отпишитесь от лишних — лента подстроится.
                </p>
              </div>
            </section>

            <section className="sources-official">
              <h2>Официальные данные</h2>
              <p className="sources-official__mode">автоматически</p>
              <ul className="sources-official__list">
                {officialSources.map((source) => (
                  <li key={source.name} className="sources-official__item">
                    <span className="sources-official__body">
                      <span className="sources-official__name">{source.name}</span>
                      <span className="sources-official__description">{source.description}</span>
                    </span>
                    <span className="sources-official__check" aria-hidden="true">
                      ✓
                    </span>
                  </li>
                ))}
              </ul>
              <p className="sources-official__note">
                Выключенный источник пропадает из ленты, но продолжает проверять факты в карточках.
              </p>
            </section>

            <section className="sources-analytics">
              <span className="sources-analytics__label">
                {data.alfa_analytics ? "Включено" : "Выключено"}
              </span>
              <strong className="sources-analytics__title">Аналитика Альфа-Банка</strong>
              <span className="sources-analytics__text">Мнение аналитиков банка в каждой новости</span>
            </section>
          </aside>

          <section className="sources-panel">
            {tab === "channels" ? (
              <>
                <div className="sources-panel__head">
                  <h2 className="sources-panel__title">Мои каналы · {channels.length}</h2>
                  <button
                    type="button"
                    className="sources-unsubscribe sources-unsubscribe--desktop"
                    onClick={() => unsubscribeAll.mutate()}
                    disabled={unsubscribeAll.isPending}
                  >
                    {unsubscribeAll.isPending ? "Отписываемся…" : "Отписаться от всех"}
                  </button>
                </div>

                {channels.length === 0 ? (
                  emptyView
                ) : (
                  <ul className="sources-grid sources-grid--desktop">
                    {channels.map((channel, index) => (
                      <li key={channel.id}>
                        <ChannelCard
                          variant="desktop"
                          channel={channel}
                          index={index}
                          onToggle={toggleChannel}
                          disabled={pending}
                        />
                      </li>
                    ))}

                    {remaining > 0 ? (
                      <li>
                        <MoreCard
                          variant="desktop"
                          count={remaining}
                          onClick={() => setTab("catalog")}
                        />
                      </li>
                    ) : null}
                  </ul>
                )}
              </>
            ) : (
              <>
                <div className="sources-panel__head">
                  <button
                    type="button"
                    className="sources-panel__back"
                    onClick={() => setTab("channels")}
                  >
                    ← Мои каналы
                  </button>
                  <h2 className="sources-panel__title">Каталог · {data.catalog_total}</h2>
                </div>
                <div className="sources-desktop-catalog">{catalogView}</div>
              </>
            )}
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="sources-page">
      <div className="sources-top">
        <SourcesHeader
          tab={tab}
          channelCount={channels.length}
          catalogCount={data.catalog_total}
          onTabChange={setTab}
        />

        {tab === "channels" ? (
          <section className="sources-hint">
            <span className="sources-hint__covers" aria-hidden="true">
              <span className="sources-hint__cover sources-hint__cover--back">{covers[1]}</span>
              <span className="sources-hint__cover sources-hint__cover--front">{covers[0]}</span>
            </span>
            <div className="sources-hint__text">
              <p className="sources-hint__label">Подобрали каналы под профиль</p>
              <p className="sources-hint__value">{recommended.join(" · ") || "Ваш бизнес"}</p>
            </div>
          </section>
        ) : null}
      </div>

      {tab === "channels" ? (
        <>
          {channels.length === 0 ? (
            emptyView
          ) : (
            <section className="sources-collection">
              <ul className="sources-grid">
                {channels.map((channel, index) => (
                  <li key={channel.id}>
                    <ChannelCard
                      channel={channel}
                      index={index}
                      onToggle={toggleChannel}
                      disabled={pending}
                    />
                  </li>
                ))}

                {remaining > 0 ? (
                  <li>
                    <MoreCard count={remaining} onClick={() => setTab("catalog")} />
                  </li>
                ) : null}
              </ul>

              <button
                type="button"
                className="sources-unsubscribe"
                onClick={() => unsubscribeAll.mutate()}
                disabled={unsubscribeAll.isPending}
              >
                {unsubscribeAll.isPending ? "Отписываемся…" : "Отписаться от всех"}
              </button>
            </section>
          )}
        </>
      ) : (
        catalogView
      )}
    </div>
  );
}
