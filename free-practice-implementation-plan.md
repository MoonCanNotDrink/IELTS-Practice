# Free Practice Implementation Plan

## Goal

Add a free-practice speaking mode where the user:

1. enters a custom prompt,
2. chooses a speaking countdown duration from presets or a custom value,
3. starts answering,
4. then goes through the existing transcription and scoring flow.

The UI should stay consistent with the current app style.

## Constraints

- Reuse the existing Part 2 upload and scoring pipeline.
- Keep changes minimal and avoid unrelated refactors.
- Avoid database schema changes unless they become strictly necessary.
- Preserve current full exam and Part 2 only behavior.

## Current Reuse Points

- Frontend state machine and Part 2 flow are in `frontend/app.js`.
- Main SPA structure is in `frontend/index.html`.
- Existing styles are in `frontend/index.css`.
- Part 2 session creation, upload, and scoring are in `backend/app/routes/part2.py`.
- History/detail fallbacks are in `backend/app/routes/scoring.py`.
- Existing Part 2 scoring already uses `Recording.question_text`, which can carry the free-practice prompt.

## Implementation Plan

### 1. Backend support for custom prompt sessions

- Extend Part 2 session creation to support either a seeded `topic_id` or a user-provided `custom_topic`.
- Keep `PracticeSession.topic_id` nullable and continue storing recordings as `part2`.
- During upload, use the custom prompt as the Part 2 `question_text` when the session has no seeded topic.

### 2. History and detail fallback for custom topics

- Update history/detail responses so completed free-practice sessions use the saved Part 2 `question_text` instead of showing `Unknown`.
- Keep returned scoring scope as `part2_only` so the existing results UI continues to work.
- Update Part 2 scoring to build `question_text` from the saved Part 2 recording when the session has no seeded `Topic`, so the scoring prompt still includes the custom free-practice topic.

### 3. Frontend free-practice entry flow

- Add a third mode on the home screen for free practice.
- Add a small form for:
  - custom prompt text,
  - preset duration options,
  - custom duration input.
- Validate that the prompt is filled in and that the custom duration is a positive number when selected.

### 4. Frontend Part 2 reuse

- Reuse the current Part 2 cue card, recording, upload, transcript, and scoring display flow.
- Represent the custom prompt in the same shape used by the topic card where possible.
- Make the speaking timer configurable instead of hardcoded to 120 seconds.

### 5. Testing and verification

- Add backend tests for custom session creation and history/detail fallback.
- Add a Playwright test that covers the free-practice UI path.
- Extend the static frontend Playwright test server in `tests/fixtures/static-frontend-server.cjs` so it can mock the new free-practice API requests instead of returning `401` for all `/api/*` routes.
- Run the exact verification commands below so the new backend tests are included alongside the existing suite.
- Manually verify the new path end-to-end with the app running locally.

#### QA Scenarios

- Backend contract: create a custom-topic Part 2 session, upload a Part 2 response, score it, then verify the score payload still reports `exam_scope: "part2_only"` and that history/detail return the custom prompt title.
- Frontend duration handling: verify preset duration selection updates the speaking timer target, and verify custom duration only starts when a positive number is entered.
- Playwright free-practice flow: load the SPA, choose free practice, enter a prompt, choose a duration, start the flow, submit a mocked recording, and assert the existing score view renders with the mocked transcript and scores.
- Regression checks: verify the existing Part 2 only and full exam Playwright specs still pass without changes in behavior.
- Manual QA: run the app locally, complete one free-practice attempt in the browser, and confirm the custom prompt appears on the score screen entry path and in history/detail views after completion.

### 6. Git delivery

- After verification passes, create a dedicated branch for the feature.
- Commit the tested changes with a focused message.
- Push the branch to the remote.

## Acceptance Criteria

- Users can start a free-practice attempt without drawing a random topic.
- Users can choose a preset duration or enter a custom duration.
- The speaking countdown uses the chosen duration.
- After answering, the app uses the existing transcription and scoring pipeline.
- Completed free-practice sessions show the custom prompt in history/detail views.
- Existing full exam and Part 2 only flows still pass tests.

## Verification Commands

- `cd backend && (python -m unittest test_tts_route test_free_practice_routes -v || python3 -m unittest test_tts_route test_free_practice_routes -v)`
- `npx playwright test`
- Manual browser QA against a locally running app for the free-practice flow with these expected results:
  - entering a custom prompt and valid duration starts the free-practice Part 2 path,
  - the speaking timer uses the chosen duration,
  - finishing recording reaches the existing score screen,
  - the completed session shows the custom prompt in home history and `/history` detail.
