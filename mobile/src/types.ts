export type Workspace = { id: string; name: string };

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  organization_id: string;
  organization_name: string;
  role: string;
  workspace_id: string;
  workspace_name: string;
  workspaces: Workspace[];
};

export type DatasetSummary = {
  dataset_id: string;
  created_at?: string | null;
  organization_id?: string | null;
  workspace_id?: string | null;
  file_name: string;
  file_type: string;
  row_count: number;
  column_count: number;
  columns?: string[];
  business_model: string | null;
  business_model_label: string | null;
  business_model_confidence: number;
  analysis_status?: string;
  analysis_status_reason?: string | null;
  quality_issues: number;
  capabilities?: unknown;
  supported_concepts?: string[];
};

export type MobileContext = {
  user: AuthUser;
  latest_datasets: Record<string, DatasetSummary>;
};

export type Evidence = {
  metric: string;
  value?: number | null;
  comparison_value?: number | null;
  calculation: string;
  scope: string;
  source_fields: string[];
  source_records: string[];
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

export type Overview = {
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

export type ActionItem = {
  id: string;
  priority: string;
  status: string;
  title: string;
  action: string;
  owner: string;
  rationale: string;
  expected_outcome: string;
  metric: string;
  display_value: string;
  evidence: Evidence;
  source_insight_id: string;
};

export type ActionsResponse = {
  dataset_id: string;
  business_model: string | null;
  business_model_label: string | null;
  headline: string;
  summary: string;
  actions: ActionItem[];
};

export type InsightItem = {
  id: string;
  kind: string;
  severity: string;
  title: string;
  what_changed: string;
  why_it_matters: string;
  recommendation: string;
  metric: string;
  value?: number | null;
  display_value: string;
  evidence: Evidence;
  priority_score?: number | null;
  impact_score?: number | null;
  urgency_score?: number | null;
  evidence_score?: number | null;
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

export type AskAnswer = {
  status: string;
  text: string;
  confidence: string;
  evidence?: Evidence | null;
};

export type AskFollowUp = {
  label: string;
  question: string;
};

export type AskResponse = {
  dataset_id: string;
  question: string;
  business_model: string | null;
  business_model_label: string | null;
  answer: AskAnswer;
  follow_ups: AskFollowUp[];
  explore_metric?: string | null;
  explore_dimension?: string | null;
  supported_summary?: string | null;
  analytical_plan?: Record<string, unknown> | null;
};

export type ReportResponse = {
  dataset_id: string;
  file_name: string;
  business_model: string | null;
  business_model_label: string | null;
  scope_label: string;
  title: string;
  executive_summary: string;
  generated_at: string;
  metrics: OverviewMetric[];
  what_changed: string[];
  attention: OverviewInsight[];
  opportunities: OverviewInsight[];
  actions: ActionItem[];
  source_note: string;
};

export type AlertRule = {
  rule_id: string;
  dataset_id: string;
  session_id: string;
  name: string;
  metric: string;
  operator: string;
  threshold: number;
  cadence: string;
  scope_label: string;
  active: boolean;
  created_at: string;
  last_evaluated_at?: string | null;
  due: boolean;
  next_due_at?: string | null;
};

export type AlertEvent = {
  event_id: string;
  rule_id: string;
  dataset_id: string;
  session_id: string;
  status: string;
  metric: string;
  value?: number | null;
  threshold: number;
  operator: string;
  title: string;
  message: string;
  scope_label: string;
  evidence: Evidence;
  evaluated_at: string;
};

export type AlertsResponse = {
  dataset_id: string;
  business_model: string | null;
  business_model_label: string | null;
  scope_label: string;
  rules: AlertRule[];
  events: AlertEvent[];
};

export type SavedIntelligence = {
  id: string;
  dataset_id: string;
  session_id: string;
  name: string;
  kind: string;
  title: string;
  summary: string;
  metric: string;
  metric_label: string;
  dimension?: string | null;
  dimension_label?: string | null;
  value?: number | null;
  display_value: string;
  scope_label: string;
  source_workspace: string;
  source_id: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type SavedResponse = {
  dataset_id: string;
  business_model: string | null;
  business_model_label: string | null;
  scope_label: string;
  items: SavedIntelligence[];
};

export type Plan = {
  id: string;
  name: string;
  price_usd_monthly: number;
  max_seats: number;
  max_workspaces: number;
};

export type Billing = {
  provider: string;
  checkout_ready: boolean;
  customer_portal_available: boolean;
  paddle_environment: "sandbox" | "live" | null;
};

export type CommercialEntitlements = {
  plan: Plan;
  access: {
    status: string;
    trial: boolean;
    trial_ends_at?: string | null;
    subscription_id?: string | null;
  };
  usage: Record<string, { used: number; limit: number }>;
  billing: Billing;
};

export type AnalysisSession = {
  session_id: string;
  dataset_id: string;
  organization_id?: string | null;
  workspace_id?: string | null;
  scope?: { filters: Array<{ field: string; operator: string; values: string[] }> };
};
