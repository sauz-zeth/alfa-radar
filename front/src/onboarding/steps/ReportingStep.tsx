import { useState } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery } from "../../api";
import { MarkdownView } from "../../components/MarkdownView";
import { reportingMarkdown } from "../../lib/reportingMarkdown";
import { OnboardingLayout } from "../OnboardingLayout";
import { useOnboarding } from "../useOnboarding";
import type { SimpleStepProps } from "./types";

const forms = [
  { key: "balance", label: "Бухгалтерский баланс" },
  { key: "income", label: "Отчёт о финансовых результатах" },
  { key: "cash_flow", label: "Отчёт о движении денежных средств" },
] as const;

type FormKey = (typeof forms)[number]["key"];

const formLabels: Record<string, string> = {
  balance: "Бухгалтерский баланс",
  income: "Отчёт о финансовых результатах",
  cash_flow: "Отчёт о движении денежных средств",
};

export function ReportingStep({ onDone }: SimpleStepProps) {
  const api = useApi();
  const { data: state } = useOnboarding();
  const [files, setFiles] = useState<Partial<Record<FormKey, File>>>({});

  const reporting = useApiQuery({
    queryKey: ["onboarding", "reporting"],
    queryFn: (signal) => api.onboarding.reporting({ signal }),
  });

  const upload = useApiMutation({
    mutationFn: () => api.onboarding.uploadReporting(files),
  });

  const skip = useApiMutation({
    mutationFn: () => api.onboarding.skip({ step: "reporting_uploaded" }),
    onSuccess: onDone,
  });

  const hasFiles = Boolean(files.balance || files.income || files.cash_flow);
  const error = upload.error ?? skip.error;
  const uploads = reporting.data?.uploads ?? [];
  const summary = upload.data?.summary ?? reporting.data?.summary;
  const markdown = reportingMarkdown(summary);
  const uploaded = Boolean(upload.data);

  if (!state) return null;

  return (
    <OnboardingLayout
      state={state}
      title="Отчётность"
      description="Необязательный шаг. Загрузите формы — агент выделит ключевые цифры и будет учитывать их в разборе. Поддерживаются PDF, Excel и CSV."
      footer={
        <>
          {error ? (
            <p className="form-error">{error instanceof ApiError ? error.detail : "Не удалось загрузить отчётность"}</p>
          ) : null}
          <div className="onboarding-actions">
            <button
              type="button"
              className="button button--ghost button--block"
              onClick={() => skip.mutate()}
              disabled={skip.isPending || upload.isPending}
            >
              Пропустить
            </button>
            <button
              type="button"
              className="button button--primary button--block"
              onClick={() => upload.mutate()}
              disabled={!hasFiles || upload.isPending || skip.isPending}
            >
              {upload.isPending ? "Загружаем…" : uploaded ? "Загрузить снова" : "Загрузить"}
            </button>
          </div>
          {uploaded ? (
            <button
              type="button"
              className="button button--primary button--block"
              onClick={onDone}
              disabled={skip.isPending}
            >
              Продолжить
            </button>
          ) : null}
        </>
      }
    >
      <div className="onboarding-fields">
        {forms.map((form) => (
          <label key={form.key} className="file-field">
            <span className="file-field__label">{form.label}</span>
            <span className="file-field__value">
              {files[form.key]?.name ?? reporting.data?.uploads.find((item) => item.form_type === form.key)?.filename ?? "Файл не выбран"}
            </span>
            <input
              type="file"
              accept=".pdf,.xlsx,.xlsm,.csv,.txt"
              onChange={(event) =>
                setFiles((current) => ({ ...current, [form.key]: event.target.files?.[0] }))
              }
            />
          </label>
        ))}
      </div>

      {uploads.length > 0 ? (
        <section className="onboarding-section">
          <h2 className="onboarding-section__title">Загружено</h2>
          <ul className="upload-list">
            {uploads.map((item) => (
              <li key={item.id}>
                <span>{formLabels[item.form_type] ?? item.form_type}</span>
                <span className="upload-list__file">{item.filename}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {markdown ? (
        <section className="onboarding-section">
          <h2 className="onboarding-section__title">Что удалось выделить</h2>
          <MarkdownView markdown={markdown} />
        </section>
      ) : null}
    </OnboardingLayout>
  );
}
