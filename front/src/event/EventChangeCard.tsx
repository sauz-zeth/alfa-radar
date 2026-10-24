import { shortDate, type EventModel } from "./eventModel";

type EventChangeCardProps = {
  event: EventModel;
};

export function EventChangeCard({ event }: EventChangeCardProps) {
  const label =
    event.conclusionsChanged && event.changedAt
      ? `С ${shortDate(event.changedAt)} · выводы изменились`
      : `С ${shortDate(event.publishedAt)} · без изменений`;

  return (
    <article className="event-change">
      <p className="event-change__label">{label}</p>
      <p className="event-change__text">{event.fact.text}</p>
    </article>
  );
}
