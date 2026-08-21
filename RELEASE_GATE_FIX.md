Release-gate fix

The "Deprecated Streamlit API — clean" diagnostic was falsely failing because
the diagnostic/test source itself contains the string "use_container_width" as
the term being searched for.

The release gate now scans only production application Python files and excludes
runtime diagnostics and tests. This is a diagnostics correction, not a change
to production UI behavior.

Validation:
- 34 tests passed.
- Release-gate false-positive check passed.
