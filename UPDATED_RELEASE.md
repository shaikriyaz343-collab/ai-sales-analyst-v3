# v3 Runtime/UX Hardening Release

## Live-runtime warnings fixed
- Replaced deprecated Streamlit `use_container_width` calls with `width="stretch"`.
- Pinned Streamlit to the 1.61.x/1.62.x-compatible range and pyarrow below 25 so Cloud does not silently downgrade it.
- Disabled automatic function calling for direct Gemini structured/text generation calls because this app is not supplying tools to those calls.

## Review Your Business navigation
- Uses Streamlit segmented control consistently; no radio-button fallback.
- Navigation state is synchronized with session state.
- Programmatic navigation (for example, Investigate this -> Ask Your Business Analyst) updates both widget and session state.
- New file / new analysis resets the selected review section to Overview.

## Recording observations addressed
- The previous recording showed radio-style review controls and a long vertical page; the radio fallback is removed.
- Performance and Payments switched correctly, but the navigation looked like form controls; segmented navigation is now the standard UI.
- The recording also showed a stale/older Q&A wording (`selected reporting period`) and older button text; the current Q&A engine uses explicit uploaded-period scope and the current `Analyze my business` wording.

## Validation
- 28 regression tests pass.
- 21 runtime diagnostics pass in the live-runtime simulation.
- PDF generation passes for all four representative business files.
