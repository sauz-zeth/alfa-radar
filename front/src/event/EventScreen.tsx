import { useMemo, useRef, useState } from "react";
import {
  ApiError,
  useApi,
  useApiMutation,
  useApiQuery,
  useQueryClient,
  type FeedItemDetail,
} from "../api";
import { useRouter } from "../router";
import { AskBar } from "./AskBar";
import { CompanyImpact } from "./CompanyImpact";
import { EventChangeCard } from "./EventChangeCard";
import { EventHeader } from "./EventHeader";
import { EventHero } from "./EventHero";
import { EventTabContent } from "./EventTabContent";
import { EventTabs, type EventTab } from "./EventTabs";
import { EventTimeline } from "./EventTimeline";
import { FactCard } from "./FactCard";
import { FeedbackSection } from "./FeedbackSection";
import { QuestionsSection } from "./QuestionsSection";
import { SectionHeader } from "./SectionHeader";
import { SourcesSection } from "./SourcesSection";
import { TextListCard } from "./TextListCard";
import { toEvent } from "./eventModel";
import "./event.css";

export default function EventScreen() {
  const api = useApi();
  const queryClient = useQueryClient();
  const { path, navigate } = useRouter();
  const eventId = path.split("/")[2] ?? "";
  const [tab, setTab] = useState<EventTab>("Разбор");
  const [question, setQuestion] = useState("");
  const [trackedOverride, setTrackedOverride] = useState<boolean | null>(null);
  const askRef = useRef<HTMLInputElement | null>(null);

  const detail = useApiQuery({
    queryKey: ["event", eventId],
    queryFn: (signal) => api.feed.detail(eventId, { signal }),
    enabled: Boolean(eventId),
    staleTime: 0,
  });

  const trackMutation = useApiMutation<unknown, boolean>({
    mutationFn: async (tracked) => {
      if (!tracked) {
        await api.feed.track(eventId);
        return;
      }
      await api.feed.untrack(eventId);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      void queryClient.invalidateQueries({ queryKey: ["tracked"] });
      void queryClient.invalidateQueries({ queryKey: ["feed"] });
    },
  });

  const feedbackMutation = useApiMutation<unknown, string>({
    mutationFn: (reason) =>
      api.feed.feedback(eventId, {
        action:
          reason === "Не касается нас"
            ? "not_relevant"
            : reason === "Ошибка в факте"
              ? "fact_error"
              : "score_inaccurate",
        reason,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["event", eventId] });
      void queryClient.invalidateQueries({ queryKey: ["feed"] });
    },
  });

  const event = useMemo(() => (detail.data ? toEvent(detail.data) : null), [detail.data]);
  const tracked = trackedOverride ?? detail.data?.is_tracked ?? false;

  const toggleTracked = () => {
    const next = !tracked;
    setTrackedOverride(next);
    trackMutation.mutate(next, { onError: () => setTrackedOverride(null) });
  };

  const submitFeedback = async (reason: string) => {
    await feedbackMutation.mutateAsync(reason);
  };

  const goBack = () => {
    if (window.history.length > 1) window.history.back();
    else navigate("/");
  };

  const focusAsk = () => askRef.current?.focus();

  const askMutation = useApiMutation<FeedItemDetail, string>({
    mutationFn: (text) => api.feed.askQuestion(eventId, { question: text }),
    onSuccess: (data) => {
      queryClient.setQueryData(["event", eventId], data);
      setQuestion("");
      void queryClient.invalidateQueries({ queryKey: ["tracked"] });
    },
  });

  const submitQuestion = (text: string) => {
    const value = text.trim();
    if (value) askMutation.mutate(value);
  };
  const askError = askMutation.error
    ? askMutation.error instanceof ApiError
      ? askMutation.error.detail
      : "Не удалось получить ответ"
    : null;

  return (
    <div className="event-page">
      <div className="event-scroll">
        <div className="event-cover">
          <EventHeader
            onBack={goBack}
            tracked={tracked}
            pending={trackMutation.isPending}
            onToggleTracked={toggleTracked}
          />
          {event && detail.data ? (
            <>
              <EventHero event={event} />
              <EventChangeCard event={event} />
              <EventTimeline publishedAt={event.publishedAt} timeline={detail.data.timeline} />
            </>
          ) : null}
        </div>

        {detail.isPending ? <p className="event-state">Загружаем разбор…</p> : null}

        {detail.isError ? (
          <div className="event-state">
            <p>
              {detail.error instanceof ApiError ? detail.error.detail : "Не удалось загрузить разбор"}
            </p>
            <button type="button" className="event-state__retry" onClick={() => detail.refetch()}>
              Повторить
            </button>
          </div>
        ) : null}

        {event && detail.data ? (
          <div className="event-body">
            <EventTabs active={tab} onChange={setTab} />

            {tab === "Разбор" ? (
              <>
                <section className="event-section">
                  <SectionHeader title="Что произошло" />
                  <FactCard {...event.fact} />
                  <TextListCard items={event.changes} />
                </section>

                <section className="event-section">
                  <SectionHeader title="Сравнение источников" />
                  <FactCard {...event.agree} />
                  <TextListCard items={event.differ} />
                </section>

                <section className="event-section">
                  <SectionHeader title="Для компании изменился расчёт" />
                  <CompanyImpact
                    metrics={event.metrics}
                    note={event.companyNote}
                    scoreBreakdown={detail.data.score_breakdown}
                  />
                </section>

                <QuestionsSection
                  questions={event.questions}
                  answeredCount={event.answeredCount}
                  waitingCount={event.waitingCount}
                  onAsk={focusAsk}
                />

                <SourcesSection sources={event.sources} />
              </>
            ) : (
              <EventTabContent
                tab={tab}
                detail={detail.data}
                event={event}
                onAsk={submitQuestion}
                onAskFocus={focusAsk}
                askPending={askMutation.isPending}
              />
            )}

            <FeedbackSection
              initialReason={event.feedback?.reason ?? null}
              onFeedback={submitFeedback}
              pending={feedbackMutation.isPending}
              error={
                feedbackMutation.error
                  ? feedbackMutation.error instanceof ApiError
                    ? feedbackMutation.error.detail
                    : "Не удалось отправить отзыв"
                  : null
              }
            />

            <div className="event-ask-spacer" />
          </div>
        ) : null}
      </div>

      <AskBar
        inputRef={askRef}
        value={question}
        onChange={setQuestion}
        pending={askMutation.isPending}
        error={askError}
        onSubmit={() => submitQuestion(question)}
      />
    </div>
  );
}
