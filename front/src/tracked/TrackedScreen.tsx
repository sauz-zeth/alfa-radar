import { useMemo, useState } from "react";
import { ApiError, useApi, useApiQuery } from "../api";
import { useRouter } from "../router";
import { TopicCarousel } from "./TopicCarousel";
import { TrackedHeader } from "./TrackedHeader";
import { UnchangedSection } from "./UnchangedSection";
import { toTopic } from "./mapTracked";
import { TopicCircleSkeleton } from "./TrackedSkeletons";
import "./tracked.css";

export default function TrackedScreen() {
  const api = useApi();
  const { navigate } = useRouter();
  const [index, setIndex] = useState(0);

  const tracked = useApiQuery({
    queryKey: ["tracked", "all"],
    queryFn: (signal) => api.tracked.list({ status: "all" }, { signal }),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const topics = useMemo(
    () =>
      (tracked.data?.items ?? [])
        .filter((item) => item.status === "active")
        .map(toTopic)
        .sort((a, b) => Number(b.changed) - Number(a.changed)),
    [tracked.data],
  );

  const archived = useMemo(
    () =>
      (tracked.data?.items ?? [])
        .filter((item) => item.status !== "active")
        .map(toTopic),
    [tracked.data],
  );

  const updatesCount = topics.filter((topic) => topic.changed).length;
  const selected = Math.min(index, Math.max(0, topics.length - 1));

  if (tracked.isPending) {
    return (
      <div className="tracked-page tracked-state">
        <p>Загружаем темы…</p>
      </div>
    );
  }

  if (tracked.isError || !tracked.data) {
    return (
      <div className="tracked-page tracked-state">
        <p>
          {tracked.error instanceof ApiError
            ? tracked.error.detail
            : "Не удалось загрузить отслеживаемое"}
        </p>
        <button type="button" className="tracked-state__retry" onClick={() => tracked.refetch()}>
          Повторить
        </button>
      </div>
    );
  }

  return (
    <div className="tracked-page">
      <div className="tracked-hero">
        <TrackedHeader themeCount={topics.length} updatesCount={updatesCount} />

        {topics.length > 0 ? (
          <TopicCarousel
            topics={topics}
            index={selected}
            onSelect={setIndex}
            onOpen={(topic) => navigate(`/event/${topic.eventId}`)}
          />
        ) : (
          <div className="tracked-empty">
            <TopicCircleSkeleton />
          </div>
        )}
      </div>

      <UnchangedSection topics={archived} onOpen={(topic) => navigate(`/event/${topic.eventId}`)} />
    </div>
  );
}
