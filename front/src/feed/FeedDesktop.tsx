import { useEffect, useRef, useState } from "react";
import bookmarkIcon from "../assets/icons/bookmark.svg";
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

function RailArrow({ direction }: { direction: "up" | "down" }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d={direction === "up" ? "M4 12.5l6-6 6 6" : "M4 7.5l6 6 6-6"} />
    </svg>
  );
}

function SourceSummary({
  detail,
  index,
  onChange,
}: {
  detail: FeedItemDetail;
  index: number;
  onChange: (index: number) => void;
}) {
  const sources = detail.sources;
  const currentIndex = Math.min(index, Math.max(sources.length - 1, 0));
  const current = sources[currentIndex];
  if (!current) return null;

  return (
    <div className="feed-sources-panel__primary">
      <p className="feed-sources-panel__meta">
        {formatTime(current.time)} · {current.status_label}
      </p>
      <p className="feed-sources-panel__name">{current.name}</p>
      <p className="feed-sources-panel__text">{current.text || detail.summary}</p>
      <div className="feed-sources-panel__switch">
        <button
          type="button"
          className="feed-sources-panel__switch-button"
          aria-label="Предыдущий источник"
          disabled={currentIndex === 0}
          onClick={() => onChange(currentIndex - 1)}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M10.5 2.5 5 8l5.5 5.5" />
          </svg>
        </button>
        <p className="feed-sources-panel__count">
          Что пишут · {currentIndex + 1} из {sources.length}
        </p>
        <button
          type="button"
          className="feed-sources-panel__switch-button"
          aria-label="Следующий источник"
          disabled={currentIndex >= sources.length - 1}
          onClick={() => onChange(currentIndex + 1)}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M5.5 2.5 11 8l-5.5 5.5" />
          </svg>
        </button>
      </div>
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
  const stageAnimation = useRef<number | null>(null);
  const stageLocked = useRef(false);
  const stageAnimating = useRef(false);
  const stageUnlockTimer = useRef<number | null>(null);
  const stageLastWheel = useRef(0);
  const [activeIndex, setActiveIndex] = useState(0);
  const [sourceIndex, setSourceIndex] = useState(0);
  const signature = posts.map((post) => post.id).join("|");

  const stopStageScroll = () => {
    if (stageAnimation.current !== null) {
      cancelAnimationFrame(stageAnimation.current);
      stageAnimation.current = null;
    }
    if (stageUnlockTimer.current !== null) {
      clearTimeout(stageUnlockTimer.current);
      stageUnlockTimer.current = null;
    }
    stageAnimating.current = false;
    stageLocked.current = false;
    if (stageRef.current) stageRef.current.style.scrollSnapType = "";
  };

  const scheduleStageUnlock = () => {
    if (stageUnlockTimer.current !== null) clearTimeout(stageUnlockTimer.current);
    const wait = Math.max(0, 140 - (performance.now() - stageLastWheel.current));
    stageUnlockTimer.current = window.setTimeout(() => {
      stageUnlockTimer.current = null;
      if (!stageAnimating.current) stageLocked.current = false;
    }, wait);
  };

  const animateStageTo = (targetIndex: number) => {
    const stage = stageRef.current;
    if (!stage) return;
    const target = Math.max(0, Math.min(targetIndex, posts.length - 1));
    const targetTop = target * stage.clientHeight;
    const startTop = stage.scrollTop;

    if (Math.abs(targetTop - startTop) < 1) {
      stageLocked.current = false;
      return;
    }

    stageLocked.current = true;
    stageAnimating.current = true;
    stage.style.scrollSnapType = "none";
    const startedAt = performance.now();
    const duration = 280;

    const step = (now: number) => {
      const progress = Math.min((now - startedAt) / duration, 1);
      stage.scrollTop = startTop + (targetTop - startTop) * progress;
      if (progress < 1) {
        stageAnimation.current = requestAnimationFrame(step);
        return;
      }
      stage.scrollTop = targetTop;
      stage.style.scrollSnapType = "";
      stageAnimation.current = null;
      stageAnimating.current = false;
      scheduleStageUnlock();
    };

    stageAnimation.current = requestAnimationFrame(step);
  };

  const goToPost = (index: number) => {
    if (stageLocked.current) return;
    stageLastWheel.current = 0;
    animateStageTo(index);
  };

  useEffect(() => {
    stopStageScroll();
    setActiveIndex(0);
    stageRef.current?.scrollTo({ top: 0 });
  }, [signature]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;

    const onWheel = (event: WheelEvent) => {
      if (event.ctrlKey || !event.deltaY) return;
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
      event.preventDefault();
      stageLastWheel.current = performance.now();

      if (stageLocked.current) {
        if (!stageAnimating.current) scheduleStageUnlock();
        return;
      }

      if (!stage.clientHeight || posts.length === 0) return;
      const current = Math.round(stage.scrollTop / stage.clientHeight);
      const direction = event.deltaY > 0 ? 1 : -1;
      const target = Math.max(0, Math.min(current + direction, posts.length - 1));
      if (target === current) return;
      animateStageTo(target);
    };

    stage.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      stage.removeEventListener("wheel", onWheel);
      stopStageScroll();
    };
  }, [posts.length]);

  const activePost = posts[Math.min(activeIndex, Math.max(posts.length - 1, 0))];
  const activeId = activePost?.id ?? "";

  const detailQuery = useApiQuery({
    queryKey: ["feed", "detail", activeId],
    queryFn: (signal) => api.feed.detail(activeId, { signal }),
    enabled: Boolean(activeId),
  });
  const detail = detailQuery.data;

  useEffect(() => {
    const primary = detail?.sources.findIndex((source) => source.is_primary) ?? 0;
    setSourceIndex(Math.max(primary, 0));
  }, [detail?.id]);

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
        <aside className="feed-desktop__col" aria-label="Источники">
          <section className="feed-sources-panel">
            <h2 className="feed-sources-panel__title">Источники и важность</h2>
            {detailQuery.isError ? (
              <p className="feed-desktop__state">{detailError(detailQuery.error)}</p>
            ) : detail ? (
              <>
                {detail.sources.length > 0 ? (
                  <div className="feed-sources-panel__avatars">
                    {detail.sources.map((source, index) => (
                      <button
                        type="button"
                        className={
                          index === Math.min(sourceIndex, detail.sources.length - 1)
                            ? "feed-sources-panel__avatar is-active"
                            : "feed-sources-panel__avatar"
                        }
                        style={{ background: avatarColors[index % avatarColors.length] }}
                        key={`${source.name}-${index}`}
                        aria-label={`Источник ${source.name}`}
                        aria-pressed={index === Math.min(sourceIndex, detail.sources.length - 1)}
                        onClick={() => setSourceIndex(index)}
                      >
                        {initials(source.name)}
                      </button>
                    ))}
                  </div>
                ) : null}
                <SourceSummary detail={detail} index={sourceIndex} onChange={setSourceIndex} />
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
            posts.map((post, index) => (
              <FeedPost
                key={post.id}
                post={post}
                onToggleTracked={onToggleTracked}
                desktop
                desktopSourceIndex={index === activeIndex ? sourceIndex : undefined}
                onDesktopSourceChange={index === activeIndex ? setSourceIndex : undefined}
              />
            ))
          )}
        </div>

        <aside className="feed-desktop__actions" aria-label="Действия с новостью">
          <button
            type="button"
            className="feed-desktop__action"
            aria-label="Предыдущая новость"
            disabled={activeIndex <= 0}
            onClick={() => goToPost(activeIndex - 1)}
          >
            <RailArrow direction="up" />
          </button>
          <button
            type="button"
            className="feed-desktop__action"
            aria-label="Следующая новость"
            disabled={activeIndex >= posts.length - 1}
            onClick={() => goToPost(activeIndex + 1)}
          >
            <RailArrow direction="down" />
          </button>
          <button
            type="button"
            className={
              activePost?.tracked
                ? "feed-desktop__action feed-desktop__action--track is-tracked"
                : "feed-desktop__action feed-desktop__action--track"
            }
            aria-label={activePost?.tracked ? "Не отслеживать тему" : "Отслеживать тему"}
            aria-pressed={activePost?.tracked ?? false}
            disabled={!activePost}
            onClick={() => {
              if (activePost) onToggleTracked(activePost.id);
            }}
          >
            <img src={bookmarkIcon} alt="" width={22} height={22} />
          </button>
        </aside>

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
