import { SectionHeader } from "./SectionHeader";
import { QuestionRow } from "./QuestionRow";
import type { EventQuestion } from "./eventModel";

type QuestionsSectionProps = {
  questions: EventQuestion[];
  answeredCount: number;
  waitingCount: number;
  onAsk: () => void;
};

export function QuestionsSection({ questions, answeredCount, waitingCount, onAsk }: QuestionsSectionProps) {
  const counter = `${answeredCount} ответ · ${waitingCount} ждём`;

  return (
    <section className="event-section">
      {questions.length > 0 ? (
        <>
          <SectionHeader title="Вопросы к истории" aside={counter} />
          <div className="event-questions">
            {questions.map((question) => (
              <QuestionRow key={question.id} question={question} />
            ))}
          </div>
        </>
      ) : null}

      <button type="button" className="event-questions__add" onClick={onAsk}>
        + Свой вопрос к истории
      </button>
    </section>
  );
}
