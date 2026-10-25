import type { ReactNode } from "react";
import { useApi, useApiQuery } from "../api";
import { Link, useRouter } from "../router";
import { HeaderSearch } from "./HeaderSearch";
import "./desktop.css";

const NAV = [
  { label: "Лента", to: "/" },
  { label: "Поиск", to: "/search" },
  { label: "Отслеживаемое", to: "/tracked" },
  { label: "Источники", to: "/sources" },
  { label: "Профиль", to: "/profile" },
  { label: "Скрытые", to: "/hidden" },
];

function isCurrent(path: string, to: string): boolean {
  return to === "/" ? path === "/" : path === to || path.startsWith(`${to}/`);
}

export function DesktopShell({ children }: { children: ReactNode }) {
  const { path, navigate } = useRouter();
  const api = useApi();
  const profile = useApiQuery({
    queryKey: ["profile"],
    queryFn: (signal) => api.profile.get({ signal }),
  });
  const name = profile.data?.profile.entrepreneur_name ?? "";
  const role = profile.data?.profile.role_label ?? "";
  const company = profile.data?.profile.business_name ?? "";
  const avatar = name
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();

  return (
    <div className="desktop-shell">
      <header className="desktop-topbar">
        <Link to="/" className="desktop-topbar__brand">
          <span className="desktop-topbar__logo">a</span>
          <span>Лента новостей</span>
        </Link>
        <nav className="desktop-topbar__nav" aria-label="Основная навигация">
          {NAV.map((item) => {
            const active = isCurrent(path, item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={active ? "desktop-topbar__link is-active" : "desktop-topbar__link"}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        {path === "/search" ? null : <HeaderSearch />}
        <div className="desktop-topbar__user">
          <span className="desktop-topbar__avatar">{avatar}</span>
          <span>
            {name ? <strong>{name}</strong> : null}
            {role || company ? <small>{role || company}</small> : null}
          </span>
        </div>
      </header>

      <div className="desktop-body">
        <aside className="desktop-tools" aria-label="Инструменты">
          <button
            type="button"
            className="desktop-tools__button"
            aria-label="Поиск"
            onClick={() => navigate("/search")}
          >
            <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
              <circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <path d="M12.5 12.5 16 16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </button>
          <button type="button" className="desktop-tools__button is-active" aria-label="Лента">
            <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
              <rect x="2" y="2" width="5.5" height="5.5" rx="1.5" fill="currentColor" />
              <rect x="10.5" y="2" width="5.5" height="5.5" rx="1.5" fill="currentColor" />
              <rect x="2" y="10.5" width="5.5" height="5.5" rx="1.5" fill="currentColor" />
              <rect x="10.5" y="10.5" width="5.5" height="5.5" rx="1.5" fill="currentColor" />
            </svg>
          </button>
          <button type="button" className="desktop-tools__button" aria-label="Чаты">
            <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
              <path
                d="M3 3.5h12v8H8l-3.5 3v-3H3z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          <button type="button" className="desktop-tools__button" aria-label="Метки">
            <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
              <path
                d="M2.5 2.5h5.5l7 7-5.5 5.5-7-7z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <circle cx="6" cy="6" r="1" fill="currentColor" />
            </svg>
          </button>
        </aside>

        <main className="desktop-main">{children}</main>
      </div>
    </div>
  );
}
