import type { FeedItemDetail } from "../api";
import { monthLabel, timelineDate } from "./eventModel";

type EventTimelineProps = {
  publishedAt: string;
  timeline: FeedItemDetail["timeline"];
};

const VISIBLE_POINTS = 5;

export function EventTimeline({ publishedAt, timeline }: EventTimelineProps) {
  const hiddenCount = Math.max(0, timeline.length - VISIBLE_POINTS);
  const points = hiddenCount > 0 ? timeline.slice(-VISIBLE_POINTS) : timeline;
  const currentIndex = Math.max(0, timeline.findIndex((point) => point.is_current));

  if (points.length === 0) {
    return null;
  }

  return (
    <div className="event-timeline">
      <div className="event-timeline__dates">
        {hiddenCount > 0 ? (
          <span className="event-date event-date--more">
            <span className="event-date__day">+{hiddenCount}</span>
            <span className="event-date__month">ещё</span>
          </span>
        ) : null}

        {points.map((point, index) => {
          const { day, month } = timelineDate(point.date);
          const isCurrent = point.is_current || (!timeline.some((item) => item.is_current) && index === points.length - 1);

          return (
            <span
              key={`${point.date}-${index}`}
              className={isCurrent ? "event-date is-current" : "event-date"}
            >
              <span className="event-date__day">{day}</span>
              <span className="event-date__month">{month}</span>
            </span>
          );
        })}
      </div>

      <div className="event-timeline__caption">
        <span>{monthLabel(publishedAt)}</span>
        <span>{`Событие ${currentIndex + 1}/${Math.max(timeline.length, 1)}`}</span>
      </div>

    </div>
  );
}
