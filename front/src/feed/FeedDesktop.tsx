import { useEffect, useRef, useState } from "react";
import bookmarkIcon from "../assets/icons/bookmark.svg";
import { ApiError, useApi, useApiQuery, type FeedItemDetail, type ScoreComponent } from "../api";
import { Link } from "../router";
import { FeedFilters } from "./FeedFilters";
import { avatarColors, formatTime, initials } from "./mapFeed";
import type { FeedPost as FeedPostModel, ImpactTone } from "./types";

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

function scoreTone(score: number): string {
  if (score >= 80) return "is-high";
  if (score >= 50) return "is-mid";
  return "is-low";
}

function toneClass(tone: ImpactTone): string {
  return `is-${tone}`;
}

function shortImpactLabel(tone: ImpactTone): string {
  if (tone === "risk") return "Риск";
  if (tone === "opportunity") return "Возможность";
  if (tone === "mixed") return "Смешанное";
  return "Нейтрально";
}

function ImpactArrow({ tone }: { tone: ImpactTone }) {
  if (tone === "risk") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 7l6 6 4-4 8 8" />
        <path d="M15 17h6v-6" />
      </svg>
    );
  }
  if (tone === "opportunity") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 17l6-6 4 4 8-8" />
        <path d="M15 7h6v6" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 12h16" />
    </svg>
  );
}

function NavArrow({ direction }: { direction: "up" | "down" }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d={direction === "up" ? "M4 12.5l6-6 6 6" : "M4 7.5l6 6 6-6"} />
    </svg>
  );
}

function Chevron({ direction }: { direction: "left" | "right" }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d={direction === "left" ? "M10.5 2.5 5 8l5.5 5.5" : "M5.5 2.5 11 8l-5.5 5.5"} />
    </svg>
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
    <section className="feed-desk-compare">
      <h3 className="feed-desk-panel__label">Сравнение источников</h3>
      {groups.map((group) => (
        <div className={`feed-desk-compare__group ${group.tone}`} key={group.label}>
          <p className="feed-desk-compare__name">{group.label}</p>
          {group.items.map((text, index) => (
            <p className="feed-desk-compare__point" key={`${group.label}-${index}`}>
              {text}
            </p>
          ))}
        </div>
      ))}
    </section>
  );
}

function SourceViewer({ detail }: { detail: FeedItemDetail }) {
  const sources = detail.sources;
  const primaryIndex = Math.max(
    sources.findIndex((source) => source.is_primary),
    0,
  );
  const [index, setIndex] = useState(primaryIndex);
  const current = sources[Math.min(index, Math.max(sources.length - 1, 0))];

  if (!current) {
    return (
      <section className="feed-desk-panel__sources">
        <p className="feed-desk-panel__label">Что пишут</p>
        <p className="feed-desk-source__text">{detail.summary}</p>
      </section>
    );
  }

  const go = (next: number) => setIndex(Math.max(0, Math.min(sources.length - 1, next)));
  const sourceColor = avatarColors[index % avatarColors.length];

  return (
    <section className="feed-desk-panel__sources">
      <div className="feed-desk-panel__sources-head">
        <span className="feed-desk-panel__label">
          Что пишут · {index + 1} из {sources.length}
        </span>
        <div className="feed-desk-panel__arrows">
          <button
            type="button"
            aria-label="Предыдущий источник"
            disabled={index === 0}
            onClick={() => go(index - 1)}
          >
            <Chevron direction="left" />
          </button>
          <button
            type="button"
            aria-label="Следующий источник"
            disabled={index >= sources.length - 1}
            onClick={() => go(index + 1)}
          >
            <Chevron direction="right" />
          </button>
        </div>
      </div>

      <div className="feed-desk-pills">
        {sources.map((source, sourceIndex) => (
          <button
            key={`${source.name}-${sourceIndex}`}
            type="button"
            className={sourceIndex === index ? "feed-desk-pill is-active" : "feed-desk-pill"}
            style={{ background: avatarColors[sourceIndex % avatarColors.length] }}
            aria-label={source.name}
            aria-pressed={sourceIndex === index}
            onClick={() => setIndex(sourceIndex)}
          >
            {initials(source.name)}
          </button>
        ))}
      </div>

      <article className="feed-desk-source">
        <header className="feed-desk-source__head">
          <span className="feed-desk-source__avatar" style={{ background: sourceColor }}>
            {initials(current.name)}
          </span>
          <span className="feed-desk-source__who">
            <strong>{current.name}</strong>
            <span>
              {formatTime(current.time)} · {current.status_label}
            </span>
          </span>
        </header>
        <p className="feed-desk-source__text">{current.text || detail.summary}</p>
      </article>
    </section>
  );
}

