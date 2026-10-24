import type { SourcePost } from "../api";
import { channelInitials } from "../sources/channelVisuals";
import arrowUpRight from "../assets/icons/sources-arrow.svg";

type SourceCardProps = {
  source: SourcePost;
};

export function SourceCard({ source }: SourceCardProps) {
  return (
    <article className="event-source">
      <div className="event-source__head">
        <span className="event-source__avatar">{channelInitials(source.name)}</span>
        <div className="event-source__who">
          <span className="event-source__name">{source.name}</span>
          <span className="event-source__time">
            {new Date(source.time).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
      </div>

      <p className="event-source__text">{source.text}</p>

      <div className="event-source__foot">
        <span className="event-source__status">{source.status_label}</span>
        {source.url ? (
          <a
            className="event-source__link"
            href={source.url}
            target="_blank"
            rel="noreferrer"
          >
            Оригинал поста
            <img src={arrowUpRight} alt="" width={12} height={12} />
          </a>
        ) : null}
      </div>
    </article>
  );
}
