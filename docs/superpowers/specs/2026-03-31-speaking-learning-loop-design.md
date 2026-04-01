# Speaking Learning Loop Design

## Scope

This design covers GitHub issues #16, #17, and #18 for the IELTS-Practice speaking product:

- #16 Same-prompt retry comparison
- #17 Recurring weakness summaries
- #18 Answer-expansion coaching for short responses

The goal is to turn the current speaking history and scoring flow into a reusable learning loop without introducing a separate product surface in V1.

## Product goals

1. Let users compare two attempts on the same prompt and see what improved or regressed.
2. Show recurring weaknesses across recent speaking attempts, with actionable guidance.
3. When an answer is too short or underdeveloped, provide prompt-specific expansion coaching and a one-click retry path.
4. Make the first version work across all speaking attempts, including Part 2-only and full-exam speaking, with comparison/coaching attached to the individual answer or question rather than only the session.

## Non-goals

- Fuzzy semantic prompt matching in V1.
- A separate learning dashboard in V1.
- Broad frontend or backend refactors unrelated to the learning loop.
- Reprocessing all historical data perfectly before launch.

## User-approved product decisions

- Primary UX home: history detail first.
- Prompt matching: exact match as the base, with room for a future manual merge flow.
- Coaching source of truth: store structured tags and coaching data per attempt.
- V1 scope: all speaking attempts.
- Full-exam granularity: per answer/question, not session summary only.

## Current codebase constraints

### Backend

- Speaking data is stored in `PracticeSession` and `Recording`.
- `PracticeSession` holds speaking scores, overall score, status, timestamps, feedback JSON text, and sample answer.
- `Recording` holds per-answer data such as part, question index, question text, transcript, timestamps, duration, notes, and audio metadata.
- Official Part 2 topics have stable identity through `PracticeSession.topic_id`.
- Saved topics already have normalized prompt logic through `SavedTopic.normalized_prompt` and `services/saved_topic_service.py`.
- Custom prompts and most full-exam prompts are not currently normalized into a durable comparison key.
- Current feedback is parseable JSON text, but it is still largely prose and `key_improvements` text rather than normalized weakness codes.

### Frontend

- The history page (`frontend/history.html` + `frontend/history.js`) already owns the main progress UI and detail overlay.
- The speaking result screen (`frontend/speaking.html` + `frontend/speaking/scoring.js`) already renders scores, transcript tabs, feedback, improvements, and sample answer.
- Free-practice retry/setup already exists through `frontend/free-practice.js` and current speaking session state.
- There is no existing comparison or coaching surface in history detail beyond plain transcript/feedback rendering.

## Recommended architecture

Use the existing history page and speaking result page, but persist learning-loop metadata at the answer level on `Recording`.

This is the smallest safe design because:

- `Recording` is already the per-answer unit for Part 1, Part 2, and Part 3.
- Full-exam support requires answer-level identity and coaching.
- Storing learning metadata once during scoring makes later comparison and aggregation cheap and consistent.
- It avoids inventing a separate dashboard-only store that duplicates `Recording` data.

## Data model changes

Add nullable learning-loop fields to the speaking `Recording` model.

### Prompt identity fields

These fields create an exact-match comparison key for official, saved, custom, and exam-generated prompts.

- `prompt_match_type`
  - `official_topic`
  - `normalized_text`
- `prompt_match_key`
  - Example: `topic:123` for official topics
  - Otherwise a normalized text key derived from the actual prompt/question text
- `prompt_source`
  - `official`
  - `saved`
  - `custom`
  - `exam_generated`

The existing `question_text` field remains the user-facing label.

### Learning analysis fields

- `weakness_tags`
  - JSON array of normalized codes such as:
    - `answer_too_short`
    - `limited_examples`
    - `repetitive_connectors`
    - `tense_inconsistency`
    - `limited_vocabulary`
    - `weak_part3_reasoning`
- `coaching_payload`
  - JSON object with:
    - `expand_target_sentence`
    - `followup_angles[]`
    - `model_extension`
    - `retry_recommendation`
- `analysis_version`
  - Integer or string version to allow future logic upgrades without breaking older rows

These fields should remain nullable so old history still renders safely.

## Prompt identity rules

### Official topics

For official Part 2 topics, use the stable topic ID:

- `prompt_match_type = official_topic`
- `prompt_match_key = topic:<topic_id>`

### Saved and custom prompts

For saved/custom/free-practice prompts, use normalized prompt text:

- `prompt_match_type = normalized_text`
- `prompt_match_key = normalize_saved_topic_prompt(question_text)` or an equivalent shared normalizer

### Full-exam answers

For Part 1 and Part 3 answers, use the normalized per-question text already stored on `Recording.question_text`.

This keeps V1 exact and deterministic. A future manual-merge UI can later link related prompt keys without changing the base model.

## API design

Add dedicated read APIs for learning-loop features instead of overloading the current history payload too heavily.

### 1. Comparison API

`GET /api/speaking/comparisons/{recording_id}`

Returns:

- current recording snapshot
- latest previous exact-match recording for the same user and `prompt_match_key`
- score deltas
- transcript diff payload
- feedback/weakness follow-through summary
- attempt count for the exact-match group

Behavior:

- If no previous exact-match recording exists, return a no-comparison payload rather than an error.
- For full-exam sessions, the comparison is still attached to a single answer/recording.

### 2. Weakness summary API

`GET /api/speaking/weakness-summary?limit=N`

Returns:

- recent answer count used in aggregation
- top recurring weakness tags
- trend direction by score dimension
- actionable suggestions mapped from the top tags
- confidence/degradation label for small sample sizes

