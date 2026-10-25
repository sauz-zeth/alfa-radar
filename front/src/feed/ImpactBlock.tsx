import arrowIcon from "../assets/icons/arrow-up-right.svg";
import type { ImpactMetric } from "./types";

type ImpactBlockProps = {
  metrics: ImpactMetric[];
};

export function ImpactBlock({ metrics }: ImpactBlockProps) {
  return (
    <div className="impact">
      <p className="impact__title">Влияние на компанию</p>
      <div className="impact__metrics">
        {metrics.map((metric, index) => (
          <div className="metric" key={index}>
            <p className={metric.tone ? `metric__value metric__value--${metric.tone}` : "metric__value"}>{metric.value}</p>
            <p className="metric__note">{metric.note}</p>
          </div>
        ))}
        <button type="button" className="metric metric--details" aria-label="Подробнее о новости">
          <img src={arrowIcon} alt="" width={14} height={14} />
          <span>Подробнее</span>
        </button>
      </div>
    </div>
  );
}
