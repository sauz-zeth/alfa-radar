type FeedEndProps = {
  onOpen: () => void;
};

export function FeedEnd({ onOpen }: FeedEndProps) {
  return (
    <section className="feed-end">
      <h2 className="feed-end__title">Лента просмотрена</h2>
      <p className="feed-end__text">Пропущенные, устаревшие и новости со слабым влиянием — в скрытом.</p>
      <button type="button" className="feed-end__trigger" onClick={onOpen}>
        Завершить просмотр
      </button>
    </section>
  );
}
