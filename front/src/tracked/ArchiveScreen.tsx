import { useMemo } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery, useQueryClient } from "../api";
import { pluralRu } from "../lib/plural";
import { Link } from "../router";
import "./archive.css";

type ArchiveRow = {
  id: string;
  title: string;
  events: number;
  days: number;
};

function daysWithoutNews(iso: string): number {
  const diff = Date.now() - new Date(iso).getTime();
  return Math.max(0, Math.floor(diff / 86_400_000));
}

function daysLabel(days: number): string {
  return `${days} ${pluralRu(days, ["день", "дня", "дней"])} без новостей`;
}

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

  const rows = useMemo<ArchiveRow[]>(
    () =>
      (tracked.data?.items ?? []).map((item) => {
        const latest = item.events[item.events.length - 1]?.published_at ?? item.event.published_at;
        return {
          id: item.id,
          title: item.title ?? item.event.title,
          events: Math.max(1, item.events.length),
          days: daysWithoutNews(latest),
        };
      }),
    [tracked.data],
  );

  const error = resume.error;
  const errorId = resume.variables ? `archive-error-${resume.variables}` : undefined;

  return (
    <div className="archive-page">
      <div className="archive-shell">
        <header className="archive-head">
          <Link to="/tracked" className="archive-back" aria-label="Назад к отслеживаемому">
            <span aria-hidden="true">←</span>
          </Link>
          <h1 className="archive-head__title">Архив</h1>
          <span className="archive-head__spacer" aria-hidden="true" />
        </header>

        <main className="archive-body">
          {tracked.isPending ? <p className="archive-note">Загружаем архив…</p> : null}

          {tracked.isError ? (
            <p className="archive-note">
              {tracked.error instanceof ApiError
                ? tracked.error.detail
                : "Не удалось загрузить архив"}
            </p>
          ) : null}

          {tracked.data && rows.length === 0 ? (
            <section className="archive-empty">
              <h2>Нет тем</h2>
              <p>Архивные темы появятся здесь, когда вы приостановите отслеживание.</p>
              <Link to="/tracked" className="archive-empty__action">
                К отслеживаемому
              </Link>
            </section>
          ) : null}

          {rows.length > 0 ? (
            <ul className="archive-list">
              {rows.map((row) => {
                const rowError = resume.isError && resume.variables === row.id;
                return (
                  <li key={row.id} className="archive-card">
                    <div
                      className="archive-card__date"
                      aria-label={`Событий в теме: ${row.events}`}
                    >
                      <span className="archive-card__day">{row.events}</span>
                    </div>
                    <div className="archive-card__main">
                      <div className="archive-card__text">
                        <h2 className="archive-card__title">{row.title}</h2>
                        <p className="archive-card__meta">{daysLabel(row.days)}</p>
                      </div>
                      {rowError ? (
                        <p className="archive-card__error" id={errorId} role="alert">
                          {error instanceof ApiError
                            ? error.detail
                            : "Не удалось возобновить тему"}
                        </p>
                      ) : null}
                      <button
                        type="button"
                        className="archive-card__resume"
                        onClick={() => resume.mutate(row.id)}
                        disabled={resume.isPending}
                        aria-describedby={rowError ? errorId : undefined}
                      >
                        Возобновить
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </main>
      </div>
    </div>
  );
}
