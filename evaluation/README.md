# Scoring Reliability Evaluation Set

## Purpose

This evaluation set checks score reliability for the speaking scoring pipeline across IELTS Speaking Part 1, Part 2, and Part 3 responses at different target proficiency levels.

## Methodology

- We created 8 human-annotated transcript samples (`evaluation/samples/`) with expected scores for 5 dimensions:
  - `fluency_score`
  - `vocabulary_score`
  - `grammar_score`
  - `pronunciation_score`
  - `overall_score`
- Coverage includes lower, mid, and higher performance bands across all 3 speaking parts.
- The runner executes each sample **N=3** times through the real async `score_speaking` pipeline.
- For each dimension, we compute:
  - mean
  - standard deviation (run-to-run variability)
  - delta from human expected (`mean - expected`)

## How to Run

From repository root:

```bash
python evaluation/run_eval.py
```

If `python` is not available in your shell, use:

```bash
python3 evaluation/run_eval.py
```

## Sample Set

| ID | Part | Band | Transcript preview |
|---|---|---|---|
| S01 | part1 | band5 | "Uh, I think the internet is mostly good for people..." |
| S02 | part1 | band6.5 | "I generally prefer working in the morning because..." |
| S03 | part1 | band8 | "My hometown has changed dramatically over the past decade..." |
| S04 | part2 | band5 | "Um, I read a book last month, but I forgot the name..." |
| S05 | part2 | band6.5 | "I'd like to talk about a time when I helped my younger cousin..." |
| S06 | part2 | band8+ | "One place that left a lasting impression on me was Kyoto..." |
| S07 | part3 | band5.5 | "Well, I think online learning is easier for many people..." |
| S08 | part3 | band7 | "In general, I believe governments should prioritize public transport..." |

## Results

Run executed on: `2026-04-01`

- Output JSON: `evaluation/results/20260401_183747.json`
- Runtime status: API unavailable for scoring due expired Gemini API key (`API_KEY_INVALID`)

Actual runner summary output:

```text
ID  | band    | overall_expected | overall_mean | overall_stddev | overall_delta
----+---------+------------------+--------------+----------------+--------------
S01 | band5   | 5.00             | N/A          | N/A            | N/A
S02 | band6.5 | 6.50             | N/A          | N/A            | N/A
S03 | band8   | 8.00             | N/A          | N/A            | N/A
S04 | band5   | 5.00             | N/A          | N/A            | N/A
S05 | band6.5 | 6.50             | N/A          | N/A            | N/A
S06 | band8+  | 8.00             | N/A          | N/A            | N/A
S07 | band5.5 | 5.50             | N/A          | N/A            | N/A
S08 | band7   | 7.00             | N/A          | N/A            | N/A
```

## Observations

- All 24 scoring attempts (8 samples × 3 runs) failed with the same upstream error: `400 API key expired`.
- Because there were no successful runs, reliability metrics (mean/stddev/delta) are currently unavailable (`N/A`) for every sample.
- This run still validates runner behavior for failure handling:
  - failed runs are captured without crashing,
  - full error payloads are persisted in the result JSON,
  - summary output remains structured and comparable across samples.
- Once a valid API key is configured in `backend/.env`, rerunning the same command will produce real numeric reliability metrics.

## Known Limitations

- LLM non-determinism: repeated runs can differ even with identical input.
- External API availability and credential validity can block evaluation runs.
- No human inter-rater reliability baseline yet (single synthetic reference label per sample).
- Pronunciation is inferred from transcript-only input in this evaluation; no real audio evidence is provided.
- Small sample size (8 items) is useful for smoke-level reliability checks, not full psychometric validation.
