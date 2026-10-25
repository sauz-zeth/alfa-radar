import { useEffect, useId, useState } from "react";
import { useApi, useApiQuery } from "../api";
import { pluralRu } from "../lib/plural";
import { useRouter } from "../router";

const MIN_QUERY = 2;

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}

type Suggestion = {
  key: string;
  label: string;
  meta: string;
  to: string;
};

export function HeaderSearch() {
  const api = useApi();
  const { navigate } = useRouter();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(timer);
  }, [query]);

  const enabled = debounced.length >= MIN_QUERY;
  const results = useApiQuery({
    queryKey: ["search-suggest", debounced],
    queryFn: (signal) => api.search.search({ q: debounced }, { signal }),
    enabled,
  });

  const suggestions: Suggestion[] = enabled && results.data
    ? results.data.news.slice(0, 5).map((item) => ({
        key: `news-${item.id}`,
        label: item.title,
        meta: `${item.source_name} · ${shortDate(item.published_at)} · ${pluralRu(
          item.source_count,
          ["источник", "источника", "источников"],
        )}`,
        to: `/event/${item.id}`,
      }))
    : [];

  useEffect(() => {
    setActive(-1);
  }, [debounced]);

  const goToSearch = () => {
    const trimmed = query.trim();
    setOpen(false);
    navigate(trimmed ? `/search?q=${encodeURIComponent(trimmed)}` : "/search");
  };

  const select = (suggestion: Suggestion) => {
    setOpen(false);
    setActive(-1);
    navigate(suggestion.to);
  };

  const showList = open && enabled;

  return (
    <form
      className="desktop-topbar__search"
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        goToSearch();
      }}
    >
      <input
        type="search"
        value={query}
        placeholder="Поиск по новостям"
        aria-label="Поиск по новостям"
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={showList ? listId : undefined}
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={(event) => {
          if (!event.currentTarget.form?.contains(event.relatedTarget)) setOpen(false);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setOpen(false);
            setActive(-1);
            return;
          }
          if (!showList) return;
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            if (suggestions.length === 0) return;
            const step = event.key === "ArrowDown" ? 1 : -1;
            setActive((current) => {
              if (current === -1) return step === 1 ? 0 : suggestions.length - 1;
              return (current + step + suggestions.length) % suggestions.length;
            });
          }
          if (event.key === "Enter" && active >= 0 && suggestions[active]) {
            event.preventDefault();
            select(suggestions[active]);
          }
        }}
      />
      <span>Ctrl K</span>

      {showList ? (
        <div className="desktop-search-pop" id={listId} role="listbox" aria-label="Подсказки поиска">
          {results.isPending ? (
            <p className="desktop-search-pop__state">Ищем…</p>
          ) : results.isError ? (
            <p className="desktop-search-pop__state">Не удалось загрузить подсказки.</p>
          ) : suggestions.length === 0 ? (
            <p className="desktop-search-pop__state">Ничего не нашлось.</p>
          ) : (
            <>
              {suggestions.map((suggestion, index) => (
                <button
                  key={suggestion.key}
                  type="button"
                  role="option"
                  id={`${listId}-${index}`}
                  aria-selected={index === active}
                  className={
                    index === active
                      ? "desktop-search-pop__item is-active"
                      : "desktop-search-pop__item"
                  }
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => select(suggestion)}
                >
                  <span className="desktop-search-pop__label">{suggestion.label}</span>
                  <span className="desktop-search-pop__meta">{suggestion.meta}</span>
                </button>
              ))}
              <button
                type="button"
                className="desktop-search-pop__all"
                onMouseDown={(event) => event.preventDefault()}
                onClick={goToSearch}
              >
                Все результаты по запросу «{query.trim()}»
              </button>
            </>
          )}
        </div>
      ) : null}
    </form>
  );
}
