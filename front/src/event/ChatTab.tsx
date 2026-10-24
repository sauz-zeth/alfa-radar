import type { FeedItemDetail } from "../api";

type ChatTabProps = {
  detail: FeedItemDetail;
  askPending: boolean;
  onAsk: (text: string) => void;
};

const QUICK_QUESTION = "Покажи эффект по кварталам";

export function ChatTab({ detail, askPending, onAsk }: ChatTabProps) {
  const featured =
    detail.open_questions.find((question) => !question.answer)?.text ??
    detail.open_questions[0]?.text ??
    null;
  const primary = detail.sources.find((source) => source.is_primary);
  const sourceUrl = primary?.url ?? detail.source_url ?? null;

  return (
    <section className="event-section event-chat">
      <h2 className="event-chat__title">Разберём подробнее</h2>
      <p className="event-chat__lead">
        Спросите про эту историю: уточнить деталь, показать данные в другом разрезе или открыть
        первоисточник.
      </p>

      {featured ? (
        <button
          type="button"
          className="event-chat__question"
          disabled={askPending}
          onClick={() => onAsk(featured)}
        >
          <span className="event-chat__question-text">{featured}</span>
          <span className="event-chat__open" aria-hidden="true">
            ↗
          </span>
        </button>
      ) : null}

      <div className="event-chat__quick">
        <button
          type="button"
          className="event-chat__card"
          disabled={askPending}
          onClick={() => onAsk(QUICK_QUESTION)}
        >
          <svg viewBox="0 0 30 30" width="30" height="30" aria-hidden="true">
            <path
              d="M2 4V22H24M7 17L12 12L17 15L24 6"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="event-chat__card-text">{QUICK_QUESTION}</span>
        </button>

        {sourceUrl ? (
          <a
            className="event-chat__card event-chat__card--source"
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
          >
            <svg viewBox="0 0 30 30" width="30" height="30" aria-hidden="true">
              <path
                d="M25 9V8L20 3H7V27H25V9ZM20 3V9H25M12 15H20M12 20H20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span className="event-chat__card-text">Открой первоисточник</span>
          </a>
        ) : null}
      </div>

      {detail.chat.length > 0 ? (
        <div className="event-chat__thread">
          {detail.chat.map((message, index) => (
            <article key={`${message.question}-${index}`} className="event-chat__message">
              <p className="event-chat__message-question">{message.question}</p>
              {message.answer ? (
                <>
                  <p className="event-chat__message-answer">{message.answer}</p>
                  <p className="event-chat__message-origin">{message.origin}</p>
                </>
              ) : (
                <p className="event-chat__message-pending">
                  Ответ не получен. Попробуйте спросить ещё раз.
                </p>
              )}
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
