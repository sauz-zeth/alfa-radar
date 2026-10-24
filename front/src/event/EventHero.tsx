import { longDate, sourcesLabel, type EventModel } from "./eventModel";

type EventHeroProps = {
  event: EventModel;
};

export function EventHero({ event }: EventHeroProps) {
  const mainMetric = event.metrics[0];

  return (
    <article className="event-hero">
      <p className="event-hero__meta">
        {event.sourceName} · {longDate(event.publishedAt)} · {sourcesLabel(event.sourcesCount)}
      </p>
      <h1 className="event-hero__title">{event.title}</h1>

      <div className="event-hero__params">
        <div className="event-hero__param">
          <span className="event-hero__label">{mainMetric?.label ?? "Влияние"} ↗</span>
          <span className="event-hero__value">{mainMetric?.value ?? "—"}</span>
        </div>
        <div className="event-hero__param">
          <span className="event-hero__label">Важность · {event.impactShort}</span>
          <span className="event-hero__value">
            {event.importance} <span className="event-hero__of">/ 100</span>
          </span>
        </div>
      </div>
    </article>
  );
}
