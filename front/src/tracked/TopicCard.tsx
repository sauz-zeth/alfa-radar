import arrowInk from "../assets/icons/tracked/arrow-ink.svg";
import arrowSurface from "../assets/icons/tracked/arrow-surface.svg";
import { ImportanceScore } from "./ImportanceScore";
import { eventsLabel, type Topic } from "./mapTracked";

type TopicCardProps = {
  topic: Topic;
  onOpen?: () => void;
  variant?: "mobile" | "desktop";
  compact?: boolean;
};

function statusLabel(topic: Topic): string {
  return topic.updateLabel ?? (topic.changed ? "Обновление" : "Без изменений");
}

export function TopicCard({ topic, onOpen, variant = "mobile", compact = false }: TopicCardProps) {
  const dark = topic.tone === "dark";

  if (variant === "desktop") {
    return (
      <article
        className={`topic-card topic-card--desktop${compact ? " topic-card--compact" : ""}${
          topic.image ? " topic-card--with-image" : ""
        }`}
      >
        <div className="topic-card__info">
          <p className="topic-card__date">
            <span>{topic.dateLong}</span>
            <span>· {statusLabel(topic)}</span>
            {topic.changed ? (
              <span className="topic-card__badge">Выводы изменились</span>
            ) : topic.updateLabel ? (
              <span className="topic-card__badge topic-card__badge--muted">
                Уточнение, выводы прежние
              </span>
            ) : null}
          </p>

          <h3 className="topic-card__desk-title">{topic.title}</h3>
          {topic.conclusionQuestion ? (
            <p className="topic-card__question">{topic.conclusionQuestion}</p>
          ) : null}
          <p className="topic-card__conclusion">{topic.conclusion}</p>

          <div className="topic-card__foot-desktop">
            <div className="topic-card__stats">
              <span className="topic-card__score-line">
                {topic.importance} / 100
                <span className={`topic-card__impact topic-card__impact--${topic.impactTone}`}>
                  {" "}
                  · {topic.impactLabel}
                </span>
              </span>
              <span className="topic-card__events-desktop">{eventsLabel(topic.eventsCount)}</span>
            </div>
            <button
              type="button"
              className="topic-card__open-desktop"
              aria-label={`Открыть тему «${topic.title}»`}
              onClick={onOpen}
            >
              Открыть
              <img src={arrowSurface} alt="" width={16} height={16} />
            </button>
          </div>
        </div>

        {topic.image ? (
          <img className="topic-card__image" src={topic.image} alt="" loading="lazy" />
        ) : null}
      </article>
    );
  }

  return (
    <article className={`topic-card topic-card--${topic.tone}`}>
      <div className="topic-card__head">
        <span className="topic-card__status">{topic.impactLabel}</span>
        <h3 className="topic-card__title">{topic.title}</h3>
      </div>

      <div className="topic-card__foot">
        <span className="topic-card__label">Важность</span>
        <div className="topic-card__score-row">
          <span className="topic-card__score">
            <ImportanceScore value={topic.importance} variant="card" />
            <span className="topic-card__of">/100</span>
          </span>
          <button
            type="button"
            className="topic-card__open"
            aria-label={`Открыть тему «${topic.title}»`}
            onClick={onOpen}
          >
            <img src={dark ? arrowInk : arrowSurface} alt="" width={18} height={18} />
          </button>
        </div>
      </div>
    </article>
  );
}
