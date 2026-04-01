# [Speaking Learning Loop] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

I'm using the writing-plans skill to create the implementation plan.

Goal: Implement answer-level learning metadata, exact-match prompt grouping, comparison API and UI, recurring weakness summary API and UI, and answer-expansion coaching with retry flow, covering issues #16, #17, #18.

Architecture: Persist learning-loop metadata on Recording. Generate metadata during scoring, store it on Recording, and expose lightweight read APIs. Frontend will fetch these APIs in history detail and on scoring result to render comparison, recurring weaknesses, and coaching. Keep changes minimal and additive.

Tech Stack: Python (FastAPI, SQLAlchemy), vanilla JS/HTML, unittest for backend route tests, Playwright for UI tests.

---

### Files to create or modify

- Modify: `backend/app/models.py` — add nullable learning-loop columns on Recording
- Add: `backend/app/services/speaking_learning_service.py` — prompt identity generator, weakness detector, coaching generator
- Modify: `backend/app/routes/part2.py` — call generator during Part 2 scoring and persist on Recording
- Modify: `backend/app/routes/scoring.py` — call generator during full-session scoring and persist per-answer Recording
- Add: `backend/app/routes/speaking_learning.py` — new read APIs:
  - `GET /api/speaking/comparisons/{recording_id}`
  - `GET /api/speaking/weakness-summary?limit=N`
- Modify: `backend/app/routes/part2.py` and `backend/app/routes/scoring.py` responses to include lightweight coaching metadata for immediate scoring response when present
- Modify: `backend/app/routes/helpers.py` — no change required, but reuse `get_part2_prompt_title` and `parse_feedback_blob` where needed
- Add tests: `backend/test_speaking_learning_routes.py` following existing unittest style
- Modify: `frontend/history.js` — show attempt-count badge in session list, call comparison/weakness endpoints in detail overlay, render new UI blocks
- Modify: `frontend/history.html` — minimal DOM hooks already present. No structural overhaul. Add small placeholder CSS classes are optional; prefer JS injection into the existing detail content
- Modify: `frontend/speaking/scoring.js` — show compact coaching card after scoring, wire `Try again with these ideas` button to prefill retry flow in free practice
- Add Playwright tests: `tests/history-comparison.spec.js`, `tests/history-weakness.spec.js`, `tests/speaking-coaching.spec.js`

Notes about scope: do not change public APIs except to add read endpoints and lightweight response fields. Do not perform any historical backfill. All DB fields must be nullable and backward compatible.

---

### Task 1: Add nullable learning-loop fields to Recording model

Files:
- Modify: `backend/app/models.py`

- [ ] Step 1: Update the Recording model with these new columns. Exact code to add inside the Recording class:

```python
# new columns to add in backend/app/models.py within class Recording
prompt_match_type = Column(String(50), nullable=True)  # 'official_topic' or 'normalized_text'
prompt_match_key = Column(String(255), nullable=True)   # e.g. 'topic:123' or normalized text key
prompt_source = Column(String(50), nullable=True)       # 'official', 'saved', 'custom', 'exam_generated'
weakness_tags = Column(JSON, nullable=True)             # JSON array of normalized codes
coaching_payload = Column(JSON, nullable=True)          # JSON object per spec
analysis_version = Column(String(20), nullable=True)    # allows future logic upgrades
```

Expected result: model file contains new nullable columns. No runtime behavior change until services call them. Database migration: these columns are nullable so adding columns in most DBs is safe without a dedicated migration step for V1. Test environments that create tables fresh will include columns in their schema.

- [ ] Step 2: Run lsp diagnostics on `backend/app/models.py` and ensure zero errors on that file. Command:

```
# run in repo root
# (for verification when implementing) run via toolchain as described in repo docs
python -m pip install -r requirements.txt  # if needed in dev environment
# then run language server diagnostics via CI or editor. For plan: note to run lsp_diagnostics on modified file
```

Expected: no lsp diagnostics errors in the edited file.

