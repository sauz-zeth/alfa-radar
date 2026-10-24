import { useState } from "react";
import { useApi, useApiQuery, type FeedItemDetail, type Horizon, type ScenarioSet } from "../api";
import type { EventModel } from "./eventModel";
import { QuestionsSection } from "./QuestionsSection";

type ScenariosTabProps = {
  detail: FeedItemDetail;
  event: EventModel;
  onAskFocus: () => void;
};

const HORIZONS: Array<{ value: Horizon; label: string }> = [
  { value: "3m", label: "3 мес" },
  { value: "6m", label: "6 мес" },
  { value: "12m", label: "12 мес" },
];

function initialHorizon(value: string): Horizon {
  return HORIZONS.some((item) => item.value === value) ? (value as Horizon) : "12m";
}

function labelOrigin(origin: string): string {
  return origin.toLowerCase() === "ai" ? "Вывод AI" : origin;
}

export function ScenariosTab({ detail, event, onAskFocus }: ScenariosTabProps) {
  const api = useApi();
  const first = initialHorizon(detail.scenarios.horizon);
  const [horizon, setHorizon] = useState<Horizon>(first);

  const query = useApiQuery<ScenarioSet>({
    queryKey: ["event", detail.id, "scenarios", horizon],
    queryFn: (signal) => api.feed.scenarios(detail.id, { horizon }, { signal }),
    enabled: horizon !== first,
    staleTime: 5 * 60 * 1000,
  });

  const set = query.data ?? detail.scenarios;
  const foundBase = set.scenarios.findIndex((scenario) => scenario.is_base);
  const baseIndex = foundBase >= 0 ? foundBase : 0;
  const base = set.scenarios[baseIndex];
  const others = set.scenarios.filter((_, index) => index !== baseIndex);
  const shareValue = Number.parseInt(base?.share ?? "0", 10);

  return (
    <>
      <section className="event-section event-scenarios">
        <h2 className="event-scenarios__title">Три варианта</h2>
        <p className="event-scenarios__question">{set.lever_label}</p>

        <div className="event-horizon" role="group" aria-label="Горизонт сценариев">
          {HORIZONS.map((item) => (
            <button
              key={item.value}
              type="button"
              className={
                item.value === horizon
                  ? "event-horizon__option is-active"
                  : "event-horizon__option"
              }
              aria-pressed={item.value === horizon}
              disabled={query.isFetching}
              onClick={() => setHorizon(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {query.isError ? (
          <p className="event-stub">Не удалось обновить сценарии</p>
        ) : base ? (
          <div className="event-scenario-strip">
            <article className="event-scenario">
              <p className="event-scenario__label">
                {base.name}
                {base.share ? ` · в цену ${base.share}` : ""}
              </p>
              <p className="event-scenario__value">{base.effect_label}</p>
              <div className="event-scenario__row">
                <ScenarioDonut value={shareValue} />
                <p className="event-scenario__note">{base.note}</p>
              </div>
              {base.origin ? (
                <p className="event-scenario__source">{labelOrigin(base.origin)}</p>
              ) : null}
            </article>

            {others.length > 0 ? (
              <div className="event-scenario-pair">
                {others.map((scenario) => (
                  <article key={scenario.name} className="event-scenario event-scenario--compact">
                    <p className="event-scenario__label">
                      {scenario.name}
                      {scenario.share ? ` · в цену ${scenario.share}` : ""}
                    </p>
                    <p className="event-scenario__value">{scenario.effect_label}</p>
                    <p className="event-scenario__note">{scenario.note}</p>
                    {scenario.origin ? (
                      <p className="event-scenario__source">{labelOrigin(scenario.origin)}</p>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          <p className="event-stub">Пока нет данных по этому разделу</p>
        )}

        {set.forecast_note ? (
          <p className="event-scenarios__forecast">{set.forecast_note}</p>
        ) : null}
      </section>

      <QuestionsSection
        questions={event.questions}
        answeredCount={event.answeredCount}
        waitingCount={event.waitingCount}
        onAsk={onAskFocus}
      />
    </>
  );
}

function ScenarioDonut({ value }: { value: number }) {
  const percent = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const radius = 30.88;
  const circumference = 2 * Math.PI * radius;
  const filled = (percent / 100) * circumference;

  return (
    <svg className="event-scenario__donut" viewBox="0 0 64 64" aria-hidden="true">
      <circle
        cx="32"
        cy="32"
        r={radius}
        fill="none"
        stroke="#f7f7f7"
        strokeOpacity="0.16"
        strokeWidth="2.24"
      />
      <circle
        cx="32"
        cy="32"
        r={radius}
        fill="none"
        stroke="#ef3124"
        strokeWidth="2.24"
        strokeDasharray={`${filled} ${circumference}`}
      />
      <text
        x="32"
        y="32"
        fill="#f7f7f7"
        fontSize="12"
        textAnchor="middle"
        dominantBaseline="central"
      >
        {percent}%
      </text>
    </svg>
  );
}
