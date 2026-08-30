# V4 Reconciliated Architecture Checkpoint

This checkpoint consolidates the V4 SaaS source around one shared analytical contract and one frontend workspace model.

## Workspaces
- overview
- explore
- insights
- ask
- actions
- reports
- monitoring
- saved

## Source of truth
The backend owns validated dataset semantics, capabilities, deterministic metrics, evidence, insights, answers, and actions. The frontend renders those contracts and keeps navigation separate from analytical state.

## Action invariant
Every action is derived from an existing validated Overview insight and carries the same evidence object.

## Validation gate
Run the complete Python regression suite and the Next.js production build before accepting this checkpoint. Browser acceptance is required for every workspace before a feature is marked complete.
