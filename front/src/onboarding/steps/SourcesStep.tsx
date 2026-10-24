import { useState } from "react";
import { OnboardingLayout } from "../OnboardingLayout";
import type { StepProps } from "./types";

const channels = [
  "Ключевая ставка",
  "Курс рубля",
  "Санкции",
  "Пошлины",
  "Налоги",
  "Корпоративное право",
  "Металлургия",
  "Логистика",
  "ИТ и телеком",
  "Ритейл",
  "Нефтегаз",
  "АПК",
  "Энергоресурсы",
  "Госзакупки",
  "Мировая экономика",
];

export function SourcesStep({ state, onDone }: StepProps) {
  const [selected, setSelected] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(channels.map((channel) => [channel, true])),
  );

  return (
    <OnboardingLayout
      state={state}
      title="Источники"
      description="Для профиля подобраны 15 каналов. Список можно изменить позже на вкладке «Источники»."
      footer={
        <button type="button" className="button button--primary button--block" onClick={onDone}>
          Продолжить
        </button>
      }
    >
      <div className="source-list">
        {channels.map((channel) => (
          <label key={channel} className="source-item">
            <input
              type="checkbox"
              checked={Boolean(selected[channel])}
              onChange={(event) =>
                setSelected((current) => ({ ...current, [channel]: event.target.checked }))
              }
            />
            <span>{channel}</span>
          </label>
        ))}
      </div>
    </OnboardingLayout>
  );
}
