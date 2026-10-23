import searchIcon from "../assets/icons/search.svg";

export type SourcesTab = "channels" | "catalog";

type SourcesHeaderProps = {
  tab: SourcesTab;
  channelCount: number;
  catalogCount: number;
  onTabChange: (tab: SourcesTab) => void;
};

export function SourcesHeader({ tab, channelCount, catalogCount, onTabChange }: SourcesHeaderProps) {
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