Commit checkpoint: commit with message `feat(speaking): persist learning-loop fields on Recording`.

---

### Task 2: New service for prompt identity, weakness detection, and coaching generation

Files:
- Add: `backend/app/services/speaking_learning_service.py`

Purpose: centralize logic for computing prompt_match_type, prompt_match_key, prompt_source, derive weakness_tags from scoring outputs and heuristics, and build coaching_payload when answer is underdeveloped. Reuse existing `normalize_saved_topic_prompt` from `saved_topic_service.py`.

- [ ] Step 1: Create `backend/app/services/speaking_learning_service.py` with these exported functions and exact behavior:

Code sketch (copy into new file):

```python
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Recording, PracticeSession, SavedTopic
from app.services.saved_topic_service import normalize_saved_topic_prompt

THRESHOLDS = {
    'min_duration_seconds': 30.0,
    'min_word_count': 40,
}

async def compute_prompt_identity(db: AsyncSession, recording: Recording) -> Dict[str, str]:
    """Return dict with prompt_match_type, prompt_match_key, prompt_source.

    Rules:
    - If the recording's session.topic_id is set, return official_topic/topic:<id>
    - Else if the recording.question_text matches a SavedTopic.normalized_prompt for the user, return normalized_text/<normalized> with source 'saved'
    - Else use normalized_text of recording.question_text with source 'custom'
    """
    # If recording belongs to a session with topic_id, prefer that stable id.
    session = recording.session
    if session and getattr(session, 'topic_id', None):
        return {
            'prompt_match_type': 'official_topic',
            'prompt_match_key': f'topic:{session.topic_id}',
            'prompt_source': 'official',
        }

    prompt_text = (recording.question_text or '').strip()
    normalized = normalize_saved_topic_prompt(prompt_text)

    # attempt to find a user-saved topic with the same normalized_prompt
    if session and session.user_id and normalized:
        result = await db.execute(
            select(SavedTopic).where(SavedTopic.user_id == session.user_id, SavedTopic.normalized_prompt == normalized)
        )
        saved = result.scalars().first()
        if saved:
            return {
                'prompt_match_type': 'normalized_text',
                'prompt_match_key': normalized,
                'prompt_source': 'saved',
            }

    # fallback to normalized text
    return {
        'prompt_match_type': 'normalized_text',
        'prompt_match_key': normalized or '',
        'prompt_source': 'custom',
    }


def detect_weakness_tags(score_result: Dict[str, Any], transcript: str, duration_seconds: float | None) -> List[str]:
    tags: List[str] = []
    # derive from structured scoring output if present
    if score_result:
        # example: low vocabulary score
        v = score_result.get('vocabulary_score')
        if v is not None and v < 5.0:
            tags.append('limited_vocabulary')
        g = score_result.get('grammar_score')
        if g is not None and g < 5.0:
            tags.append('tense_inconsistency')
    # heuristics for repetitive connectors could inspect transcript tokens; keep minimal
    if transcript and transcript.count('and') > 10:
        tags.append('repetitive_connectors')
    return tags


def build_coaching_payload(transcript: str, duration_seconds: float | None) -> Dict[str, Any] | None:
    word_count = len((transcript or '').split())
    too_short = (duration_seconds is not None and duration_seconds < THRESHOLDS['min_duration_seconds']) or (word_count < THRESHOLDS['min_word_count'])
    if not too_short:
        return None

    # pick the sentence to expand: choose the longest short sentence or first sentence
    sentences = [s.strip() for s in (transcript or '').split('.') if s.strip()]
    target = sentences[0] if sentences else (transcript or '')

    followups = [
        'Give an extra example that supports your main point.',
        'Add a personal experience related to this topic.',
    ]
    payload = {
        'expand_target_sentence': target[:400],
        'followup_angles': followups,
        'model_extension': f"Try adding one concrete example and one reason to support '{target[:80]}'",
        'retry_recommendation': 'Try again focusing on an example plus a reason. Aim for 40+ words.'
    }
    return payload
```

