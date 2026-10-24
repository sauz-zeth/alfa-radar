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

const GROUP_LABELS: Record<string, string> = {
  direct: "Прямое влияние",
  indirect: "Косвенное влияние",
  background: "Фоновое влияние",
  none: "Не влияют",
};

const GROUP_SHORT: Record<string, string> = {
  direct: "Прямое",
  indirect: "Косвенное",
  background: "Фоновое",
};

function splitMoney(label: string): [string, string] {
  const space = label.indexOf(" ");
  return space === -1 ? [label, ""] : [label.slice(0, space), label.slice(space + 1)];
}

type ReportingFormKey = "balance" | "income" | "cash_flow";

type ReportingForm = {
  label: string;
  filename: string;
  data: Record<string, unknown>;
};

type ParsedReporting = {
  period: string | null;
  keyPoints: string[];
  forms: Partial<Record<ReportingFormKey, ReportingForm>>;
};

const FORM_LABELS: Record<ReportingFormKey, string> = {
  balance: "Бухгалтерский баланс",
  income: "Отчёт о финансовых результатах",
  cash_flow: "Отчёт о движении денежных средств",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asStringList(value: unknown): string[] {
  return asArray(value).filter((item): item is string => typeof item === "string");
}

function parseForm(value: unknown, fallbackLabel: string): ReportingForm | null {
  if (!isRecord(value)) return null;
  return {
    label: asString(value.label) ?? fallbackLabel,
    filename: asString(value.filename) ?? "",
    data: isRecord(value.data) ? value.data : {},
  };
}

function parseReporting(reporting: Record<string, unknown>): ParsedReporting {
  const source = isRecord(reporting.forms) ? reporting.forms : {};
  const forms: Partial<Record<ReportingFormKey, ReportingForm>> = {};
  for (const key of ["balance", "income", "cash_flow"] as const) {
    const form = parseForm(source[key], FORM_LABELS[key]);
    if (form) forms[key] = form;
  }
  return {
    period: asString(reporting.period),
    keyPoints: asStringList(reporting.key_points),
    forms,
  };
}

function formFigures(data: Record<string, unknown>): { label: string; value: string }[] {
  const figures: { label: string; value: string }[] = [];
  const moneyFields: [string, string][] = [
    ["revenue", "Выручка"],
    ["profit", "Прибыль"],
    ["debt", "Долг"],
    ["interest_expense", "Процентные расходы"],
  ];
  for (const [key, label] of moneyFields) {
    const value = asNumber(data[key]);
    if (value !== null) figures.push({ label, value: formatMoney(value) });
  }

  if (isRecord(data.cash_flows)) {
    const flows: [string, string][] = [
      ["operating", "Операционный поток"],
      ["investing", "Инвестиционный поток"],
      ["financing", "Финансовый поток"],
    ];
    for (const [key, label] of flows) {
      const value = asNumber(data.cash_flows[key]);
      if (value !== null) figures.push({ label, value: formatMoney(value) });
    }
  }

  const positions = asArray(data.currency_positions);
  if (positions.length > 0) {
    const strings = asStringList(positions);
    figures.push({
      label: "Валютные позиции",
      value: strings.length === positions.length ? strings.join(", ") : String(positions.length),
    });
  }

  const costStructure = asArray(data.cost_structure);
  if (costStructure.length > 0) {
    figures.push({ label: "Структура затрат", value: String(costStructure.length) });
  }

  return figures;
}

function ReportingSummary({ reporting }: { reporting: Record<string, unknown> }) {
  const report = parseReporting(reporting);
  const hasContent =
    report.period !== null ||
    report.keyPoints.length > 0 ||
    Object.keys(report.forms).length > 0;

  if (!hasContent) {
    return (
      <div className="profile-reporting">
        <p className="profile-reporting__empty">Отчётность не загружена</p>
        <p className="profile-reporting__hint">
          Формы можно загрузить на шаге онбординга «Отчётность».
        </p>
      </div>
    );
  }

  return (
    <div className="profile-reporting">
      {report.period ? <p className="profile-reporting__period">Период: {report.period}</p> : null}

      {report.keyPoints.length > 0 ? (
        <ul className="profile-reporting__points">
          {report.keyPoints.map((point, index) => (
            <li key={`${index}-${point}`}>{point}</li>
          ))}
        </ul>
      ) : null}

      <div className="profile-reporting__cards">
        {(["balance", "income", "cash_flow"] as const).map((key) => {
          const form = report.forms[key];
          if (!form) {
            return (
              <article key={key} className="profile-reporting__card profile-reporting__card--empty">
                <p className="profile-reporting__form-title">{FORM_LABELS[key]}</p>
                <p className="profile-reporting__missing">не загружено</p>
              </article>
            );
          }
          const figures = formFigures(form.data);
          return (
            <article key={key} className="profile-reporting__card">
              <p className="profile-reporting__form-title">{form.label}</p>
              {form.filename ? (
                <p className="profile-reporting__filename">{form.filename}</p>
              ) : null}
              {figures.length > 0 ? (
                <dl className="profile-reporting__figures">
                  {figures.map((figure) => (
                    <div key={figure.label} className="profile-reporting__figure">
                      <dt>{figure.label}</dt>
                      <dd>{figure.value}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}
            </article>
          );
        })}
      </div>
    </div>
  );
}

export default function Profile() {
  const api = useApi();
  const { signOut } = useAuth();
  const { navigate } = useRouter();
  const [tab, setTab] = useState<"categories" | "counterparties" | "reporting">("categories");
  const [cpDirection, setCpDirection] = useState<"supplier" | "buyer">("supplier");

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
  const influenceGroups = useMemo(
    () => (data?.category_groups ?? []).filter((group) => group.key !== "none"),
    [data?.category_groups],
  );
  const noneGroup = data?.category_groups.find((group) => group.key === "none");

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

  const revenueText = stats.revenue_label || formatMoney(stats.revenue);
  const [revenueValue, revenueUnit] = splitMoney(revenueText);
  const industry = stats.industry ?? company?.main_okved_name;
  const city = stats.city ?? company?.city;
  const companyAge = [company?.org_type, stats.age].filter(Boolean).join(" · ");
  const rankedCounterparties = counterparties
    .filter((item) => item.direction === cpDirection)
    .sort((a, b) => b.share - a.share);

  return (
    <div className="profile-page">
      <div className="profile-mobile">
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
        <button
          type="button"
          role="tab"
          aria-selected={tab === "reporting"}
          className={tab === "reporting" ? "profile-tab is-active" : "profile-tab"}
          onClick={() => setTab("reporting")}
        >
          Отчётность
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
      ) : tab === "counterparties" ? (
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
      ) : (
        <section className="profile-list">
          <ReportingSummary reporting={data.reporting} />
        </section>
      )}
      </div>

      <div className="profile-desktop">
        <h1 className="profile-desktop__title">Профиль</h1>

        <div className="profile-desktop__grid">
          <aside className="profile-company">
            <div className="profile-user">
              <span className="profile-user__avatar" aria-hidden="true">
                {initials(info.entrepreneur_name)}
              </span>
              <span className="profile-user__name">{info.entrepreneur_name}</span>
            </div>

            <div className="profile-company__card">
              <div className="profile-company__body">
                {companyAge ? (
                  <div className="profile-company__meta">
                    <span>{companyAge}</span>
                    {stats.age ? <span className="profile-company__meta-muted">лет на рынке</span> : null}
                  </div>
                ) : null}
                <p className="profile-company__name">{info.business_name}</p>
                {industry ? <p className="profile-company__line">{industry}</p> : null}
                {city ? <p className="profile-company__line">{city}</p> : null}
              </div>
              <span className="profile-company__monogram" aria-hidden="true">
                {initials(info.business_name)}
              </span>
            </div>

            <div className="profile-money-row">
              <div className="profile-money profile-money--revenue">
                <span className="profile-money__label">Выручка</span>
                <span className="profile-money__amount">
                  <span className="profile-money__value">{revenueValue}</span>
                  {revenueUnit ? <span className="profile-money__unit">{revenueUnit}</span> : null}
                </span>
              </div>
              <div className="profile-money profile-money--scale">
                <div>
                  <span className="profile-money__label profile-money__label--muted">Сотрудники</span>
                  <p className="profile-money__big">{stats.employees ?? "—"}</p>
                </div>
                <div className="profile-money__row">
                  <span className="profile-money__label profile-money__label--muted">ВЭД</span>
                  <span className="profile-money__ved">{stats.foreign_trade_country ?? "—"}</span>
                </div>
              </div>
            </div>

            <div className="profile-switch">
              <div className="profile-switch__item">
                <span>Категории</span>
                <span className="profile-switch__count">{data.categories.length}</span>
              </div>
              <span className="profile-switch__item profile-switch__item--muted">Контрагенты</span>
            </div>

            <div className="profile-impact">
              {(["direct", "indirect", "background"] as const).map((key) => {
                const count = data.category_groups.find((group) => group.key === key)?.items.length ?? 0;
                return (
                  <div
                    key={key}
                    className={
                      key === "direct"
                        ? "profile-impact__tile profile-impact__tile--dark"
                        : "profile-impact__tile"
                    }
                  >
                    <span className="profile-impact__count">{count}</span>
                    <span className="profile-impact__label">{GROUP_SHORT[key]}</span>
                  </div>
                );
              })}
            </div>

            <p className="profile-note">Данные компании влияют на оценку новостей</p>

            <button
              type="button"
              className="profile-logout profile-logout--desktop"
              onClick={() => {
                signOut();
                navigate("/login", { replace: true });
              }}
            >
              Выйти
            </button>
          </aside>

          <section className="profile-categories">
            <h2 className="profile-section-title">Категории · {data.categories.length}</h2>
            <p className="profile-section-sub">Лента отбирает новости по силе влияния</p>

            <div className="profile-cat-grid">
              {influenceGroups.map((group) => (
                <section
                  key={group.key}
                  className={
                    group.key === "direct"
                      ? "profile-cat-card profile-cat-card--dark"
                      : "profile-cat-card"
                  }
                >
                  <h3 className="profile-cat-card__title">
                    {GROUP_LABELS[group.key] ?? group.name} · {group.items.length}
                  </h3>
                  {group.items.map((category) => (
                    <div
                      key={category.category_id}
                      className={
                        category.is_manual
                          ? "profile-cat__item profile-cat__item--manual"
                          : "profile-cat__item"
                      }
                    >
                      <p className="profile-cat__name">{category.short_name || category.name}</p>
                      {category.rationale ? (
                        <p className="profile-cat__note">{category.rationale}</p>
                      ) : null}
                    </div>
                  ))}
                </section>
              ))}
            </div>

            {noneGroup && noneGroup.items.length > 0 ? (
              <details className="profile-none">
                <summary className="profile-none__summary">
                  {GROUP_LABELS.none} · {noneGroup.items.length}
                </summary>
                <ul className="profile-none__list">
                  {noneGroup.items.map((category) => (
                    <li key={category.category_id}>{category.short_name || category.name}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </section>

          <aside className="profile-counterparties">
            <div className="profile-cp-panel">
              <h2 className="profile-section-title">Контрагенты</h2>
              <p className="profile-section-sub">По данным платежей</p>

              <div className="profile-cp-tabs" role="tablist" aria-label="Контрагенты">
                {directions.map((item) => {
                  const count = counterparties.filter((entry) => entry.direction === item).length;
                  return (
                    <button
                      key={item}
                      type="button"
                      role="tab"
                      aria-selected={cpDirection === item}
                      className={cpDirection === item ? "profile-cp-tab is-active" : "profile-cp-tab"}
                      onClick={() => setCpDirection(item)}
                    >
                      {item === "supplier" ? "Поставщики" : "Покупатели"} · {count}
                    </button>
                  );
                })}
              </div>

              {rankedCounterparties.length > 0 ? (
                <div className="profile-cp-list">
                  {rankedCounterparties.map((item) => (
                    <div key={item.id} className="profile-cp-row">
                      <div className="profile-cp-row__main">
                        <p className="profile-cp-row__name">{item.display_name}</p>
                        {item.note ? <p className="profile-cp-row__note">{item.note}</p> : null}
                      </div>
                      <span className="profile-cp-row__share">
                        {formatShare(item.share)} {cpDirection === "supplier" ? "закупок" : "продаж"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="profile-cp-empty">По этому бизнесу пока нет платёжных данных.</p>
              )}
            </div>
          </aside>
        </div>

        <section className="profile-reporting profile-reporting--desktop">
          <h2 className="profile-section-title">Отчётность</h2>
          <ReportingSummary reporting={data.reporting} />
        </section>
      </div>
    </div>
  );
}
