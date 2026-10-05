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
  workspace_id?: string | null;
  file_name: string;
  file_type: string;
  row_count: number;
  column_count: number;
  business_model: string | null;
  business_model_label: string | null;
  business_model_confidence: number;
  analysis_status?: string;
  quality_issues: number;
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
  title: string;
  summary: string;
  recommendation: string;
  priority_score: number;
  impact_score: number;
  urgency_score: number;
  evidence_score: number;
  severity: string;
  evidence: Evidence;
  status: string;
};

export type ActionsResponse = {
  dataset_id: string;
  business_model_label: string | null;
  scope_label: string;
  actions: ActionItem[];
};

export type InsightsResponse = {
  dataset_id: string;
  business_model_label: string | null;
  scope_label: string;
  insights: OverviewInsight[];
};

export type AskResponse = {
  status: string;
  question: string;
  answer: string;
  evidence: Evidence[];
  suggested_followups: string[];
};

export type ReportResponse = {
  dataset_id: string;
  business_model_label: string | null;
  scope_label: string;
  headline: string;
  executive_summary: string;
  metrics: OverviewMetric[];
  insights: OverviewInsight[];
  actions: ActionItem[];
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
  business_model_label: string | null;
  scope_label: string;
  rules: AlertRule[];
  events: AlertEvent[];
};

export type SavedIntelligence = {
  item_id: string;
  name: string;
  source_workspace: string;
  source_id: string;
  title?: string | null;
  summary?: string | null;
  metric?: string | null;
  dimension?: string | null;
  created_at: string;
};

export type SavedResponse = {
  dataset_id: string;
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
  workspace_id?: string | null;
  organization_id?: string | null;
};
