import type { ImpactTile } from "../api";

type ImpactTilesProps = {
  tiles: ImpactTile[];
};

export function ImpactTiles({ tiles }: ImpactTilesProps) {
  if (tiles.length === 0) return null;

  return (
    <div className="event-tiles">
      {tiles.map((tile, index) => {
        const full = tile.type === "statement" || tile.span === "full";
        const className = [
          "event-tile",
          `event-tile--${tile.type}`,
          full ? "event-tile--full" : null,
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <article key={`${tile.type}-${index}`} className={className}>
            {tile.value ? <p className="event-tile__value">{tile.value}</p> : null}
            <p className="event-tile__label">{tile.label}</p>
            {tile.note ? <p className="event-tile__note">{tile.note}</p> : null}
          </article>
        );
      })}
    </div>
  );
}
