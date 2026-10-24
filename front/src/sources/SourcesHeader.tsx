import searchIcon from "../assets/icons/search.svg";

export type SourcesTab = "channels" | "catalog";

type SourcesHeaderProps = {
  tab: SourcesTab;
  channelCount: number;
  catalogCount: number;
  onTabChange: (tab: SourcesTab) => void;
  variant?: "mobile" | "desktop";
  subtitle?: string;
  query?: string;
  onQueryChange?: (query: string) => void;
};

export function SourcesHeader({
  tab,
  channelCount,
  catalogCount,
  onTabChange,
  variant = "mobile",
  subtitle,
  query,
  onQueryChange,
}: SourcesHeaderProps) {
  if (variant === "desktop") {
    return (
      <header className="sources-head sources-head--desktop">
        <div className="sources-head__titles">
          <h1>Источники</h1>
          {subtitle ? <p className="sources-head__subtitle">{subtitle}</p> : null}
        </div>
        <label className="sources-head__search">
          <input
            value={query ?? ""}
            onChange={(event) => onQueryChange?.(event.target.value)}
            onFocus={() => onTabChange("catalog")}
            placeholder="Найти канал или вставить ссылку"
            aria-label="Найти канал или вставить ссылку"
          />
        </label>
      </header>
    );
  }

  return (
    <>
      <header className="sources-head">
        <h1>Источники</h1>
        <button
          type="button"
          className="sources-search-button"
          aria-label="Найти канал"
          onClick={() => onTabChange("catalog")}
        >
          <img src={searchIcon} alt="" width={18} height={18} />
        </button>
      </header>

      <div className="sources-tabs" role="tablist" aria-label="Источники">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "channels"}
          className={tab === "channels" ? "sources-tab is-active" : "sources-tab"}
          onClick={() => onTabChange("channels")}
        >
          Каналы
          <span className="sources-tab__count">{channelCount}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "catalog"}
          className={tab === "catalog" ? "sources-tab is-active" : "sources-tab"}
          onClick={() => onTabChange("catalog")}
        >
          Каталог
          <span className="sources-tab__count">{catalogCount}</span>
        </button>
      </div>
    </>
  );
}
