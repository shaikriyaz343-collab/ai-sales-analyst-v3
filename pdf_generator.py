
from __future__ import annotations

import html
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _safe_text(value) -> str:
    return html.escape(str(value))


def _paragraph(text, style):
    return Paragraph(
        _safe_text(text).replace("\n", "<br/>"),
        style
    )


def _add_bullets(story, items, normal_style, bullet_style):
    for item in items or []:
        story.append(
            Paragraph(
                f"&bull; {_safe_text(item)}",
                bullet_style
            )
        )
        story.append(Spacer(1, 4))


def generate_pdf(
    report,
    output_file,
    ai_insights,
    business_name="ABC Coffee Roasters",
):
    """
    Generate the executive PDF using the same verified report,
    deterministic BI findings, and AI Analyst output shown in the dashboard.
    """

    kpis = report["kpis"]
    products = report["products"]
    customers = report["customers"]
    monthly = report["monthly"]

    business_findings = report.get(
        "business_findings",
        {}
    )

    priority_findings = business_findings.get(
        "priority_findings",
        []
    )

    positive_findings = business_findings.get(
        "positive_findings",
        []
    )

    reporting_period = report.get(
        "reporting_period"
    )

    doc = SimpleDocTemplate(
        output_file,
        pagesize=letter,
        rightMargin=42,
        leftMargin=42,
        topMargin=42,
        bottomMargin=42,
        title=f"{business_name} Business Performance Report",
        author="AI Business Analytics",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        spaceBefore=8,
        spaceAfter=10,
    )

    subheading_style = ParagraphStyle(
        "ReportSubheading",
        parent=styles["Heading3"],
        spaceBefore=6,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["BodyText"],
        leading=14,
        spaceAfter=4,
    )

    small_style = ParagraphStyle(
        "ReportSmall",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
        spaceAfter=3,
    )

    bullet_style = ParagraphStyle(
        "ReportBullet",
        parent=normal_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=4,
    )

    signal_style = ParagraphStyle(
        "SignalText",
        parent=normal_style,
        leading=13,
        spaceAfter=2,
    )

    story = []

    # -------------------------
    # Cover / Title
    # -------------------------

    story.append(
        Paragraph(
            _safe_text(business_name),
            title_style
        )
    )

    story.append(
        Paragraph(
            "AI Business Performance Report",
            subtitle_style
        )
    )

    if reporting_period:

        start = reporting_period.get("start")
        end = reporting_period.get("end")

        if start is not None and end is not None:

            story.append(
                Paragraph(
                    (
                        f"<b>Reporting Period:</b> "
                        f"{_safe_text(start.strftime('%B %d, %Y'))} "
                        f"to "
                        f"{_safe_text(end.strftime('%B %d, %Y'))}"
                    ),
                    normal_style
                )
            )

            story.append(Spacer(1, 10))

    # -------------------------
    # Executive Summary
    # -------------------------

    story.append(
        Paragraph(
            "Executive Summary",
            heading_style
        )
    )

    executive_summary = ""

    if isinstance(ai_insights, dict):

        executive_summary = ai_insights.get(
            "executive_summary",
            ""
        )

    elif isinstance(ai_insights, str):

        executive_summary = ai_insights

    if executive_summary:

        story.append(
            _paragraph(
                executive_summary,
                normal_style
            )
        )

    else:

        story.append(
            _paragraph(
                "No executive summary was generated.",
                normal_style
            )
        )

    story.append(Spacer(1, 10))

    # -------------------------
    # Key Metrics
    # -------------------------

    story.append(
        Paragraph(
            "Key Metrics",
            heading_style
        )
    )

    metrics = [
        ["Metric", "Value"],
        [
            "Total Revenue",
            f"${kpis['total_revenue']:,.2f}"
        ],
        [
            "Total Orders",
            f"{kpis['total_orders']:,}"
        ],
        [
            "Total Items Sold",
            f"{kpis['total_quantity']:,}"
        ],
        [
            "Average Order Value",
            f"${kpis['average_order_value']:,.2f}"
        ],
    ]

    metrics_table = Table(
        metrics,
        colWidths=[3.6 * inch, 2.2 * inch]
    )

    metrics_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#EAF0F6"),
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.HexColor("#17324D"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#AAB7C4"),
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
        ])
    )

    story.append(metrics_table)
    story.append(Spacer(1, 15))

    # -------------------------
    # Business Signals
    # -------------------------

    story.append(
        Paragraph(
            "Priority Business Findings",
            heading_style
        )
    )

    if priority_findings:

        for finding in priority_findings:

            message = finding.get(
                "message",
                "Priority business finding."
            )

            driver = finding.get(
                "primary_driver"
            )

            why_it_matters = finding.get(
                "why_it_matters",
                ""
            )

            driver_products = finding.get(
                "driver_product_text",
                ""
            )

            detail = (
                f"<b>{_safe_text(message)}</b>"
                f"<br/>"
                f"Primary measurable driver: "
                f"{_safe_text(driver or 'Not isolated')}"
            )

            if driver_products:

                if driver == "order volume":

                    label = "Products driving order volume"

                else:

                    label = (
                        "Product-level revenue movement "
                        "during the period"
                    )

                detail += (
                    f"<br/>{_safe_text(label)}: "
                    f"{_safe_text(driver_products)}"
                )

            if why_it_matters:

                detail += (
                    f"<br/>Why it matters: "
                    f"{_safe_text(why_it_matters)}"
                )

            story.append(
                Paragraph(
                    detail,
                    signal_style
                )
            )

            story.append(Spacer(1, 7))

    else:

        story.append(
            _paragraph(
                "No priority business findings were triggered "
                "for the selected reporting period.",
                normal_style
            )
        )

    if positive_findings:

        story.append(
            Paragraph(
                "Positive Movements",
                subheading_style
            )
        )

        for finding in positive_findings:

            story.append(
                Paragraph(
                    (
                        f"&bull; "
                        f"{_safe_text(finding.get('message', ''))}"
                        f" "
                        f"{_safe_text(finding.get('why_it_matters', ''))}"
                    ),
                    bullet_style
                )
            )

    story.append(Spacer(1, 12))

    # -------------------------
    # AI Analyst
    # -------------------------

    # Keep the section heading with its content instead of leaving
    # the heading at the bottom of a page.
    story.append(PageBreak())

    story.append(
        Paragraph(
            "AI Analyst",
            heading_style
        )
    )

    if isinstance(ai_insights, dict):

        story.append(
            Paragraph(
                "Key Insights",
                subheading_style
            )
        )

        _add_bullets(
            story,
            ai_insights.get(
                "key_insights",
                []
            ),
            normal_style,
            bullet_style
        )

        story.append(
            Paragraph(
                "Recommendations",
                subheading_style
            )
        )

        _add_bullets(
            story,
            ai_insights.get(
                "recommendations",
                []
            ),
            normal_style,
            bullet_style
        )

        story.append(
            Paragraph(
                "Product Insights",
                subheading_style
            )
        )

        _add_bullets(
            story,
            ai_insights.get(
                "product_insights",
                []
            ),
            normal_style,
            bullet_style
        )

        story.append(
            Paragraph(
                "Customer Insights",
                subheading_style
            )
        )

        _add_bullets(
            story,
            ai_insights.get(
                "customer_insights",
                []
            ),
            normal_style,
            bullet_style
        )

        story.append(
            Paragraph(
                "Monthly Insights",
                subheading_style
            )
        )

        _add_bullets(
            story,
            ai_insights.get(
                "monthly_insights",
                []
            ),
            normal_style,
            bullet_style
        )

    story.append(PageBreak())

    # -------------------------
    # Product Performance
    # -------------------------

    story.append(
        Paragraph(
            "Product Performance",
            heading_style
        )
    )

    product_rows = [
        [
            "Product",
            "Orders",
            "Items",
            "Revenue",
            "Revenue %",
        ]
    ]

    for product, row in products.iterrows():

        product_rows.append([
            _safe_text(product),
            f"{int(row['orders']):,}",
            f"{int(row['quantity_sold']):,}",
            f"${row['revenue']:,.2f}",
            f"{row['revenue_percentage']:.2f}%",
        ])

    product_table = Table(
        product_rows,
        repeatRows=1,
        colWidths=[
            1.55 * inch,
            0.75 * inch,
            0.75 * inch,
            1.2 * inch,
            1.0 * inch,
        ]
    )

    product_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#EAF0F6"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#B5C0CA"),
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8.5,
            ),
        ])
    )

    story.append(product_table)
    story.append(Spacer(1, 15))

    # -------------------------
    # Customer Performance
    # -------------------------

    story.append(
        Paragraph(
            "Customer Performance - Top 10",
            heading_style
        )
    )

    customer_rows = [
        [
            "Customer",
            "Orders",
            "Items",
            "Revenue",
            "Revenue %",
        ]
    ]

    for customer, row in customers.head(10).iterrows():

        customer_rows.append([
            _safe_text(customer),
            f"{int(row['orders']):,}",
            f"{int(row['quantity_purchased']):,}",
            f"${row['revenue']:,.2f}",
            f"{row['revenue_percentage']:.2f}%",
        ])

    customer_table = Table(
        customer_rows,
        repeatRows=1,
        colWidths=[
            1.55 * inch,
            0.75 * inch,
            0.75 * inch,
            1.2 * inch,
            1.0 * inch,
        ]
    )

    customer_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#EAF0F6"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#B5C0CA"),
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8.5,
            ),
        ])
    )

    story.append(customer_table)
    story.append(Spacer(1, 15))

    # -------------------------
    # Monthly Performance
    # -------------------------

    story.append(
        Paragraph(
            "Monthly Performance",
            heading_style
        )
    )

    monthly_rows = [
        [
            "Month",
            "Revenue",
            "Orders",
            "Items",
        ]
    ]

    for month, row in monthly.iterrows():

        monthly_rows.append([
            _safe_text(month),
            f"${row['revenue']:,.2f}",
            f"{int(row['orders']):,}",
            f"{int(row['quantity']):,}",
        ])

    monthly_table = Table(
        monthly_rows,
        repeatRows=1,
        colWidths=[
            1.6 * inch,
            1.6 * inch,
            1.2 * inch,
            1.2 * inch,
        ]
    )

    monthly_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#EAF0F6"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.HexColor("#B5C0CA"),
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8.5,
            ),
        ])
    )

    story.append(monthly_table)

    # -------------------------
    # Build PDF
    # -------------------------

    os.makedirs(
        os.path.dirname(output_file) or ".",
        exist_ok=True
    )

    doc.build(story)

    print(
        f"PDF created: {output_file}"
    )
