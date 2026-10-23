import type { FeedItem } from "../api";
import fallbackPhoto from "../assets/photos/steel-export.png";
import type { FeedPost, FeedSource, ImpactTone } from "./types";

const avatarColors = ["#4d6070", "#525e72", "#5b4d70", "#4d6b5f", "#6b5a4d"];

const impacts: Record<string, { tone: ImpactTone; label: string }> = {
  risk: { tone: "risk", label: "Риск" },
  opportunity: { tone: "opportunity", label: "Возможность" },
  mixed: { tone: "mixed", label: "Смешанное риск/возможность" },
  neutral: { tone: "neutral", label: "Нейтрально" },
};

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase() ?? "")
      .join("") || "•"
  );
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

export function toFeedPost(item: FeedItem): FeedPost {
  const sources: FeedSource[] = item.sources.length
    ? item.sources.map((source, index) => ({
        id: `${item.id}-${index}`,
        initials: initials(source.name),
        name: source.name,
        color: avatarColors[index % avatarColors.length]!,
        time: formatTime(source.time),
        image: source.image_url ?? fallbackPhoto,
        imageAlt: item.title,
        fullBleed: index > 0,
      }))
    : [
        {
          id: `${item.id}-0`,
          initials: initials(item.source_name),
          name: item.source_name,
          color: avatarColors[0]!,
          time: formatTime(item.published_at),
          image: fallbackPhoto,
          imageAlt: item.title,
        },
      ];

  const categories = (item.matched_categories.length ? item.matched_categories : item.categories).map(
    (category) => category.short_name,
  );
  const impact = impacts[item.impact] ?? { tone: "neutral" as ImpactTone, label: item.impact_label };

  return {
    id: item.id,
    title: item.title,
    topics: categories.slice(0, 3),
    categories,
    effectiveLabel: item.update_label ?? formatDate(item.published_at),
    note: item.prognosis_note,
    impact: impact.tone,
    impactLabel: impact.label,
    importance: item.importance,
    sources,
    metrics: item.impact_metrics.map((metric) => ({
      value: metric.value,
      note: metric.note,
      tone: metric.tone ?? undefined,
    })),
    tracked: item.is_tracked,
  };
}

export function buildFilters(posts: FeedPost[]): string[] {
  const categories = new Set<string>();
  for (const post of posts) {
    for (const category of post.categories) categories.add(category);
  }
  return ["Все", "Важное", ...categories].slice(0, 14);
}
