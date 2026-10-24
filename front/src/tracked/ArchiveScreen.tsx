import { useMemo } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery, useQueryClient } from "../api";
import { Link } from "../router";
import { eventsLabel, toTopic } from "./mapTracked";
import "./tracked.css";

export default function ArchiveScreen() {
  const api = useApi();
  const queryClient = useQueryClient();

  const tracked = useApiQuery({
    queryKey: ["tracked", "archived"],
    queryFn: (signal) => api.tracked.list({ status: "archived" }, { signal }),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const resume = useApiMutation<unknown, string>({
    mutationFn: (itemId) => api.tracked.resume(itemId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tracked"] });
    },
  });

  const items = useMemo(() => (tracked.data?.items ?? []).map(toTopic), [tracked.data]);

  return (
    <div className="tracked-page tracked-page--archive">
      <header className="tracked-archive__head">
        <Link to="/tracked" className="tracked-archive__back">
          Назад
        </Link>
        <h1>Архив</h1>
      </header>

      {tracked.isPending ? <p className="tracked-state__note">Загружаем архив…</p> : null}

      {tracked.isError ? (
        <p className="tracked-state__note">
          {tracked.error instanceof ApiError ? tracked.error.detail : "Не удалось загрузить архив"}
        </p>
      ) : null}

      {tracked.data && items.length === 0 ? (
        <p className="tracked-state__note">В архиве пока пусто.</p>
      ) : null}

      <ul className="tracked-archive__list">
        {items.map((topic) => (
          <li key={topic.id} className="tracked-archive__row">
            <div className="tracked-archive__body">
              <h2 className="tracked-archive__title">{topic.title}</h2>
              <p className="tracked-archive__meta">
                {topic.date} · {eventsLabel(topic.eventsCount)}
              </p>
            </div>
            <button
              type="button"
              className="tracked-archive__resume"
              onClick={() => resume.mutate(topic.id)}
              disabled={resume.isPending}
            >
              Возобновить
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
