import type { Channel } from "../api";

const ICONS = {
  telegram: {
    label: "Telegram",
    color: "#229ED9",
    path: "M9.04 15.51 8.7 20.3c.49 0 .7-.21.96-.46l2.3-2.2 4.78 3.5c.88.48 1.5.23 1.72-.8l3.12-14.6c.28-1.3-.47-1.8-1.3-1.5L2.1 9.9c-1.28.5-1.26 1.2-.22 1.53l4.8 1.5L17.84 6.2c.5-.33.96-.15.58.18l-9.38 8.45z",
  },
  rss: {
    label: "RSS",
    color: "#EE802F",
    paths: [
      "M4 4v3c7.18 0 13 5.82 13 13h3C20 11.16 12.84 4 4 4z",
      "M4 10v3c3.87 0 7 3.13 7 7h3c0-5.52-4.48-10-10-10z",
      "M6 17a2 2 0 1 0 0 4 2 2 0 0 0 0-4z",
    ],
  },
} as const;

export function SourceIcon({ type }: { type: Channel["source_type"] }) {
  const icon = ICONS[type];

  return (
    <span className="source-icon" role="img" aria-label={icon.label} title={icon.label}>
      <svg viewBox="0 0 24 24" fill={icon.color} aria-hidden="true">
        {"path" in icon ? (
          <path d={icon.path} />
        ) : (
          icon.paths.map((path) => <path key={path} d={path} />)
        )}
      </svg>
    </span>
  );
}
