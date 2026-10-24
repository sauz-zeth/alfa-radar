import { useState } from "react";
import { useApi, useApiQuery, type FeedItemDetail, type Horizon, type ScenarioSet } from "../api";
import type { EventModel } from "./eventModel";
import { QuestionsSection } from "./QuestionsSection";
import "./event-scenarios.css";

type ScenariosTabProps = {
  detail: FeedItemDetail;
  event: EventModel;
  onAsk: (text: string) => void;
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

export function ScenariosTab({ detail, event, onAsk, onAskFocus }: ScenariosTabProps) {
  const api = useApi();
  const first = initialHorizon(detail.scenarios.horizon);
  const [horizon, setHorizon] = useState<Horizon>(first);
  const [customQuestion, setCustomQuestion] = useState("");

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

  const confirmed = event.questions.filter((question) => Boolean(question.answer));
  const waiting = event.questions.filter((question) => !question.answer);
  const mainAssumption = set.assumptions[0];

  return (
    <>
      <div className="event-scenarios-mobile">
        <section className="event-section event-scenarios">
          <h2 className="event-scenarios__title">Три варианта</h2>
          <p className="event-scenarios__question">{set.lever_label}</p>

          <HorizonSwitch horizon={horizon} pending={query.isFetching} onChange={setHorizon} />

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
      </div>

      <div className="event-scenarios-desktop">
        <div className="event-scenarios-desktop__main">
          <header className="event-scenarios-desktop__head">
            <div>
              <h2 className="event-scenarios-desktop__title">Три сценария</h2>
              <p className="event-scenarios-desktop__subtitle">
                Эффект на операционную прибыль за {set.horizon_label}
              </p>
            </div>
            <div className="event-scenarios-desktop__horizon">
              <span className="event-scenarios-desktop__horizon-label">Горизонт</span>
              <HorizonSwitch horizon={horizon} pending={query.isFetching} onChange={setHorizon} />
            </div>
          </header>

          {query.isError ? (
            <p className="event-stub">Не удалось обновить сценарии</p>
          ) : base ? (
            <div className="event-scenarios-desktop__cards">
              {set.scenarios.map((scenario) => (
                <article
                  key={scenario.name}
                  className={
                    scenario.is_base
                      ? "event-scenarios-desktop__card is-base"
                      : "event-scenarios-desktop__card"
                  }
                >
                  <p className="event-scenarios-desktop__card-name">{scenario.name}</p>
                  {scenario.share ? (
                    <p className="event-scenarios-desktop__card-share">Допущение: {scenario.share}</p>
                  ) : null}
                  <p className="event-scenarios-desktop__card-value">{scenario.effect_label}</p>
                  <p className="event-scenarios-desktop__card-note">{scenario.note}</p>
                  <div className="event-scenarios-desktop__card-foot">
                    {scenario.origin ? (
                      <span>{labelOrigin(scenario.origin)}</span>
                    ) : null}
                    <span>Вероятность {scenario.probability}%</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="event-stub">Пока нет данных по этому разделу</p>
          )}

          <article className="event-scenarios-desktop__assumption">
            <p className="event-scenarios-desktop__assumption-label">Главное допущение</p>
            <div className="event-scenarios-desktop__assumption-body">
              <p className="event-scenarios-desktop__assumption-text">{set.lever_label}</p>
              <div className="event-scenarios-desktop__assumption-side">
                {set.forecast_note ? (
                  <p className="event-scenarios-desktop__assumption-note">{set.forecast_note}</p>
                ) : mainAssumption ? (
                  <p className="event-scenarios-desktop__assumption-note">
                    {mainAssumption.label}: {mainAssumption.effect}
                  </p>
                ) : set.note ? (
                  <p className="event-scenarios-desktop__assumption-note">{set.note}</p>
                ) : null}
                <p className="event-scenarios-desktop__assumption-source">А · Альфа-Банк</p>
              </div>
            </div>
          </article>
        </div>

        <aside className="event-scenarios-desktop__side">
          <header>
            <h2 className="event-scenarios-desktop__title">Что ждём</h2>
            <p className="event-scenarios-desktop__subtitle">
              События, которые покажут, какой сценарий сбывается
            </p>
          </header>

          <div className="event-scenarios-desktop__questions">
            {confirmed.map((question) => (
              <article
                key={question.id}
                className="event-scenarios-desktop__question is-confirmed"
              >
                <p className="event-scenarios-desktop__question-status">
                  {question.status}
                  {question.meta ? ` · ${question.meta}` : ""}
                </p>
                <p className="event-scenarios-desktop__question-title">
                  {question.answer ?? question.text}
                </p>
                <p className="event-scenarios-desktop__question-text">{question.text}</p>
              </article>
            ))}

            {waiting.length > 0 ? (
              <div className="event-scenarios-desktop__question-grid">
                {waiting.map((question) => (
                  <article key={question.id} className="event-scenarios-desktop__question">
                    <p className="event-scenarios-desktop__question-status">
                      {question.status}
                      {question.meta ? ` · ${question.meta}` : ""}
                    </p>
                    <p className="event-scenarios-desktop__question-title">{question.text}</p>
                  </article>
                ))}
              </div>
            ) : null}
          </div>

          <form
            className="event-scenarios-desktop__ask"
            onSubmit={(formEvent) => {
              formEvent.preventDefault();
              if (!customQuestion.trim()) return;
              onAsk(customQuestion.trim());
              setCustomQuestion("");
            }}
          >
            <input
              className="event-scenarios-desktop__ask-input"
              value={customQuestion}
              onChange={(inputEvent) => setCustomQuestion(inputEvent.target.value)}
              placeholder="Свой вопрос: что отследить?"
              aria-label="Свой вопрос: что отследить?"
            />
            <button
              type="submit"
              className="event-scenarios-desktop__ask-submit"
              disabled={!customQuestion.trim()}
            >
              Добавить
            </button>
          </form>
        </aside>
      </div>
    </>
  );
}

function HorizonSwitch({
  horizon,
  pending,
  onChange,
}: {
  horizon: Horizon;
  pending: boolean;
  onChange: (value: Horizon) => void;
}) {
  return (
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
          disabled={pending}
          onClick={() => onChange(item.value)}
        >
          {item.label}
        </button>
      ))}
    </div>
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
