from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SemanticSummary(BaseModel):
    """What the validated dataset means; kept separate from product capabilities."""

    fields: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)


class CapabilitySet(BaseModel):
    """Product workspaces and validated business-specific capabilities."""

    workspaces: list[str] = Field(default_factory=list)
    analytics: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)




class ScopeFilter(BaseModel):
    field: str
    operator: str = "in"
    values: list[str] = Field(default_factory=list)


class ScopeState(BaseModel):
    filters: list[ScopeFilter] = Field(default_factory=list)


class ScopeValue(BaseModel):
    value: str
    label: str


class ScopeValuesResponse(BaseModel):
    field: str
    values: list[ScopeValue] = Field(default_factory=list)


class AnalysisSession(BaseModel):
    session_id: str
    dataset_id: str
    scope: ScopeState = Field(default_factory=ScopeState)
    active_analysis: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None

class DatasetSummary(BaseModel):
    dataset_id: str
    file_name: str
    file_type: str
    row_count: int
    column_count: int
    columns: list[str]
    business_model: str | None
    business_model_label: str | None
    business_model_confidence: float
    quality_issues: int
    semantic: SemanticSummary = Field(default_factory=SemanticSummary)
    capabilities: CapabilitySet = Field(default_factory=CapabilitySet)
    # Backward-compatible alias retained for existing clients/tests.
    supported_concepts: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    product: str
    version: str


class ErrorResponse(BaseModel):
    detail: str


class OnboardingResponse(BaseModel):
    dataset: DatasetSummary
    message: str
    session_id: str | None = None


class Evidence(BaseModel):
    metric: str
    value: float | None = None
    comparison_value: float | None = None
    calculation: str
    scope: str = "All data"
    source_fields: list[str] = Field(default_factory=list)


class OverviewMetric(BaseModel):
    id: str
    label: str
    value: float | None
    display_value: str
    delta_pct: float | None = None
    delta_label: str | None = None
    tone: str = "neutral"
    evidence: Evidence


class OverviewInsight(BaseModel):
    id: str
    severity: str
    title: str
    summary: str
    why_it_matters: str
    recommendation: str
    evidence: Evidence


class OverviewResponse(BaseModel):
    dataset_id: str
    business_model: str | None
    business_model_label: str | None
    scope_label: str = "All data"
    headline: str
    subheadline: str
    metrics: list[OverviewMetric] = Field(default_factory=list)
    what_changed: list[str] = Field(default_factory=list)
    attention: list[OverviewInsight] = Field(default_factory=list)
    opportunities: list[OverviewInsight] = Field(default_factory=list)


class ExploreOption(BaseModel):
    id: str
    label: str


class ExploreRow(BaseModel):
    key: str
    value: float
    display_value: str
    share_pct: float | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ExploreResponse(BaseModel):
    dataset_id: str
    scope_label: str = "All data"
    business_model: str | None
    business_model_label: str | None
    metric: str
    metric_label: str
    dimension: str
    dimension_label: str
    total_value: float | None
    total_display_value: str
    available_metrics: list[ExploreOption] = Field(default_factory=list)
    available_dimensions: list[ExploreOption] = Field(default_factory=list)
    rows: list[ExploreRow] = Field(default_factory=list)


class InsightItem(BaseModel):
    id: str
    kind: str
    severity: str
    title: str
    what_changed: str
    why_it_matters: str
    recommendation: str
    metric: str
    value: float | None = None
    display_value: str
    evidence: Evidence


class InsightsResponse(BaseModel):
    dataset_id: str
    business_model: str | None
    business_model_label: str | None
    scope_label: str = "All data"
    headline: str
    summary: str
    insights: list[InsightItem] = Field(default_factory=list)


class AskEvidence(BaseModel):
    metric: str
    value: float | None = None
    comparison_value: float | None = None
    calculation: str
    scope: str = "All data"
    source_fields: list[str] = Field(default_factory=list)


class AskFollowUp(BaseModel):
    label: str
    question: str


class AskAnswer(BaseModel):
    status: str
    text: str
    confidence: str = "high"
    evidence: AskEvidence | None = None


class AskResponse(BaseModel):
    dataset_id: str
    question: str
    business_model: str | None
    business_model_label: str | None
    answer: AskAnswer
    follow_ups: list[AskFollowUp] = Field(default_factory=list)
    explore_metric: str | None = None
    explore_dimension: str | None = None
    supported_summary: str | None = None

class ActionItem(BaseModel):
    id: str
    priority: str
    status: str = "open"
    title: str
    action: str
    owner: str
    rationale: str
    expected_outcome: str
    metric: str
    display_value: str
    evidence: Evidence
    source_insight_id: str


class ActionsResponse(BaseModel):
    dataset_id: str
    business_model: str | None
    business_model_label: str | None
    headline: str
    summary: str
    actions: list[ActionItem] = Field(default_factory=list)


class AlertRule(BaseModel):
    rule_id: str
    dataset_id: str
    session_id: str
    name: str
    metric: str
    operator: str
    threshold: float
    cadence: str = "manual"
    scope_label: str = "All data"
    active: bool = True
    created_at: str
    last_evaluated_at: str | None = None


class AlertEvent(BaseModel):
    event_id: str
    rule_id: str
    dataset_id: str
    session_id: str
    status: str
    metric: str
    value: float | None = None
    threshold: float
    operator: str
    title: str
    message: str
    scope_label: str
    evidence: Evidence
    evaluated_at: str


class AlertsResponse(BaseModel):
    dataset_id: str
    business_model: str | None
    business_model_label: str | None
    scope_label: str = "All data"
    rules: list[AlertRule] = Field(default_factory=list)
    events: list[AlertEvent] = Field(default_factory=list)


class AlertRuleCreate(BaseModel):
    name: str = ""
    metric: str
    operator: str
    threshold: float
    cadence: str = "manual"


class ReportResponse(BaseModel):
    dataset_id: str
    file_name: str
    business_model: str | None
    business_model_label: str | None
    scope_label: str = "All data"
    title: str
    executive_summary: str
    generated_at: str
    metrics: list[OverviewMetric] = Field(default_factory=list)
    what_changed: list[str] = Field(default_factory=list)
    attention: list[OverviewInsight] = Field(default_factory=list)
    opportunities: list[OverviewInsight] = Field(default_factory=list)
    actions: list[ActionItem] = Field(default_factory=list)
    source_note: str
