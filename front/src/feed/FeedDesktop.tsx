import { useEffect, useRef, useState } from "react";
import { ApiError, useApi, useApiQuery, type FeedItemDetail, type ScoreComponent } from "../api";
import { Link } from "../router";
import { FeedFilters } from "./FeedFilters";
import { FeedPost } from "./FeedPost";
import { avatarColors, formatTime, initials } from "./mapFeed";
import type { FeedPost as FeedPostModel } from "./types";

type FeedDesktopProps = {
  posts: FeedPostModel[];
  hiddenCount: number;
  filters: string[];
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  onToggleTracked: (id: string) => void;
};

function detailError(error: Error | null): string {
  return error instanceof ApiError ? error.detail : "Не удалось загрузить разбор.";
}

function scoreValue(item: ScoreComponent): string {
  if (item.key === "scale") return `${item.value}/${item.max}`;
  const ratio = item.max ? item.value / item.max : 0;
  return `×${ratio.toLocaleString("ru-RU", { maximumFractionDigits: 1 })}`;
}

function SourceSummary({ detail }: { detail: FeedItemDetail }) {
  const sources = detail.sources;
  const primaryIndex = Math.max(
    sources.findIndex((source) => source.is_primary),
    0,
  );
  const primary = sources[primaryIndex];
  if (!primary) return null;

  return (
    <div className="feed-sources-panel__primary">
      <p className="feed-sources-panel__meta">
        {formatTime(primary.time)} · {primary.status_label}
      </p>
      <p className="feed-sources-panel__name">{primary.name}</p>
      <p className="feed-sources-panel__text">{primary.text || detail.summary}</p>
      {sources.length > 0 ? (
        <p className="feed-sources-panel__count">
          Что пишут · {primaryIndex + 1} из {sources.length}
        </p>
      ) : null}
    </div>
  );
}

function SourceComparison({ detail }: { detail: FeedItemDetail }) {
  const { agree, differ, single } = detail.comparison;
  const groups = [
    { label: "Сходятся", tone: "", items: agree.length ? agree : [detail.summary] },
    { label: "Расходятся", tone: "is-differ", items: differ },
    { label: "Пишет один источник", tone: "is-single", items: single },
  ].filter((group) => group.items.length > 0);

  if (groups.length === 0) return null;

  return (
    <div className="feed-sources-panel__comparison">
      <h3 className="feed-sources-panel__subtitle">Сравнение источников</h3>
      {groups.map((group) => (
        <div className={`feed-sources-panel__group ${group.tone}`} key={group.label}>
          <p className="feed-sources-panel__group-label">{group.label}</p>
          {group.items.map((text, index) => (
            <p className="feed-sources-panel__point" key={`${group.label}-${index}`}>
              {text}
            </p>
          ))}
        </div>
      ))}
    </div>
  );
}

function ImportanceCards({ detail }: { detail: FeedItemDetail }) {
  const note = detail.prognosis_note || detail.what_it_means;

  return (
    <>
      <section className="feed-importance-card">
        <p className="feed-importance-card__label">
          Важность · {detail.impact_label || detail.impact} · из 100
        </p>
        <p className="feed-importance-card__score">{detail.importance}</p>
        {note ? <p className="feed-importance-card__note">{note}</p> : null}
        {detail.impact_share ? (
          <p className="feed-importance-card__share">Затронуто: {detail.impact_share}</p>
        ) : null}
      </section>

      {detail.score_breakdown.length > 0 || detail.score_why ? (
        <section className="feed-breakdown-card">
          {detail.score_breakdown.length > 0 ? (
            detail.score_breakdown.map((item) => (
              <div className="feed-breakdown__row" key={item.key}>
                <p className="feed-breakdown__head">
                  {item.label} · {scoreValue(item)}
                </p>
                {item.text ? <p className="feed-breakdown__text">{item.text}</p> : null}
              </div>
            ))
          ) : (
            <p className="feed-breakdown__text">{detail.score_why}</p>
          )}
        </section>
      ) : null}
    </>
  );
}

export function FeedDesktop({
  posts,
  hiddenCount,
  filters,
  activeFilter,
  onFilterChange,
  onToggleTracked,
}: FeedDesktopProps) {
  const api = useApi();
  const stageRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const signature = posts.map((post) => post.id).join("|");

  useEffect(() => {
    setActiveIndex(0);
    stageRef.current?.scrollTo({ top: 0 });
  }, [signature]);

  const activePost = posts[Math.min(activeIndex, Math.max(posts.length - 1, 0))];
  const activeId = activePost?.id ?? "";

  const detailQuery = useApiQuery({
    queryKey: ["feed", "detail", activeId],
    queryFn: (signal) => api.feed.detail(activeId, { signal }),
    enabled: Boolean(activeId),
  });
  const detail = detailQuery.data;

  const handleStageScroll = () => {
    const stage = stageRef.current;
    if (!stage || !stage.clientHeight || posts.length === 0) return;
    const next = Math.min(
      Math.max(Math.round(stage.scrollTop / stage.clientHeight), 0),
      posts.length - 1,
    );
    setActiveIndex((current) => (current === next ? current : next));
  };

  return (
    <div className="feed-desktop">
      <header className="feed-desktop__head">
        <div className="feed-desktop__head-row">
          <h1 className="feed-desktop__title">Лента</h1>
          <Link to="/hidden" className="feed-desktop__hidden">
            Скрытые · {hiddenCount}
          </Link>
        </div>
        <FeedFilters filters={filters} active={activeFilter} onChange={onFilterChange} />
      </header>

      <div className="feed-desktop__body">
        <aside className="feed-desktop__col" aria-label="Источники и сравнение">
          <section className="feed-sources-panel">
            <h2 className="feed-sources-panel__title">Источники и важность</h2>
            {detailQuery.isError ? (
              <p className="feed-desktop__state">{detailError(detailQuery.error)}</p>
            ) : detail ? (
              <>
                {detail.sources.length > 0 ? (
                  <div className="feed-sources-panel__avatars">
                    {detail.sources.map((source, index) => (
                      <span
                        className="feed-sources-panel__avatar"
                        style={{ background: avatarColors[index % avatarColors.length] }}
                        key={`${source.name}-${index}`}
                      >
                        {initials(source.name)}
                      </span>
                    ))}
                  </div>
                ) : null}
                <SourceSummary detail={detail} />
                <SourceComparison detail={detail} />
              </>
            ) : posts.length === 0 ? null : (
              <p className="feed-desktop__state">Загрузка…</p>
            )}
          </section>
        </aside>

        <div className="feed-desktop__stage" ref={stageRef} onScroll={handleStageScroll}>
          {posts.length === 0 ? (
            <p className="feed-desktop__empty">Нет новостей по этому фильтру</p>
          ) : (
            posts.map((post) => (
              <FeedPost key={post.id} post={post} onToggleTracked={onToggleTracked} desktop />
            ))
          )}
        </div>

        <aside className="feed-desktop__col" aria-label="Важность и расчёт">
          {detailQuery.isError ? (
            <section className="feed-rail-state">
              <p>{detailError(detailQuery.error)}</p>
            </section>
          ) : detail ? (
            <ImportanceCards detail={detail} />
          ) : posts.length === 0 ? null : (
            <section className="feed-rail-state">
              <p>Загрузка…</p>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
