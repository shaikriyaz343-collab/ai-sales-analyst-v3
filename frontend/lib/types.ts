export type AuthWorkspace = { id: string; name: string };
export type AuthUser = {
  id: string; email: string; name: string; organization_id: string; organization_name: string;
  role: string; workspace_id: string; workspace_name: string; workspaces: AuthWorkspace[];
};

export type CapabilitySet = {
  workspaces: Workspace[];
  analytics: string[];
  modules: string[];
};

export type Workspace = "overview" | "explore" | "insights" | "ask" | "actions" | "reports" | "monitoring" | "saved";

export type ScopeFilter = { field: string; operator: "in" | "not_in" | "eq" | "neq"; values: string[] };
export type ScopeState = { filters: ScopeFilter[] };
export type AnalysisSession = { session_id: string; dataset_id: string; organization_id?: string | null; workspace_id?: string | null; scope: ScopeState; active_analysis?: Record<string, unknown> | null; comparison?: Record<string, unknown> | null };

export type DataQualityIssue = {
  severity: string;
  code: string;
  message: string;
  affected_rows: number;
  recommendation: string;
};
export type DataQualitySummary = {
  row_count: number;
  issue_count: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  quality_status: string;
  issues: DataQualityIssue[];
};

export type DatasetSummary = {
  dataset_id: string;
  organization_id?: string | null;
  workspace_id?: string | null;
  file_name: string;
  file_type: string;
  row_count: number;
  column_count: number;
  columns: string[];
  business_model: string | null;
  business_model_label: string | null;
  business_model_confidence: number;
  analysis_status?: "ready" | "needs_review" | string;
  analysis_status_reason?: string | null;
  quality_issues: number;
  quality?: DataQualitySummary | null;
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
export type ExploreEvidence = Evidence;
export type ExploreRow = {
  key: string;
  value: number;
  display_value: string;
  share_pct?: number | null;
  evidence: ExploreEvidence;
};
export type ExploreResponse = {
  dataset_id: string;
  scope_label: string;
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

export type ForecastMonthly = {
  month: string;
  expected_value: number;
  weighted_forecast: number;
  opportunities: number;
  evidence: Evidence;
};
export type ForecastResponse = {
  dataset_id: string;
  business_model: string | null;
  business_model_label: string | null;
  scope_label: string;
  weighted_forecast: number;
  open_pipeline_value: number;
  open_opportunities: number;
  has_probability: boolean;
  basis_note: string;
  evidence: Evidence;
  monthly_forecast: ForecastMonthly[];
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

export type AskEvidence = Evidence;
export type AskFollowUp = { label: string; question: string };
export type AskAnswer = { status: string; text: string; confidence: string; evidence?: AskEvidence | null };
export type AskResponse = {
  dataset_id: string; question: string; business_model: string | null; business_model_label: string | null;
  answer: AskAnswer; follow_ups: AskFollowUp[]; explore_metric?: string | null; explore_dimension?: string | null; supported_summary?: string | null;
  analytical_plan?: { intent: string; metric?: string | null; dimension?: string | null; direction?: string | null; evidence_requested?: boolean; supported?: boolean; reason?: string } | null;
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

export type ScopeValue = { value: string; label: string; count?: number | null; };
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
export type AlertEvent = { event_id: string; rule_id: string; dataset_id: string; session_id: string; status: string; metric: string; value?: number | null; threshold: number; operator: string; title: string; message: string; scope_label: string; evidence: Evidence; evaluated_at: string; };
export type AlertsResponse = { dataset_id: string; business_model: string | null; business_model_label: string | null; scope_label: string; rules: AlertRule[]; events: AlertEvent[]; };

export type SavedIntelligence = { id: string; dataset_id: string; session_id: string; name: string; kind: string; title: string; summary: string; metric: string; metric_label: string; dimension?: string | null; dimension_label?: string | null; value?: number | null; display_value: string; scope_label: string; scope_filters: ScopeFilter[]; evidence: Evidence; source_workspace: string; source_id: string; active: boolean; created_at: string; updated_at: string; };
export type SavedIntelligenceResponse = { dataset_id: string; business_model: string | null; business_model_label: string | null; scope_label: string; items: SavedIntelligence[]; };


export type CommercialPlan = {
  plan_id: string;
  name: string;
  price_usd_monthly: number;
  trial_days: number;
  max_seats: number;
  max_workspaces: number;
  monthly_limits: Record<string, number | null>;
  features: string[];
};

export type CommercialEntitlements = {
  organization_id: string;
  subscription: {
    plan_id: string | null;
    plan_name: string | null;
    access_active: boolean;
    access_reason: string;
    status: string;
    provider: string | null;
    provider_subscription_id: string | null;
  };
  entitlements: {
    max_seats: number;
    max_workspaces: number;
    features: string[];
    remaining: Record<string, number | null>;
  };
  usage_period_start: string | null;
  usage: Record<string, number>;
  catalog: CommercialPlan[];
  billing: {
    provider: string;
    checkout_ready: boolean;
    customer_portal_available: boolean;
  };
};
