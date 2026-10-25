import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ApiError,
  useApi,
  useApiMutation,
  useApiQuery,
  useQueryClient,
  type Counterparty,
} from "../api";
import { useAuth } from "../auth/useAuth";
import { Link, useRouter } from "../router";
import { pluralRu } from "../lib/plural";
import { formatMoney, formatShare } from "../onboarding/format";
import profilePencilIcon from "../assets/icons/profile-edit.svg";
import "./profile.css";
import "../profile/mobile.css";
import "../profile/desktop.css";

function initials(name: string): string {
  const words = name
    .split(/\s+/)
    .filter(Boolean)
    .filter((word) => /[A-Za-zА-Яа-яЁё]/.test(word[0] ?? ""));

  if (words.length > 1) {
    return words
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase() ?? "")
      .join("");
  }

  const word = words[0] ?? name.trim();
  if (!word) return "А";
  const parts = word.match(/[A-ZА-ЯЁ][a-zа-яё]+/g) ?? [];
  if (parts.length > 1) {
    return parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("");
  }
  return word[0]?.toUpperCase() ?? "А";
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

const REPORT_FORMS = [
  { key: "balance", label: "Бухгалтерский баланс" },
  { key: "income", label: "Отчёт о финансовых результатах" },
  { key: "cash_flow", label: "Отчёт о движении денежных средств" },
] as const;

type ReportForm = {
  key: (typeof REPORT_FORMS)[number]["key"];
  label: string;
  filename: string;
};

type CategoryTone = "light" | "dark" | "accent";

const TONE_SEQUENCE: Record<string, CategoryTone[]> = {
  direct: ["dark", "light", "light", "dark", "accent", "light"],
  indirect: ["light", "dark", "light", "accent", "light", "dark"],
  background: ["dark", "light", "light", "accent", "light", "dark"],
};

function toneFor(groupKey: string, index: number): CategoryTone {
  const sequence = TONE_SEQUENCE[groupKey] ?? ["light", "dark", "light", "accent"];
  return sequence[index % sequence.length] ?? "light";
}

function desktopToneFor(groupKey: string, index: number): CategoryTone {
  if (groupKey === "direct") return index === 0 ? "dark" : "light";
  if (groupKey === "indirect") {
    if (index === 1) return "dark";
    if (index === 3) return "accent";
    return "light";
  }
  return "light";
}

function splitMoney(label: string): [string, string] {
  const space = label.indexOf(" ");
  return space === -1 ? [label, ""] : [label.slice(0, space), label.slice(space + 1)];
}

