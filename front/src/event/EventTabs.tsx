import { useEffect, useRef } from "react";
import arrowUpRight from "../assets/icons/arrow-up-right.svg";

export const EVENT_TABS = [
  "Разбор",
  "Влияние",
  "Сценарии",
  "Действия",
  "Ход анализа",
  "Чат",
] as const;

export type EventTab = (typeof EVENT_TABS)[number];

type EventTabsProps = {
  active: EventTab;
  onChange: (tab: EventTab) => void;
  onAllStories?: () => void;
};

export function EventTabs({ active, onChange, onAllStories }: EventTabsProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const activeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const list = listRef.current;
    const tab = activeRef.current;
    if (!list || !tab) return;
    const left = tab.offsetLeft - (list.clientWidth - tab.clientWidth) / 2;
    list.scrollTo({ left: Math.max(0, left), behavior: "smooth" });
  }, [active]);

  return (
    <div ref={listRef} className="event-tabs" role="tablist" aria-label="Разделы разбора">
      {EVENT_TABS.map((tab) => (
        <button
          key={tab}
          ref={tab === active ? activeRef : undefined}
          type="button"
          role="tab"
          aria-selected={tab === active}
          className={tab === active ? "event-tabs__tab is-active" : "event-tabs__tab"}
          onClick={() => onChange(tab)}
        >
          {tab}
        </button>
      ))}
      {onAllStories ? (
        <button type="button" className="event-tabs__all" onClick={onAllStories}>
          Все истории
          <img src={arrowUpRight} alt="" width={12} height={12} />
        </button>
      ) : null}
    </div>
  );
}