- [ ] Step 2: Run lsp diagnostics on the new file and ensure imports resolve. Expected: zero errors on new file.

Commit checkpoint: `feat(speaking): add speaking_learning_service`.

Rationale: centralizing logic avoids duplicating normalizer logic and keeps scoring routes minimal.

---

### Task 3: Persist learning metadata during scoring

Files to modify:
- `backend/app/routes/part2.py` in `score_session` after `score_result` is produced and before session and recording updates are committed
- `backend/app/routes/scoring.py` in `score_full_session` in the loop that handles recordings for full exam, persist per-answer metadata similarly

- [ ] Step 1: Import the new service into scoring routes and call it. Example insertion in `part2.score_session` just after LLM scoring and before setting session.status:

```python
# in backend/app/routes/part2.py near where score_result is available
from app.services.speaking_learning_service import (
    compute_prompt_identity,
    detect_weakness_tags,
    build_coaching_payload,
)

# after score_result returned and part2_recording exists:
identity = await compute_prompt_identity(db, part2_recording)
part2_recording.prompt_match_type = identity.get('prompt_match_type')
part2_recording.prompt_match_key = identity.get('prompt_match_key')
part2_recording.prompt_source = identity.get('prompt_source')

# compute weakness tags and coaching payload
weaknesses = detect_weakness_tags(score_result, part2_recording.transcript or '', part2_recording.duration_seconds)
part2_recording.weakness_tags = weaknesses or None
coaching = build_coaching_payload(part2_recording.transcript or '', part2_recording.duration_seconds)
part2_recording.coaching_payload = coaching or None
part2_recording.analysis_version = 'v1'

# ensure db session sees updates
db.add(part2_recording)
```

- [ ] Step 2: In `scoring.score_full_session`, after `score_result` is computed and `recordings` are present, update the Part 2 recording and any other per-answer recordings as needed. For full exam: scoring returns per-part transcripts in `transcripts` and the combined score in session.feedback. The plan keeps V1 scope by applying prompt identity and coaching to the per-answer Recording objects already present from earlier insertion:

```python
# in backend/app/routes/scoring.py after score_result and before session.status assignment
# for each recording in recordings:
for r in recordings:
    # compute identity using the individual recording row and session context
    identity = await compute_prompt_identity(db, r)
    r.prompt_match_type = identity.get('prompt_match_type')
    r.prompt_match_key = identity.get('prompt_match_key')
    r.prompt_source = identity.get('prompt_source')

    # For Part 2 only use LLM-derived tags from combined score_result and part-specific heuristics
    r.weakness_tags = detect_weakness_tags(score_result, r.transcript or '', r.duration_seconds) or None
    r.coaching_payload = build_coaching_payload(r.transcript or '', r.duration_seconds) or None
    r.analysis_version = 'v1'
    db.add(r)
```

- [ ] Step 3: Return lightweight coaching metadata in the scoring response when present. Update the existing return payloads to include optional `coaching` keys for the part2 recording or for the selected recording, for example:

```json
"coaching": { "recording_id": 123, "coaching_payload": {...} }
```

Expected result: After scoring, Recording rows include the learning metadata. No historical backfill required.

Commit checkpoint: `feat(speaking): persist learning metadata during scoring`.

---

### Task 4: New read APIs for comparison and weakness summary

Files to add:
- `backend/app/routes/speaking_learning.py`

APIs to implement exactly:
- `GET /api/speaking/comparisons/{recording_id}`
  - Behavior:
    - Ensure user ownership
    - Find latest previous exact-match recording for same user and prompt_match_key
    - If none, return payload indicating no comparison
    - Compute score deltas and transcript diff
    - Return attempt_count for the exact-match group
- `GET /api/speaking/weakness-summary?limit=N`
  - Behavior:
    - Query most recent N recordings for the current user
    - Aggregate `weakness_tags` frequency
    - Compute simple trend by comparing average scores across the same set
    - Map top tags to actionable suggestions

