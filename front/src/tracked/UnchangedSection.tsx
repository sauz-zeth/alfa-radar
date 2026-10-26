import { Link } from "../router";
import archiveArrow from "../assets/icons/tracked/archive-arrow.svg";
import { TopicCard } from "./TopicCard";
import { TopicCardSkeleton } from "./TrackedSkeletons";
import type { Topic } from "./mapTracked";

type UnchangedSectionProps = {
  topics: Topic[];
  onOpen?: (topic: Topic) => void;
  variant?: "mobile" | "desktop";
  emptyNote?: string;
};

export function UnchangedSection({ topics, onOpen, variant = "mobile", emptyNote }: UnchangedSectionProps) {
  if (variant === "desktop") {
    return (
      <section className="tracked-section tracked-section--desktop">
        <div className="tracked-section__head">
          <h2 className="tracked-section__title">Без изменений</h2>
          <span className="tracked-section__count">{topics.length}</span>
        </div>

        <ul className="tracked-desk-list">
          {topics.length > 0
            ? topics.map((topic) => (
                <li key={topic.id}>
                  <TopicCard
                    topic={topic}
                    variant="desktop"
                    compact
                    onOpen={onOpen ? () => onOpen(topic) : undefined}
                  />
                </li>
              ))
            : null}
        </ul>

        {topics.length === 0 ? (
          <div className="tracked-desk-subempty">
            <span className="tracked-desk-subempty__dot" aria-hidden="true" />
            <span>{emptyNote ?? "Пока без изменений"}</span>
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <section className="tracked-section">
      <div className="tracked-section__head">
        <h2 className="tracked-section__title">Без изменений</h2>
        <Link to="/tracked/archive" className="tracked-section__link">
          Архив
          <img src={archiveArrow} alt="" width={16} height={16} />
        </Link>
      </div>

      <ul className="tracked-row">
        {topics.length > 0 ? (
          topics.map((topic) => (
            <li key={topic.id}>
              <TopicCard topic={topic} onOpen={onOpen ? () => onOpen(topic) : undefined} />
            </li>
          ))
        ) : (
          <>
            <li>
              <TopicCardSkeleton />
            </li>
            <li>
              <TopicCardSkeleton />
            </li>
          </>
        )}
      </ul>
    </section>
  );
}
