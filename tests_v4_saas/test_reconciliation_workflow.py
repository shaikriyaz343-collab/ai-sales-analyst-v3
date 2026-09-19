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

    assert "push:" in workflow
    assert "v4/saas-foundation" in workflow
    assert "workflow_dispatch:" in workflow
    assert "RELEASE_SHA:" in workflow
    assert "currentSha" in workflow
    assert "targetSha" in workflow
    assert "v4-development-ci.yml" in workflow
    assert "browser-qa.yml" in workflow
    assert "v4-production-probe.yml" in workflow
    assert "workflowPath = '.github/workflows/' + workflowFile" in workflow
    assert "run.path === workflowPath" in workflow
    assert "response.data.workflow_runs" in workflow
    assert "github.rest.actions.listWorkflowRunsForRepo" in workflow
    assert "run && run.path === workflowPath" in workflow
    assert "observationWorkflowPath" in workflow
    assert "run.path === observationWorkflowPath" in workflow
    assert "workflow_id: workflowFile" not in workflow
    assert "release_ready" in workflow
    assert "run.head_sha === targetSha" in workflow
    assert "actions: read" in workflow
    assert "issues: read" in workflow
    assert "state: 'closed'" not in workflow


def test_release_probe_evidence_uses_python_literals() -> None:
    probe = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "v4-production-probe.yml"
    ).read_text(encoding="utf-8")

    assert '"release_candidate_probe": True,' in probe
    assert '"release_candidate_probe": true,' not in probe


def test_browser_qa_waits_for_the_current_public_release_marker() -> None:
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "browser-qa.yml"
    ).read_text(encoding="utf-8")

    assert "Wait for deployed V4 release markers" in workflow
    assert "expected public application marker" in workflow
    assert 'grep -Fq "<title>AI Sales Analyst | AI Revenue Analyst</title>" /tmp/v4-home.html' in workflow
    assert "V4 frontend/API are reachable and the public application marker is live." in workflow

def test_metered_product_routes_use_hard_quota_slots() -> None:
    main = (
        Path(__file__).parents[1]
        / "backend"
        / "api"
        / "main.py"
    ).read_text(encoding="utf-8")

    expected = {
        "profile_upload": '"dataset_uploads"',
        "ask": '"analyst_questions"',
        "report": '"reports"',
        "create_alert": '"monitoring_rules"',
        "save": '"saved_intelligence"',
    }

    for function_name, metric in expected.items():
        marker = f"def {function_name}("
        start = main.index(marker)
        next_route = main.find("\n@app.", start + len(marker))
        section = main[start:] if next_route == -1 else main[start:next_route]
        assert "with _commercial_usage_slot" in section, function_name
        assert metric in section, f"{function_name} metric mapping"


def test_auth_screen_syncs_query_selected_signup_mode() -> None:
    auth = (
        Path(__file__).parents[1]
        / "frontend"
        / "components"
        / "auth-screen.tsx"
    ).read_text(encoding="utf-8")

    assert "useEffect" in auth
    assert "setMode(initialMode)" in auth
    assert "[initialMode]" in auth
