import type { Channel } from "../api";

export function SourceBadge({ type }: { type: Channel["source_type"] }) {
  return (
    <span className={`source-badge source-badge--${type}`}>
      {type === "rss" ? "RSS" : "ТГ"}
    </span>
  );
}
