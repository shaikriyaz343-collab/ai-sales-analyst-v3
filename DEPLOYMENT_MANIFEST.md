# Deployment Manifest — AI Business Analyst v3.3

Deploy the COMPLETE repository, preserving all files and directories.

Required runtime modules include:
- app.py
- scope_engine_v1.py
- schema_profiler_v2.py
- semantic_business_model_v2.py
- data_quality_engine_v1.py
- business_type_detector_v1.py
- adaptive_analysis_engine_v1.py
- business_analysis_packs_v1.py
- adaptive_dashboard_engine_v1.py
- sales_query_engine_v1.py
- business_intelligence.py
- analyst_intelligence_v2.py
- adaptive_pdf_generator_v1.py
- report_generator.py
- pdf_generator.py
- runtime_diagnostics.py
- samples/

Critical compatibility contract:
`scope_engine_v1.py` must provide `apply_scope_filters` and `available_scope_dimensions`.

The app also contains a defensive compatibility fallback for `available_scope_dimensions`,
but the canonical function must remain in scope_engine_v1.py.
