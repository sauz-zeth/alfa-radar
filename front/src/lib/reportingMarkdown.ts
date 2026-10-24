import { formatMoney } from "../onboarding/format";

type FormKey = "balance" | "income" | "cash_flow";

const FORM_ORDER: FormKey[] = ["balance", "income", "cash_flow"];

const FORM_LABELS: Record<FormKey, string> = {
  balance: "Бухгалтерский баланс",
  income: "Отчёт о финансовых результатах",
  cash_flow: "Отчёт о движении денежных средств",
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function escapeCell(value: string): string {
  return value.replace(/\|/g, "\\|").replace(/\n/g, " ");
}

function table(headers: string[], rows: string[][]): string[] {
  if (rows.length === 0) return [];
  const line = `| ${headers.join(" | ")} |`;
  const divider = `| ${headers.map(() => "---").join(" | ")} |`;
  return [
    line,
    divider,
    ...rows.map((row) => `| ${row.map((cell) => escapeCell(cell)).join(" | ")} |`),
  ];
}

function formMarkdown(key: FormKey, entry: Record<string, unknown>): string {
  const explicit = asString(entry.markdown);
  if (explicit) return explicit;

  const data = asRecord(entry.data);
  if (!data) return "";

  const lines = [
    `## ${asString(entry.label) ?? FORM_LABELS[key]}`,
    "",
    `**Файл:** ${asString(entry.filename) ?? "—"}`,
  ];
  const period = asString(data.period);
  if (period) lines.push(`**Период:** ${period}`);
  lines.push("");

  const figures: string[][] = [];
  for (const [field, label] of [
    ["revenue", "Выручка"],
    ["profit", "Прибыль"],
    ["debt", "Долг"],
    ["interest_expense", "Проценты к уплате"],
  ] as const) {
    const value = asNumber(data[field]);
    if (value !== null) figures.push([label, formatMoney(value)]);
  }
  if (figures.length > 0) {
    lines.push("### Ключевые цифры", "", ...table(["Показатель", "Значение"], figures), "");
  }

  const cash = asRecord(data.cash_flows);
  if (cash) {
    const flows: string[][] = [];
    for (const [field, label] of [
      ["operating", "Операционный поток"],
      ["investing", "Инвестиционный поток"],
      ["financing", "Финансовый поток"],
    ] as const) {
      const value = asNumber(cash[field]);
      if (value !== null) flows.push([label, formatMoney(value)]);
    }
    if (flows.length > 0) {
      lines.push("### Денежные потоки", "", ...table(["Поток", "Сумма"], flows), "");
    }
  }

  const costs: string[][] = [];
  for (const item of asArray(data.cost_structure)) {
    const row = asRecord(item);
    const name = asString(row?.name);
    if (!name) continue;
    const value = asNumber(row?.value);
    costs.push([name, value === null ? "—" : formatMoney(value)]);
  }
  if (costs.length > 0) {
    lines.push("### Структура затрат", "", ...table(["Статья", "Сумма"], costs), "");
  }

  const positions: string[][] = [];
  for (const item of asArray(data.currency_positions)) {
    const row = asRecord(item);
    const currency = asString(row?.currency);
    if (!currency) continue;
    positions.push([currency, String(row?.amount ?? "—")]);
  }
  if (positions.length > 0) {
    lines.push("### Валютные позиции", "", ...table(["Валюта", "Сумма"], positions), "");
  }

  const points = asArray(data.key_points)
    .filter((item): item is string => typeof item === "string" && Boolean(item.trim()))
    .map((item) => `- ${item.trim()}`);
  if (points.length > 0) {
    lines.push("### Что важно", "", ...points, "");
  }

  return lines.join("\n").trim();
}

export function reportingMarkdown(summary: Record<string, unknown> | null | undefined): string {
  if (!summary) return "";
  const explicit = asString(summary.markdown);
  if (explicit) return explicit;

  const forms = asRecord(summary.forms);
  if (!forms) {
    const lines: string[] = [];
    const period = asString(summary.period);
    if (period) lines.push(`**Период:** ${period}`);
    for (const point of asArray(summary.key_points)) {
      if (typeof point === "string" && point.trim()) lines.push(`- ${point.trim()}`);
    }
    return lines.join("\n");
  }

  return FORM_ORDER.map((key) => {
    const entry = asRecord(forms[key]);
    return entry ? formMarkdown(key, entry) : "";
  })
    .filter(Boolean)
    .join("\n\n");
}
