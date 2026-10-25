import arrowWhite from "../assets/icons/tracked/arrow-white.svg";
import { ImportanceRing } from "./ImportanceRing";
import { ImportanceScore } from "./ImportanceScore";
import { eventsLabel, type Topic } from "./mapTracked";

type TopicCircleProps = {
  topic: Topic;
  side?: "prev" | "next";
  onSelect?: () => void;
  onOpen?: () => void;
};

export function TopicCircle({ topic, side, onSelect, onOpen }: TopicCircleProps) {
  const openMark = <img src={arrowWhite} alt="" width={11} height={11} />;

  const body = (
    <>
      <ImportanceRing value={topic.importance} />
      <span className="topic-circle__content">
        <span className="topic-circle__score-block">
          <span className="topic-circle__score-label">Важность</span>
          <ImportanceScore value={topic.importance} variant="circle" />
        </span>

        <span className="topic-circle__title-block">
          <span className="topic-circle__meta">
            <span>
              {topic.impactLabel} · {topic.date}
            </span>
            {topic.processing ? (
              <>
                <span className="topic-circle__spinner" aria-hidden="true" />
                <span className="topic-circle__processing">Агент обрабатывает</span>
              </>
            ) : null}
            {topic.changed && !topic.processing ? (
              <>
                <span className="topic-circle__marker" />
                <span>Есть изменения</span>
              </>
            ) : null}
          </span>
          <span className="topic-circle__title">{topic.title}</span>
        </span>

        <span className="topic-circle__footer">
          <span className="topic-circle__events">{eventsLabel(topic.eventsCount)}</span>
          {onOpen ? (
            <button
              type="button"
              className="topic-circle__open"
              aria-label={`Открыть тему «${topic.title}»`}
              onClick={onOpen}
            >
              {openMark}
            </button>
          ) : (
            <span className="topic-circle__open" aria-hidden="true">
              {openMark}
            </span>
          )}
        </span>
      </span>
    </>
  );

  if (side) {
    return (
      <button
        type="button"
        className={`topic-circle topic-circle--side topic-circle--${side}`}
        aria-label={`Показать тему «${topic.title}»`}
        onClick={onSelect}
      >
        {body}
      </button>
    );
  }

  return (
    <article className="topic-circle topic-circle--active" aria-roledescription="слайд">
      {body}
    </article>
  );
}
