import type { CSSProperties } from "react";
import type { Channel } from "../api";
import { cardTilt, cardTone, channelInitials } from "./channelVisuals";

type ChannelCardProps = {
  channel: Channel;
  index: number;
  onToggle: (channel: Channel) => void;
  disabled?: boolean;
  variant?: "mobile" | "desktop";
};

export function ChannelCard({ channel, index, onToggle, disabled, variant = "mobile" }: ChannelCardProps) {
  const isDesktop = variant === "desktop";
  const meta = isDesktop
    ? `${channel.recommended ? "по профилю" : "свой"}${channel.topics ? ` · ${channel.topics}` : ""}`
    : channel.recommended
      ? "Профиль"
      : "Свой";

  return (
    <button
      type="button"
      className={isDesktop ? "channel-card channel-card--desktop" : "channel-card"}
      aria-pressed={channel.subscribed}
      disabled={disabled}
      onClick={() => onToggle(channel)}
    >
      <span className="channel-folder" data-tone={isDesktop ? "dark" : cardTone(index)}>
        <span
          className="channel-folder__avatar"
          style={{ "--tilt": `${isDesktop ? 10 : cardTilt(index)}deg` } as CSSProperties}
        >
          {channelInitials(channel.name)}
        </span>

        <span className="channel-folder__glass">
          <span className="channel-folder__rivet channel-folder__rivet--left" aria-hidden="true" />
          <span className="channel-folder__rivet channel-folder__rivet--right" aria-hidden="true" />
          <span className="channel-folder__check" aria-hidden="true">
            {channel.subscribed ? (
              <svg width="13.8" height="11.8" viewBox="0 0 13.8 11.8" fill="none">
                <path
                  d="M0.9 6.9L4.9 10.9L12.9 0.9"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M6.5 1V12M1 6.5H12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            )}
          </span>
        </span>
      </span>

      <span className="channel-card__info">
        <span className="channel-card__name">{channel.name}</span>
        <span className="channel-card__type">{meta}</span>
      </span>
    </button>
  );
}
