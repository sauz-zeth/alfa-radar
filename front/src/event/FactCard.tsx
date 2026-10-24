import type { EventTextItem } from "./eventModel";

type FactCardProps = EventTextItem & {
  image?: string;
};

export function FactCard({ label, text, meta, image }: FactCardProps) {
  return (
    <div className={image ? "event-fact-row is-with-image" : "event-fact-row"}>
      <article className="event-fact">
        <p className="event-fact__label">{label}</p>
        <p className="event-fact__text">{text}</p>
        <p className="event-fact__meta">{meta}</p>
      </article>
      {image ? <img className="event-fact__image" src={image} alt="" /> : null}
    </div>
  );
}
