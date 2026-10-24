import { useMemo, useState } from "react";
import { useApi, useApiMutation, useQueryClient } from "../api";
import { Link } from "../router";
import arrowInk from "../assets/icons/tracked/arrow-ink.svg";
import { TopicCard } from "./TopicCard";
import { TopicCardSkeleton } from "./TrackedSkeletons";
import { UnchangedSection } from "./UnchangedSection";
import { eventsLabel, storiesLabel, type Topic } from "./mapTracked";

type TrackedDesktopProps = {
  topics: Topic[];
  archived: Topic[];
  onOpen: (topic: Topic) => void;
};

function matches(topic: Topic, query: string): boolean {
  if (!query) return true;
  return [topic.title, topic.conclusion, topic.conclusionQuestion ?? "", topic.impactLabel]
    .join(" ")
    .toLowerCase()
    .includes(query);
}

export function TrackedDesktop({ topics, archived, onOpen }: TrackedDesktopProps) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  const resume = useApiMutation<unknown, string>({
    mutationFn: (itemId) => api.tracked.resume(itemId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tracked"] });
    },
  });

  const query = search.trim().toLowerCase();
  const filteredTopics = useMemo(() => topics.filter((topic) => matches(topic, query)), [topics, query]);
  const filteredArchived = useMemo(
    () => archived.filter((topic) => matches(topic, query)),
    [archived, query],
  );

  const changed = filteredTopics.filter((topic) => topic.changed);
  const unchanged = filteredTopics.filter((topic) => !topic.changed);

  return (
    <div className="tracked-desktop">
      <header className="tracked-desk-head">
        <div>
          <h1>Отслеживаемое</h1>
          <p>{storiesLabel(topics.length)}</p>
        </div>
        <label className="tracked-desk-search">
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Поиск по историям"
            aria-label="Поиск по историям"
          />
          <span>Ctrl K</span>
        </label>
      </header>

      <div className="tracked-desk-grid">
        <section className="tracked-desk-col">
          <div className="tracked-desk-section-head">
            <h2>Есть новое</h2>
            <span>{changed.length}</span>
          </div>

          <ul className="tracked-desk-list">
            {changed.map((topic) => (
              <li key={topic.id}>
                <TopicCard topic={topic} variant="desktop" onOpen={() => onOpen(topic)} />
              </li>
            ))}
          </ul>

          {changed.length === 0 && topics.length === 0 ? (
            <TopicCardSkeleton />
          ) : changed.length === 0 ? (
            <p className="tracked-desk-note">{query ? "Ничего не найдено" : "Новых изменений нет"}</p>
          ) : null}
        </section>

        <aside className="tracked-desk-col">
          <UnchangedSection
            variant="desktop"
            topics={unchanged}
            onOpen={onOpen}
            emptyNote={query ? "Ничего не найдено" : "Пока без изменений"}
          />

          <section className="tracked-archive-panel">
            <header className="tracked-archive-panel__head">
              <Link to="/tracked/archive" className="tracked-archive-panel__title">
                Архив
              </Link>
              <span>{filteredArchived.length}</span>
            </header>

            <ul className="tracked-archive-panel__list">
              {filteredArchived.map((topic) => (
                <li key={topic.id} className="tracked-archive-panel__row">
                  <div className="tracked-archive-panel__body">
                    <h3>{topic.title}</h3>
                    <p>
                      {topic.dateLong} · {eventsLabel(topic.eventsCount)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="tracked-archive-panel__resume"
                    onClick={() => resume.mutate(topic.id)}
                    disabled={resume.isPending}
                  >
                    Возобновить
                    <img src={arrowInk} alt="" width={14} height={14} />
                  </button>
                </li>
              ))}
            </ul>

            {filteredArchived.length === 0 ? (
              <p className="tracked-desk-note">{query ? "Ничего не найдено" : "В архиве пусто"}</p>
            ) : null}
          </section>
        </aside>
      </div>
    </div>
  );
}
