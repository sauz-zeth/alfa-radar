import { useMemo, useState } from "react";
import { ApiError, useApi, useApiQuery } from "../api";
import { useAuth } from "../auth/useAuth";
import { useRouter } from "../router";
import { formatMoney, formatShare, formatWeight } from "../onboarding/format";
import "./profile.css";

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase() ?? "")
      .join("") || "А"
  );
}

export default function Profile() {
  const api = useApi();
  const { signOut } = useAuth();
  const { navigate } = useRouter();
  const [tab, setTab] = useState<"categories" | "counterparties">("categories");

  const profile = useApiQuery({
    queryKey: ["profile"],
    queryFn: (signal) => api.profile.get({ signal }),
  });

  const data = profile.data;
  const categories = useMemo(
    () => [...(data?.categories ?? [])].sort((a, b) => b.weight - a.weight).slice(0, 10),
    [data?.categories],
  );
  const directions = ["supplier", "buyer"] as const;

  if (profile.isPending) {
    return (
      <div className="profile-state">
        <p>Загружаем профиль…</p>
      </div>
    );
  }

  if (profile.isError || !data) {
    return (
      <div className="profile-state">
        <p>{profile.error instanceof ApiError ? profile.error.detail : "Не удалось загрузить профиль"}</p>
        <button type="button" className="button button--ghost" onClick={() => profile.refetch()}>
          Повторить
        </button>
      </div>
    );
  }

  const { profile: info, stats, counterparties } = data;
  const company = info.company;
  const meta = [stats.industry ?? company?.main_okved_name, stats.city ?? company?.city]
    .filter(Boolean)
    .join(" · ");

  const statsItems = [
    { label: "Выручка", value: stats.revenue_label || formatMoney(stats.revenue) },
    { label: "Сотрудники", value: stats.employees ?? "—" },
    { label: "Возраст", value: stats.age ?? "—" },
    { label: "ВЭД", value: stats.foreign_trade_country ?? "—" },
  ];

  return (
    <div className="profile-page">
      <header className="profile-header">
        <span className="profile-avatar" aria-hidden="true">
          {initials(info.entrepreneur_name)}
        </span>
        <div className="profile-identity">
          <p className="profile-name">{info.entrepreneur_name}</p>
          <p className="profile-business">{info.business_name}</p>
          <p className="profile-meta">
            {meta}
            {info.role_label ? ` · ${info.role_label}` : ""}
          </p>
        </div>
      </header>

      <div className="profile-stats">
        {statsItems.map((item) => (
          <div key={item.label} className="profile-stat">
            <span className="profile-stat__label">{item.label}</span>
            <span className="profile-stat__value">{item.value}</span>
          </div>
        ))}
      </div>

      <button
        type="button"
        className="profile-logout"
        onClick={() => {
          signOut();
          navigate("/login", { replace: true });
        }}
      >
        Выйти
      </button>

      <div className="profile-tabs" role="tablist" aria-label="Профиль бизнеса">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "categories"}
          className={tab === "categories" ? "profile-tab is-active" : "profile-tab"}
          onClick={() => setTab("categories")}
        >
          Категории
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "counterparties"}
          className={tab === "counterparties" ? "profile-tab is-active" : "profile-tab"}
          onClick={() => setTab("counterparties")}
        >
          Контрагенты
        </button>
      </div>

      {tab === "categories" ? (
        <section className="profile-list">
          <p className="profile-hint">
            По этим категориям лента отбирает новости. Чем сильнее влияние, тем выше новость в ленте.
          </p>
          {categories.map((category) => (
            <div key={category.category_id} className="profile-category">
              <div className="profile-category__head">
                <span className="profile-category__name">{category.name}</span>
                <span className="profile-category__weight">{formatWeight(category.weight)}</span>
              </div>
              <div className="profile-category__bar" aria-hidden="true">
                <span style={{ width: `${Math.round(category.weight * 100)}%` }} />
              </div>
              {category.rationale ? <p className="profile-category__note">{category.rationale}</p> : null}
            </div>
          ))}
        </section>
      ) : (
        <section className="profile-list">
          {directions.map((direction) => {
            const group = counterparties.filter((item) => item.direction === direction);
            if (group.length === 0) return null;
            return (
              <div key={direction} className="profile-group">
                <h2 className="profile-group__title">
                  {direction === "supplier" ? "Поставщики" : "Покупатели"} · {group.length}
                </h2>
                {group.map((item) => (
                  <div key={item.id} className="profile-counterparty">
                    <div>
                      <p className="profile-counterparty__name">{item.display_name}</p>
                      <p className="profile-counterparty__note">{item.note}</p>
                    </div>
                    <span className="badge">
                      {formatMoney(item.total_amount)} · {formatShare(item.share)}
                    </span>
                  </div>
                ))}
              </div>
            );
          })}
          {counterparties.length === 0 ? (
            <p className="profile-hint">По этому бизнесу пока нет платёжных данных.</p>
          ) : null}
        </section>
      )}
    </div>
  );
}
