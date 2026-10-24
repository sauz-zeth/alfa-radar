import type { TrackedItem } from "../api";
import { pluralRu } from "../lib/plural";

export type TopicTone = "dark" | "light";
export type ImpactTone = "positive" | "negative" | "neutral";

export type Topic = {
  id: string;
  eventId: string;
  title: string;
  impactLabel: string;
  impactTone: ImpactTone;
  importance: number;
  date: string;
  dateLong: string;
  updateLabel: string | null;
  conclusion: string;
  conclusionQuestion: string | null;
  image: string | null;
  changed: boolean;
  eventsCount: number;
  tone: TopicTone;
};

function shortDate(iso: string): string {
  const formatted = new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
  return formatted.replace(".", "");
}

function longDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

function impactTone(impact: string): ImpactTone {
  if (impact === "opportunity") return "positive";
  if (impact === "risk") return "negative";
  return "neutral";
}

export function toTopic(item: TrackedItem): Topic {
  const event = item.event;
  const insight = item.insight;
  const answered = (insight?.open_questions ?? []).filter(
    (question) => question.status_code !== "waiting" && question.answer,
  );
  const latestAnswer = answered[answered.length - 1];
  const image =
    event.sources.find((source) => source.image_url)?.image_url ??
    insight?.sources.find((source) => source.image_url)?.image_url ??
    null;

  return {
    id: item.id,
    eventId: event.id,
    title: item.title ?? event.title,
    impactLabel: event.impact_label,
    impactTone: impactTone(event.impact),
    importance: Math.round(event.importance),
    date: shortDate(event.published_at),
    dateLong: longDate(event.published_at),
    updateLabel: event.update_label?.trim() || null,
    conclusion: latestAnswer?.answer ?? item.what_changed ?? event.summary,
    conclusionQuestion: latestAnswer ? latestAnswer.text.replace(/\?$/, "") : null,
    image,
    changed: item.conclusions_changed,
    eventsCount: item.events.length,
    tone: event.impact === "opportunity" ? "dark" : "light",
  };
}

export const themesLabel = (count: number) => pluralRu(count, ["тема", "темы", "тем"]);
export const updatesLabel = (count: number) => pluralRu(count, ["обновление", "обновления", "обновлений"]);
export const eventsLabel = (count: number) => pluralRu(count, ["событие", "события", "событий"]);
export const storiesLabel = (count: number) =>
  pluralRu(count, ["активная история", "активные истории", "активных историй"]);
