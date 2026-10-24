import lightFeedIcon from "../assets/icons/light/nav-feed.svg";
import lightProfileIcon from "../assets/icons/light/nav-profile.svg";
import lightSourcesIcon from "../assets/icons/light/nav-sources-active.svg";
import lightTopicsIcon from "../assets/icons/light/nav-topics.svg";
import { Link, useRouter } from "../router";
import "./bottom-nav.css";

const items = [
  { id: "feed", label: "Лента", icon: lightFeedIcon, to: "/" },
  { id: "topics", label: "Темы", icon: lightTopicsIcon, to: "/tracked" },
  { id: "sources", label: "Источники", icon: lightSourcesIcon, to: "/sources", compact: true },
  { id: "profile", label: "Профиль", icon: lightProfileIcon, to: "/profile" },
];

function isCurrent(path: string, to: string): boolean {
  return to === "/" ? path === "/" : path === to || path.startsWith(`${to}/`);
}

export function BottomNav() {
  const { path } = useRouter();

  if (path.startsWith("/event/")) return null;

  const theme = path === "/sources" || path.startsWith("/tracked") ? "light" : "dark";

  return (
    <nav className={`bottom-nav bottom-nav--${theme}`} aria-label="Основная навигация">
      <div className="bottom-nav__capsule">
        {items.map((item) => {
          const active = item.to ? isCurrent(path, item.to) : false;
          const className = active ? "bottom-nav__item is-active" : "bottom-nav__item";
          const iconClass =
            item.id === "sources"
              ? "bottom-nav__icon bottom-nav__icon--sources"
              : item.id === "topics"
                ? "bottom-nav__icon bottom-nav__icon--topics"
                : "bottom-nav__icon";
          const content = <img src={item.icon} alt="" className={iconClass} />;

          if (!item.to) {
            return (
              <button key={item.id} type="button" className={className} aria-label={item.label} aria-disabled="true">
                {content}
              </button>
            );
          }

          return (
            <Link
              key={item.id}
              to={item.to}
              className={className}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
            >
              {content}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
