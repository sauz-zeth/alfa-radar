import { useState } from "react";
import type { FeedItemDetail } from "../api";
import { ImpactTiles } from "./ImpactTiles";
import { SectionHeader } from "./SectionHeader";

type InfluenceTabProps = {
  detail: FeedItemDetail;
};

export function InfluenceTab({ detail }: InfluenceTabProps) {
  const [open, setOpen] = useState(false);
  const [primary, secondary] = detail.impact_metrics;
  const canExplain = detail.score_breakdown.length > 0;
  const alfa = detail.alfa;

  return (
    <>
      <section className="event-section">
        <SectionHeader title="Для компании изменился расчёт" tight />

        <div className="event-recalc__cards">
          {primary ? (
            <article className="event-recalc__card event-recalc__card--dark">
              <p className="event-recalc__label">{primary.label}</p>
              <p className="event-recalc__value">{primary.value}</p>
              <div className="event-recalc__foot">
                <span className="event-recalc__was">
                  {primary.previous_value ? `Было ${primary.previous_value}` : primary.note}
                </span>
                {canExplain ? (
                  <button
                    type="button"
                    className="event-recalc__link"
                    aria-expanded={open}
                    onClick={() => setOpen((value) => !value)}
                  >
                    Как посчитано ↗
                  </button>
                ) : null}
              </div>
            </article>
          ) : null}

          {secondary ? (
            <article className="event-recalc__card">
              <p className="event-recalc__label">{secondary.label}</p>
              <p className="event-recalc__value">{secondary.value}</p>
              <p className="event-recalc__compare">
                {[secondary.previous_value ? `Было ${secondary.previous_value}` : null, secondary.note]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </article>
          ) : null}
        </div>

        {open && canExplain ? (
          <div className="event-calc">
            <p className="event-calc__title">Оценка важности</p>
            {detail.score_breakdown.map((item) => (
              <div key={item.key} className="event-calc__row">
                <span className="event-calc__label">{item.label}</span>
                <span className="event-calc__value">
                  {item.value} / {item.max}
                </span>
              </div>
            ))}
            {detail.score_why ? <p className="event-calc__text">{detail.score_why}</p> : null}
          </div>
        ) : null}

        {detail.what_it_means ? (
          <p className="event-recalc__note">{detail.what_it_means}</p>
        ) : null}
      </section>

      {detail.impact_tiles.length > 0 ? (
        <section className="event-section">
          <ImpactTiles tiles={detail.impact_tiles} />

          {canExplain ? (
            <button
              type="button"
              className="event-calc-pill"
              aria-expanded={open}
              onClick={() => setOpen((value) => !value)}
            >
              Как посчитано ↗
            </button>
          ) : null}
        </section>
      ) : null}

      {alfa ? (
        <section className="event-section">
          <article className="event-alfa">
            <div className="event-alfa__accent" />
            <p className="event-alfa__label">Аналитика Альфа-Банка</p>
            <div className="event-alfa__text">
              {alfa.text
                .split(/\n{2,}/)
                .filter(Boolean)
                .map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
            </div>
            {alfa.author ? <p className="event-alfa__author">{alfa.author}</p> : null}
          </article>
        </section>
      ) : null}
    </>
  );
}
