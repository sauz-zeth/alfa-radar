import { useMemo, useState } from "react";
import { ApiError, useApi, useApiQuery } from "../api";
import { useMediaQuery } from "../lib/useMediaQuery";
import { useRouter } from "../router";
import { TopicCarousel } from "./TopicCarousel";
import { TrackedHeader } from "./TrackedHeader";
import { TrackedDesktop } from "./TrackedDesktop";
import { UnchangedSection } from "./UnchangedSection";
import { toTopic } from "./mapTracked";
import "./tracked.css";

export default function TrackedScreen() {
  const api = useApi();
  const { navigate } = useRouter();
  const isDesktop = useMediaQuery("(min-width: 1200px)");
  const [index, setIndex] = useState(0);

  const tracked = useApiQuery({
    queryKey: ["tracked", "all"],
    queryFn: (signal) => api.tracked.list({ status: "all" }, { signal }),
    staleTime: 0,
    refetchOnMount: "always",
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => item.analysis_pending) ? 2500 : false,
  });

  const topics = useMemo(
    () =>
      (tracked.data?.items ?? [])
        .filter((item) => item.status === "active")
        .map(toTopic)
        .sort(
          (a, b) =>
            Number(b.processing) - Number(a.processing) || Number(b.changed) - Number(a.changed),
        ),
    [tracked.data],
  );

  const archived = useMemo(
    () =>
      (tracked.data?.items ?? [])
        .filter((item) => item.status !== "active")
        .map(toTopic),
    [tracked.data],
  );

  const updatesCount = topics.filter((topic) => topic.changed || topic.processing).length;
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

  if (topics.length === 0 && archived.length === 0) {
    return (
      <div className="tracked-page tracked-page--empty">
        <div className="tracked-empty-screen">
          <h1>Отслеживаемое</h1>
          <p>Сначала добавьте новости в ленте, чтобы следить за темами здесь.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="tracked-page">
      {isDesktop ? (
        <TrackedDesktop
          topics={topics}
          archived={archived}
          onOpen={(topic) => navigate(`/event/${topic.eventId}`)}
        />
      ) : (
        <>
          <div className="tracked-hero">
            <TrackedHeader themeCount={topics.length} updatesCount={updatesCount} />

            {topics.length > 0 ? (
              <>
                {updatesCount === 0 ? (
                  <p className="tracked-calm">
                    Новых изменений нет — агент продолжает следить за темами
                  </p>
                ) : null}
                <TopicCarousel
                  topics={topics}
                  index={selected}
                  onSelect={setIndex}
                  onOpen={(topic) => navigate(`/event/${topic.eventId}`)}
                />
              </>
            ) : (
              <div className="tracked-empty tracked-empty--note">
                <p className="tracked-empty__title">Пока ничего не отслеживается</p>
                <p className="tracked-empty__text">
                  Добавьте новость из ленты — агент начнёт следить за темой и покажет здесь
                  изменения.
                </p>
              </div>
            )}
          </div>

          <UnchangedSection
            topics={archived}
            onOpen={(topic) => navigate(`/event/${topic.eventId}`)}
          />
        </>
      )}
    </div>
  );
}
