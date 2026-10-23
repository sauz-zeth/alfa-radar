type FeedFiltersProps = {
  filters: string[];
  active: string;
  onChange: (filter: string) => void;
};

export function FeedFilters({ filters, active, onChange }: FeedFiltersProps) {
  return (
    <div className="feed-filters" role="tablist" aria-label="Фильтры ленты">
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
