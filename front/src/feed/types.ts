export type ImpactTone = "risk" | "opportunity" | "mixed" | "neutral";

export type FeedSource = {
  id: string;
  initials: string;
  name: string;
  color: string;
  time: string;
  image: string;
  imageAlt: string;
  fullBleed?: boolean;
};

export type ImpactMetric = {
  value: string;
  note: string;
  tone?: "negative" | "positive";
};

export type FeedPost = {
  id: string;
  title: string;
  topics: string[];
  categories: string[];
  effectiveLabel: string;
  note: string;
  impact: ImpactTone;
  impactLabel: string;
  importance: number;
  sources: FeedSource[];
  metrics: ImpactMetric[];
  tracked: boolean;
};
