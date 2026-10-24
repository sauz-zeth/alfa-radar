import chevronDown from "../assets/icons/tracked/chevron-down.svg";
import { themesLabel, updatesLabel } from "./mapTracked";

type TrackedHeaderProps = {
  themeCount: number;
  updatesCount: number;
};

export function TrackedHeader({ themeCount, updatesCount }: TrackedHeaderProps) {
  return (
    <header className="tracked-head">
      <div className="tracked-head__title">
        <h1>Отслеживаемое</h1>
        <img src={chevronDown} alt="" width={20} height={20} />
      </div>
      <p className="tracked-head__meta">
        <span>{themesLabel(themeCount)}</span>
        <span>{updatesLabel(updatesCount)}</span>
      </p>
    </header>
  );
}
