import type { RefObject } from "react";

type AskBarProps = {
  inputRef: RefObject<HTMLInputElement | null>;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function AskBar({ inputRef, value, onChange, onSubmit }: AskBarProps) {
  return (
    <form
      className="event-ask"
      onSubmit={(event) => {
        event.preventDefault();
        if (value.trim()) onSubmit();
      }}
    >
      <input
        ref={inputRef}
        className="event-ask__input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Спросить про эту историю"
        aria-label="Спросить про эту историю"
      />
      <button type="submit" className="event-ask__submit" disabled={!value.trim()}>
        <svg viewBox="0 0 13.7 13.7" width="14" height="14" aria-hidden="true">
          <path
            d="M6.85 12.85V0.85M12.85 6.85 6.85 0.85 0.85 6.85"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </form>
  );
}
