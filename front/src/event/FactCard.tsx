import type { EventTextItem } from "./eventModel";

type FactCardProps = EventTextItem;

export function FactCard({ label, text, meta }: FactCardProps) {
  return (
    <article className="event-fact">
      <p className="event-fact__label">{label}</p>
      <p className="event-fact__text">{text}</p>
      <p className="event-fact__meta">{meta}</p>
    </article>
  );
}
