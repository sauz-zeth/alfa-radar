import { useState } from "react";
import type { EventQuestion } from "./eventModel";

type QuestionRowProps = {
  question: EventQuestion;
};

export function QuestionRow({ question }: QuestionRowProps) {
  const answered = Boolean(question.answer);
  const [open, setOpen] = useState(answered);

  return (
    <div className={open ? "event-question is-open" : "event-question"}>
      <button
        type="button"
        className="event-question__head"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="event-question__body">
          <span className="event-question__text">{question.text}</span>
          <span className="event-question__meta">
            {question.status}
            {question.meta ? ` · ${question.meta}` : ""}
          </span>
        </span>
        <span className="event-question__toggle" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>

      {open && question.answer ? (
        <div className="event-question__answer">
          <p className="event-question__answer-text">{question.answer}</p>
          {question.meta ? <p className="event-question__answer-meta">{question.meta}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
