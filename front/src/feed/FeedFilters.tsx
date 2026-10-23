import { useCallback, useEffect, useRef, useState } from "react";

type FeedFiltersProps = {
  filters: string[];
  active: string;
  onChange: (filter: string) => void;
};

export function FeedFilters({ filters, active, onChange }: FeedFiltersProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [fade, setFade] = useState({ left: false, right: true });

  const updateFade = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const left = el.scrollLeft > 1;
    const right = el.scrollLeft + el.clientWidth < el.scrollWidth - 1;
    setFade((current) =>
      current.left === left && current.right === right ? current : { left, right },
    );
  }, []);

  useEffect(() => {
    updateFade();
  }, [filters, active, updateFade]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    updateFade();
    el.addEventListener("scroll", updateFade, { passive: true });
    const observer = new ResizeObserver(updateFade);
    observer.observe(el);
    return () => {
      el.removeEventListener("scroll", updateFade);
      observer.disconnect();
    };
  }, [updateFade]);

  const className = [
    "feed-filters",
    fade.left ? "is-fade-left" : "",
    fade.right ? "is-fade-right" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div ref={scrollerRef} className={className} role="tablist" aria-label="Фильтры ленты">
      {filters.map((filter) => (
        <button
          key={filter}
          type="button"
          role="tab"
          aria-selected={filter === active}
          className={filter === active ? "feed-filter is-active" : "feed-filter"}
          onClick={() => onChange(filter)}
        >
          {filter}
        </button>
      ))}
    </div>
  );
}