- [ ] Step 1: Implement `speaking_learning.py` using patterns in `part2.py` and `scoring.py`. Use `difflib` to build a line-based transcript diff. Example code sketch:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Recording, PracticeSession
from app.routes.helpers import assert_session_access
from app.services.speaking_learning_service import normalize_saved_topic_prompt  # if needed
import difflib

router = APIRouter(prefix='/api/speaking', tags=['Speaking Learning'])

@router.get('/comparisons/{recording_id}')
async def get_comparison(recording_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rec = await db.get(Recording, recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail='Recording not found')
    session = await db.get(PracticeSession, rec.session_id)
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail='No access')

    key = rec.prompt_match_key
    if not key:
        return { 'comparison': None, 'attempt_count': 1 }

    # find previous recording with same key and earlier created_at
    q = select(Recording).join(PracticeSession).where(
        PracticeSession.user_id == current_user.id,
        Recording.prompt_match_key == key,
        Recording.id != rec.id,
    ).order_by(Recording.created_at.desc()).limit(1)
    prev = (await db.execute(q)).scalars().first()

    if not prev:
        # compute attempt count
        count_q = select(func.count()).select_from(Recording).join(PracticeSession).where(
            PracticeSession.user_id == current_user.id,
            Recording.prompt_match_key == key
        )
        attempt_count = (await db.execute(count_q)).scalar_one()
        return { 'comparison': None, 'attempt_count': attempt_count }

    # compute score deltas by loading their sessions
    cur_session = await db.get(PracticeSession, rec.session_id)
    prev_session = await db.get(PracticeSession, prev.session_id)
    deltas = {
        'overall': (cur_session.overall_score or 0) - (prev_session.overall_score or 0),
        'fluency': (cur_session.fluency_score or 0) - (prev_session.fluency_score or 0),
    }

    # transcript diff
    from difflib import ndiff
    diff_lines = list(ndiff((prev.transcript or '').splitlines(), (rec.transcript or '').splitlines()))

    return {
        'comparison': {
            'current': { 'recording_id': rec.id, 'transcript': rec.transcript },
            'previous': { 'recording_id': prev.id, 'transcript': prev.transcript },
            'deltas': deltas,
            'transcript_diff': diff_lines,
            'previous_weakness_tags': prev.weakness_tags or [],
            'current_weakness_tags': rec.weakness_tags or [],
        },
        'attempt_count': attempt_count,
    }
```

- [ ] Step 2: Implement weakness-summary endpoint that aggregates frequency and maps tags to actionable suggestions. Use simple mapping dict in route file.

Expected result: lightweight read APIs available for frontend wiring.

Commit checkpoint: `feat(speaking): add comparison and weakness-summary read APIs`.

---

### Task 5: Expose small metadata in history and session detail endpoints

Files to modify:
- `backend/app/routes/part2.py` -> `get_history`
- `backend/app/routes/scoring.py` -> `get_history`, `get_session_detail`

Goal: add fields `has_retry_match`, `attempt_count`, `has_expansion_coaching` to history rows and session detail payload so frontend can show badges without heavy extra requests.

- [ ] Step 1: For each history row construction, query the representative Part 2 recording for the session and compute attempt_count for its prompt_match_key, and coaching presence.

Example snippet in `part2.get_history` when building history entry for session `s`:

```python
# find primary part2 recording for session s
rec_res = await db.execute(select(Recording).where(Recording.session_id == s.id, Recording.part == 'part2').limit(1))
rec = rec_res.scalars().first()
attempt_count = 1
has_retry_match = False
has_expansion_coaching = False
if rec and rec.prompt_match_key:
    cnt_q = select(func.count()).select_from(Recording).join(PracticeSession).where(PracticeSession.user_id == s.user_id, Recording.prompt_match_key == rec.prompt_match_key)
    attempt_count = (await db.execute(cnt_q)).scalar_one() or 1
    has_retry_match = attempt_count > 1
    has_expansion_coaching = bool(rec.coaching_payload)

