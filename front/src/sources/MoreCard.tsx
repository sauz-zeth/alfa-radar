import arrowIcon from "../assets/icons/sources-arrow.svg";
import { channelCountLabel } from "../lib/plural";

type MoreCardProps = {
  count: number;
  onClick: () => void;
};

export function MoreCard({ count, onClick }: MoreCardProps) {
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
