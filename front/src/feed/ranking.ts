import type { FeedItem } from "../api";

export function importanceScore(item: Pick<FeedItem, "importance">): number {
  return item.importance;
}

export function rankFeed(items: FeedItem[], threshold = 30): FeedItem[] {
  const score = (item: FeedItem) => item.importance;
  const date = (item: FeedItem) => Date.parse(item.published_at) || 0;
  const primary = items.filter((item) => score(item) > threshold).sort((a, b) => score(b) - score(a) || date(b) - date(a));
  const weak = items
    .filter((item) => score(item) < threshold)
    .sort((a, b) => b.independent_source_count - a.independent_source_count || date(b) - date(a))
    .slice(0, 10);
  return [...primary, ...weak];
}
