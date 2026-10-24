import { useRef } from "react";
import type { FeedItemDetail } from "../api";
import { pluralRu } from "../lib/plural";
import { longDate } from "./eventModel";
import { SectionHeader } from "./SectionHeader";

type AnalysisTabProps = {
  detail: FeedItemDetail;
};

export function AnalysisTab({ detail }: AnalysisTabProps) {
  const firstCorrection = useRef<HTMLDivElement | null>(null);
  const steps = detail.agent_log;
  const corrections = steps.filter((step) => step.is_correction ?? false).length;
  const firstCorrectionIndex = steps.findIndex((step) => step.is_correction ?? false);
  const meta = [
    longDate(detail.published_at),
    `${steps.length} ${pluralRu(steps.length, ["шаг", "шага", "шагов"])}`,
    corrections > 0
      ? `${corrections} ${pluralRu(corrections, ["исправление", "исправления", "исправлений"])}`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="event-section event-analysis">
      <SectionHeader title="Ход анализа" tight />
      <p className="event-analysis__meta">{meta}</p>

      <div className="event-analysis__summary">
        <div className="event-analysis__stat event-analysis__stat--steps">
          <span className="event-analysis__ring" aria-hidden="true" />
          <span className="event-analysis__stat-value">{steps.length}</span>
          <span className="event-analysis__stat-label">шагов проверки</span>
        </div>

        <button
          type="button"
          className="event-analysis__stat event-analysis__stat--fixes"
          disabled={corrections === 0}
          onClick={() => firstCorrection.current?.scrollIntoView({ behavior: "smooth", block: "center" })}
        >
          <span className="event-analysis__stat-value">{corrections}</span>
          <span className="event-analysis__stat-label">
            {pluralRu(corrections, ["исправление", "исправления", "исправлений"])}
          </span>
        </button>
      </div>

      {steps.length > 0 ? (
        <div className="event-analysis__journal">
          {steps.map((step, index) => {
            const correction = step.is_correction ?? false;
            const last = index === steps.length - 1;

            return (
              <div
                key={`${step.type}-${index}`}
                ref={index === firstCorrectionIndex ? firstCorrection : undefined}
                className={
                  correction ? "event-analysis__step is-correction" : "event-analysis__step"
                }
              >
                <span className="event-analysis__rail" aria-hidden="true">
                  <span className="event-analysis__dot" />
                  {!last ? <span className="event-analysis__line" /> : null}
                </span>
                <div className="event-analysis__body">
                  <p className="event-analysis__label">
                    {String(index + 1).padStart(2, "0")} {step.type}
                    {step.at ? ` · ${step.at}` : ""}
                  </p>
                  <p className="event-analysis__text">{step.text}</p>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="event-stub">Пока нет данных по этому разделу</p>
      )}

      {detail.analysis_finished_at ? (
        <p className="event-analysis__done">Готово · {detail.analysis_finished_at}</p>
      ) : null}
    </section>
  );
}
