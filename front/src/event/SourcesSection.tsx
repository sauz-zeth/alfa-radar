import type { SourcePost } from "../api";
import { SectionHeader } from "./SectionHeader";
import { SourceCard } from "./SourceCard";
import { sourcesLabel } from "./eventModel";

type SourcesSectionProps = {
  sources: SourcePost[];
};

export function SourcesSection({ sources }: SourcesSectionProps) {
  return (
    <section className="event-section">
      <SectionHeader title="Источники" aside={sourcesLabel(sources.length)} />

      <div className="event-sources">
        {sources.map((source, index) => (
          <SourceCard key={`${source.name}-${index}`} source={source} />
        ))}
      </div>
    </section>
  );
}
