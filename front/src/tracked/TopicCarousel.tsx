import { TopicCircle } from "./TopicCircle";
import type { Topic } from "./mapTracked";

type TopicCarouselProps = {
  topics: Topic[];
  index: number;
  onSelect: (index: number) => void;
  onOpen?: (topic: Topic) => void;
};

export function TopicCarousel({ topics, index, onSelect, onOpen }: TopicCarouselProps) {
  const active = topics[index] ?? topics[0];

  if (!active) return null;

  const count = topics.length;
  const prevIndex = count > 1 ? (index - 1 + count) % count : -1;
  const nextIndex = count > 1 ? (index + 1) % count : -1;
  const prev = prevIndex >= 0 ? topics[prevIndex] : undefined;
  const next = nextIndex >= 0 ? topics[nextIndex] : undefined;

  return (
    <div className="topic-carousel">
      {prev ? (
        <TopicCircle topic={prev} side="prev" onSelect={() => onSelect(prevIndex)} />
      ) : null}
      {next ? (
        <TopicCircle topic={next} side="next" onSelect={() => onSelect(nextIndex)} />
      ) : null}
      <TopicCircle topic={active} onOpen={onOpen ? () => onOpen(active) : undefined} />
    </div>
  );
}