Behavior:

- 1–2 answers: early-signal messaging
- 3–4 answers: emerging-pattern messaging
- 5+: recurring-pattern messaging

### 3. History/detail payload extensions

Existing speaking history/detail endpoints should add lightweight fields such as:

- `has_retry_match`
- `attempt_count`
- `has_expansion_coaching`
- answer-level metadata for full-exam recordings so the frontend can render per-answer actions in detail view

This lets the history page show badges without forcing multiple extra requests up front.

## Generation and persistence flow

Learning metadata should be generated during speaking analysis rather than recomputed on every page load.

### During scoring/analysis

For each speaking answer:

1. compute `prompt_match_type`, `prompt_match_key`, and `prompt_source`
2. detect weakness tags from the structured scoring output and answer heuristics
3. if the answer is too short or underdeveloped, generate coaching payload
4. persist the answer-level learning snapshot on the corresponding `Recording`

### Why store instead of recompute

- recurring summaries become stable and cheap
- comparison can show historical “was this suggestion addressed?” results consistently
- retry coaching does not depend on re-running expensive generation during history viewing

## UI design

### History page (`#16`, `#17`, `#18` entry point)

Keep the history page as the main learning hub.

#### Session list enhancements

Each speaking history row can show:

- attempt count badge for exact-match groups
- small coaching hint if any answer in the session has expansion coaching

The row still opens the existing detail overlay.

#### Detail overlay enhancements

For speaking sessions, extend the current overlay with three new blocks below the existing score/feedback/transcript content:

1. **Compare with previous attempt**
   - visible when an exact previous match exists for the selected answer
2. **Recurring weaknesses**
   - summary of recent speaking answers for the user
3. **Expand this answer**
   - visible when the selected answer has coaching payload

### Full-exam detail behavior

Because V1 must support all speaking attempts, full-exam detail cannot stay purely session-level.

In the speaking detail overlay:

- list the individual recorded answers/questions
- let the user select an answer to inspect
- load comparison/coaching for that selected answer

This preserves session context while attaching learning-loop actions to a specific answer.

### Speaking result page bridge

The speaking result page should remain lightweight.

On `frontend/speaking/scoring.js`:

- if the just-scored answer has expansion coaching, show one compact coaching card
- include a `Try again with these ideas` button
- keep the deeper comparison and recurring-summary experience on history detail

This respects the user-approved “history detail first” decision while still making immediate coaching visible after scoring.

### Retry action

Retry should reuse the existing speaking/free-practice entry flow.

The retry button should:

- preselect official topics when the answer came from an official topic
- preselect saved topics when still available
- prefill custom prompts when the answer came from a custom prompt

Do not create a second session-start UI for V1.

## Feature behavior

### Issue #16 — same-prompt retry comparison

When a speaking answer has a previous exact-match answer:

- compare current answer against the latest previous answer for that prompt key
- show transcript diff
- show score deltas by dimension and overall
- show feedback changes
- show whether previous weakness tags/coaching targets were addressed, unchanged, or regressed

History should also surface a visible attempt count so users notice repeated prompt work before opening detail.

### Issue #17 — recurring weakness summaries

Aggregate the most recent N speaking answers for the user.

Compute:

- frequency of stored `weakness_tags`
- per-dimension trend direction from existing answer/session scores
- actionable guidance mapped from the dominant tags

Do not derive recurring weaknesses from raw prose alone in V1.

### Issue #18 — answer-expansion coaching

Trigger coaching when an answer is below configurable duration/word/depth thresholds.

Persist:

- the sentence or segment most worth expanding
- 2–3 prompt-specific follow-up angles
- a natural model extension
- retry guidance

Show:

- a compact coaching card immediately after scoring
- the full coaching block in history detail
- a one-click retry action in both places

## Graceful degradation and backwards compatibility

- Old speaking rows without learning-loop fields must still render normally.
- If a previous exact-match attempt does not exist, hide comparison UI.
- If coaching payload is missing, hide expansion UI.
- If there are too few attempts for a stable recurring summary, show a lighter “early signal” state instead of empty charts.

## Migration strategy

1. add nullable columns/JSON fields first
2. write new rows with learning metadata going forward
3. optionally backfill exact prompt keys where deterministic and cheap
4. do not block rollout on a full historical backfill

This keeps the feature safe for production and avoids a risky one-shot migration.

## Testing strategy

### Backend

- unit tests for prompt-key generation
- unit tests for weakness tag persistence and summary aggregation
- route tests for:
  - comparison payloads
  - no-previous-attempt behavior
  - weakness summary degradation behavior
  - coaching payload presence and retry metadata

### Frontend

- Playwright tests for:
  - attempt badges in history
  - comparison block in history detail
  - recurring weakness summary in history detail
  - coaching card on speaking result page
  - `Try again with these ideas` retry flow
  - full-exam detail with per-answer selection

## Recommended implementation order

1. answer-level persistence on `Recording`
2. prompt identity generation and exact-match grouping
3. comparison API + history-detail comparison UI (`#16`)
4. weakness summary API + history-detail summary UI (`#17`)
5. expansion coaching generation + result/detail retry bridge (`#18`)

## Why this order

- `#16` builds the exact-match foundation used by all three features
- `#17` depends on structured weakness tags being stored consistently
- `#18` reuses the same answer-level analysis path and retry plumbing

## Open future extension

A later phase can add user-driven manual merges of similar prompt groups without changing the exact-match baseline in V1. That future layer should sit above `prompt_match_key`, not replace it.
