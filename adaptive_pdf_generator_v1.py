
from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def generate_adaptive_pdf(
    output_file: str | Path,
    business_name: str,
    business_type: dict[str, Any],
    profile: dict[str, Any],
    analysis: dict[str, Any],
    quality: dict[str, Any],
    packs: dict[str, Any],
    business_brief: dict[str, Any] | None = None,
):
    output_file = str(output_file)

    doc = SimpleDocTemplate(
        output_file,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=f"{business_name} Business Report",
        author="AI Business Analyst",
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            business_name,
            styles["Title"],
        )
    )
    story.append(
        Paragraph(
            "AI Business Analysis Report",
            styles["Heading2"],
        )
    )
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            f"<b>Business type:</b> "
            f"{business_type.get('primary_label', 'Business data')}",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "<b>Data quality:</b> "
            + quality.get(
                "quality_status",
                "unknown",
            ),
            styles["BodyText"],
        )
    )

    if business_brief:
        coverage = business_brief.get("coverage", {})
        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                f"<b>Data coverage:</b> {coverage.get('coverage_label', 'Unknown')} — "
                f"{coverage.get('rows', 0):,} rows × {coverage.get('source_columns', coverage.get('columns', 0)):,} source fields; "
                f"period: {coverage.get('period', 'uploaded data')}",
                styles["BodyText"],
            )
        )

        signals = business_brief.get("signals", [])[:3]
        if signals:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Executive takeaways", styles["Heading2"]))
            for signal in signals:
                title = signal.get("title", signal.get("message", "Review this finding."))
                story.append(Paragraph(f"<b>{title}</b>", styles["BodyText"]))
                if signal.get("why_it_matters"):
                    story.append(Paragraph(f"Why it matters: {signal['why_it_matters']}", styles["BodyText"]))
                if signal.get("recommended_action"):
                    story.append(Paragraph(f"Recommended action: {signal['recommended_action']}", styles["BodyText"]))
                story.append(Spacer(1, 5))

    # Overview metrics.
    sales = analysis.get(
        "modules",
        {},
    ).get(
        "sales_performance"
    )

    if sales and sales.get("available"):
        story.append(
            Paragraph(
                "Performance overview",
                styles["Heading2"],
            )
        )

        metrics = sales.get(
            "metrics",
            {},
        )

        table = Table(
            [
                ["Metric", "Value"],
                ["Recorded Revenue", f"${metrics.get('revenue', 0):,.2f}"],
                ["Orders", f"{metrics.get('orders', 0):,}"],
                ["Units", f"{metrics.get('quantity', 0):,.0f}"],
                ["Average Order Value", f"${metrics.get('aov', 0):,.2f}"],
            ],
            colWidths=[220, 220],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                    ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                    ("PADDING", (0,0), (-1,-1), 6),
                ]
            )
        )
        story.append(table)

        returns_module = (
            analysis.get("modules", {}).get("returns")
        )
        if returns_module and returns_module.get("available"):
            story.append(
                Paragraph(
                    "Revenue is the recorded transaction value in the uploaded data. "
                    "Return activity is reported separately and should not be interpreted "
                    "as net realized sales unless the source contains a dedicated net-sales field.",
                    styles["BodyText"],
                )
            )

        story.append(Spacer(1, 12))

    # Adaptive modules.
    for key, module in analysis.get(
        "modules",
        {},
    ).items():

        if not module.get("available"):
            continue

        # A module can be semantically recognized but contain no usable values
        # (for example a blank Region column). Do not render empty headings.
        metrics = module.get("metrics", {}) or {}
        ranked_values = module.get("ranked_values") or []
        top_values = (
            module.get("top_products")
            or module.get("top_customers")
            or module.get("stage_breakdown")
            or module.get("customer_breakdown")
            or module.get("client_breakdown")
            or module.get("employee_breakdown")
            or ranked_values
        )
        if not metrics and not top_values:
            continue

        title = module.get(
            "title",
            key.replace("_", " ").title(),
        )

        if key in {
            "data_quality",
            "sales_performance",
        }:
            continue

        story.append(
            Paragraph(
                title,
                styles["Heading2"],
            )
        )

        rows = [
            ["Metric", "Value"]
        ]

        for metric, value in metrics.items():

            if metric == "return_amount_is_estimated":
                continue

            if isinstance(value, float):
                if "pct" in metric:
                    display = f"{value:.1f}%"
                else:
                    display = f"{value:,.2f}"
            else:
                display = str(value)

            label = metric.replace("_", " ").title()
            if metric == "return_amount" and metrics.get("return_amount_is_estimated"):
                label = "Estimated Return Amount"

            rows.append(
                [
                    label,
                    display,
                ]
            )

        if metrics.get("return_amount_is_estimated"):
            rows.append(
                [
                    "Basis",
                    "Estimated from revenue on rows marked returned; no separate return-amount field was provided.",
                ]
            )

        if len(rows) > 1:
            table = Table(
                rows,
                colWidths=[220, 220],
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                        ("PADDING", (0,0), (-1,-1), 6),
                    ]
                )
            )
            story.append(table)

        if top_values:
            story.append(
                Spacer(1, 4)
            )
            story.append(
                Paragraph(
                    "Top breakdown",
                    styles["Heading3"],
                )
            )

            columns = list(top_values[0].keys())

            table_rows = [
                [
                    column.replace("_", " ").title()
                    for column in columns
                ]
            ]

            for row in top_values[:10]:
                table_rows.append(
                    [
                        str(row.get(column, ""))
                        for column in columns
                    ]
                )

            table = Table(
                table_rows,
                repeatRows=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                        ("PADDING", (0,0), (-1,-1), 5),
                    ]
                )
            )
            story.append(table)

        story.append(
            Spacer(1, 12)
        )

    # Pipeline / subscription / services pack information.
    for pack_name, pack in packs.get(
        "packs",
        {},
    ).items():

        if not pack.get("available"):
            continue

        # Transactional Sales is already represented by the adaptive sales
        # performance module. The pack is a compatibility container, not a
        # separate report section.
        if pack_name == "transactional_sales":
            continue

        story.append(
            Paragraph(
                pack.get(
                    "title",
                    pack_name.replace("_", " ").title(),
                ),
                styles["Heading2"],
            )
        )

        metrics = pack.get("metrics", {})

        for metric, value in metrics.items():
            if metric == "return_amount_is_estimated":
                continue
            display = (
                f"{value:.1f}%"
                if isinstance(value, float) and "pct" in metric
                else f"{value:,.2f}"
                if isinstance(value, float)
                else str(value)
            )
            label = metric.replace("_", " ").title()
            if metric == "return_amount" and metrics.get("return_amount_is_estimated"):
                label = "Estimated Return Amount"

            story.append(
                Paragraph(
                    f"<b>{label}:</b> {display}",
                    styles["BodyText"],
                )
            )
        if metrics.get("return_amount_is_estimated"):
            story.append(
                Paragraph(
                    "Estimated from revenue on rows marked returned; no separate return-amount field was provided.",
                    styles["BodyText"],
                )
            )

        story.append(
            Spacer(1, 8)
        )

    story.append(
        Paragraph(
            "This report reflects the fields available in the uploaded file. "
            "The absence of a metric means the source data did not provide the "
            "information needed to calculate it.",
            styles["BodyText"],
        )
    )

    doc.build(story)

    return output_file
