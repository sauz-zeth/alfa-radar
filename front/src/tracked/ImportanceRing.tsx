import type { CSSProperties } from "react";

type ImportanceRingProps = {
  value: number;
};

export function ImportanceRing({ value }: ImportanceRingProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));

  return (
    <span
      className="topic-ring"
      style={{ "--importance": clamped } as CSSProperties}
      aria-hidden="true"
    >
      <span className="topic-ring__base" />
      <span className="topic-ring__progress" />
      <span className="topic-ring__ticks" />
      <span className="topic-ring__dots" />
    </span>
  );
}
