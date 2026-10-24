import { useState } from "react";
import arrowUpRight from "../assets/icons/arrow-up-right.svg";
import type { ScoreComponent } from "../api";
import type { EventMetric } from "./eventModel";

type CompanyImpactProps = {
  metrics: EventMetric[];
  note: string;
  scoreBreakdown?: ScoreComponent[];
};

export function CompanyImpact({ metrics, note, scoreBreakdown }: CompanyImpactProps) {
  const [primary, secondary, ...rest] = metrics;
  const [open, setOpen] = useState(false);
  const canExplain = Boolean(scoreBreakdown && scoreBreakdown.length > 0);

  return (
    <div className="event-company">
      {primary ? (
        <article className="event-company__card event-company__card--dark">
          <p className="event-company__label">{primary.label}</p>
          <p className="event-company__value">{primary.value}</p>
          <div className="event-company__foot">
            <span className="event-company__note">
              {primary.previousValue ? `Было ${primary.previousValue}` : primary.note}
            </span>
            {canExplain ? (
              <button
                type="button"
                className="event-company__link"
                aria-expanded={open}
                onClick={() => setOpen((value) => !value)}
              >
                Как посчитано
                <img src={arrowUpRight} alt="" width={12} height={12} />
              </button>
            ) : null}
          </div>

          {open && scoreBreakdown ? (
            <div className="event-company__calc">
              {scoreBreakdown.map((item) => (
                <div key={item.key}>
                  <div className="event-company__calc-row">
                    <span className="event-company__calc-label">{item.label}</span>
                    <span className="event-company__calc-value">
                      {item.value} / {item.max}
                    </span>
                  </div>
                  <p className="event-company__calc-text">{item.text}</p>
                </div>
              ))}
            </div>
          ) : null}
        </article>
      ) : null}

      {secondary ? (
        <article className="event-company__card">
          <p className="event-company__label">{secondary.label}</p>
          <p className="event-company__value">{secondary.value}</p>
          <p className="event-company__note">
            {secondary.previousValue ? `Было ${secondary.previousValue} · ${secondary.note}` : secondary.note}
          </p>
        </article>
      ) : null}

      {rest.map((metric) => (
        <article key={metric.label} className="event-company__card">
          <p className="event-company__label">{metric.label}</p>
          <p className="event-company__value">{metric.value}</p>
          <p className="event-company__note">{metric.note}</p>
        </article>
      ))}

      {note ? <p className="event-company__summary">{note}</p> : null}
    </div>
  );
}
