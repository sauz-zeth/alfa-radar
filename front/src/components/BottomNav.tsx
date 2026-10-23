import navFeedIcon from "../assets/icons/nav-feed.svg";
import navProfileIcon from "../assets/icons/nav-profile.svg";
import navSourcesIcon from "../assets/icons/nav-sources.svg";
import navTopicsIcon from "../assets/icons/nav-topics.svg";
import { Link, useRouter } from "../router";
import "./bottom-nav.css";

const items = [
  { id: "feed", label: "Лента", icon: navFeedIcon, to: "/" },
  { id: "topics", label: "Темы", icon: navTopicsIcon },
  { id: "sources", label: "Источники", icon: navSourcesIcon },
  { id: "profile", label: "Профиль", icon: navProfileIcon, to: "/profile" },
];

export function BottomNav() {
  const { path } = useRouter();

  return (
    <nav className="bottom-nav" aria-label="Основная навигация">
      <div className="bottom-nav__capsule">
        {items.map((item) => {
          const isActive = item.to === path;
          const className = isActive ? "bottom-nav__item is-active" : "bottom-nav__item";
          const content = <img src={item.icon} alt="" className="bottom-nav__icon" />;

          if (!item.to) {
            return (
              <button key={item.id} type="button" className={className} aria-label={item.label} aria-disabled="true">
                {content}
              </button>
            );
          }

          return (
            <Link key={item.id} to={item.to} className={className} aria-label={item.label} aria-current={isActive ? "page" : undefined}>
              {content}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
