export function TopicCircleSkeleton() {
  return <span className="topic-skeleton topic-skeleton--circle" aria-hidden="true" />;
}

export function TopicCardSkeleton() {
  return (
    <span className="topic-skeleton topic-skeleton--card" aria-hidden="true">
      <span className="topic-skeleton__line topic-skeleton__line--short" />
      <span className="topic-skeleton__line" />
      <span className="topic-skeleton__line" />
      <span className="topic-skeleton__score" />
    </span>
  );
}
