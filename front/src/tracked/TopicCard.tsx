import arrowInk from "../assets/icons/tracked/arrow-ink.svg";
import arrowSurface from "../assets/icons/tracked/arrow-surface.svg";
import { ImportanceScore } from "./ImportanceScore";
import type { Topic } from "./mapTracked";

type TopicCardProps = {
  topic: Topic;
  onOpen?: () => void;
};

export function TopicCard({ topic, onOpen }: TopicCardProps) {
  const dark = topic.tone === "dark";

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