function displayBusinessName(name: string): string {
  return (
    name
      .replace(/^(ООО|АО|ПАО|ЗАО|ОАО|НАО|ИП)\s+/i, "")
      .replace(/[«»"]/g, "")
      .trim() || name
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function reportingForms(reporting: Record<string, unknown>): ReportForm[] {
  const forms = asRecord(reporting.forms);
  if (!forms) return [];

  return REPORT_FORMS.flatMap(({ key, label }) => {
    const entry = asRecord(forms[key]);
    if (!entry) return [];
    const filename =
      typeof entry.filename === "string" && entry.filename.trim()
        ? entry.filename.trim()
        : label;
    return [{ key, label, filename }];
  });
}

function shareLabel(item: Counterparty, direction: "supplier" | "buyer"): string {
  if (!item.share) return "Доля не указана";
  return `${formatShare(item.share)} ${direction === "supplier" ? "закупок" : "выручки"}`;
}

export default function Profile() {
  const api = useApi();
  const queryClient = useQueryClient();
  const { signOut } = useAuth();
  const { navigate } = useRouter();
  const [tab, setTab] = useState<"categories" | "counterparties">("categories");
  const [cpDirection, setCpDirection] = useState<"supplier" | "buyer">("supplier");
  const [cpExpanded, setCpExpanded] = useState(false);
  const [noneOpen, setNoneOpen] = useState(false);
  const [editing, setEditing] = useState<Counterparty | null>(null);
  const [draft, setDraft] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const profile = useApiQuery({
    queryKey: ["profile"],
    queryFn: (signal) => api.profile.get({ signal }),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const rename = useApiMutation<Counterparty[], { id: string; name: string }>({
    mutationFn: ({ id, name }) => api.profile.renameCounterparty(id, { name }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
      setEditing(null);
      setFormError(null);
    },
  });

  useEffect(() => {
    if (!editing) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setEditing(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editing]);

  const data = profile.data;
  const influenceGroups = useMemo(
    () => (data?.category_groups ?? []).filter((group) => group.key !== "none"),
    [data?.category_groups],
  );
  const noneGroup = data?.category_groups.find((group) => group.key === "none");
  const directions = ["supplier", "buyer"] as const;

  const handleSignOut = () => {
    signOut();
    navigate("/login", { replace: true });
  };

  const openEdit = (item: Counterparty) => {
    setEditing(item);
    setDraft(item.custom_name?.trim() || item.display_name);
    setFormError(null);
    rename.reset();
  };

  const closeEdit = () => {
    if (rename.isPending) return;
    setEditing(null);
    setFormError(null);
    rename.reset();
  };

  const submitRename = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editing) return;
    const name = draft.trim();
    if (!name) {
      setFormError("Введите название");
      return;
    }
    setFormError(null);
    rename.mutate({ id: editing.id, name });
  };

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
  const revenueText = stats.revenue_label || formatMoney(stats.revenue);
  const [revenueValue, revenueUnit] = splitMoney(revenueText);
  const industry = stats.industry ?? company?.main_okved_name;
  const city = stats.city ?? company?.city;
  const companyAge = [company?.org_type, stats.age].filter(Boolean).join(" · ");
  const desktopCompanyMeta = [company?.org_type, stats.age ? `${stats.age} лет на рынке` : null]
    .filter(Boolean)
    .join(" · ");
  const businessDisplayName = displayBusinessName(info.business_name);
  const rankedCounterparties = counterparties
    .filter((item) => item.direction === cpDirection)
    .sort((a, b) => b.share - a.share);
  const previewCount = 9;
  const visibleCounterparties = cpExpanded
    ? rankedCounterparties
    : rankedCounterparties.slice(0, previewCount);
  const hiddenCounterparties = rankedCounterparties.slice(previewCount);
  const hiddenShare = hiddenCounterparties.reduce((total, item) => total + item.share, 0);
  const desktopPreviewCount = 10;
  const desktopVisibleCounterparties = cpExpanded
    ? rankedCounterparties
    : rankedCounterparties.slice(0, desktopPreviewCount);
  const desktopHiddenCounterparties = rankedCounterparties.slice(desktopPreviewCount);
  const desktopHiddenShare = desktopHiddenCounterparties.reduce(
    (total, item) => total + item.share,
    0,
  );
  const counterpartyNoun: [string, string, string] =
    cpDirection === "supplier"
      ? ["поставщик", "поставщика", "поставщиков"]
      : ["покупатель", "покупателя", "покупателей"];
  const reportForms = reportingForms(data.reporting);
  const renameError = rename.isError
    ? rename.error instanceof ApiError
      ? rename.error.detail
      : "Не удалось сохранить название"
    : null;
  const sheetError = formError ?? renameError;
  const hasCategories = influenceGroups.some((group) => group.items.length > 0);

  return (
    <div className="profile-page">
      <div className="profile-mobile">
        <div className="profile-mobile-user">
          <div className="profile-mobile-user__id">
            <span className="profile-mobile-user__avatar" aria-hidden="true">
              {initials(info.entrepreneur_name)}
            </span>
            <span className="profile-mobile-user__name">{info.entrepreneur_name}</span>
          </div>
          <button type="button" className="profile-mobile-user__logout" onClick={handleSignOut}>
            Выйти
          </button>
        </div>

        <div className="profile-overview">
          <div className="profile-company-mobile">
            <div className="profile-company-mobile__card">
              <div className="profile-company-mobile__body">
                {companyAge ? (
                  <p className="profile-company-mobile__meta">
                    {company?.org_type ? <span>{company.org_type}</span> : null}
                    {stats.age ? (
                      <>
                        <span>{stats.age}</span>
                        <span className="profile-company-mobile__meta-muted">лет на рынке</span>
                      </>
                    ) : null}
                  </p>
                ) : null}
                <h1 className="profile-company-mobile__name">{businessDisplayName}</h1>
                {industry ? <p className="profile-company-mobile__line">{industry}</p> : null}
                {city ? <p className="profile-company-mobile__line">{city}</p> : null}
              </div>
              <span className="profile-company-mobile__monogram" aria-hidden="true">
                {initials(businessDisplayName)
                  .split("")
                  .map((letter, index) => (
                    <span key={`${letter}-${index}`} className={index === 1 ? "is-accent" : undefined}>
                      {letter}
                    </span>
                  ))}
              </span>
            </div>

            <div className="profile-metrics">
              <div className="profile-revenue">
                <span className="profile-revenue__label">Выручка</span>
                <p className="profile-revenue__amount">
                  <span className="profile-revenue__value">{revenueValue}</span>
                  {revenueUnit ? <span className="profile-revenue__unit">{revenueUnit}</span> : null}
                </p>
              </div>
              <div className="profile-scale">
                <div className="profile-scale__team">
                  <span className="profile-scale__label">Сотрудники</span>
                  <p className="profile-scale__value">{stats.employees ?? "—"}</p>
                </div>
                <div className="profile-scale__ved">
                  <span className="profile-scale__label profile-scale__label--small">ВЭД</span>
                  <span className="profile-scale__country">{stats.foreign_trade_country ?? "—"}</span>
                </div>
              </div>
            </div>
          </div>

          <section className="profile-summary" aria-labelledby="profile-summary-title">
            <div className="profile-summary__head">
              <h2 id="profile-summary-title" className="profile-summary__title">
                Саммари отчётов
              </h2>
              <span
                className="profile-summary__badge"
                aria-label={`Загружено файлов: ${reportForms.length}`}
              >
                {reportForms.length}
              </span>
            </div>
            {reportForms.length > 0 ? (
              <ul className="profile-summary__list">
                {reportForms.map((form) => (
                  <li key={form.key}>
                    <Link
                      to={`/profile/reports/${form.key}`}
                      className="profile-summary__link"
                      aria-label={`${form.label}: ${form.filename}`}
                    >
                      <span className="profile-summary__file">{form.filename}</span>
                      <span className="profile-summary__arrow" aria-hidden="true">
                        ↗
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="profile-summary__empty">Отчёты не загружены</p>
            )}
          </section>
        </div>

        <div className="profile-tabs" role="tablist" aria-label="Профиль бизнеса">
          <button
            id="profile-tab-categories"
            type="button"
            role="tab"
            aria-selected={tab === "categories"}
            aria-controls="profile-panel-categories"
            className={tab === "categories" ? "profile-tab is-active" : "profile-tab"}
            onClick={() => setTab("categories")}
          >
            <span className="profile-tab__label">Категории</span>
            <span className="profile-tab__count">{data.categories.length}</span>
          </button>
          <button
            id="profile-tab-counterparties"
            type="button"
            role="tab"
            aria-selected={tab === "counterparties"}
            aria-controls="profile-panel-counterparties"
            className={tab === "counterparties" ? "profile-tab is-active" : "profile-tab"}
            onClick={() => setTab("counterparties")}
          >
            <span className="profile-tab__label">Контрагенты</span>
            <span className="profile-tab__count">{counterparties.length}</span>
          </button>
        </div>

        {tab === "categories" ? (
          <div
            id="profile-panel-categories"
            role="tabpanel"
            aria-labelledby="profile-tab-categories"
            className="profile-tabpanel"
          >
            <div className="profile-impact-tiles">
              {(["direct", "indirect", "background"] as const).map((key) => {
                const group = data.category_groups.find((item) => item.key === key);
                const count = group?.items.length ?? 0;
                return (
                  <div
                    key={key}
                    className={
                      key === "direct"
                        ? "profile-impact-tile profile-impact-tile--dark"
                        : "profile-impact-tile"
                    }
                  >
                    <div className="profile-impact-tile__top">
                      <span className="profile-impact-tile__count">{count}</span>
                      <span className="profile-impact-tile__dots" aria-hidden="true">
                        {Array.from({ length: 6 }).map((_, index) => (
                          <i key={index} className={index < count ? "is-on" : undefined} />
                        ))}
                      </span>
                    </div>
                    <span className="profile-impact-tile__label">{GROUP_SHORT[key]}</span>
                  </div>
                );
              })}
            </div>

            {hasCategories ? (
              <div className="profile-cat-sections">
                {influenceGroups
                  .filter((group) => group.items.length > 0)
                  .map((group) => (
                    <section
                      key={group.key}
                      className="profile-cat-section"
                      aria-labelledby={`profile-cat-${group.key}`}
                    >
                      <header className="profile-cat-section__head">
                        <h3 id={`profile-cat-${group.key}`} className="profile-cat-section__title">
                          {GROUP_LABELS[group.key] ?? group.name}
                        </h3>
                        <span className="profile-cat-section__count">{group.items.length}</span>
                      </header>
                      <div className="profile-cat-grid-mobile">
                        {group.items.map((category, index) => {
                          const tone = toneFor(group.key, index);
                          const visual = index === 0 && group.key !== "background";
                          const wide =
                            category.name.length > 28 || (category.rationale?.length ?? 0) > 60;
                          const weight = Math.max(0, Math.min(100, Math.round(category.weight * 100)));
                          const className = [
                            "profile-cat-card",
                            `profile-cat-card--${tone}`,
                            wide ? "profile-cat-card--wide" : "",
                            visual ? "profile-cat-card--visual" : "",
                          ]
                            .filter(Boolean)
                            .join(" ");

                          return (
                            <article key={category.category_id} className={className}>
                              {visual ? (
                                <div className="profile-motif" aria-hidden="true">
                                  <span className="profile-motif__value">
                                    {weight}
                                    <span className="profile-motif__percent">%</span>
                                  </span>
                                  <span className="profile-dotbar">
                                    {Array.from({ length: 10 }).map((_, dot) => (
                                      <i
                                        key={dot}
                                        className={dot < Math.round(weight / 10) ? "is-on" : undefined}
                                      />
                                    ))}
                                  </span>
                                </div>
                              ) : null}
                              <p className="profile-cat-card__name">{category.name}</p>
                              {category.rationale ? (
                                <p className="profile-cat-card__note">{category.rationale}</p>
                              ) : null}
                            </article>
                          );
                        })}
                      </div>
                    </section>
                  ))}
              </div>
            ) : (
              <p className="profile-mobile-empty">По этому бизнесу пока нет категорий.</p>
            )}

            {noneGroup && noneGroup.items.length > 0 ? (
              <div className="profile-none-mobile">
                <button
                  type="button"
                  className="profile-none-mobile__toggle"
                  aria-expanded={noneOpen}
                  aria-controls="profile-none-list"
                  onClick={() => setNoneOpen((value) => !value)}
                >
                  <span>{GROUP_LABELS.none}</span>
                  <span className="profile-none-mobile__count">{noneGroup.items.length}</span>
                </button>
                <ul
                  id="profile-none-list"
                  className="profile-none-mobile__list"
                  hidden={!noneOpen}
                >
                  {noneGroup.items.map((category) => (
                    <li key={category.category_id}>{category.short_name || category.name}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : (
          <div
            id="profile-panel-counterparties"
            role="tabpanel"
            aria-labelledby="profile-tab-counterparties"
            className="profile-tabpanel"
          >
            <section className="profile-cp-card" aria-label="Контрагенты">
              <div className="profile-cp-tabs-mobile" role="tablist" aria-label="Направление контрагентов">
                {directions.map((direction) => {
                  const count = counterparties.filter(
                    (item) => item.direction === direction,
                  ).length;
                  return (
                    <button
                      key={direction}
                      type="button"
                      role="tab"
                      aria-selected={cpDirection === direction}
                      className={
                        cpDirection === direction
                          ? "profile-cp-tab-mobile is-active"
                          : "profile-cp-tab-mobile"
                      }
                      onClick={() => {
                        setCpDirection(direction);
                        setCpExpanded(false);
                      }}
                    >
                      {direction === "supplier" ? "Поставщики" : "Покупатели"} · {count}
                    </button>
                  );
                })}
              </div>
              <div className="profile-cp-divider" aria-hidden="true" />

              {rankedCounterparties.length > 0 ? (
                <ul className="profile-cp-list-mobile">
                  {visibleCounterparties.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className="profile-cp-row-mobile"
                        onClick={() => openEdit(item)}
                        aria-label={`Изменить название контрагента ${item.display_name}`}
                      >
                        <span className="profile-cp-row-mobile__avatar" aria-hidden="true">
                          {initials(item.display_name)}
                        </span>
                        <span className="profile-cp-row-mobile__main">
                          <span className="profile-cp-row-mobile__name">{item.display_name}</span>
                          {item.note ? (
                            <span className="profile-cp-row-mobile__note">{item.note}</span>
                          ) : null}
                        </span>
                        <span className="profile-cp-row-mobile__share">
                          {shareLabel(item, cpDirection)}
                        </span>
                        <span className="profile-cp-row-mobile__chevron" aria-hidden="true">
                          ›
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="profile-cp-empty">По этому бизнесу пока нет платёжных данных.</p>
              )}

              {hiddenCounterparties.length > 0 ? (
                <button
                  type="button"
                  className="profile-cp-more"
                  aria-expanded={cpExpanded}
                  onClick={() => setCpExpanded((value) => !value)}
                >
                  {cpExpanded
                    ? "Свернуть"
                    : `Ещё ${pluralRu(hiddenCounterparties.length, counterpartyNoun)}${
                        hiddenShare > 0 ? ` · ${formatShare(hiddenShare)}` : ""
                      }`}
                  <span aria-hidden="true">{cpExpanded ? "↑" : "↓"}</span>
                </button>
              ) : null}
            </section>
          </div>
        )}

      </div>

      {editing ? (
        <div
          className="profile-sheet-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeEdit();
          }}
        >
          <form
            className="profile-sheet"
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-sheet-title"
            onSubmit={submitRename}
          >
            <div className="profile-sheet__head">
              <h2 id="profile-sheet-title" className="profile-sheet__title">
                Название контрагента
              </h2>
              <p className="profile-sheet__subtitle">
                {editing.note
                  ? `${editing.note} · ${shareLabel(editing, cpDirection)}`
                  : shareLabel(editing, cpDirection)}
              </p>
            </div>
            <label className="profile-sheet__field">
              <span className="profile-sheet__label">Новое название</span>
              <input
                className="profile-sheet__input"
                value={draft}
                maxLength={128}
                autoFocus
                disabled={rename.isPending}
                aria-invalid={sheetError ? true : undefined}
                onChange={(event) => {
                  setDraft(event.target.value);
                  setFormError(null);
                  if (rename.isError) rename.reset();
                }}
              />
            </label>
            {sheetError ? (
              <p className="profile-sheet__error" role="alert">
                {sheetError}
              </p>
            ) : null}
            <div className="profile-sheet__actions">
              <button
                type="button"
                className="profile-sheet__button profile-sheet__button--cancel"
                onClick={closeEdit}
                disabled={rename.isPending}
              >
                Отмена
              </button>
              <button
                type="submit"
                className="profile-sheet__button profile-sheet__button--save"
                disabled={rename.isPending}
              >
                {rename.isPending ? "Сохраняем…" : "Сохранить"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="profile-desktop">
        <h1 className="profile-desktop__title">Профиль</h1>

        <div className="profile-desktop__layout">
          <aside className="profile-desk-aside">
            <div className="profile-desk-passport">
              <div className="profile-desk-company">
                <div className="profile-desk-company__body">
                  {desktopCompanyMeta ? (
                    <p className="profile-desk-company__meta">{desktopCompanyMeta}</p>
                  ) : null}
                  <p className="profile-desk-company__name">{businessDisplayName}</p>
                  {industry ? <p className="profile-desk-company__line">{industry}</p> : null}
                  {city ? <p className="profile-desk-company__line">{city}</p> : null}
                </div>
                <span className="profile-desk-company__monogram" aria-hidden="true">
                  {initials(businessDisplayName)
                    .split("")
                    .map((letter, index) => (
                      <span
                        key={`${letter}-${index}`}
                        className={index === 1 ? "is-accent" : undefined}
                      >
                        {letter}
                      </span>
                    ))}
                </span>
              </div>

              <div className="profile-desk-metrics">
                <div className="profile-desk-revenue">
                  <span className="profile-desk-revenue__label">Выручка</span>
                  <p className="profile-desk-revenue__amount">
                    <span className="profile-desk-revenue__value">{revenueValue}</span>
                    {revenueUnit ? (
                      <span className="profile-desk-revenue__unit">{revenueUnit}</span>
                    ) : null}
                  </p>
                </div>
                <div className="profile-desk-scale">
                  <div>
                    <span className="profile-desk-scale__label">Сотрудники</span>
                    <p className="profile-desk-scale__value">{stats.employees ?? "—"}</p>
                  </div>
                  <div className="profile-desk-scale__ved">
                    <span className="profile-desk-scale__label profile-desk-scale__label--small">
                      ВЭД
                    </span>
                    <span className="profile-desk-scale__country">
                      {stats.foreign_trade_country ?? "—"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <section className="profile-desk-summary" aria-labelledby="profile-desk-summary-title">
              <div className="profile-desk-summary__head">
                <h2 id="profile-desk-summary-title" className="profile-desk-summary__title">
                  Саммари отчётов
                </h2>
                <span
                  className="profile-desk-summary__badge"
                  aria-label={`Загружено файлов: ${reportForms.length}`}
                >
                  {reportForms.length}
                </span>
              </div>
              {reportForms.length > 0 ? (
                <ul className="profile-desk-summary__list">
                  {reportForms.map((form) => (
                    <li key={form.key}>
                      <Link
                        to={`/profile/reports/${form.key}`}
                        className="profile-desk-summary__link"
                        aria-label={`${form.label}: ${form.filename}`}
                      >
                        <span className="profile-desk-summary__file">{form.filename}</span>
                        <span className="profile-desk-summary__arrow" aria-hidden="true">
                          ↗
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="profile-desk-summary__empty">Отчёты не загружены</p>
              )}
            </section>

            <div className="profile-desk-actions">
              <button type="button" className="profile-desk-logout" onClick={handleSignOut}>
                Выйти
              </button>
            </div>
          </aside>

          <section
            className={`profile-desktop__main${
              tab === "counterparties" ? " profile-desktop__main--cp" : ""
            }`}
          >
            <div className="profile-desk-tabsbar">
              <div className="profile-desk-tabs" role="tablist" aria-label="Профиль бизнеса">
                <button
                  id="profile-desk-tab-categories"
                  type="button"
                  role="tab"
                  aria-selected={tab === "categories"}
                  aria-controls="profile-desk-panel-categories"
                  className={
                    tab === "categories"
                      ? "profile-desk-tab is-active"
                      : "profile-desk-tab"
                  }
                  onClick={() => setTab("categories")}
                >
                  <span>Категории</span>
                  <span className="profile-desk-tabs__count">{data.categories.length}</span>
                </button>
                <button
                  id="profile-desk-tab-counterparties"
                  type="button"
                  role="tab"
                  aria-selected={tab === "counterparties"}
                  aria-controls="profile-desk-panel-counterparties"
                  className={
                    tab === "counterparties"
                      ? "profile-desk-tab is-active"
                      : "profile-desk-tab"
                  }
                  onClick={() => setTab("counterparties")}
                >
                  Контрагенты
                </button>
              </div>
            </div>

            {tab === "categories" ? (
              <div
                id="profile-desk-panel-categories"
                role="tabpanel"
                aria-labelledby="profile-desk-tab-categories"
                className="profile-desk-cats"
              >
                {hasCategories ? (
                  <>
                    <div className="profile-desk-cats__grid">
                      {(["direct", "indirect", "background"] as const).map((key) => {
                        const group = data.category_groups.find((item) => item.key === key);
                        const items = group?.items ?? [];
                        return (
                          <section
                            key={key}
                            className="profile-desk-cat-group"
                            aria-labelledby={`profile-desk-cat-${key}`}
                          >
                            <header className="profile-desk-cat-group__head">
                              <h3
                                id={`profile-desk-cat-${key}`}
                                className="profile-desk-cat-group__title"
                              >
                                {GROUP_LABELS[key] ?? group?.name ?? key}
                              </h3>
                              <span className="profile-desk-cat-group__count">{items.length}</span>
                            </header>
                            <div className="profile-desk-cat-group__items">
                              {items.map((category, index) => {
                                const tone = desktopToneFor(key, index);
                                return (
                                  <article
                                    key={category.category_id}
                                    className={`profile-desk-cat-card profile-desk-cat-card--${tone}`}
                                  >
                                    <p className="profile-desk-cat-card__name">{category.name}</p>
                                    {category.rationale ? (
                                      <p className="profile-desk-cat-card__note">
                                        {category.rationale}
                                      </p>
                                    ) : null}
                                  </article>
                                );
                              })}
                            </div>
                          </section>
                        );
                      })}
                    </div>

                    {noneGroup && noneGroup.items.length > 0 ? (
                      <div className="profile-desk-none">
                        <button
                          type="button"
                          className="profile-desk-none__toggle"
                          aria-expanded={noneOpen}
                          aria-controls="profile-desk-none-list"
                          onClick={() => setNoneOpen((value) => !value)}
                        >
                          {GROUP_LABELS.none} · {noneGroup.items.length}
                        </button>
                        <ul
                          id="profile-desk-none-list"
                          className="profile-desk-none__list"
                          hidden={!noneOpen}
                        >
                          {noneGroup.items.map((category) => (
                            <li key={category.category_id}>
                              {category.short_name || category.name}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <p className="profile-desk-empty">По этому бизнесу пока нет категорий.</p>
                )}
              </div>
            ) : (
              <div
                id="profile-desk-panel-counterparties"
                role="tabpanel"
                aria-labelledby="profile-desk-tab-counterparties"
                className="profile-desk-cp"
              >
                <div className="profile-desk-cp__head">
                  <div
                    className="profile-desk-cp__directions"
                    role="tablist"
                    aria-label="Направление контрагентов"
                  >
                    {directions.map((direction) => {
                      const count = counterparties.filter(
                        (item) => item.direction === direction,
                      ).length;
                      return (
                        <button
                          key={direction}
                          type="button"
                          role="tab"
                          aria-selected={cpDirection === direction}
                          className={
                            cpDirection === direction
                              ? "profile-desk-cp__direction is-active"
                              : "profile-desk-cp__direction"
                          }
                          onClick={() => {
                            setCpDirection(direction);
                            setCpExpanded(false);
                          }}
                        >
                          {direction === "supplier" ? "Поставщики" : "Покупатели"}
                          <span className="profile-desk-cp__dir-count">{count}</span>
                        </button>
                      );
                    })}
                  </div>
                  <span className="profile-desk-cp__col">Деятельность</span>
                  <span className="profile-desk-cp__col profile-desk-cp__col--share">
                    Доля
                  </span>
                </div>

                {rankedCounterparties.length > 0 ? (
                  <ul className="profile-desk-cp__list">
                    {desktopVisibleCounterparties.map((item) => (
                      <li key={item.id}>
                        <button
                          type="button"
                          className="profile-desk-cp__row"
                          onClick={() => openEdit(item)}
                          aria-label={`Изменить название контрагента ${item.display_name}`}
                        >
                          <span className="profile-desk-cp__company">
                            <span className="profile-desk-cp__name">{item.display_name}</span>
                            <img
                              className="profile-desk-cp__edit"
                              src={profilePencilIcon}
                              alt=""
                              aria-hidden="true"
                            />
                          </span>
                          <span className="profile-desk-cp__activity">{item.note || "—"}</span>
                          <span className="profile-desk-cp__share">
                            {shareLabel(item, cpDirection)}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="profile-desk-empty">По этому бизнесу пока нет платёжных данных.</p>
                )}

                {desktopHiddenCounterparties.length > 0 ? (
                  <div className="profile-desk-cp__more-row">
                    <button
                      type="button"
                      className="profile-desk-cp__more"
                      aria-expanded={cpExpanded}
                      onClick={() => setCpExpanded((value) => !value)}
                    >
                      {cpExpanded
                        ? "Свернуть"
                        : `Ещё ${pluralRu(
                            desktopHiddenCounterparties.length,
                            counterpartyNoun,
                          )}${
                            desktopHiddenShare > 0 ? ` · ${formatShare(desktopHiddenShare)}` : ""
                          }`}
                      <span aria-hidden="true">{cpExpanded ? "↑" : "↓"}</span>
                    </button>
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
