import arrowIcon from "../assets/icons/arrow-up-right.svg";
import { Link } from "../router";
import type { ImpactMetric } from "./types";

type ImpactBlockProps = {
  metrics: ImpactMetric[];
  title?: string;
  action?: { label: string; to: string };
};

export function ImpactBlock({ metrics, title, action }: ImpactBlockProps) {
  return (
    <div className="impact">
      <p className="impact__title">{title ?? "Влияние на компанию"}</p>
      <div className="impact__metrics">
        {metrics.map((metric, index) => (
          <div className="metric" key={index}>
            <p className={metric.tone ? `metric__value metric__value--${metric.tone}` : "metric__value"}>{metric.value}</p>
            <p className="metric__note">{metric.note}</p>
          </div>
        ))}
        {action ? null : (
          <button type="button" className="metric metric--details" aria-label="Подробнее о новости">
            <img src={arrowIcon} alt="" width={14} height={14} />
            <span>Подробнее</span>
          </button>
        )}
      </div>
      {action ? (
        <Link to={action.to} className="impact__action">
          <span>{action.label}</span>
          <img src={arrowIcon} alt="" width={14} height={14} />
        </Link>
      ) : null}
    </div>
  );
}