# include into history row
history.append({
    ...,
    'has_retry_match': has_retry_match,
    'attempt_count': attempt_count,
    'has_expansion_coaching': has_expansion_coaching,
})
```

- [ ] Step 2: In `scoring.get_session_detail` include per-answer metadata: map recordings to arrays with their recording.id, part, prompt_match_key, attempt_count and coaching presence so frontend can select specific answer inside a full-exam session and then call comparison API for that recording.

Commit checkpoint: `feat(speaking): expose learning metadata in history and session detail`.

---

### Task 6: Frontend UI wiring

Files to modify:
- `frontend/history.js` — session list badge and detail overlay blocks
- `frontend/speaking/scoring.js` — showing compact coaching card after scoring

Principles: minimal DOM changes. Reuse detail overlay content insertion used by `viewSessionDetail` in `history.js`. Inject new blocks at the end of the main detail HTML.

- [ ] Step 1: Show attempt badge in session list

Change in `renderSessionList` inside `frontend/history.js` where HTML for each session is built. Insert attempt count badge next to title when `session.attempt_count` > 1. Example snippet to inject into the session title area:

```js
// near title rendering
const attemptBadge = session.attempt_count && session.attempt_count > 1 ? `<span class="attempt-badge">${session.attempt_count}</span>` : '';
// then include ${attemptBadge} next to title
```

- [ ] Step 2: On session detail load, after constructing main HTML, issue the comparison and weakness-summary requests for the selected recording if applicable, then append three blocks below the existing content: Compare with previous attempt, Recurring weaknesses, Expand this answer.

Add helper functions in `frontend/history.js`:

```js
async function loadComparison(recordingId) {
  const token = localStorage.getItem('ielts_token');
  const res = await fetch(`/api/speaking/comparisons/${recordingId}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) return null;
  return await res.json();
}

function renderComparisonBlock(comparison) {
  if (!comparison || !comparison.comparison) return '';
  // build small diff viewer from comparison.transcript_diff
}

async function loadWeaknessSummary(limit=10) {
  const token = localStorage.getItem('ielts_token');
  const res = await fetch(`/api/speaking/weakness-summary?limit=${limit}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) return null;
  return await res.json();
}

function renderWeaknessBlock(summary) { ... }

function renderCoachingBlock(coaching) { ... }
```

Implementation details:
- Place blocks below transcript and sample answer. Use small cards consistent with existing CSS.
- The 'Try again with these ideas' button should call the existing free-practice start flow. For V1, call `startFreePractice` by programmatically creating a session via `/api/part2/sessions` then redirect to the speaking flow UI. Prefer to reuse client code already used by `startFreePractice` in `free-practice.js`. If that is not directly callable, use the API contract `POST /api/part2/sessions` with payload selecting `topic_id` or `custom_topic` depending on rec.prompt_source, then navigate to the exam flow UI.

- [ ] Step 3: On speaking result page (`frontend/speaking/scoring.js`) show compact coaching card when `result.coaching` exists. Insert small card UI into the feedback area and attach retry button to prefill the free practice session using the same logic described above. Example snippet to add near the top of `displayResults`:

```js
if (result.coaching && result.coaching.coaching_payload) {
  const c = result.coaching.coaching_payload;
  const card = `<div class="coaching-card">...<button onclick="retryWithCoaching(${result.coaching.recording_id})">Try again with these ideas</button></div>`;
  document.getElementById('feedbackSection').insertAdjacentHTML('afterbegin', card);
}

