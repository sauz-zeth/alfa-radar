import type { FeedItemDetail, SourcePost } from "../api";
import { pluralRu } from "../lib/plural";

export type EventTextItem = {
  label: string;
  text: string;
  meta: string;
};

export type EventQuestion = {
  id: string;
  text: string;
  status: string;
  statusCode: string;
  answer?: string;
  meta: string;
};

export type EventMetric = {
  label: string;
  value: string;
  previousValue?: string;
  note: string;
  tone?: "negative" | "positive" | null;
};

export type EventModel = {
  id: string;
  title: string;
  sourceName: string;
  publishedAt: string;
  changedAt: string | null;
  conclusionsChanged: boolean;
  sourcesCount: number;
  impactLabel: string;
  impactShort: string;
  importance: number;
  fact: EventTextItem;
  changes: EventTextItem[];
  agree: EventTextItem;
  differ: EventTextItem[];
  metrics: EventMetric[];
  companyNote: string;
  questions: EventQuestion[];
  answeredCount: number;
  waitingCount: number;
  feedback: { action: string; reason?: string | null } | null;
  sources: SourcePost[];
};

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" }).replace(".", "");
}

export function longDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

export function monthLabel(iso: string): string {
  const value = new Date(iso).toLocaleDateString("ru-RU", { month: "long", year: "numeric" }).replace(" г.", "");
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function timelineDate(value: string): { day: string; month: string } {
  const [day = "", month = ""] = value.split(".");
  return {
    day: day ? String(Number(day)) : "",
    month: month
      ? new Date(2026, Number(month) - 1, 1).toLocaleDateString("ru-RU", { month: "short" }).replace(".", "")
      : "",
  };
}

export function sourcesLabel(count: number): string {
  return pluralRu(count, ["источник", "источника", "источников"]);
}

export function eventsLabel(count: number): string {
  return pluralRu(count, ["событие", "события", "событий"]);
}

export function toEvent(detail: FeedItemDetail): EventModel {
  const theses = detail.theses ?? [];
  const comparison = detail.comparison;
  const metrics = detail.impact_metrics ?? [];
  const questions = detail.open_questions ?? [];
  const sources = detail.sources ?? [];
  const dated = detail.published_at;
  const sourceMeta = [detail.source_name, longDate(dated), sourcesLabel(sources.length)]
    .filter(Boolean)
    .join(" · ");

  const fact: EventTextItem = {
    label: "Факт",
    text: detail.summary,
    meta: `${detail.source_name} · ${sourcesLabel(Math.max(sources.length, 1))} · ${detail.theses[0]?.status ?? "официально"}`,
  };

  const changes: EventTextItem[] = theses
    .filter((thesis) => thesis.text !== detail.summary)
    .map((thesis) => ({
      label: thesis.category,
      text: thesis.text,
      meta: [...thesis.sources, thesis.status].filter(Boolean).join(" · "),
    }));

  const agree: EventTextItem = {
    label: "Сходятся",
    text: comparison.agree[0] ?? detail.summary,
    meta: sourceMeta,
  };

  const differ: EventTextItem[] = [
    ...comparison.differ.map((text) => ({
      label: "Расходятся",
      text,
      meta: detail.source_name,
    })),
    ...comparison.single.map((text) => ({
      label: "Пишет один источник",
      text,
      meta: detail.source_name,
    })),
  ];

  const eventMetrics: EventMetric[] = metrics.map((metric, index) => ({
    label: metric.label || (index === 0 ? "EBITDA в год" : "Экспорт под пошлиной"),
    value: metric.value,
    previousValue: metric.previous_value ?? undefined,
    note: metric.note.replace(/\s*\n\s*/g, " "),
    tone: metric.tone,
  }));

  if (eventMetrics.length === 0) {
    eventMetrics.push({
      label: "Влияние на бизнес",
      value: detail.what_it_means,
      note: "",
      tone: null,
    });
  }

  return {
    id: detail.id,
    title: detail.title,
    sourceName: detail.source_name,
    publishedAt: dated,
    changedAt: detail.changed_at ?? null,
    conclusionsChanged: detail.conclusions_changed,
    sourcesCount: sources.length,
    impactLabel: detail.impact_label,
    impactShort: ({ risk: "риск", opportunity: "возможность", mixed: "смешанное", neutral: "нейтральное" } as Record<string, string>)[detail.impact] ?? detail.impact_label.toLowerCase(),
    importance: detail.importance,
    fact,
    changes,
    agree,
    differ,
    metrics: eventMetrics,
    companyNote: detail.what_it_means,
    questions: questions.map((question) => ({
      id: question.id,
      text: question.text,
      status: question.status,
      statusCode: question.status_code,
      answer: question.answer ?? undefined,
      meta: [question.source, question.date].filter(Boolean).join(" · "),
    })),
    answeredCount:
      detail.questions_answered ||
      questions.filter((question) => question.status_code !== "waiting").length,
    waitingCount:
      detail.questions_waiting ||
      questions.filter((question) => question.status_code === "waiting").length,
    feedback: detail.feedback
      ? { action: detail.feedback.action, reason: detail.feedback.reason }
      : null,
    sources,
  };
}
