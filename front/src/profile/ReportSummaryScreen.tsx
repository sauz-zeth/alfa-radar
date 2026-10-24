import { ApiError, useApi, useApiQuery, type ProfileStats } from "../api";
import { MarkdownView } from "../components/MarkdownView";
import { formatMoney } from "../onboarding/format";
import { reportingMarkdown } from "../lib/reportingMarkdown";
import { Link, useRouter } from "../router";
import "./report-summary.css";

type FormKey = "balance" | "income" | "cash_flow";

const FORM_KEYS: FormKey[] = ["balance", "income", "cash_flow"];

const FORM_LABELS: Record<FormKey, string> = {
  balance: "Бухгалтерский баланс",
  income: "Отчёт о финансовых результатах",
  cash_flow: "Отчёт о движении денежных средств",
};

const KEY_TITLES: Record<FormKey, string> = {
  balance: "Данные из отчёта",
  income: "Доли выручки",
  cash_flow: "Доли закупок",
};

type KeyRow = { name: string; value: string; share?: number };
type KeyBlock = { title: string; rows: KeyRow[]; bars: boolean };

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function isFormKey(value: string): value is FormKey {
  return (FORM_KEYS as string[]).includes(value);
}

function stripLeadingHeading(markdown: string, label: string): string {
  let result = markdown.trim();
  const heading = result.match(/^#{1,6}\s+(.+?)\r?\n+/);
  const headingText = heading?.[1]?.replace(/\s+#+\s*$/, "").trim();
  if (heading && headingText) {
    if (headingText.toLocaleLowerCase("ru") === label.trim().toLocaleLowerCase("ru")) {
      result = result.slice(heading[0].length).trim();
    }
  }
  const fileLine = result.match(/^\*\*Файл:\*\*[^\n]*\r?\n*/);
  if (fileLine) result = result.slice(fileLine[0].length).trim();
  return result;
}

function findExportShare(value: unknown, depth = 0): string | null {
  if (depth > 3 || value === null || value === undefined) return null;
  if (Array.isArray(value)) {
    for (const item of value) {
      const hit = findExportShare(item, depth + 1);
      if (hit) return hit;
    }
    return null;
  }
  const record = asRecord(value);
  if (!record) return null;

  for (const [key, raw] of Object.entries(record)) {
    if (!/export|экспорт/i.test(key)) continue;
    if (!/share|percent|дол/i.test(key)) continue;
    const text = asString(raw);
    if (text) return text;
    const number = asNumber(raw);
    if (number !== null && number >= 0) {
      return `${Math.round(number <= 1 ? number * 100 : number)}%`;
    }
  }

  for (const point of asArray(record.key_points)) {
    if (typeof point !== "string" || !/экспорт/i.test(point)) continue;
    const match = point.match(/(\d+(?:[.,]\d+)?)\s*%/);
    if (match?.[1]) return `${match[1]}%`;
  }

  for (const raw of Object.values(record)) {
    const hit = findExportShare(raw, depth + 1);
    if (hit) return hit;
  }
  return null;
}

function balanceBlock(
  data: Record<string, unknown> | null,
  stats: ProfileStats,
  reporting: Record<string, unknown> | null,
): KeyBlock {
  return {
    title: KEY_TITLES.balance,
    bars: false,
    rows: [
      { name: "Выручка", value: stats.revenue_label || formatMoney(stats.revenue) },
      { name: "Сотрудники", value: asString(stats.employees) ?? "—" },
      { name: "Доля экспорта", value: findExportShare([data, reporting]) ?? "—" },
    ],
  };
}

function sharesBlock(form: FormKey, data: Record<string, unknown> | null): KeyBlock | null {
  const costs = asArray(data?.cost_structure).flatMap((item) => {
    const row = asRecord(item);
    const name = asString(row?.name);
    const value = asNumber(row?.value);
    return name && value !== null && value > 0 ? [{ name, value }] : [];
  });

  if (costs.length > 0) {
    const total = costs.reduce((sum, item) => sum + item.value, 0);
    return {
      title: KEY_TITLES[form],
      bars: true,
      rows: costs
        .sort((a, b) => b.value - a.value)
        .map((item) => ({
          name: item.name,
          value: `${Math.round((item.value / total) * 100)}%`,
          share: item.value / total,
        })),
    };
  }

  const positions = asArray(data?.currency_positions).flatMap((item) => {
    const row = asRecord(item);
    const currency = asString(row?.currency);
    if (!currency) return [];
    const amount = asNumber(row?.amount);
    return [{ name: currency, value: amount === null ? "—" : formatMoney(amount) }];
  });

  if (positions.length > 0) {
    return { title: "Валютные позиции", bars: false, rows: positions };
  }

  const figures = (
    [
      ["revenue", "Выручка"],
      ["profit", "Прибыль"],
      ["debt", "Долг"],
      ["interest_expense", "Проценты к уплате"],
    ] as const
  ).flatMap(([field, label]) => {
    const value = asNumber(data?.[field]);
    return value === null ? [] : [{ name: label, value: formatMoney(value) }];
  });

  if (figures.length > 0) {
    return { title: "Ключевые цифры", bars: false, rows: figures };
  }

  return null;
}

function SummaryHeader() {
  return (
    <header className="report-summary__head">
      <Link to="/profile" className="report-summary__back" aria-label="Назад в профиль">
        ←
      </Link>
      <h1 className="report-summary__title">Саммари отчёта</h1>
      <span className="report-summary__spacer" aria-hidden="true" />
    </header>
  );
}

function StateScreen({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="report-summary">
      <div className="report-summary__inner">
        <SummaryHeader />
        <div className="report-summary__state">
          <p>{message}</p>
          {retry ? (
            <button type="button" className="report-summary__retry" onClick={retry}>
              Повторить
            </button>
          ) : (
            <Link to="/profile" className="report-summary__retry">
              Вернуться в профиль
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ReportSummaryScreen() {
  const api = useApi();
  const { path } = useRouter();
  const formParam = path.split("/")[3] ?? "";
  const form = isFormKey(formParam) ? formParam : null;

  const profile = useApiQuery({
    queryKey: ["profile"],
    queryFn: (signal) => api.profile.get({ signal }),
  });

  if (profile.isPending) {
    return <StateScreen message="Загружаем саммари…" />;
  }

  if (profile.isError || !profile.data) {
    return (
      <StateScreen
        message={
          profile.error instanceof ApiError
            ? profile.error.detail
            : "Не удалось загрузить профиль"
        }
        retry={() => profile.refetch()}
      />
    );
  }

  const data = profile.data;
  const reporting = asRecord(data.reporting);
  const forms = asRecord(reporting?.forms);
  const entry = form && forms ? asRecord(forms[form]) : null;

  if (!form || !entry) {
    return <StateScreen message="Этот отчёт ещё не загружен." />;
  }

  const stats = data.stats;
  const label = asString(entry.label) ?? FORM_LABELS[form];
  const filename = asString(entry.filename) ?? label;
  const rawMarkdown =
    asString(entry.markdown) ?? reportingMarkdown({ forms: { [form]: entry } });
  const markdown = stripLeadingHeading(rawMarkdown, label);
  const entryData = asRecord(entry.data);
  const keyBlock =
    form === "balance" ? balanceBlock(entryData, stats, reporting) : sharesBlock(form, entryData);
  const profileFacts = [stats.industry, stats.city, stats.revenue_label, data.profile.role_label]
    .filter((item): item is string => Boolean(item))
    .join(" · ");

  return (
    <div className="report-summary">
      <div className="report-summary__inner">
        <SummaryHeader />

        <section className="report-summary__card">
          <div className="report-summary__file">
            <h2 className="report-summary__filename">{filename}</h2>
            {markdown ? (
              <MarkdownView markdown={markdown} className="report-summary__markdown" />
            ) : (
              <p className="report-summary__empty">В отчёте пока нет данных для выжимки.</p>
            )}
          </div>

          {keyBlock && keyBlock.rows.length > 0 ? (
            <div className="report-summary__key">
              <h3 className="report-summary__key-title">{keyBlock.title}</h3>
              {keyBlock.rows.map((row, index) => (
                <div key={`${row.name}-${index}`} className="report-summary__row">
                  <div className="report-summary__row-head">
                    <span className="report-summary__row-name">{row.name}</span>
                    <span className="report-summary__row-value">{row.value}</span>
                  </div>
                  {keyBlock.bars && row.share !== undefined ? (
                    <div className="report-summary__bar" aria-hidden="true">
                      <span
                        style={{ width: `${Math.min(100, Math.max(0, row.share * 100))}%` }}
                      />
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </section>

        <section className="report-summary__profile">
          <h2 className="report-summary__profile-title">Учтено в профиле</h2>
          {profileFacts ? (
            <p className="report-summary__profile-facts">{profileFacts}</p>
          ) : null}
          <p className="report-summary__profile-text">
            Саммари собрано по загруженным отчётам и профилю бизнеса.
          </p>
        </section>
      </div>
    </div>
  );
}
