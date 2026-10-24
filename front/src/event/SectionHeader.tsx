import type { ReactNode } from "react";

type SectionHeaderProps = {
  title: string;
  aside?: ReactNode;
  tight?: boolean;
};

export function SectionHeader({ title, aside, tight }: SectionHeaderProps) {
  return (
    <div className={tight ? "event-section-head is-tight" : "event-section-head"}>
      <h2 className="event-section-head__title">{title}</h2>
      {aside ? <span className="event-section-head__aside">{aside}</span> : null}
    </div>
  );
}
