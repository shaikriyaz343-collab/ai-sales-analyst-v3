from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "v4-commercial-reconciliation.yml"

def test_reconciliation_workflow_uses_live_actions_expressions() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert r"\${{" not in content
    assert "${{ vars.V4_BILLING_RECONCILIATION_URL" in content
    assert "${{ secrets.V4_BILLING_RECONCILIATION_TOKEN }}" in content
    assert 'curl -sS \\' in content
    assert "X-V4-Reconciliation-Token" in content

def test_reconciliation_workflow_allows_billing_disabled_noop() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "if [[ -z" not in content
    assert "V4_BILLING_RECONCILIATION_URL" in content
    assert 'status" != "200"' in content


def test_production_probe_owns_failure_alert_lifecycle() -> None:
    probe = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "v4-production-probe.yml"
    ).read_text(encoding="utf-8")

    assert "issues: write" in probe
    assert "Create or update production probe incident" in probe
    assert "Close recovered production probe incident" in probe
    assert "Automated V4 production probe failure" in probe

def test_production_observation_window_counts_completed_runs_only() -> None:
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "v4-production-observation-window.yml"
    ).read_text(encoding="utf-8")

    assert "const completedRuns = eligibleRuns.filter" in workflow
    assert "run.status === 'completed' && run.conclusion" in workflow
    assert "failed_completed_run_count" in workflow
    assert "incomplete_run_count" in workflow
    assert "pass: completedRuns.length >= minCompletedRuns" in workflow


def test_release_readiness_workflow_is_non_destructive_and_exact_sha_aware() -> None:
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "v4-release-readiness.yml"
    ).read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "RELEASE_SHA:" in workflow
    assert "currentSha" in workflow
    assert "targetSha" in workflow
    assert "v4-development-ci.yml" in workflow
    assert "browser-qa.yml" in workflow
    assert "v4-production-probe.yml" in workflow
    assert "release_ready" in workflow
    assert "run.head_sha === targetSha" in workflow
    assert "actions: read" in workflow
    assert "issues: read" in workflow
    assert "state: 'closed'" not in workflow