function ScoreBreakdown({ detail }: { detail: FeedItemDetail }) {
  const hasRows = detail.score_breakdown.length > 0;

  return (
    <section className="feed-desk-score">
      <p className="feed-desk-panel__label">Важность для бизнеса</p>
      <div className="feed-desk-score__head">
        <p className="feed-desk-score__why">
          {detail.score_why || detail.prognosis_note || detail.what_it_means}
        </p>
        <p className={`feed-desk-score__value ${scoreTone(detail.importance)}`}>
          {detail.importance}
          <span>/100</span>
        </p>
      </div>

      {hasRows ? (
        <div className="feed-desk-score__rows">
          {detail.score_breakdown.map((item) => {
            const level = item.max ? Math.round((item.value / item.max) * 5) : 0;
            return (
              <div className="feed-desk-score__row" key={item.key}>
                <div className="feed-desk-score__row-head">
                  <span>{item.label}</span>
                  <span className="feed-desk-score__row-value">
                    <span className="feed-desk-score__bars" aria-hidden="true">
                      {[1, 2, 3, 4, 5].map((bar) => (
                        <i key={bar} className={bar <= level ? "is-on" : undefined} />
                      ))}
                    </span>
                    {scoreValue(item)}
                  </span>
                </div>
                {item.text ? <p className="feed-desk-score__row-text">{item.text}</p> : null}
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="feed-desk-score__meta">
        <div>
          <span>Тип</span>
          <strong className={toneClass(detail.impact as ImpactTone)}>
            {detail.impact_label || detail.impact}
          </strong>
        </div>
        {detail.impact_share ? (
          <div>
            <span>Затронуто</span>
            <strong>{detail.impact_share}</strong>
          </div>
        ) : null}
      </div>
      {detail.prognosis_note && detail.score_why ? (
        <p className="feed-desk-score__note">{detail.prognosis_note}</p>
      ) : null}
    </section>
  );
}

type ReelProps = {
  post: FeedPostModel;
  activeSlide: number;
  isActive: boolean;
  canPrev: boolean;
  canNext: boolean;
  registerCarousel: (id: string, element: HTMLDivElement | null) => void;
  onSlideScroll: (id: string, element: HTMLDivElement) => void;
  onToggleTracked: (id: string) => void;
  onOpenSources: () => void;
  onOpenScore: () => void;
  onPrev: () => void;
  onNext: () => void;
};

function FeedReel({
  post,
  activeSlide,
  isActive,
  canPrev,
  canNext,
  registerCarousel,
  onSlideScroll,
  onToggleTracked,
  onOpenSources,
  onOpenScore,
  onPrev,
  onNext,
}: ReelProps) {
  const current = post.sources[Math.min(activeSlide, Math.max(post.sources.length - 1, 0))];
  const scoreClass = scoreTone(post.importance);

  return (
    <div className="feed-desk-reel">
      <div className="feed-desk-nav" aria-label={isActive ? "Навигация по ленте" : undefined}>
        {isActive ? (
          <>
            <button type="button" aria-label="Предыдущая новость" disabled={!canPrev} onClick={onPrev}>
              <NavArrow direction="up" />
            </button>
            <button type="button" aria-label="Следующая новость" disabled={!canNext} onClick={onNext}>
              <NavArrow direction="down" />
            </button>
          </>
        ) : null}
      </div>

      <div className="feed-desk-card">
        <div
          className="feed-desk-carousel"
          ref={(element) => registerCarousel(post.id, element)}
          onScroll={(event) => onSlideScroll(post.id, event.currentTarget)}
        >
          {post.sources.map((source) => (
            <div className="feed-desk-slide" key={source.id}>
              <img src={source.image} alt={source.imageAlt} draggable={false} />
            </div>
          ))}
        </div>
        {current ? (
          <div className="feed-desk-chip">
            <span className="feed-desk-chip__avatar" style={{ background: current.color }}>
              {current.initials}
            </span>
            <span className="feed-desk-chip__name">{current.name}</span>
            <span className="feed-desk-chip__time">{current.time}</span>
          </div>
        ) : null}
      </div>

      <div className="feed-desk-actions" aria-label="Действия">
        <button type="button" className="feed-desk-act" onClick={onOpenSources}>
          <span className="feed-desk-ring feed-desk-ring--sources">
            {post.sources.slice(0, 2).map((source, index) => (
              <span
                className="feed-desk-ring__avatar"
                key={source.id}
                style={{ background: source.color, marginLeft: index ? -8 : 0 }}
              >
                {source.initials}
              </span>
            ))}
          </span>
          <span className="feed-desk-act__caption">{post.sources.length} ист.</span>
        </button>

        <button type="button" className="feed-desk-act" onClick={onOpenScore}>
          <span className={`feed-desk-ring feed-desk-ring--score ${scoreClass}`}>
            {post.importance}
          </span>
          <span className="feed-desk-act__caption">Важность</span>
        </button>

        <div className="feed-desk-act feed-desk-act--static" aria-label={shortImpactLabel(post.impact)}>
          <span className={`feed-desk-ring feed-desk-ring--tone ${toneClass(post.impact)}`}>
            <ImpactArrow tone={post.impact} />
          </span>
          <span className="feed-desk-act__caption">{shortImpactLabel(post.impact)}</span>
        </div>

        <button
          type="button"
          className="feed-desk-act"
          aria-pressed={post.tracked}
          aria-label={post.tracked ? "Не отслеживать тему" : "Отслеживать тему"}
          onClick={() => onToggleTracked(post.id)}
        >
          <span className={post.tracked ? "feed-desk-ring feed-desk-ring--track is-on" : "feed-desk-ring feed-desk-ring--track"}>
            <img src={bookmarkIcon} alt="" width={22} height={22} />
          </span>
          <span className="feed-desk-act__caption">
            {post.tracked ? "Отслеживается" : "Отслеживать"}
          </span>
        </button>
      </div>
    </div>
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
  const panelRef = useRef<HTMLDivElement>(null);
  const carousels = useRef<Record<string, HTMLDivElement | null>>({});
  const stageAnimation = useRef<number | null>(null);
  const stageLocked = useRef(false);
  const stageAnimating = useRef(false);
  const stageUnlockTimer = useRef<number | null>(null);
  const stageLastWheel = useRef(0);
  const [activeIndex, setActiveIndex] = useState(0);
  const [slides, setSlides] = useState<Record<string, number>>({});
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
    const target = Math.max(0, Math.min(targetIndex, posts.length));
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

  useEffect(() => {
    stopStageScroll();
    setActiveIndex(0);
    setSlides({});
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

      if (!stage.clientHeight) return;
      const current = Math.round(stage.scrollTop / stage.clientHeight);
      const direction = event.deltaY > 0 ? 1 : -1;
      const target = Math.max(0, Math.min(current + direction, posts.length));
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
  const activeSlide = activePost ? (slides[activePost.id] ?? 0) : 0;

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

  const handleSlideScroll = (id: string, element: HTMLDivElement) => {
    if (!element.clientWidth) return;
    const next = Math.round(element.scrollLeft / element.clientWidth);
    setSlides((current) => (current[id] === next ? current : { ...current, [id]: next }));
  };

  const showSlide = (index: number) => {
    if (!activePost) return;
    const carousel = carousels.current[activePost.id];
    if (!carousel) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    carousel.scrollTo({ left: index * carousel.clientWidth, behavior: reduceMotion ? "auto" : "smooth" });
    setSlides((current) => ({ ...current, [activePost.id]: index }));
  };

  const goToPost = (index: number) => {
    if (stageLocked.current) return;
    const next = Math.max(0, Math.min(index, posts.length - 1));
    stageLastWheel.current = 0;
    animateStageTo(next);
  };

  const scrollPanelTo = (selector: string) => {
    const target = panelRef.current?.querySelector<HTMLElement>(selector);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const restartFeed = () => {
    stopStageScroll();
    stageRef.current?.scrollTo({ top: 0 });
    setActiveIndex(0);
    setSlides({});
  };

  const currentSource =
    activePost?.sources[Math.min(activeSlide, Math.max(activePost.sources.length - 1, 0))];
  const facts = detail?.impact_metrics.length ? detail.impact_metrics : (activePost?.metrics ?? []);
  const sourceCount = activePost?.sources.length ?? 0;

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
        <aside className="feed-desk-info" aria-label="Информация о текущей новости">
          {activePost && currentSource ? (
            <>
              <div className="feed-desk-author">
                <span className="feed-desk-author__avatar" style={{ background: currentSource.color }}>
                  {currentSource.initials}
                </span>
                <span className="feed-desk-author__name">{currentSource.name}</span>
                <time className="feed-desk-author__time">{currentSource.time}</time>
              </div>

              <div className="feed-desk-info__bottom">
                <div className="feed-desk-tags">
                  {activePost.topics.map((topic) => (
                    <span className="feed-desk-tag" key={topic}>
                      #{topic}
                    </span>
                  ))}
                </div>
                <h2 className="feed-desk-title">{activePost.title}</h2>
                <div className="feed-desk-meaning">
                  <p className="feed-desk-meaning__label">Что это значит для вас</p>
                  {facts.length > 0 ? (
                    facts.map((fact, index) => (
                      <p className="feed-desk-fact" key={`${fact.value}-${index}`}>
                        <strong>{fact.value}</strong>
                        <span>{fact.note}</span>
                      </p>
                    ))
                  ) : (
                    <p className="feed-desk-fact">
                      <span>{detail?.what_it_means || detail?.summary || "Разбор загружается…"}</span>
                    </p>
                  )}
                </div>
                <Link to={`/event/${activePost.id}`} className="feed-desk-open">
                  Открыть разбор
                </Link>
              </div>
            </>
          ) : null}
        </aside>

        <div className="feed-desktop__stage-wrap">
          <div className="feed-desktop__stage" ref={stageRef} onScroll={handleStageScroll}>
            {posts.length === 0 ? (
              <p className="feed-desktop__empty">Нет новостей по этому фильтру</p>
            ) : (
              <>
                {posts.map((post, index) => (
                  <FeedReel
                    key={post.id}
                    post={post}
                    activeSlide={slides[post.id] ?? 0}
                    isActive={index === activeIndex}
                    canPrev={activeIndex > 0}
                    canNext={activeIndex < posts.length - 1}
                    registerCarousel={(id, element) => {
                      carousels.current[id] = element;
                    }}
                    onSlideScroll={handleSlideScroll}
                    onToggleTracked={onToggleTracked}
                    onOpenSources={() => scrollPanelTo(".feed-desk-panel__sources")}
                    onOpenScore={() => scrollPanelTo(".feed-desk-score")}
                    onPrev={() => goToPost(activeIndex - 1)}
                    onNext={() => goToPost(activeIndex + 1)}
                  />
                ))}
                <section className="feed-desk-end">
                  <p className="feed-desk-end__label">Конец ленты</p>
                  <h2 className="feed-desk-end__title">Лента просмотрена</h2>
                  <p className="feed-desk-end__text">
                    Пропущенные, устаревшие и новости со слабым влиянием — в скрытом
                  </p>
                  <div className="feed-desk-end__actions">
                    <Link to="/hidden" className="feed-desk-end__primary">
                      Посмотреть скрытые · {hiddenCount}
                    </Link>
                    <button type="button" className="feed-desk-end__ghost" onClick={restartFeed}>
                      Начать заново
                    </button>
                  </div>
                </section>
              </>
            )}
          </div>

          {posts.length > 0 ? (
            <div className="feed-desk-bottom">
              <div className="feed-desk-dots">
                {activePost?.sources.map((source, index) => (
                  <button
                    key={source.id}
                    type="button"
                    className={index === activeSlide ? "feed-desk-dot is-active" : "feed-desk-dot"}
                    aria-label={`Показать публикацию ${index + 1}`}
                    onClick={() => showSlide(index)}
                  />
                ))}
              </div>
              <span className="feed-desk-pos">
                {Math.min(activeSlide + 1, sourceCount)}/{sourceCount}
              </span>
            </div>
          ) : null}
        </div>

        <aside className="feed-desk-panel" aria-label="Источники и важность">
          <header className="feed-desk-panel__head">
            <span>Источники и важность</span>
            {/* activePost ? (
              <Link to={`/event/${activePost.id}`} className="feed-desk-panel__open">
                Разбор
              </Link>
            ) : null */}
          </header>
          <div className="feed-desk-panel__body" ref={panelRef}>
            {detailQuery.isError ? (
              <p className="feed-desktop__state">{detailError(detailQuery.error)}</p>
            ) : detail ? (
              <>
                <h2 className="feed-desk-panel__title">{detail.title}</h2>
                <SourceViewer key={detail.id} detail={detail} />
                <ScoreBreakdown detail={detail} />
                <SourceComparison detail={detail} />
              </>
            ) : posts.length === 0 ? (
              <p className="feed-desktop__state">Выберите новость в ленте</p>
            ) : (
              <p className="feed-desktop__state">Загрузка…</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
