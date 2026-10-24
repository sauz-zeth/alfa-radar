import type { TrackedItem } from "../api";
import { pluralRu } from "../lib/plural";

export type TopicTone = "dark" | "light";

export type Topic = {
  id: string;
  eventId: string;
  title: string;
  impactLabel: string;
  importance: number;
  date: string;
  changed: boolean;
  eventsCount: number;
  tone: TopicTone;
};

function shortDate(iso: string): string {
  const formatted = new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
  return formatted.replace(".", "");
}

export function toTopic(item: TrackedItem): Topic {
  const event = item.event;
  return {
    id: item.id,
    eventId: event.id,
    title: item.title ?? event.title,
    impactLabel: event.impact_label,
    importance: Math.round(event.importance),
    date: shortDate(event.published_at),
    changed: item.conclusions_changed,
    eventsCount: item.events.length,
    tone: event.impact === "opportunity" ? "dark" : "light",
  };
}

export const themesLabel = (count: number) => pluralRu(count, ["тема", "темы", "тем"]);
export const updatesLabel = (count: number) => pluralRu(count, ["обновление", "обновления", "обновлений"]);
export const eventsLabel = (count: number) => pluralRu(count, ["событие", "события", "событий"]);
