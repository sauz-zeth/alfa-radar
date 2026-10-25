import { useCallback, useEffect, useRef, useState } from "react";
import bookmarkIcon from "../assets/icons/bookmark.svg";
import { Link } from "../router";
import { ImpactBlock } from "./ImpactBlock";
import type { FeedPost as FeedPostModel } from "./types";

type FeedPostProps = {
  post: FeedPostModel;
  onToggleTracked: (id: string) => void;
  desktop?: boolean;
  desktopSourceIndex?: number;
  onDesktopSourceChange?: (index: number) => void;
};

function sourceCountLabel(count: number): string {
  const mod100 = count % 100;
  const mod10 = count % 10;
  const word =
    mod100 >= 11 && mod100 <= 14 ? "источников" : mod10 === 1 ? "источник" : mod10 >= 2 && mod10 <= 4 ? "источника" : "источников";
  return `${count} ${word}`;
}

const SLIDE_DURATION_MS = 5000;

export function FeedPost({
  post,
  onToggleTracked,
  desktop = false,
  desktopSourceIndex,
  onDesktopSourceChange,
}: FeedPostProps) {
  const mediaRef = useRef<HTMLDivElement>(null);
  const postRef = useRef<HTMLElement>(null);
  const [activeSource, setActiveSource] = useState(0);
  const [inView, setInView] = useState(false);
  const [documentVisible, setDocumentVisible] = useState(true);
  const controlledSource = desktop && desktopSourceIndex !== undefined;
  const currentSource = controlledSource ? desktopSourceIndex : activeSource;
  const source = post.sources[currentSource] ?? post.sources[0];

  const selectSource = useCallback(
    (index: number) => {
      const next = Math.max(0, Math.min(index, post.sources.length - 1));
      if (controlledSource && onDesktopSourceChange) {
        onDesktopSourceChange(next);
        return;
      }
      setActiveSource(next);
    },
    [controlledSource, onDesktopSourceChange, post.sources.length],
  );

  useEffect(() => {
    if (!controlledSource || desktopSourceIndex === undefined) return;
    const media = mediaRef.current;
    if (!media || !media.clientWidth) return;
    const current = Math.round(media.scrollLeft / media.clientWidth);
    if (current === desktopSourceIndex) return;
    media.scrollTo({ left: desktopSourceIndex * media.clientWidth, behavior: "smooth" });
  }, [controlledSource, desktopSourceIndex]);

  useEffect(() => {
    const node = postRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry?.isIntersecting ?? false),
      { threshold: 0.6 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onVisibilityChange = () => setDocumentVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, []);

  const paused = !inView || !documentVisible;

  const handleMediaScroll = useCallback(() => {
    const media = mediaRef.current;
    if (!media || media.clientWidth === 0) return;
    const index = Math.round(media.scrollLeft / media.clientWidth);
    selectSource(index);
  }, [selectSource]);

  const showSource = useCallback(
    (index: number) => {
      const media = mediaRef.current;
      if (!media) return;
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      media.scrollTo({ left: index * media.clientWidth, behavior: reduceMotion ? "auto" : "smooth" });
      selectSource(index);
    },
    [selectSource],
  );

  const advance = useCallback(() => {
    showSource((currentSource + 1) % post.sources.length);
  }, [currentSource, post.sources.length, showSource]);

  return (
    <article className="feed-post" ref={postRef} aria-labelledby={`${post.id}-title`}>
      <div className="feed-post__media" ref={mediaRef} onScroll={handleMediaScroll}>
        {post.sources.map((item) => (
          <div key={item.id} className={item.fullBleed ? "post-slide is-full" : "post-slide"}>
            <img className="post-slide__photo" src={item.image} alt={item.imageAlt} draggable={false} />
          </div>
        ))}
      </div>
      <div className="feed-post__scrim" aria-hidden="true" />

      {desktop && source ? (
        <div className="post-source-chip">
          <span className="post-source-chip__avatar" style={{ background: source.color }}>
            {source.initials}
          </span>
          <span className="post-source-chip__name">{source.name}</span>
          <span className="post-source-chip__dot" aria-hidden="true">
            ·
          </span>
          <time className="post-source-chip__time">{source.time}</time>
        </div>
      ) : null}

      <div className="post-rail">
        <div className="post-rail__score">
          <div className="post-rail__dial">{post.importance}</div>
          <span className="post-rail__label">Важность</span>
        </div>
        <button
          type="button"
          className={post.tracked ? "post-rail__bookmark is-tracked" : "post-rail__bookmark"}
          aria-pressed={post.tracked}
          aria-label="Отслеживать тему"
          onClick={() => onToggleTracked(post.id)}
        >
          <img src={bookmarkIcon} alt="" width={20} height={20} />
        </button>
      </div>

      <div className="feed-post__content">
        <div className="post-source">
          <div className="post-source__stack" aria-hidden="true">
            {post.sources.slice(0, 2).map((item) => (
              <span key={item.id} className="post-source__avatar" style={{ background: item.color }}>
                {item.initials}
              </span>
            ))}
          </div>
          <span className="post-source__name">{sourceCountLabel(post.sources.length)}</span>
          <time className="post-source__time">{post.sources[0]?.time}</time>
        </div>

        <p className="post-credit">Фото · {source?.name}</p>

        <div className="post-card">
          {post.sources.length > 1 && (
            <div className={paused ? "post-card__progress is-paused" : "post-card__progress"}>
              {post.sources.map((item, index) => (
                <button
                  key={item.id}
                  type="button"
                  className={index === currentSource ? "is-current" : undefined}
                  aria-label={`Публикация ${index + 1} из ${post.sources.length}: ${item.name}`}
                  aria-current={index === currentSource ? "true" : undefined}
                  onClick={() => showSource(index)}
                >
                  <span
                    aria-hidden="true"
                    className={
                      index < currentSource
                        ? "story-fill is-complete"
                        : index === currentSource
                          ? "story-fill is-running"
                          : "story-fill"
                    }
                    style={{ animationDuration: `${SLIDE_DURATION_MS}ms` }}
                    onAnimationEnd={index === currentSource ? advance : undefined}
                  />
                </button>
              ))}
            </div>
          )}
          <Link to={`/event/${post.id}`} className="post-card__head">
            <p className="post-card__topics">{post.topics.join(" · ")}</p>
            <h2 className="post-card__title" id={`${post.id}-title`}>
              {post.title}
            </h2>
          </Link>
          <p className="post-card__meta">
            <span className="post-card__effective">{post.effectiveLabel}</span>
            {" · "}
            <span className={`impact-label impact-label--${post.impact}`}>{post.impactLabel}</span>
            {post.note ? (
              <button type="button" className="note-hint" aria-label={post.note}>
                !
                <span className="note-hint__tip" role="tooltip">
                  {post.note}
                </span>
              </button>
            ) : null}
          </p>
        </div>

        <ImpactBlock
          metrics={post.metrics}
          title={desktop ? "Что это значит для вас" : undefined}
          action={desktop ? { label: "Открыть разбор", to: `/event/${post.id}` } : undefined}
        />
      </div>
    </article>
  );
}
