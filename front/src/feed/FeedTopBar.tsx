import hiddenIcon from "../assets/icons/hidden.svg";
import searchIcon from "../assets/icons/search.svg";
import { FeedFilters } from "./FeedFilters";

type FeedTopBarProps = {
  hiddenCount: number;
  feedCount: number;
  filters: string[];
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  onOpenHidden: () => void;
  onSearch: () => void;
  hideFilters?: boolean;
};

export function FeedTopBar({
  hiddenCount,
  feedCount,
  filters,
  activeFilter,
  onFilterChange,
  onOpenHidden,
  onSearch,
  hideFilters = false,
}: FeedTopBarProps) {
  return (
    <header className="feed-topbar">
      <div className="feed-topbar__scrim" aria-hidden="true" />
      <div className="feed-topbar__panel">
        <div className="feed-topbar__row">
          <button
            type="button"
            className="hidden-badge"
            aria-label={`Скрытые новости: ${hiddenCount}`}
            onClick={onOpenHidden}
          >
            <img src={hiddenIcon} alt="" width={14} height={14} />
            <span>{hiddenCount}</span>
          </button>

          <h1 className="feed-title">
            Лента
            <span className="feed-title__count">{feedCount}</span>
          </h1>

          <button type="button" className="icon-button" aria-label="Поиск по новостям и компаниям" onClick={onSearch}>
            <img src={searchIcon} alt="" width={18} height={18} />
          </button>
        </div>

        {hideFilters ? null : (
          <FeedFilters filters={filters} active={activeFilter} onChange={onFilterChange} />
        )}
      </div>
    </header>
  );
}
