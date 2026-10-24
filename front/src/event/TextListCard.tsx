import type { EventTextItem } from "./eventModel";

type TextListCardProps = {
  items: EventTextItem[];
};

export function TextListCard({ items }: TextListCardProps) {
  if (items.length === 0) return null;

  return (
    <div className="event-list">
      {items.map((item, index) => (
        <div key={`${item.label}-${index}`} className="event-list__item">
          <p className="event-list__label">{item.label}</p>
          <p className="event-list__text">{item.text}</p>
          <p className="event-list__meta">{item.meta}</p>
        </div>
      ))}
    </div>
  );
}
