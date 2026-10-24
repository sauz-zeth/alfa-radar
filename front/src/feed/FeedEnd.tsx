type FeedEndProps = {
  hiddenCount: number;
  onRestart: () => void;
  onOpenHidden: () => void;
};

export function FeedEnd({ hiddenCount, onRestart, onOpenHidden }: FeedEndProps) {
  return (
    <section className="feed-end">
      <h2 className="feed-end__title">Лента просмотрена</h2>
      <p className="feed-end__text">Пропущенные, устаревшие и новости со слабым влиянием — в скрытом.</p>
      <button type="button" className="feed-end__hidden" onClick={onOpenHidden}>
        Посмотреть скрытые · {hiddenCount}
      </button>
      <button type="button" className="feed-end__restart" onClick={onRestart}>
        Начать заново
      </button>
    </section>
  );
}
