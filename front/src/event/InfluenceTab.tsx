import { Fragment, useState } from "react";
import { useApi, useApiQuery, type FeedItemDetail } from "../api";
import { SectionHeader } from "./SectionHeader";
import "./event-influence.css";

type InfluenceTabProps = {
  detail: FeedItemDetail;
};

export function InfluenceTab({ detail }: InfluenceTabProps) {
  const api = useApi();
  const [open, setOpen] = useState(false);
  const profile = useApiQuery({
    queryKey: ["profile"],
    queryFn: (signal) => api.profile.get({ signal }),
  });
  const metrics = detail.impact_metrics.slice(0, 3);
  const primary = metrics.find((item) => item.tone === "negative") ?? metrics[0];
  const ordered = primary
    ? [primary, ...metrics.filter((item) => item !== primary)]
    : metrics;
  const secondary = ordered[1];
  const contracts = metrics.find(
    (item) =>
      item.key === "export" ||
      /контракт/i.test(item.label ?? "") ||
      /контракт/i.test(item.note ?? ""),
  );
  const canExplain = detail.score_breakdown.length > 0;
  const alfa = detail.alfa;

  const factorMetric = metrics.find((item) => item.key === "rate") ?? metrics[2];
  const factor = factorMetric ? `${factorMetric.value} ${factorMetric.label}`.trim() : null;
  const consequence = primary
    ? `${primary.value} ${primary.label}`.trim()
    : detail.impact_tiles[0]?.value ?? detail.what_it_means;
  const profileData = profile.data;
  const exportShare = metrics
    .map((item) => item.note?.match(/(?:доле экспорта|доля экспорта)[^\d]*(\d+(?:[.,]\d+)?%)/i)?.[1])
    .find(Boolean);
  const positions = (
    profileData?.reporting as { currency_positions?: unknown } | undefined
  )?.currency_positions;
  const profileFacts = profileData
    ? [
        { value: profileData.stats.revenue_label, label: "Выручка за год" },
        { value: exportShare ?? "—", label: "Доля экспорта" },
        {
          value: contracts?.value ?? "—",
          label: "Контракты IV кв. с отгрузкой после 1 ноября",
        },
        {
          value: Array.isArray(positions) && positions.length > 0 ? "да" : "нет",
          label: "Валютное хеджирование",
        },
      ]
    : [];

  const chain = [
    { label: "Событие", value: detail.title, note: "" },
    { label: "Фактор", value: factor ?? detail.theses[0]?.text ?? detail.summary, note: "" },
    { label: "Последствие", value: consequence, note: primary ? "Вывод AI" : "" },
  ];

  const calcPanel = (extra?: string) =>
    open && canExplain ? (
      <div className={extra ? `event-calc ${extra}` : "event-calc"}>
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
    ) : null;

  return (
    <div className="event-influence">
      <div className="event-influence__main">
        <section className="event-section event-influence__recalc">
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

          {calcPanel()}

        </section>

        {metrics.length > 0 ? (
          <section className="event-section event-influence__numbers">
            <h2 className="event-influence__heading">Цифры для компании</h2>
            <div
              className={
                ordered.length === 2
                  ? "event-influence__metrics event-influence__metrics--two"
                  : "event-influence__metrics"
              }
            >
              {ordered.map((metric, index) => {
                const label = metric.label ?? "";
                const note = metric.note ?? "";
                const text =
                  label && note.toLowerCase().includes(label.toLowerCase()) ? note : label || note;
                return (
                  <article
                    key={metric.key ?? index}
                    className={
                      index === 0
                        ? "event-influence__metric event-influence__metric--accent"
                        : "event-influence__metric"
                    }
                  >
                    <p className="event-influence__metric-value">{metric.value}</p>
                    <p className="event-influence__metric-label">{text}</p>
                    {canExplain ? (
                      <button
                        type="button"
                        className="event-influence__metric-calc"
                        aria-expanded={open}
                        onClick={() => setOpen((value) => !value)}
                      >
                        Как посчитано ↗
                      </button>
                    ) : null}
                  </article>
                );
              })}
            </div>

            {calcPanel("event-influence__calc")}
          </section>
        ) : null}

        <section className="event-section event-influence__chain">
          <h2 className="event-influence__card-title">Как возникает эффект</h2>
          <div className="event-influence__steps">
            {chain.map((step, index) => (
              <Fragment key={step.label}>
                {index > 0 ? (
                  <span className="event-influence__arrow" aria-hidden="true">
                    →
                  </span>
                ) : null}
                <div className="event-influence__step">
                  <p className="event-influence__step-label">{step.label}</p>
                  <p className="event-influence__step-value">{step.value}</p>
                  {step.note ? <p className="event-influence__step-note">{step.note}</p> : null}
                </div>
              </Fragment>
            ))}
          </div>
        </section>

        {profileFacts.length > 0 || detail.score_breakdown.length > 0 ? (
          <section className="event-section event-influence__profile">
            <h2 className="event-influence__card-title">Почему это важно для вас</h2>
            <p className="event-influence__profile-note">
              Данные профиля, которые повлияли на вывод
            </p>
            <div className="event-influence__profile-grid">
              {profileFacts.length > 0
                ? profileFacts.map((item) => (
                    <div key={item.label} className="event-influence__profile-item">
                      <p className="event-influence__profile-value">{item.value}</p>
                      <p className="event-influence__profile-label">{item.label}</p>
                    </div>
                  ))
                : detail.score_breakdown.map((item) => (
                    <div key={item.key} className="event-influence__profile-item">
                      <p className="event-influence__profile-value">
                        {item.value} / {item.max}
                      </p>
                      <p className="event-influence__profile-label">{item.label}</p>
                    </div>
                  ))}
            </div>
          </section>
        ) : null}
      </div>

      <div className="event-influence__aside">
        {detail.theses.length > 0 ? (
          <section className="event-section event-influence__risks">
            <h2 className="event-influence__heading">Риски и возможности</h2>
            <div className="event-influence__risk-list">
              {detail.theses.map((thesis, index) => (
                <article key={`${thesis.text}-${index}`} className="event-influence__risk">
                  <p className="event-influence__risk-text">{thesis.text}</p>
                  <p className="event-influence__risk-meta">
                    {[thesis.sources.join(" · "), thesis.status].filter(Boolean).join(" · ")}
                  </p>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {alfa ? (
          <section className="event-section event-influence__alfa">
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
      </div>
    </div>
  );
}
