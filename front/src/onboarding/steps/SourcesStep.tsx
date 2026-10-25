import { ApiError, useApi, useApiMutation, useApiQuery, type Channel, type SourcesState } from "../../api";
import { formatSubscribers } from "../../sources/channelVisuals";
import { SourceIcon } from "../../sources/SourceIcon";
import { OnboardingLayout } from "../OnboardingLayout";
import type { StepProps } from "./types";

export function SourcesStep({ state, onDone }: StepProps) {
  const api = useApi();
  const sources = useApiQuery({
    queryKey: ["onboarding", "sources"],
    queryFn: (signal) => api.sources.state({ signal }),
  });

  const toggle = useApiMutation<SourcesState, Channel>({
    mutationFn: (channel) =>
      channel.subscribed
        ? api.sources.unsubscribe(channel.id)
        : api.sources.subscribe(channel.id),
    onSuccess: () => {
      void sources.refetch();
    },
  });

  const channels = sources.data?.channels ?? [];
  const telegramCount = channels.filter((item) => item.source_type === "telegram").length;
  const rssCount = channels.length - telegramCount;

  return (
    <OnboardingLayout
      state={state}
      title="Источники"
      description={
        channels.length > 0
          ? `Подобрали ${channels.length} источников по вашим категориям: ${telegramCount} Telegram и ${rssCount} RSS. Список можно изменить позже на вкладке «Источники».`
          : "Подбираем источники под ваш профиль…"
      }
      footer={
        <button
          type="button"
          className="button button--primary button--block"
          onClick={onDone}
          disabled={sources.isPending}
        >
          Продолжить
        </button>
      }
    >
      {sources.isPending ? <p className="onboarding-note">Подбираем источники…</p> : null}
      {sources.isError ? (
        <p className="form-error">
          {sources.error instanceof ApiError
            ? sources.error.detail
            : "Не удалось загрузить источники"}
        </p>
      ) : null}
      {!sources.isPending && channels.length === 0 ? (
        <p className="onboarding-note">Источники не найдены. Добавьте их позже в разделе «Источники».</p>
      ) : null}

      {channels.length > 0 ? (
        <section className="onboarding-section">
          <div className="source-list source-list--onboarding">
            {channels.map((channel) => (
              <label key={channel.id} className="source-item">
                <input
                  type="checkbox"
                  checked={channel.subscribed}
                  disabled={toggle.isPending}
                  onChange={() => toggle.mutate(channel)}
                />
                <span className="source-item__body">
                  <span className="source-item__name">
                    <SourceIcon type={channel.source_type} />
                    {channel.name}
                  </span>
                  <span className="source-item__meta">
                    {channel.handle ?? channel.topics}
                    {channel.tg_subscribers
                      ? ` · ${formatSubscribers(channel.tg_subscribers)}`
                      : ""}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </section>
      ) : null}
    </OnboardingLayout>
  );
}
