import type { FeedItemDetail } from "../api";
import { ActionsTab } from "./ActionsTab";
import { AnalysisTab } from "./AnalysisTab";
import { ChatTab, type ChatStreamMessage } from "./ChatTab";
import type { EventModel } from "./eventModel";
import type { EventTab } from "./EventTabs";
import { InfluenceTab } from "./InfluenceTab";
import { ScenariosTab } from "./ScenariosTab";

type EventTabContentProps = {
  tab: Exclude<EventTab, "Разбор">;
  detail: FeedItemDetail;
  event: EventModel;
  onAsk: (text: string) => void;
  onAskFocus: () => void;
  streams: ChatStreamMessage[];
};

export function EventTabContent({
  tab,
  detail,
  event,
  onAsk,
  onAskFocus,
  streams,
}: EventTabContentProps) {
  if (tab === "Влияние") {
    return <InfluenceTab detail={detail} />;
  }

  if (tab === "Сценарии") {
    return <ScenariosTab detail={detail} event={event} onAskFocus={onAskFocus} />;
  }

  if (tab === "Действия") {
    return <ActionsTab detail={detail} />;
  }

  if (tab === "Ход анализа") {
    return <AnalysisTab detail={detail} />;
  }

  return <ChatTab detail={detail} streams={streams} onAsk={onAsk} />;
}