window.retryWithCoaching = async function(recordingId) {
  // fetch recording detail or use session.topic info to call /api/part2/sessions
}
```

Commit checkpoint: `feat(ui): history detail comparison, weaknesses, and coaching card`.

---

### Task 7: Backend unit tests

Files to add:
- `backend/test_speaking_learning_routes.py`

Tests to include exactly and follow existing unittest/TestClient style used in `backend/test_free_practice_routes.py`:

- test_prompt_identity_generation: create a PracticeSession with topic_id and Recording, call compute_prompt_identity and assert `topic:<id>` key
- test_comparison_api_no_previous: create a single recording with prompt key, call `GET /api/speaking/comparisons/{recording_id}` and assert comparison is None and attempt_count==1
- test_comparison_api_with_previous: create two recordings for same normalized prompt for same user, call API for second and assert comparison.previous exists and deltas keys present
- test_weakness_summary_degradation_behavior: create 1, then 3, then 6 recordings with various weakness_tags and assert API returns early-signal vs recurring-pattern text
- test_coaching_payload_persisted_on_score: simulate scoring route by patching `score_speaking` to return a low-word answer, call `/api/part2/sessions/{id}/score`, then query DB recording row and assert `coaching_payload` is not None

Each test should mirror the existing test harness pattern in backend/test_free_practice_routes.py: create temp DB, override dependencies, patch external services, use TestClient. Include code snippets in the test file.

Commands to run tests locally:

```
# from repo root
corepack pnpm install
corepack pnpm test
# or for python-only tests
python -m pytest backend/test_speaking_learning_routes.py -q
```

Expected: new backend unit tests pass. If linter or style checks fail, address minimal issues.

Commit checkpoint: `test(speaking): add tests for comparison, weaknesses, coaching`.

---

### Task 8: Playwright UI tests

Files to add:
- `tests/history-comparison.spec.js`
- `tests/history-weakness.spec.js`
- `tests/speaking-coaching.spec.js`

Design tests similar to existing Playwright specs in `tests/`.
Each test should:
- Seed minimal server state via backend unit test helpers or by driving the UI through mocked APIs (preferred for isolation). For V1 prefer blackbox e2e: use UI flows to create sessions and score them with patched server responses where the test harness supports it.
- Verify: session list shows attempt badge, detail overlay shows comparison block for same-prompt, weakness block for aggregated tags, coaching card on scoring page and retry bridge works.

Example Playwright assertion in `history-comparison.spec.js`:

```js
// navigate to /history
// find session row for test prompt
// click to open detail overlay
// expect comparison block text to contain 'Improved' or score delta
```

Commands to run Playwright tests:

```
corepack pnpm install
corepack pnpm test:playwright
```

Expected: UI tests for new features pass. If they are flaky, keep tests focused and deterministic by patching backend responses or seeding DB in test setup.

Commit checkpoint: `test(ui): add Playwright tests for history comparison, weaknesses, and coaching`.

---

### Task 9: Verification checklist to run after each implementation step

For every code change:
- [ ] Run lsp_diagnostics on modified files, zero errors.
- [ ] Run backend unit tests related to modified files. Use unittest or pytest according to repo convention. All tests pass.
- [ ] Run Playwright tests for frontend changes when UI is updated. All tests pass.
- [ ] Manual smoke: start dev server and verify history page loads and detail overlay shows new blocks when data present.

Commands summary:

```
# run unit tests
corepack pnpm test

# run only backend python tests
python -m pytest backend/test_speaking_learning_routes.py -q

# run Playwright tests
corepack pnpm test:playwright
```

Expected final state: All modified files have zero LSP diagnostics, backend unit tests pass, Playwright tests for modified flows pass.

---

### Migration and rollout notes

- Columns are nullable. No destructive migration required.
- Backfill is optional. V1 ships writing new rows only. Backfill can be done later in a safe script that computes prompt keys where deterministic.
- Keep analysis_version = 'v1' on rows produced by this code. Change version when logic changes in future.

---

## Spec coverage self-review

1. Answer-level persistence on Recording: covered in Task 1 and Task 3.
2. Prompt identity generation and exact-match grouping: covered in Task 2 and Task 3, with normalization using existing saved_topic_service.
3. Comparison API and history-detail comparison UI: covered in Task 4 and Task 6.
4. Weakness summary API/UI: covered in Task 4 and Task 6.
5. Expansion coaching generation and retry bridge: covered in Task 2, Task 3, and Task 6.

Gaps: none. All items requested in the approved design doc are mapped to concrete files and tasks.

---

I will now mark the plan creation task completed.
