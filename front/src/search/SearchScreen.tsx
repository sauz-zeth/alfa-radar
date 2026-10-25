import { useEffect, useState } from "react";
import {
  ApiError,
  useApi,
  useApiQuery,
  type SearchCompany,
  type SearchNews,
} from "../api";
import { Link, useRouter } from "../router";
import "./search.css";

const MIN_QUERY = 2;
const RESULT_LIMIT = 10;

const RECENT_STUBS = ["ключевая ставка", "металлургия", "логистика", "Алроса"];

const impactTones: Record<string, string> = {
  risk: "risk",
  opportunity: "opportunity",
  mixed: "mixed",
  neutral: "neutral",
};

function companyMeta(company: SearchCompany): string {
  return [company.city, company.region].filter(Boolean).join(" · ");
}

function CompanyRow({ company }: { company: SearchCompany }) {
  const meta = companyMeta(company);

  return (
    <li className="search-company">
      <span className="search-company__avatar" aria-hidden="true">
        {company.initials}
      </span>
      <div className="search-company__body">
        <p className="search-company__name">{company.name}</p>
        <p className="search-company__uid">UID {company.uid}</p>
        <p className="search-company__meta">
          {meta ? `${meta} · ` : ""}
          {company.role}
        </p>
      </div>
      {company.revenue_segment ? (
        <span className="search-company__segment">{company.revenue_segment}</span>
      ) : null}
    </li>
  );
}

function NewsRow({ item }: { item: SearchNews }) {
  const tone = impactTones[item.impact] ?? "neutral";

  return (
    <li>
      <Link to={`/event/${item.id}`} className="search-news">
        <span className="search-news__meta">
          <span>{item.source_name}</span>
          <span className="search-news__importance" aria-label={`Важность ${item.importance}`}>
            {item.importance}
          </span>
          <span className={`search-news__impact search-news__impact--${tone}`}>
            {item.impact_label}
          </span>
        </span>
        <span className="search-news__title">{item.title}</span>
      </Link>
    </li>
  );
}

export default function SearchScreen() {
  const api = useApi();
  const { search } = useRouter();
  const urlQuery = new URLSearchParams(search).get("q") ?? "";
  const [query, setQuery] = useState(urlQuery);

  useEffect(() => {
    setQuery(urlQuery);
  }, [urlQuery]);

  const trimmed = query.trim();
  const active = trimmed.length >= MIN_QUERY;

  const results = useApiQuery({
    queryKey: ["search", trimmed],
    queryFn: (signal) => api.search.search({ q: trimmed }, { signal }),
    enabled: active,
  });

  const data = results.data;
  const companies = data?.companies.slice(0, RESULT_LIMIT) ?? [];
  const news = data?.news.slice(0, RESULT_LIMIT) ?? [];
  const empty = Boolean(data && data.total_companies === 0 && data.total_news === 0);

  return (
    <div className="search-page">
      <header className="search-head">
        <h1 className="search-head__title">Поиск</h1>
        <p className="search-head__subtitle">Новости, компании и контрагенты в одном месте</p>
        <label className="search-field">
          <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
            <circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
            <path
              d="M12.5 12.5 16 16"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Новости, компании, контрагенты"
            aria-label="Новости, компании, контрагенты"
            autoFocus
            enterKeyHint="search"
          />
        </label>
      </header>

      {!active ? (
        <div className="search-start">
          <p className="search-hint">
            Введите хотя бы {MIN_QUERY} символа, чтобы найти новости по компаниям, отраслям и
            контрагентам.
          </p>
          <div className="search-recent">
            <p className="search-recent__label">Недавно искали</p>
            <div className="search-recent__chips">
              {RECENT_STUBS.map((item) => (
                <span key={item} className="search-recent__chip">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : results.isPending ? (
        <div className="search-state">
          <p>Ищем по базе…</p>
        </div>
      ) : results.isError ? (
        <div className="search-state">
          <p>
            {results.error instanceof ApiError
              ? results.error.detail
              : "Не удалось выполнить поиск."}
          </p>
          <button type="button" className="search-retry" onClick={() => results.refetch()}>
            Повторить
          </button>
        </div>
      ) : data ? (
        empty ? (
          <div className="search-state">
            <p>По запросу «{trimmed}» ничего не нашлось.</p>
            <p className="search-state__note">Попробуйте другое название или более короткий запрос.</p>
          </div>
        ) : (
          <div className="search-results" aria-busy={results.isFetching}>
            {companies.length > 0 ? (
              <section className="search-section" aria-labelledby="search-companies">
                <div className="search-section__head">
                  <h2 className="search-section__title" id="search-companies">
                    Компании
                  </h2>
                  <span className="search-section__count">{data.total_companies}</span>
                </div>
                <ul className="search-list">
                  {companies.map((company) => (
                    <CompanyRow key={company.uid} company={company} />
                  ))}
                </ul>
              </section>
            ) : null}

            {news.length > 0 ? (
              <section className="search-section" aria-labelledby="search-news">
                <div className="search-section__head">
                  <h2 className="search-section__title" id="search-news">
                    Новости
                  </h2>
                  <span className="search-section__count">{data.total_news}</span>
                </div>
                <ul className="search-list">
                  {news.map((item) => (
                    <NewsRow key={item.id} item={item} />
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        )
      ) : null}
    </div>
  );
}
