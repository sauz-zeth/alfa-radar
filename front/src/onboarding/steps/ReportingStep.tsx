import { useState } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery } from "../../api";
import { formatMoney } from "../format";
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

type Snapshot = Record<string, unknown>;

function asRecord(value: unknown): Snapshot | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Snapshot)
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map(asString).filter((item): item is string => item !== null);
}

function asPeriod(value: unknown): string | null {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return asString(value);
}

const moneyKeys: [string, string][] = [
  ["revenue", "Выручка"],
  ["profit", "Прибыль"],
  ["debt", "Долг"],
  ["interest_expense", "Проценты к уплате"],
];

const cashFlowKeys: [string, string][] = [
  ["operating", "Операционный поток"],
  ["investing", "Инвестиционный поток"],
  ["financing", "Финансовый поток"],
];

function figures(data: Snapshot | null): { label: string; value: number }[] {
  if (!data) return [];
  const result: { label: string; value: number }[] = [];
  for (const [key, label] of moneyKeys) {
    const value = asNumber(data[key]);
    if (value !== null) result.push({ label, value });
  }
  const cashFlows = asRecord(data.cash_flows);
  for (const [key, label] of cashFlowKeys) {
    const value = asNumber(cashFlows?.[key]);
    if (value !== null) result.push({ label, value });
  }
  if (Array.isArray(data.currency_positions)) {
    for (const item of data.currency_positions) {
      const position = asRecord(item);
      const currency = asString(position?.currency);
      const amount = asNumber(position?.amount);
      if (currency && amount !== null) result.push({ label: currency, value: amount });
    }
  }
  return result;
}

type FormSummary = {
  label: string;
  filename: string | null;
  data: Snapshot | null;
};

function readForms(summary: Snapshot | undefined): Partial<Record<FormKey, FormSummary>> {
  const source = asRecord(summary?.forms);
  const result: Partial<Record<FormKey, FormSummary>> = {};
  if (!source) return result;
  for (const form of forms) {
    const item = asRecord(source[form.key]);
    if (!item) continue;
    result[form.key] = {
      label: asString(item.label) ?? form.label,
      filename: asString(item.filename),
      data: asRecord(item.data),
    };
  }
  return result;
}

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
  const period = asPeriod(summary?.period);
  const keyPoints = asStringList(summary?.key_points);
  const formSummaries = readForms(summary);
  const hasSummary = Boolean(period || keyPoints.length > 0 || Object.keys(formSummaries).length > 0);
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

      {hasSummary ? (
        <section className="onboarding-section">
          <h2 className="onboarding-section__title">Что удалось выделить</h2>
          {period ? <p className="onboarding-note">Период: {period}</p> : null}
          {keyPoints.length > 0 ? (
            <ul className="reporting-points">
              {keyPoints.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          ) : null}
          {forms.map((form) => {
            const item = formSummaries[form.key];
            if (!item) return null;
            const rows = figures(item.data);
            return (
              <article key={form.key} className="reporting-card">
                <div className="reporting-card__head">
                  <p className="reporting-card__label">{item.label}</p>
                  {item.filename ? <p className="reporting-card__file">{item.filename}</p> : null}
                </div>
                {rows.length > 0 ? (
                  <dl className="reporting-card__figures">
                    {rows.map((row) => (
                      <div key={row.label} className="reporting-card__figure">
                        <dt>{row.label}</dt>
                        <dd>{formatMoney(row.value)}</dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <p className="onboarding-note">Цифры не распознаны.</p>
                )}
              </article>
            );
          })}
        </section>
      ) : null}
    </OnboardingLayout>
  );
}
