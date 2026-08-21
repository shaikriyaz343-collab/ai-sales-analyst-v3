# AI Business Analyst v3

An evidence-first business analysis app for CSV/XLSX/XLS files.

## What is different in v3

The application is capability-first rather than report-template-first.
It detects what the file can actually support, builds a Business Brief, ranks material signals, and lets the user investigate those signals with a verified Q&A workflow.

### Core flow

Upload → Understand → Analyze → Business Brief → What Needs Attention → Explore → Investigate → Executive Report

### Trust contract

- The app separates schema match from data coverage.
- Small datasets are explicitly marked directional.
- Metrics are calculated from detected fields; unsupported metrics are not fabricated.
- The Q&A surface states scope, calculation, source fields, and limitations.
- Q&A uses the full uploaded file by default.
- Dashboard filters are opt-in and can be used explicitly for scoped questions.

### Supported business patterns

- Transactional / Retail Sales
- Sales Pipeline
- Subscription / Recurring Revenue
- Services / Professional Services

The app also unlocks additional capability modules when fields exist, including products, customers, regions, channels, payments, discounts, returns, order status, and costs/margin.

## Windows quick start

Run `run_app.bat`, or use:

```text
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

## Test data

The `samples/` folder contains representative files for:

- retail.csv
- pipeline.csv
- subscription.csv
- services.csv

## Release validation

The package contains 28 regression tests. The current validation suite passed.

The environment used to produce this package does not provide a working Streamlit browser runtime, so the last validation step should always be a real browser walkthrough before deployment.
