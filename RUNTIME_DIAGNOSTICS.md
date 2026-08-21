# Live Runtime Diagnostics

This build contains an optional diagnostic panel that runs inside the same
Streamlit process serving the application.

## Enable it

Open the app with:

`?diagnostics=1`

Example:

`https://YOUR-APP.streamlit.app/?diagnostics=1`

Then click:

**Run full runtime self-test**

The diagnostics exercise the live application helpers against the four bundled
representative files:

- retail.csv
- pipeline.csv
- subscription.csv
- services.csv

They verify:
- upload/profile path
- business-type detection
- dashboard section planning
- report-context construction
- executive PDF generation
- retail factual Q&A
- Ask "Clear" / stale-answer safeguards
- Investigate-this navigation/execution contract
- review navigation state

The diagnostic panel is opt-in and is not shown during normal use.

This is a developer validation aid, not a substitute for a human browser
acceptance test.
