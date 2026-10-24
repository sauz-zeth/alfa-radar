import { useState } from "react";
import type { FeedItemDetail } from "../api";
import "./event-chat.css";

export type ChatStreamMessage = {
  id: string;
  question: string;
  answer: string;
  status: "pending" | "streaming" | "error";
};

type ChatTabProps = {
  detail: FeedItemDetail;
  streams: ChatStreamMessage[];
  onAsk: (text: string) => void;
};

const QUICK_QUESTION = "Покажи эффект по кварталам";

export function ChatTab({ detail, streams, onAsk }: ChatTabProps) {
  const [draft, setDraft] = useState("");
  const featured =
    detail.open_questions.find((question) => !question.answer)?.text ??
    detail.open_questions[0]?.text ??
    null;
  const primary = detail.sources.find((source) => source.is_primary);
  const sourceUrl = primary?.url ?? detail.source_url ?? null;
  const sourceLabel = primary?.name ?? detail.source_name;

  const submitDraft = () => {
    const value = draft.trim();
    if (!value) return;
    onAsk(value);
    setDraft("");
  };

  return (
    <section className="event-section event-chat">
      <div className="event-chat__compose">
        <h2 className="event-chat__title">
          <span className="event-chat__title-mobile">Разберём подробнее</span>
          <span className="event-chat__title-desktop">Что хотите уточнить?</span>
        </h2>
        <p className="event-chat__lead">
          Спросите про эту историю: уточнить деталь, показать данные в другом разрезе или открыть
          первоисточник.
        </p>

        <form
          className="event-chat__ask"
          onSubmit={(event) => {
            event.preventDefault();
            submitDraft();
          }}
        >
          <input
            className="event-chat__ask-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Спросить про эту историю"
            aria-label="Спросить про эту историю"
          />
          <button
            type="submit"
            className="event-chat__ask-submit"
            disabled={!draft.trim()}
            aria-label="Спросить"
          >
            <svg viewBox="0 0 13.7 13.7" width="18" height="18" aria-hidden="true">
              <path
                d="M6.85 12.85V0.85M12.85 6.85 6.85 0.85 0.85 6.85"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
      </div>

      <div className="event-chat__aside">
        <h3 className="event-chat__aside-title">Можно спросить</h3>

        {featured ? (
          <button
            type="button"
            className="event-chat__question"
            onClick={() => onAsk(featured)}
          >
            <span className="event-chat__question-text">{featured}</span>
            <span className="event-chat__question-cta">
              Спросить <span aria-hidden="true">↗</span>
            </span>
            <span className="event-chat__open" aria-hidden="true">
              ↗
            </span>
          </button>
        ) : null}

        <div className="event-chat__quick">
          <button
            type="button"
            className="event-chat__card"
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
            <span className="event-chat__card-cta">
              Спросить <span aria-hidden="true">↗</span>
            </span>
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
              <span className="event-chat__card-cta">
                {sourceLabel} <span aria-hidden="true">↗</span>
              </span>
            </a>
          ) : null}
        </div>
      </div>

      {detail.chat.length > 0 || streams.length > 0 ? (
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
          {streams.map((message) => (
            <article key={message.id} className="event-chat__message">
              <p className="event-chat__message-question">{message.question}</p>
              {message.status === "error" ? (
                <p className="event-chat__message-pending">
                  Не удалось получить ответ. Попробуйте ещё раз.
                </p>
              ) : message.answer ? (
                <>
                  <p
                    className={
                      message.status === "streaming"
                        ? "event-chat__message-answer is-streaming"
                        : "event-chat__message-answer"
                    }
                  >
                    {message.answer}
                  </p>
                  <p className="event-chat__message-origin">Анализ AI</p>
                </>
              ) : (
                <p className="event-chat__message-skeleton" aria-label="Готовим ответ">
                  <span />
                  <span />
                </p>
              )}
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
