import "./feed-end.css";

type FeedEndScreenProps = {
  hiddenCount: number;
  onOpenHidden: () => void;
  onRestart: () => void;
};

export function FeedEndScreen({ hiddenCount, onOpenHidden, onRestart }: FeedEndScreenProps) {
  return (
    <section className="feed-end-screen" aria-labelledby="feed-end-screen-title">
      <div className="feed-end-screen__oval">
        <div className="feed-end-screen__content">
          <div className="feed-end-screen__copy">
            <h2 className="feed-end-screen__title" id="feed-end-screen-title">
              Всё важное
              <br />
              посмотрели
            </h2>
            <p className="feed-end-screen__text">
              Пропущенные, устаревшие и новости со слабым влиянием — в скрытом
            </p>
          </div>

          <div className="feed-end-screen__actions">
            <button
              type="button"
              className="feed-end-screen__button feed-end-screen__button--primary"
              onClick={onOpenHidden}
            >
              Скрытые новости · {hiddenCount}
            </button>
            <button
              type="button"
              className="feed-end-screen__button feed-end-screen__button--secondary"
              onClick={onRestart}
            >
              Начать заново
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
