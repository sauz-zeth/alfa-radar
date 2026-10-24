import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, useApi, useApiMutation, useApiQuery, useQueryClient } from "../api";
import { useAuth } from "../auth/useAuth";
import { useMediaQuery } from "../lib/useMediaQuery";
import { useRouter } from "../router";
import { FeedDesktop } from "./FeedDesktop";
import { FeedEnd } from "./FeedEnd";
import { FeedPost } from "./FeedPost";
import { FeedTopBar } from "./FeedTopBar";
import { buildFilters, toFeedPost } from "./mapFeed";
import "./feed.css";

const FEED_LIMIT = 30;

export function FeedScreen() {
  const api = useApi();
  const queryClient = useQueryClient();
  const { navigate } = useRouter();
  const { signOut } = useAuth();
  const isDesktop = useMediaQuery("(min-width: 1200px)");
  const [activeFilter, setActiveFilter] = useState("Все");
  const [trackedOverrides, setTrackedOverrides] = useState<Record<string, boolean>>({});
  const feedRef = useRef<HTMLDivElement>(null);

  const feedQuery = useApiQuery({
    queryKey: ["feed", { limit: FEED_LIMIT }],
    queryFn: (signal) => api.feed.list({ limit: FEED_LIMIT, include_tracked: true }, { signal }),
  });

  const hiddenQuery = useApiQuery({
    queryKey: ["feed", "hidden"],
    queryFn: (signal) => api.feed.hidden({}, { signal }),
  });

  useEffect(() => {
    if (feedQuery.error instanceof ApiError && feedQuery.error.status === 401) {
      signOut();
    }
  }, [feedQuery.error, signOut]);

  const trackMutation = useApiMutation<unknown, { id: string; tracked: boolean }>({
    mutationFn: async ({ id, tracked }) => {
      if (!tracked) return api.feed.track(id);
      const trackedList = await api.tracked.list({});
      const item = trackedList.items.find((entry) => entry.event_id === id);
      if (item) await api.tracked.remove(item.id);
      return undefined;
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["feed"] });
    },
  });

  const posts = useMemo(() => (feedQuery.data?.items ?? []).map(toFeedPost), [feedQuery.data]);
  const filters = useMemo(() => buildFilters(posts), [posts]);
  const hiddenCount =
    hiddenQuery.data?.tabs.reduce((sum, tab) => sum + tab.count, 0) ?? hiddenQuery.data?.total ?? 0;

  const visiblePosts = useMemo(() => {
    if (activeFilter === "Все") return posts;
    if (activeFilter === "Прямое упоминание") return posts.filter((post) => post.importance >= 70);
    return posts.filter((post) => post.categories.includes(activeFilter));
  }, [activeFilter, posts]);

  const renderedPosts = useMemo(
    () =>
      visiblePosts.map((post) =>
        trackedOverrides[post.id] === undefined ? post : { ...post, tracked: trackedOverrides[post.id]! },
      ),
    [trackedOverrides, visiblePosts],
  );

  const scrollToTop = useCallback(() => {
    feedRef.current?.scrollTo({ top: 0 });
  }, []);

  const changeFilter = useCallback(
    (filter: string) => {
      setActiveFilter(filter);
      scrollToTop();
    },
    [scrollToTop],
  );

  const toggleTracked = useCallback(
    (id: string) => {
      const post = posts.find((item) => item.id === id);
      const current = trackedOverrides[id] ?? post?.tracked ?? false;
      setTrackedOverrides((overrides) => ({ ...overrides, [id]: !current }));
      trackMutation.mutate(
        { id, tracked: current },
        {
          onError: () => setTrackedOverrides((overrides) => ({ ...overrides, [id]: current })),
        },
      );
    },
    [posts, trackMutation, trackedOverrides],
  );

  return (
    <div className="feed-screen">
      {feedQuery.isError ? (
        <div className="feed-state">
          <p>
            {feedQuery.error instanceof ApiError
              ? feedQuery.error.detail
              : "Не удалось загрузить ленту."}
          </p>
          <button type="button" onClick={() => feedQuery.refetch()}>
            Повторить
          </button>
        </div>
      ) : feedQuery.isPending ? (
        <div className="feed-state">
          <p>Загрузка ленты…</p>
        </div>
      ) : isDesktop ? (
        <FeedDesktop
          posts={renderedPosts}
          hiddenCount={hiddenCount}
          filters={filters}
          activeFilter={activeFilter}
          onFilterChange={changeFilter}
          onToggleTracked={toggleTracked}
        />
      ) : (
        <>
          <div className="feed" ref={feedRef}>
            {renderedPosts.map((post) => (
              <FeedPost key={post.id} post={post} onToggleTracked={toggleTracked} />
            ))}
            {renderedPosts.length === 0 ? (
              <p className="feed-empty">Нет новостей по этому фильтру</p>
            ) : (
              <FeedEnd
                hiddenCount={hiddenCount}
                onRestart={scrollToTop}
                onOpenHidden={() => navigate("/hidden")}
              />
            )}
          </div>

          <FeedTopBar
            hiddenCount={hiddenCount}
            feedCount={renderedPosts.length}
            filters={filters}
            activeFilter={activeFilter}
            onFilterChange={changeFilter}
            onOpenHidden={() => navigate("/hidden")}
            onSearch={() => navigate("/search")}
          />
        </>
      )}
    </div>
  );
}
