from __future__ import annotations

from pydantic import BaseModel, Field


class SemanticSummary(BaseModel):
    """What the validated dataset means; kept separate from product capabilities."""

    fields: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)


class CapabilitySet(BaseModel):
    workspaces: list[str] = Field(default_factory=list)
    analytics: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)


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
