import { useState } from "react";

const REASONS = ["Ошибка в факте", "Оценка неточна", "Не касается нас"];

type FeedbackSectionProps = {
  initialReason?: string | null;
  onFeedback?: (reason: string) => Promise<void>;
  pending?: boolean;
  error?: string | null;
};

export function FeedbackSection({ initialReason, onFeedback, pending, error }: FeedbackSectionProps) {
  const [selected, setSelected] = useState<string | null>(initialReason ?? null);

  const choose = (reason: string) => {
    if (pending) return;
    setSelected(reason);
    const result = onFeedback?.(reason);
    if (result) void result.catch(() => setSelected(null));
  };

  return (
    <section className="event-section event-feedback">
      <p className="event-feedback__question">Что-то не так с разбором?</p>
      <div className="event-feedback__reasons">
        {REASONS.map((reason) => (
          <button
            key={reason}
            type="button"
            className={selected === reason ? "event-feedback__chip is-selected" : "event-feedback__chip"}
            aria-pressed={selected === reason}
            disabled={pending}
            onClick={() => choose(reason)}
          >
            {reason}
          </button>
        ))}
      </div>
      {error ? <p className="event-feedback__error">{error}</p> : null}
    </section>
  );
}
