# Debug Four-Methods Comparison

Generated: 2026-06-09T07:50:00.986220+00:00

Parameters: `--debug --debug_threads 20 --debug_agents 20 --debug_cohorts 2`

## Summary Table

| Method | Status | LLM Calls | Tokens | Runtime(s) | Size MAE | User F1 | Cohort JS | Cohort KL |
|--------|--------|-----------|--------|------------|----------|---------|-----------|-----------|
| MF-DAG | success | 40 | 57925 | 370.34 | 1.0 | 0.0 | 0.25 | 6.9078 |
| Mean-Field-LLM | success | 40 | 48662 | 337.84 | 1.1667 | 0.0 | 0.0 | 0.0 |
| Full LLM-Agent | skipped | - | - | - | - | - | - | - |
| Rule-based Agent | skipped | - | - | - | - | - | - | - |

## MF-DAG vs Mean-Field-LLM (memory value)
- User F1 delta (MF-DAG - MF-LLM): 0.0
- Size MAE delta: -0.1667
- Cohort JS delta: 0.25

## Run Directories

- **MF-DAG**: `/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/outputs/runs/mfdag_20260609_073631_9df670` (success)
- **Mean-Field-LLM**: `/Users/fgod/Desktop/FGOD/MF-DAG/MF-DAG/outputs/runs/mean_field_llm_20260609_074243_0da4ae` (success)
- **Full LLM-Agent**: `N/A` (skipped)
  - Error: skipped by user request
- **Rule-based Agent**: `N/A` (skipped)
  - Error: skipped by user request

## Notes
- Metrics computed on eval split (last 30% threads, ~6 steps for 20 threads).
- `user_f1` may be 0 under one_step setting when sim predicts many users but real next user is exactly 1.
- Prefer `continuation_size_mae` and cohort JS/KL for interpretation.
