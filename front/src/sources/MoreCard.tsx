import arrowIcon from "../assets/icons/sources-arrow.svg";
import { channelCountLabel } from "../lib/plural";

type MoreCardProps = {
  count: number;
  onClick: () => void;
  variant?: "mobile" | "desktop";
};

export function MoreCard({ count, onClick, variant = "mobile" }: MoreCardProps) {
  if (variant === "desktop") {
    return (
      <button type="button" className="more-card more-card--desktop" onClick={onClick}>
        <img className="more-card__arrow" src={arrowIcon} alt="" width={24} height={24} />
        <span className="more-card__text">Ещё {channelCountLabel(count)}</span>
        <span className="more-card__cta">Посмотреть ещё</span>
      </button>
    );
  }

  return (
    <button type="button" className="more-card" onClick={onClick}>
      <img className="more-card__arrow" src={arrowIcon} alt="" width={14} height={14} />
      <span className="more-card__text">
        Посмотреть ещё
        <br />
        {channelCountLabel(count)}
      </span>
    </button>
  );
}
