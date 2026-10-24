import { DotDigits } from "./DotDigits";

type ImportanceScoreProps = {
  value: number;
  variant: "circle" | "card";
};

export function ImportanceScore({ value, variant }: ImportanceScoreProps) {
  if (variant === "circle") {
    return (
      <span className="importance-score importance-score--circle">
        <DotDigits value={value} />
      </span>
    );
  }

  return (
    <span className={`importance-score importance-score--${variant}`}>{Math.round(value)}</span>
  );
}
