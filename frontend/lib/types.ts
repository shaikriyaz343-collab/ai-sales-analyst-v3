export type CapabilitySet = {
  workspaces: Workspace[];
  analytics: string[];
  modules: string[];
};

export type Workspace = "overview" | "explore" | "insights" | "ask" | "actions" | "reports";

export type DatasetSummary = {
  dataset_id: string;
  file_name: string;
  file_type: string;
  row_count: number;
  column_count: number;
  columns: string[];
  business_model: string | null;
  business_model_label: string | null;
  business_model_confidence: number;
  quality_issues: number;
  capabilities: CapabilitySet;
  supported_concepts: string[];
  semantic?: SemanticSummary | Record<string, unknown> | null;
};

export type Evidence = {
  metric: string;
  value?: number | null;
  comparison_value?: number | null;
  calculation: string;
  scope: string;
  source_fields: string[];
};

export type OverviewMetric = {
  id: string;
  label: string;
  value: number | null;
  display_value: string;
  delta_pct?: number | null;
  delta_label?: string | null;
  tone: string;
  evidence: Evidence;
};

export type OverviewInsight = {
  id: string;
  severity: string;
  title: string;
  summary: string;
  why_it_matters: string;
  recommendation: string;
  evidence: Evidence;
};

export type OverviewResponse = {
  dataset_id: string;
  business_model: string | null;
  business_model_label: string | null;
  scope_label: string;
  headline: string;
  subheadline: string;
  metrics: OverviewMetric[];
  what_changed: string[];
  attention: OverviewInsight[];
  opportunities: OverviewInsight[];
};

export type SemanticSummary = {
  fields: string[];
  concepts: string[];
  metrics: string[];
  dimensions: string[];
};

export type ExploreOption = { id: string; label: string };

export type ExploreEvidence = {
  metric: string;
  value?: number | null;
  comparison_value?: number | null;
  calculation: string;
  scope: string;
  source_fields: string[];
};

export type ExploreRow = {
  key: string;
  value: number;
  display_value: string;
  share_pct?: number | null;
  evidence: ExploreEvidence;
};

export type ExploreResponse = {
  dataset_id: string;
  business_model: string | null;
  business_model_label: string | null;
  metric: string;
  metric_label: string;
  dimension: string;
  dimension_label: string;
  total_value: number | null;
  total_display_value: string;
  available_metrics: ExploreOption[];
  available_dimensions: ExploreOption[];
  rows: ExploreRow[];
};


export type InsightItem = {
  id: string;
  kind: "risk" | "change" | "opportunity" | string;
  severity: string;
  title: string;
  what_changed: string;
  why_it_matters: string;
  recommendation: string;
  metric: string;
  value?: number | null;
  display_value: string;
  evidence: Evidence;
};

export type InsightsResponse = {
  dataset_id: string;
  business_model: string | null;
  business_model_label: string | null;
  scope_label: string;
  headline: string;
  summary: string;
  insights: InsightItem[];
};


export type AskEvidence = Evidence;
export type AskFollowUp = { label: string; question: string };
export type AskAnswer = { status: string; text: string; confidence: string; evidence?: AskEvidence | null };
export type AskResponse = {
  dataset_id: string; question: string; business_model: string | null; business_model_label: string | null;
  answer: AskAnswer; follow_ups: AskFollowUp[]; explore_metric?: string | null; explore_dimension?: string | null; supported_summary?: string | null;
};
