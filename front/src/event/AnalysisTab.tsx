import { useRef } from "react";
import type { FeedItemDetail } from "../api";
import { useMediaQuery } from "../lib/useMediaQuery";
import { pluralRu } from "../lib/plural";
import { longDate, shortDate } from "./eventModel";
import { SectionHeader } from "./SectionHeader";
import "./event-analysis.css";

type AnalysisTabProps = {
  detail: FeedItemDetail;
};

export function AnalysisTab({ detail }: AnalysisTabProps) {
  const firstCorrection = useRef<HTMLDivElement | null>(null);
  const isDesktop = useMediaQuery("(min-width: 1200px)");
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
  const firstAt = steps[0]?.at;
  const lastAt = steps[steps.length - 1]?.at;
  const period = [
    shortDate(detail.published_at),
    firstAt && lastAt ? `${firstAt}–${lastAt}` : firstAt,
  ]
    .filter(Boolean)
    .join(" · ");

  const renderLabel = (step: (typeof steps)[number], index: number) =>
    `${String(index + 1).padStart(2, "0")} ${step.type}${step.at ? ` · ${step.at}` : ""}`;

  return (
    <section className="event-section event-analysis">
      <SectionHeader title="Ход анализа" tight />
      {detail.analysis_pending ? (
        <p className="event-analysis__live" aria-live="polite">
          <span className="event-analysis__spinner" aria-hidden="true" />
          Агент работает — вкладки откроются, когда анализ завершится
        </p>
      ) : null}
      <p className="event-analysis__meta">{meta}</p>

      <div className="event-analysis__layout">
        <aside className="event-analysis__aside">
          <div className="event-analysis__summary">
            <h3 className="event-analysis__summary-title">
              {detail.analysis_finished_at ? "Проверка завершена" : "Проверка идёт"}
            </h3>

            <div className="event-analysis__stat event-analysis__stat--steps">
              <span className="event-analysis__ring" aria-hidden="true" />
              <span className="event-analysis__stat-value">{steps.length}</span>
              <span className="event-analysis__stat-label">шагов проверки</span>
              {period ? <span className="event-analysis__stat-note">{period}</span> : null}
            </div>

            <button
              type="button"
              className="event-analysis__stat event-analysis__stat--fixes"
              disabled={corrections === 0}
              onClick={() =>
                firstCorrection.current?.scrollIntoView({ behavior: "smooth", block: "center" })
              }
            >
              <span className="event-analysis__stat-value">{corrections}</span>
              <span className="event-analysis__stat-label">
                {pluralRu(corrections, ["исправление", "исправления", "исправлений"])}
              </span>
              {detail.analysis_finished_at ? (
                <span className="event-analysis__stat-note">
                  Готово · {detail.analysis_finished_at}
                </span>
              ) : null}
            </button>
          </div>

          {corrections > 0 ? (
            <div className="event-analysis__fixes">
              <h3 className="event-analysis__fixes-title">Что исправили</h3>
              {steps.map((step, index) =>
                step.is_correction ? (
                  <div
                    key={`fix-${step.type}-${index}`}
                    ref={index === firstCorrectionIndex && isDesktop ? firstCorrection : undefined}
                    className="event-analysis__fix"
                  >
                    <p className="event-analysis__label">{renderLabel(step, index)}</p>
                    <p className="event-analysis__text">{step.text}</p>
                  </div>
                ) : null,
              )}
            </div>
          ) : null}
        </aside>

        <div className="event-analysis__main">
          {steps.length > 0 ? (
            <div className="event-analysis__journal">
              {steps.map((step, index) => {
                const correction = step.is_correction ?? false;
                const last = index === steps.length - 1;

                return (
                  <div
                    key={`${step.type}-${index}`}
                    ref={
                      index === firstCorrectionIndex && !isDesktop ? firstCorrection : undefined
                    }
                    className={
                      correction ? "event-analysis__step is-correction" : "event-analysis__step"
                    }
                  >
                    <span className="event-analysis__rail" aria-hidden="true">
                      <span className="event-analysis__dot" />
                      {!last ? <span className="event-analysis__line" /> : null}
                    </span>
                    <div className="event-analysis__body">
                      <p className="event-analysis__label">{renderLabel(step, index)}</p>
                      <p className="event-analysis__text">{step.text}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="event-stub">Пока нет данных по этому разделу</p>
          )}
        </div>
      </div>

      {detail.analysis_finished_at ? (
        <p className="event-analysis__done">Готово · {detail.analysis_finished_at}</p>
      ) : null}
    </section>
  );
}
