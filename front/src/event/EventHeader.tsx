type EventHeaderProps = {
  onBack: () => void;
  tracked: boolean;
  pending?: boolean;
  onToggleTracked: () => void;
};

export function EventHeader({ onBack, tracked, pending, onToggleTracked }: EventHeaderProps) {
  const trackLabel = tracked ? "Не отслеживать тему" : "Отслеживать тему";

  return (
    <header className="event-head">
      <button type="button" className="event-head__button" aria-label="Назад" onClick={onBack}>
        <svg viewBox="0 0 22 22" width="22" height="22" aria-hidden="true">
          <path
            d="M13.5 5.5 8 11l5.5 5.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      <span className="event-head__title">История темы</span>

      <button
        type="button"
        className="event-head__button"
        aria-label={trackLabel}
        aria-pressed={tracked}
        title={trackLabel}
        disabled={pending}
        onClick={onToggleTracked}
      >
        <span className="event-head__dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
      </button>
    </header>
  );
}
