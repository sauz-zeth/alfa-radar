import type { Channel } from "../api";

export const channelTones = ["dark", "red", "light"] as const;

export type ChannelTone = (typeof channelTones)[number];

// Порядок тонов и наклонов как в макете: обложки в подборке не должны повторяться.
export const cardToneSequence: ChannelTone[] = ["dark", "light", "dark", "red", "light", "dark", "red"];
export const cardTiltSequence = [12, -8, 10, -12, -10, 8, -12];

export function channelInitials(name: string): string {
  return (
    name
      .split(/[\s.:-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase() ?? "")
      .join("") || "•"
  );
}

export function channelTone(channel: Channel): ChannelTone {
  let hash = 0;
  for (const char of channel.id) hash = (hash * 31 + char.charCodeAt(0)) % 997;
  return channelTones[hash % channelTones.length]!;
}

export function cardTone(index: number): ChannelTone {
  return cardToneSequence[index % cardToneSequence.length]!;
}

export function cardTilt(index: number): number {
  return cardTiltSequence[index % cardTiltSequence.length]!;
}

export function formatSubscribers(count: number): string {
  if (count >= 1_000_000) {
    return `${(count / 1_000_000).toFixed(1).replace(".", ",")} млн`;
  }
  if (count >= 1_000) {
    return `${Math.round(count / 1_000)} тыс.`;
  }
  return String(count);
}
