import { useEffect, useRef, useState } from "react";

type EventHeaderProps = {
  onBack: () => void;
  tracked: boolean;
  pending?: boolean;
  onToggleTracked: () => void;
  onShare: () => void;
};

export function EventHeader({
  onBack,
  tracked,
  pending,
  onToggleTracked,
  onShare,
}: EventHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;

    const closeOnOutside = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };

    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [menuOpen]);

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
        <span className="event-head__back-text">Назад</span>
      </button>

      <span className="event-head__title">История темы</span>

      <div className="event-head__menu-wrap" ref={menuRef}>
        <button
          type="button"
          className="event-head__button"
          aria-label="Действия с историей"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          title="Действия с историей"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="event-head__dots" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
        </button>

        {menuOpen ? (
          <div className="event-head__menu" role="menu">
            <button
              type="button"
              className="event-head__menu-item"
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                onShare();
              }}
            >
              Переслать историю
            </button>
            <button
              type="button"
              className="event-head__menu-item"
              role="menuitem"
              disabled={pending}
              onClick={() => {
                setMenuOpen(false);
                onToggleTracked();
              }}
            >
              {tracked ? "Не отслеживать" : "Отслеживать"}
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
